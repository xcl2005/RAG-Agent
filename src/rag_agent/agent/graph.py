"""Bounded, durable Agentic RAG workflow.

The graph mixes deterministic controls with two constrained model decisions:
query planning and grounded answer generation. It never performs unbounded
"reflection". Retrieval retries and citation repair both have explicit limits.

Graph:
    initialize -> plan_queries -> retrieve -> grade_evidence
       -> sufficient: generate -> validate_citations -> [repair once] -> finalize
       -> weak: retry plan/retrieve (bounded) -> abstain -> finalize
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from rag_agent.agent.guardrails import sanitize_question, validate_citations
from rag_agent.agent.prompts import (
    ABSTAIN_MESSAGE,
    ANSWER_INSTRUCTIONS,
    REPAIR_INSTRUCTIONS,
    REPAIR_PROMPT,
    build_context,
    render_answer_prompt,
    source_list,
)
from rag_agent.config import Settings, settings
from rag_agent.llm.client import LLMClient, LLMRequestError
from rag_agent.retrieval.hybrid import HybridRetriever
from rag_agent.schemas import Candidate, EvidenceAssessment


class AgentState(TypedDict, total=False):
    """JSON/checkpoint-friendly state passed between LangGraph nodes."""

    question: str
    thread_id: str
    trace_id: str
    history: list[dict[str, str]]
    search_queries: list[str]
    query_strategy: str
    retrieval_attempts: int
    candidates: list[dict[str, Any]]
    evidence: dict[str, Any]
    context: str
    answer: str
    sources: list[dict[str, Any]]
    abstained: bool
    confidence: float
    citation_report: dict[str, Any]
    repair_attempts: int
    events: list[dict[str, Any]]
    llm_calls: list[dict[str, Any]]
    error: str | None


def _candidates(state: AgentState) -> list[Candidate]:
    return [Candidate.from_dict(value) for value in state.get("candidates", [])]


def _event(
    state: AgentState,
    node: str,
    started: float,
    **details: Any,
) -> list[dict[str, Any]]:
    """Append an observable node event without exposing chain-of-thought."""

    return [
        *state.get("events", []),
        {
            "node": node,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            **details,
        },
    ]


class RAGAgent:
    """Adaptive RAG service with dependency injection for deterministic tests."""

    def __init__(
        self,
        app_settings: Settings = settings,
        *,
        llm: LLMClient | None = None,
        retriever: HybridRetriever | None = None,
        checkpointer: Any | None = None,
    ):
        self.settings = app_settings
        self.llm = llm or LLMClient(app_settings)
        self.retriever = retriever or HybridRetriever(app_settings)
        self._owns_retriever = retriever is None
        self._checkpoint_connection: sqlite3.Connection | None = None
        self._thread_locks_guard = threading.Lock()
        self._thread_locks: dict[str, tuple[threading.Lock, int]] = {}

        if checkpointer is None:
            Path(app_settings.checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
            self._checkpoint_connection = sqlite3.connect(
                app_settings.checkpoint_path,
                check_same_thread=False,
            )
            checkpointer = SqliteSaver(self._checkpoint_connection)
            checkpointer.setup()

        self.graph = self._build_graph(checkpointer)

    @contextmanager
    def _thread_singleflight(self, thread_id: str) -> Iterator[None]:
        """Serialize invocations sharing one durable conversation ID.

        LangGraph checkpoints are keyed by ``thread_id``. Without this guard,
        two simultaneous requests can both read the same prior state, overwrite
        history, or make a stream read the other request's final checkpoint.
        Reference counting removes idle locks so arbitrary IDs do not leak
        memory. This is a single-process guarantee; a multi-worker deployment
        needs a distributed lock or optimistic checkpoint versioning.
        """

        with self._thread_locks_guard:
            lock, users = self._thread_locks.get(thread_id, (threading.Lock(), 0))
            self._thread_locks[thread_id] = (lock, users + 1)

        lock.acquire()
        try:
            yield
        finally:
            lock.release()
            with self._thread_locks_guard:
                current_lock, current_users = self._thread_locks[thread_id]
                if current_users == 1:
                    del self._thread_locks[thread_id]
                else:
                    self._thread_locks[thread_id] = (current_lock, current_users - 1)

    def _build_graph(self, checkpointer: Any) -> Any:
        workflow = StateGraph(AgentState)
        workflow.add_node("initialize", self.initialize)
        workflow.add_node("plan_queries", self.plan_queries)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_evidence", self.grade_evidence)
        workflow.add_node("generate_answer", self.generate_answer)
        workflow.add_node("validate_citations", self.validate_answer_citations)
        workflow.add_node("repair_citations", self.repair_citations)
        workflow.add_node("abstain", self.abstain)
        workflow.add_node("citation_failure", self.citation_failure)
        workflow.add_node("finalize", self.finalize)

        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "plan_queries")
        workflow.add_edge("plan_queries", "retrieve")
        workflow.add_edge("retrieve", "grade_evidence")
        workflow.add_conditional_edges(
            "grade_evidence",
            self.route_after_evidence,
            {
                "retry": "plan_queries",
                "answer": "generate_answer",
                "abstain": "abstain",
            },
        )
        workflow.add_edge("generate_answer", "validate_citations")
        workflow.add_conditional_edges(
            "validate_citations",
            self.route_after_citation_validation,
            {
                "repair": "repair_citations",
                "finish": "finalize",
                "fail": "citation_failure",
            },
        )
        workflow.add_edge("repair_citations", "validate_citations")
        workflow.add_edge("abstain", "finalize")
        workflow.add_edge("citation_failure", "finalize")
        workflow.add_edge("finalize", END)
        return workflow.compile(checkpointer=checkpointer)

    # ------------------------------------------------------------------
    # Graph nodes
    # ------------------------------------------------------------------
    def initialize(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        question = sanitize_question(state["question"], self.settings.max_question_chars)
        history = state.get("history", [])[-6:]
        return {
            "question": question,
            "history": history,
            "search_queries": [],
            "query_strategy": "",
            "retrieval_attempts": 0,
            "candidates": [],
            "evidence": {},
            "context": "",
            "answer": "",
            "sources": [],
            "abstained": False,
            "confidence": 0.0,
            "citation_report": {},
            "repair_attempts": 0,
            "events": _event({}, "initialize", started, history_turns=len(history)),
            "llm_calls": [],
            "error": None,
        }

    def plan_queries(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        attempt = state.get("retrieval_attempts", 0) + 1
        question = state["question"]
        queries = [question]
        strategy = "original_query"
        llm_calls = state.get("llm_calls", [])
        error: str | None = None

        if self.llm.enabled:
            try:
                plan, call = self.llm.plan_queries(
                    question,
                    history=state.get("history", []),
                    attempt=attempt,
                    max_variants=self.settings.max_query_variants,
                )
                # 原始问题永远保留在第一位，避免改写丢失错误码、编号和专有名词。
                queries = list(dict.fromkeys([question, *plan.search_queries]))
                queries = queries[: self.settings.max_query_variants]
                strategy = plan.strategy
                llm_calls = [*llm_calls, {"purpose": "query_plan", **call.usage_dict()}]
            except LLMRequestError as exc:
                error = str(exc)
                strategy = "original_query_fallback"

        return {
            "retrieval_attempts": attempt,
            "search_queries": queries,
            "query_strategy": strategy,
            "llm_calls": llm_calls,
            "error": error,
            "events": _event(
                state,
                "plan_queries",
                started,
                attempt=attempt,
                query_count=len(queries),
                strategy=strategy,
                fallback=bool(error),
            ),
        }

    def retrieve(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        if hasattr(self.retriever, "retrieve_many_with_debug"):
            candidates, retrieval_debug = self.retriever.retrieve_many_with_debug(
                state["search_queries"],
                rerank_query=state["question"],
            )
        else:  # Small injected test doubles may implement only the list API.
            candidates = self.retriever.retrieve_many(
                state["search_queries"],
                rerank_query=state["question"],
            )
            retrieval_debug = dict(getattr(self.retriever, "last_debug", {}))
        return {
            "candidates": [candidate.to_dict() for candidate in candidates],
            "events": _event(
                state,
                "retrieve",
                started,
                candidate_count=len(candidates),
                debug=retrieval_debug,
            ),
        }

    def grade_evidence(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        candidates = _candidates(state)
        if not candidates:
            assessment = EvidenceAssessment(
                sufficient=False,
                best_score=0.0,
                score_kind="none",
                candidate_count=0,
                source_count=0,
                reason="no retrievable candidate resolved to source text",
            )
        else:
            uses_reranker = candidates[0].rerank_score is not None
            if uses_reranker:
                best_score = candidates[0].score
                score_kind = "reranker_normalized"
                threshold_description = f"reranker>={self.settings.min_rerank_relevance:.3f}"
                sufficient = best_score >= self.settings.min_rerank_relevance
            else:
                # RRF is rank-only: with one non-empty backend its first result
                # is always 1.0, regardless of semantic relevance. Gate on
                # absolute dense cosine or lexical token coverage instead.
                best_dense = max(
                    (candidate.dense_score for candidate in candidates if candidate.dense_score is not None),
                    default=-1.0,
                )
                best_sparse = max(
                    (
                        candidate.sparse_score
                        for candidate in candidates
                        if candidate.sparse_score is not None
                    ),
                    default=0.0,
                )
                sufficient = (
                    best_dense >= self.settings.min_dense_relevance
                    or best_sparse >= self.settings.min_sparse_coverage
                )
                if best_dense >= self.settings.min_dense_relevance:
                    best_score = min(max(best_dense, 0.0), 1.0)
                    score_kind = "dense_cosine"
                else:
                    best_score = best_sparse
                    score_kind = "sparse_token_coverage"
                threshold_description = (
                    f"dense>={self.settings.min_dense_relevance:.3f} OR "
                    f"sparse>={self.settings.min_sparse_coverage:.3f}"
                )
            assessment = EvidenceAssessment(
                sufficient=sufficient,
                best_score=best_score,
                score_kind=score_kind,
                candidate_count=len(candidates),
                source_count=len({str(candidate.metadata.get("source", "")) for candidate in candidates}),
                reason=(
                    f"best {score_kind} signal {best_score:.3f}; "
                    f"gate={threshold_description}; sufficient={sufficient}"
                ),
            )

        value = assessment.to_dict()
        return {
            "evidence": value,
            "events": _event(state, "grade_evidence", started, **value),
        }

    def route_after_evidence(self, state: AgentState) -> str:
        if state.get("evidence", {}).get("sufficient"):
            return "answer"
        if state.get("retrieval_attempts", 0) < self.settings.max_retrieval_attempts:
            return "retry"
        return "abstain"

    def generate_answer(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        bundle = build_context(_candidates(state), self.settings.max_context_chars)
        sources = source_list(bundle.candidates)
        llm_calls = state.get("llm_calls", [])

        if not bundle.candidates or not bundle.text:
            return {
                "answer": ABSTAIN_MESSAGE,
                "sources": [],
                "context": "",
                "abstained": True,
                "error": "empty_context_after_budgeting",
                "events": _event(
                    state,
                    "generate_answer",
                    started,
                    context_chars=0,
                    source_count=0,
                    model_called=False,
                ),
            }

        if not self.llm.enabled:
            return {
                "answer": ("已检索到相关资料，但当前未配置 OPENAI_API_KEY，因此没有调用模型生成最终答案。"),
                "sources": sources,
                "context": bundle.text,
                "abstained": True,
                "error": "llm_not_configured",
                "events": _event(
                    state,
                    "generate_answer",
                    started,
                    context_chars=bundle.character_count,
                    source_count=len(sources),
                    model_called=False,
                ),
            }

        try:
            call = self.llm.generate(
                ANSWER_INSTRUCTIONS,
                render_answer_prompt(state["question"], bundle.text),
            )
            llm_calls = [*llm_calls, {"purpose": "answer", **call.usage_dict()}]
            return {
                "answer": call.text.strip(),
                "sources": sources,
                "context": bundle.text,
                "llm_calls": llm_calls,
                "events": _event(
                    state,
                    "generate_answer",
                    started,
                    context_chars=bundle.character_count,
                    context_truncated=bundle.truncated,
                    source_count=len(sources),
                    model_called=True,
                ),
            }
        except LLMRequestError as exc:
            return {
                "answer": "模型服务暂时不可用，无法生成可靠答案。",
                "sources": sources,
                "context": bundle.text,
                "abstained": True,
                "error": str(exc),
                "events": _event(
                    state,
                    "generate_answer",
                    started,
                    source_count=len(sources),
                    model_called=True,
                    failed=True,
                ),
            }

    def validate_answer_citations(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        report = validate_citations(
            state.get("answer", ""),
            len(state.get("sources", [])),
            abstained=state.get("abstained", False),
        )
        value = report.to_dict()
        return {
            "citation_report": value,
            "events": _event(state, "validate_citations", started, **value),
        }

    def route_after_citation_validation(self, state: AgentState) -> str:
        if state.get("citation_report", {}).get("valid"):
            return "finish"
        if self.llm.enabled and state.get("repair_attempts", 0) < 1:
            return "repair"
        return "fail"

    def repair_citations(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        attempts = state.get("repair_attempts", 0) + 1
        llm_calls = state.get("llm_calls", [])
        try:
            call = self.llm.generate(
                REPAIR_INSTRUCTIONS,
                REPAIR_PROMPT.format(
                    answer=state.get("answer", ""),
                    reason=state.get("citation_report", {}).get("reason", "invalid citation"),
                    context=state.get("context", ""),
                ),
                max_output_tokens=self.settings.max_repair_output_tokens,
            )
            llm_calls = [*llm_calls, {"purpose": "citation_repair", **call.usage_dict()}]
            return {
                "answer": call.text.strip(),
                "repair_attempts": attempts,
                "llm_calls": llm_calls,
                "events": _event(state, "repair_citations", started, attempt=attempts),
            }
        except LLMRequestError as exc:
            return {
                "answer": ABSTAIN_MESSAGE,
                "abstained": True,
                "repair_attempts": attempts,
                "error": str(exc),
                "events": _event(
                    state,
                    "repair_citations",
                    started,
                    attempt=attempts,
                    failed=True,
                ),
            }

    def abstain(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        return {
            "answer": ABSTAIN_MESSAGE,
            # Low-relevance candidates are not evidence. Returning their raw
            # path/quote here would turn abstention into a document-exfiltration
            # endpoint for repeated unrelated queries.
            "sources": [],
            "abstained": True,
            "citation_report": {
                "valid": True,
                "cited_ids": [],
                "invalid_ids": [],
                "reason": "abstention does not require citations",
            },
            "events": _event(
                state,
                "abstain",
                started,
                attempts=state.get("retrieval_attempts", 0),
            ),
        }

    def citation_failure(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        return {
            "answer": ABSTAIN_MESSAGE,
            "sources": [],
            "abstained": True,
            "confidence": 0.0,
            "events": _event(
                state,
                "citation_failure",
                started,
                reason=state.get("citation_report", {}).get("reason"),
            ),
        }

    def finalize(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        citation_valid = bool(state.get("citation_report", {}).get("valid", False))
        sufficient = bool(state.get("evidence", {}).get("sufficient", False))
        confidence = (
            float(state.get("evidence", {}).get("best_score", 0.0))
            if citation_valid and sufficient and not state.get("abstained", False)
            else 0.0
        )
        history = [
            *state.get("history", []),
            {
                "question": state["question"][:1000],
                "answer": state.get("answer", "")[:3000],
            },
        ][-6:]
        return {
            "confidence": round(confidence, 4),
            "history": history,
            "events": _event(
                state,
                "finalize",
                started,
                confidence=round(confidence, 4),
                abstained=state.get("abstained", False),
            ),
        }

    # ------------------------------------------------------------------
    # Public service API
    # ------------------------------------------------------------------
    @staticmethod
    def _result(state: AgentState, *, include_trace: bool) -> dict[str, Any]:
        calls = state.get("llm_calls", [])
        abstained = bool(state.get("abstained", False))
        value: dict[str, Any] = {
            "question": state["question"],
            "thread_id": state["thread_id"],
            "trace_id": state["trace_id"],
            "status": "abstained" if abstained else "answered",
            "answer": state.get("answer", ""),
            "abstained": abstained,
            "confidence": float(state.get("confidence", 0.0)),
            "query": (state.get("search_queries") or [state["question"]])[0],
            "queries": state.get("search_queries", []),
            # Defense in depth for model-error and repair-error branches that
            # may have populated sources before deciding to abstain.
            "sources": [] if abstained else state.get("sources", []),
            "evidence": state.get("evidence", {}),
            "citation_validation": state.get("citation_report", {}),
            "usage": {
                "model_calls": len(calls),
                "input_tokens": sum(int(call.get("input_tokens", 0)) for call in calls),
                "output_tokens": sum(int(call.get("output_tokens", 0)) for call in calls),
            },
            "error": state.get("error"),
        }
        if include_trace:
            value["trace"] = state.get("events", [])
            value["model_calls"] = calls
        return value

    def ask(
        self,
        question: str,
        *,
        thread_id: str | None = None,
        include_trace: bool = True,
    ) -> dict[str, Any]:
        thread = thread_id or str(uuid.uuid4())
        trace = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread}}
        with self._thread_singleflight(thread):
            result: AgentState = self.graph.invoke(
                {
                    "question": question,
                    "thread_id": thread,
                    "trace_id": trace,
                },
                config=config,
            )
        return self._result(result, include_trace=include_trace)

    def stream(
        self,
        question: str,
        *,
        thread_id: str | None = None,
        include_trace: bool = True,
    ) -> Iterator[dict[str, Any]]:
        """Yield node-completion events followed by one final answer event."""

        thread = thread_id or str(uuid.uuid4())
        trace = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread}}
        inputs = {"question": question, "thread_id": thread, "trace_id": trace}

        # Keep the lock until the caller consumes the final event. This closes
        # the race between graph completion and graph.get_state().
        with self._thread_singleflight(thread):
            for update in self.graph.stream(inputs, config=config, stream_mode="updates"):
                for node, patch in update.items():
                    latest_event = (patch.get("events") or [{}])[-1]
                    yield {
                        "event": "node",
                        "node": node,
                        "trace_id": trace,
                        "data": latest_event,
                    }

            snapshot = self.graph.get_state(config)
            final_state: AgentState = snapshot.values
            if final_state.get("trace_id") != trace:
                # Defensive check for unsupported multi-process deployments.
                raise RuntimeError("checkpoint trace changed during stream finalization")
            yield {
                "event": "final",
                "trace_id": trace,
                "data": self._result(final_state, include_trace=include_trace),
            }

    def ready(self) -> dict[str, dict[str, str | bool]]:
        return self.retriever.ready()

    def close(self) -> None:
        if self._owns_retriever:
            self.retriever.close()
        if self._checkpoint_connection is not None:
            self._checkpoint_connection.close()
