"""Bounded, durable Agentic RAG workflow.

The graph mixes deterministic controls with two constrained model decisions:
query planning and grounded answer generation. It never performs unbounded
"reflection". Retrieval retries and citation repair both have explicit limits.

Graph:
    initialize -> plan_queries -> retrieve -> grade_evidence
       -> sufficient: prepare_context -> generate -> validate_citations -> [repair once] -> finalize
       -> weak: retry plan/retrieve (bounded) -> abstain -> finalize
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
import unicodedata
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
    CITATION_FAILURE_MESSAGE,
    GENERATION_FAILURE_MESSAGE,
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
    context_stats: dict[str, Any]
    answer: str
    sources: list[dict[str, Any]]
    abstained: bool
    confidence: float
    citation_report: dict[str, Any]
    repair_attempts: int
    events: list[dict[str, Any]]
    llm_calls: list[dict[str, Any]]
    failure_kind: str | None
    error: str | None


def _candidates(state: AgentState) -> list[Candidate]:
    return [Candidate.from_dict(value) for value in state.get("candidates", [])]


def _query_key(query: str) -> str:
    """Return a stable key for retry-level query de-duplication."""

    normalized = unicodedata.normalize("NFKC", query).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def deterministic_query_variants(
    question: str,
    *,
    max_variants: int = 6,
) -> list[str]:
    """Build bounded Chinese/English retrieval fallbacks without an LLM.

    Portfolio questions frequently wrap the real intent in phrases such as
    “目前上传的资料里” or an owner hint such as “我（name）的”. Those tokens
    can dominate a cross-lingual query even though the documents describe
    projects, papers, or internships without repeating the owner name.
    The variants below remove only those container phrases and expand a small,
    explicit set of list intents. They do not invent facts or entities.
    """

    normalized = unicodedata.normalize("NFKC", question)
    focused = re.sub(r"(?:我|本人)\s*\([^()]{1,80}\)\s*的?", " ", normalized)
    focused = re.sub(
        r"(?:目前|当前)?(?:已|所)?上传的?(?:资料|文档)(?:里|中|库中)?",
        " ",
        focused,
    )
    focused = re.sub(r"(?:根据|结合)(?:当前|现有|上述)?(?:资料|文档)", " ", focused)
    focused = focused.replace("与申请专业相关的", " ")
    focused = re.sub(r"^(?:请问|请|帮我|请帮我|告诉我|列出|总结)\s*", "", focused)
    focused = re.sub(r"(?:都)?有哪些(?:呢)?[?？。.\s]*$", "", focused)
    focused = re.sub(r"[,，、;；|/]+", " ", focused)
    focused = re.sub(r"\s+", " ", focused).strip(" 的:：?？。")

    lowered = normalized.casefold()
    chinese_terms: list[str] = []
    english_terms: list[str] = []
    intent_groups = (
        (
            ("项目", "科研", "实验"),
            ("项目", "项目经历", "课程项目", "科研项目", "学术项目", "科研实验"),
            ("project", "research", "academic project"),
        ),
        (
            ("论文", "发表", "研究成果"),
            ("论文", "课程论文", "学术论文", "研究成果", "发表"),
            ("paper", "publication", "research"),
        ),
        (
            ("实习", "工作经历", "就业经历"),
            ("实习", "实习经历", "工作经历", "任职经历"),
            ("internship", "work experience", "employment"),
        ),
    )
    for triggers, zh_aliases, en_aliases in intent_groups:
        if any(trigger.casefold() in lowered for trigger in triggers):
            chinese_terms.extend(zh_aliases)
            english_terms.extend(en_aliases)

    def unique_terms(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    candidates: list[str] = []
    if focused and _query_key(focused) != _query_key(normalized):
        candidates.append(focused)
    if chinese_terms:
        candidates.append(" ".join(unique_terms(chinese_terms)))
    if english_terms:
        candidates.append(" ".join(unique_terms(english_terms)))

    variants: list[str] = []
    seen = {_query_key(normalized)}
    for candidate in candidates:
        key = _query_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        variants.append(candidate)
        if len(variants) >= max_variants:
            break
    return variants


def assess_evidence(candidates: list[Candidate], app_settings: Settings) -> EvidenceAssessment:
    """Apply an explainable OR gate over absolute relevance signals.

    Reranker logits are model-specific and their sigmoid-normalized values are
    not calibrated probabilities. A low reranker value therefore must not veto
    an independently strong dense-cosine or sparse-token signal. Rank-only RRF
    scores remain intentionally excluded from this decision.
    """

    if not candidates:
        return EvidenceAssessment(
            sufficient=False,
            best_score=0.0,
            score_kind="none",
            candidate_count=0,
            source_count=0,
            reason="no retrievable candidate resolved to source text",
        )

    rerank_values = [candidate.score for candidate in candidates if candidate.rerank_score is not None]
    dense_values = [candidate.dense_score for candidate in candidates if candidate.dense_score is not None]
    sparse_values = [candidate.sparse_score for candidate in candidates if candidate.sparse_score is not None]
    signals: list[tuple[str, float, float]] = []
    if rerank_values:
        signals.append(
            (
                "reranker_normalized",
                min(max(max(rerank_values), 0.0), 1.0),
                app_settings.min_rerank_relevance,
            )
        )
    if dense_values:
        signals.append(
            (
                "dense_cosine",
                min(max(max(dense_values), -1.0), 1.0),
                app_settings.min_dense_relevance,
            )
        )
    if sparse_values:
        signals.append(
            (
                "sparse_token_coverage",
                min(max(max(sparse_values), 0.0), 1.0),
                app_settings.min_sparse_coverage,
            )
        )

    passed = [signal for signal in signals if signal[1] >= signal[2]]
    selected_pool = passed or signals
    if selected_pool:
        score_kind, best_score, _ = max(selected_pool, key=lambda signal: signal[1])
    else:
        score_kind, best_score = "none", 0.0
    sufficient = bool(passed)
    signal_details = ", ".join(
        f"{kind}={score:.3f}/{threshold:.3f}:{'pass' if score >= threshold else 'fail'}"
        for kind, score, threshold in signals
    )
    if not signal_details:
        signal_details = "none (rank-only fusion scores are not evidence)"
    source_count = len(
        {
            str(candidate.metadata.get("source", "")).strip()
            for candidate in candidates
            if str(candidate.metadata.get("source", "")).strip()
        }
    )
    return EvidenceAssessment(
        sufficient=sufficient,
        best_score=best_score,
        score_kind=score_kind,
        candidate_count=len(candidates),
        source_count=source_count,
        reason=(
            f"signals[{signal_details}]; gate=ANY threshold; sufficient={sufficient}; selected={score_kind}"
        ),
    )


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
        workflow.add_node("prepare_context", self.prepare_context)
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
                "answer": "prepare_context",
                "abstain": "abstain",
            },
        )
        workflow.add_edge("prepare_context", "generate_answer")
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
            "context_stats": {},
            "answer": "",
            "sources": [],
            "abstained": False,
            "confidence": 0.0,
            "citation_report": {},
            "repair_attempts": 0,
            "events": _event({}, "initialize", started, history_turns=len(history)),
            "llm_calls": [],
            "failure_kind": None,
            "error": None,
        }

    def plan_queries(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        attempt = state.get("retrieval_attempts", 0) + 1
        question = state["question"]
        previous_queries = state.get("search_queries", [])
        deterministic = deterministic_query_variants(question)
        planned_queries: list[str] = []
        strategy = "deterministic"
        llm_calls = state.get("llm_calls", [])
        planner_error: str | None = None

        if self.llm.enabled:
            try:
                plan, call = self.llm.plan_queries(
                    question,
                    history=state.get("history", []),
                    attempt=attempt,
                    max_variants=self.settings.max_query_variants,
                )
                planned_queries = plan.search_queries
                strategy = plan.strategy
                llm_calls = [*llm_calls, {"purpose": "query_plan", **call.usage_dict()}]
            except LLMRequestError as exc:
                planner_error = type(exc).__name__
                strategy = "deterministic_fallback"

        # The first pass keeps the exact question to preserve identifiers. A
        # retry prioritizes deterministic variants that were not already sent,
        # avoiding a second identical retrieval when the planner repeats itself.
        if attempt == 1:
            pool = [question, *planned_queries, *deterministic]
        else:
            pool = [*deterministic, *planned_queries, question]
            strategy = f"{strategy}+deduplicated_retry"

        previous_keys = {_query_key(query) for query in previous_queries} if attempt > 1 else set()
        queries: list[str] = []
        seen: set[str] = set()
        for query in pool:
            normalized_query = re.sub(r"\s+", " ", query).strip()
            key = _query_key(normalized_query)
            if not key or key in seen or key in previous_keys:
                continue
            seen.add(key)
            queries.append(normalized_query)
            if len(queries) >= self.settings.max_query_variants:
                break

        # A very short/generic question may have no safe deterministic rewrite.
        # Repeating the exact question is preferable to skipping retrieval.
        if not queries:
            queries = [question]

        return {
            "retrieval_attempts": attempt,
            "search_queries": queries,
            "query_strategy": strategy,
            "llm_calls": llm_calls,
            "error": None,
            "events": _event(
                state,
                "plan_queries",
                started,
                attempt=attempt,
                query_count=len(queries),
                strategy=strategy,
                fallback=bool(planner_error) or not self.llm.enabled,
                planner_error=planner_error,
                previous_queries_omitted=sum(1 for query in pool if _query_key(query) in previous_keys),
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
        assessment = assess_evidence(_candidates(state), self.settings)

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

    def prepare_context(self, state: AgentState) -> AgentState:
        """Make evidence selection a deterministic, separately observable step.

        门控通过不代表所有候选都相关。把排名中首个过门控的候选放在最前，
        避免预算很小时只留下弱证据。仍不把检索分数当成答案正确概率。
        """
        started = time.perf_counter()
        candidates = _candidates(state)
        anchor = next(
            (item for item in candidates if assess_evidence([item], self.settings).sufficient), None
        )
        if anchor is not None:
            candidates = [anchor, *(item for item in candidates if item is not anchor)]
        diversify = bool(
            re.search(
                r"哪些|有什么|列出|汇总|对比|比较|总结|\b(?:overview|compare|list)\b", state["question"], re.I
            )
        )
        bundle = build_context(candidates, self.settings.max_context_chars, diversify=diversify)
        selection_fallback = None
        if not any(assess_evidence([item], self.settings).sufficient for item in bundle.candidates):
            # Fair sharing can exclude an anchor with long path/heading metadata.
            # Re-check selected signals, then reserve the full budget for the
            # anchor. If even that cannot fit, generation reports empty context.
            # This is NOT semantic re-grading of a truncated passage.
            bundle = build_context([anchor] if anchor is not None else [], self.settings.max_context_chars)
            selection_fallback = "anchor_only"
        sources = source_list(bundle.candidates)
        stats = {
            "input_count": len(candidates),
            "selected_count": len(sources),
            "duplicate_count": bundle.duplicate_count,
            "document_count": len({str(item["source"]) for item in sources}),
            "context_chars": bundle.character_count,
            "budget_chars": self.settings.max_context_chars,
            "context_truncated": bundle.truncated,
            "diversified": diversify,
            "selection_fallback": selection_fallback,
        }
        return {
            "context": bundle.text,
            "sources": sources,
            "context_stats": stats,
            "events": _event(state, "prepare_context", started, **stats),
        }

    def generate_answer(self, state: AgentState) -> AgentState:
        started = time.perf_counter()
        context = state.get("context", "")
        sources = state.get("sources", [])
        llm_calls = state.get("llm_calls", [])

        if not sources or not context:
            return {
                "answer": GENERATION_FAILURE_MESSAGE,
                "sources": [],
                "context": "",
                "abstained": True,
                "failure_kind": "generation_failure",
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
                "answer": GENERATION_FAILURE_MESSAGE,
                "sources": sources,
                "context": context,
                "abstained": True,
                "failure_kind": "generation_failure",
                "error": "llm_not_configured",
                "events": _event(
                    state,
                    "generate_answer",
                    started,
                    context_chars=len(context),
                    source_count=len(sources),
                    model_called=False,
                ),
            }

        try:
            call = self.llm.generate(
                ANSWER_INSTRUCTIONS,
                render_answer_prompt(state["question"], context),
            )
            llm_calls = [*llm_calls, {"purpose": "answer", **call.usage_dict()}]
            answer = call.text.strip()
            if not answer:
                return {
                    "answer": GENERATION_FAILURE_MESSAGE,
                    "sources": sources,
                    "context": context,
                    "abstained": True,
                    "failure_kind": "generation_failure",
                    "llm_calls": llm_calls,
                    "error": "empty_model_output",
                    "events": _event(
                        state,
                        "generate_answer",
                        started,
                        source_count=len(sources),
                        model_called=True,
                        failed=True,
                        failure_kind="generation_failure",
                    ),
                }
            return {
                "answer": answer,
                "sources": sources,
                "context": context,
                "failure_kind": None,
                "llm_calls": llm_calls,
                "events": _event(
                    state,
                    "generate_answer",
                    started,
                    context_chars=len(context),
                    context_truncated=state.get("context_stats", {}).get("context_truncated", False),
                    source_count=len(sources),
                    model_called=True,
                ),
            }
        except LLMRequestError as exc:
            failed_call = getattr(exc, "call", None)
            if failed_call is not None and hasattr(failed_call, "usage_dict"):
                llm_calls = [
                    *llm_calls,
                    {"purpose": "answer", "failed": True, **failed_call.usage_dict()},
                ]
            return {
                "answer": GENERATION_FAILURE_MESSAGE,
                "sources": sources,
                "context": context,
                "abstained": True,
                "failure_kind": "generation_failure",
                "llm_calls": llm_calls,
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
            abstained=state.get("failure_kind") == "insufficient_evidence",
        )
        value = report.to_dict()
        return {
            "citation_report": value,
            "events": _event(state, "validate_citations", started, **value),
        }

    def route_after_citation_validation(self, state: AgentState) -> str:
        if state.get("failure_kind") in {"generation_failure", "citation_failure"}:
            return "finish"
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
            answer = call.text.strip()
            if not answer:
                return {
                    "answer": CITATION_FAILURE_MESSAGE,
                    "abstained": True,
                    "failure_kind": "citation_failure",
                    "repair_attempts": attempts,
                    "llm_calls": llm_calls,
                    "error": "empty_citation_repair_output",
                    "events": _event(
                        state,
                        "repair_citations",
                        started,
                        attempt=attempts,
                        failed=True,
                        failure_kind="citation_failure",
                    ),
                }
            return {
                "answer": answer,
                "repair_attempts": attempts,
                "failure_kind": None,
                "llm_calls": llm_calls,
                "events": _event(state, "repair_citations", started, attempt=attempts),
            }
        except LLMRequestError as exc:
            failed_call = getattr(exc, "call", None)
            if failed_call is not None and hasattr(failed_call, "usage_dict"):
                llm_calls = [
                    *llm_calls,
                    {
                        "purpose": "citation_repair",
                        "failed": True,
                        **failed_call.usage_dict(),
                    },
                ]
            return {
                "answer": CITATION_FAILURE_MESSAGE,
                "abstained": True,
                "failure_kind": "citation_failure",
                "repair_attempts": attempts,
                "llm_calls": llm_calls,
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
            "failure_kind": "insufficient_evidence",
            "error": None,
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
            "answer": CITATION_FAILURE_MESSAGE,
            "abstained": True,
            "failure_kind": "citation_failure",
            "confidence": 0.0,
            "error": "citation_validation_failed",
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
        failure_kind = state.get("failure_kind")
        if failure_kind in {"generation_failure", "citation_failure"}:
            status = "error"
        elif abstained:
            status = "abstained"
        else:
            status = "answered"
        value: dict[str, Any] = {
            "question": state["question"],
            "thread_id": state["thread_id"],
            "trace_id": state["trace_id"],
            "status": status,
            "answer": state.get("answer", ""),
            "abstained": abstained,
            "failure_kind": failure_kind,
            "confidence": float(state.get("confidence", 0.0)),
            "query": (state.get("search_queries") or [state["question"]])[0],
            "queries": state.get("search_queries", []),
            # Only low-relevance candidates are hidden. For model/citation
            # failures the gate already accepted these sources, so preserving
            # them makes the technical failure diagnosable without presenting
            # an unverified model answer as fact.
            "sources": ([] if failure_kind == "insufficient_evidence" else state.get("sources", [])),
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
