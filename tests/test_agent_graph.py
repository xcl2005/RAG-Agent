import threading

from langgraph.checkpoint.memory import InMemorySaver

from rag_agent.agent.graph import (
    RAGAgent,
    assess_evidence,
    deterministic_query_variants,
)
from rag_agent.config import Settings
from rag_agent.llm.client import LLMCall, LLMRequestError, QueryPlan
from rag_agent.schemas import Candidate


class FakeRetriever:
    def __init__(self, candidates):
        self.candidates = candidates
        self.last_debug = {"backend": "fake"}
        self.calls = 0
        self.query_batches = []

    def retrieve_many(self, queries, *, rerank_query, rerank_top_k=None):
        self.calls += 1
        self.query_batches.append(list(queries))
        return self.candidates

    def ready(self):
        return {"fake": {"ready": True, "detail": "ready"}}

    def close(self):
        return None


class DisabledLLM:
    enabled = False


class FakeLLM:
    enabled = True

    def __init__(self, answers):
        self.answers = iter(answers)

    def plan_queries(self, question, *, history, attempt, max_variants):
        return (
            QueryPlan(search_queries=[question, f"{question} 同义词"], strategy="fake-plan"),
            LLMCall("{}", "plan", "fake", 10, 5, 1.0),
        )

    def generate(self, instructions, user_input, **kwargs):
        return LLMCall(next(self.answers), "answer", "fake", 20, 8, 1.0)


class FailingAnswerLLM(FakeLLM):
    def generate(self, instructions, user_input, **kwargs):
        raise LLMRequestError("provider unavailable")


def make_settings(tmp_path, **overrides):
    values = {
        "sqlite_path": tmp_path / "rag.db",
        "checkpoint_path": tmp_path / "checkpoints.db",
        "max_retrieval_attempts": 2,
    }
    values.update(overrides)
    return Settings(**values)


def evidence_candidate():
    return Candidate(
        chunk_id="a" * 64,
        text="系统使用服务端引用校验，确保来源编号真实存在。",
        metadata={"source": "sample.md", "title": "sample.md", "chunk_index": 0},
        score=0.9,
        rerank_score=2.2,
    )


def test_agent_retries_then_abstains_when_no_evidence(tmp_path):
    retriever = FakeRetriever([])
    agent = RAGAgent(
        make_settings(tmp_path),
        llm=DisabledLLM(),
        retriever=retriever,
        checkpointer=InMemorySaver(),
    )

    result = agent.ask("资料里没有答案的问题")

    assert result["abstained"] is True
    assert result["failure_kind"] == "insufficient_evidence"
    assert result["status"] == "abstained"
    assert retriever.calls == 2
    assert [event["node"] for event in result["trace"]].count("plan_queries") == 2


def test_retry_queries_are_deduplicated_and_expand_portfolio_list_intent(tmp_path):
    retriever = FakeRetriever([])
    agent = RAGAgent(
        make_settings(tmp_path, max_query_variants=3),
        llm=DisabledLLM(),
        retriever=retriever,
        checkpointer=InMemorySaver(),
    )

    agent.ask("目前上传的资料里，我（xuchenglin）的项目有哪些？")

    assert len(retriever.query_batches) == 2
    first_keys = {query.casefold() for query in retriever.query_batches[0]}
    second_keys = {query.casefold() for query in retriever.query_batches[1]}
    assert first_keys.isdisjoint(second_keys)
    assert any("课程项目" in query for batch in retriever.query_batches for query in batch)
    assert any("project" in query.casefold() for query in retriever.query_batches[1])


def test_deterministic_query_variants_cover_papers_projects_and_internships():
    variants = deterministic_query_variants(
        "与申请专业相关的论文、课程论文、科研实验或学术项目，与申请专业相关的实习或工作经历都有哪些"
    )
    combined = " ".join(variants)

    assert "课程论文" in combined
    assert "科研项目" in combined
    assert "实习经历" in combined
    assert "publication" in combined
    assert len(variants) == len(set(variants))


def test_abstention_does_not_expose_low_relevance_candidate_text(tmp_path):
    confidential = Candidate(
        chunk_id="secret",
        text="CONFIDENTIAL salary=999999",
        metadata={"source": "C:/secret/hr.md"},
        score=1.0,
        fusion_score=1.0,
        dense_score=0.1,
        sparse_score=0.1,
    )
    agent = RAGAgent(
        make_settings(tmp_path, max_retrieval_attempts=1),
        llm=DisabledLLM(),
        retriever=FakeRetriever([confidential]),
        checkpointer=InMemorySaver(),
    )

    result = agent.ask("unrelated question")

    assert result["abstained"] is True
    assert result["sources"] == []
    assert "CONFIDENTIAL" not in str(result)
    assert "C:/secret/hr.md" not in str(result)


def test_agent_returns_grounded_answer_and_remembers_thread(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path),
        llm=FakeLLM(["结论来自资料 [S1]", "第二轮结论 [S1]"]),
        retriever=FakeRetriever([evidence_candidate()]),
        checkpointer=InMemorySaver(),
    )

    first = agent.ask("如何校验引用？", thread_id="thread-1")
    second = agent.ask("它为什么重要？", thread_id="thread-1")

    assert first["status"] == "answered"
    assert first["citation_validation"]["valid"] is True
    assert second["trace"][0]["history_turns"] == 1
    nodes = [event["node"] for event in first["trace"]]
    assert nodes.index("grade_evidence") < nodes.index("prepare_context") < nodes.index("generate_answer")
    prepared = next(event for event in first["trace"] if event["node"] == "prepare_context")
    assert prepared["selected_count"] == 1
    assert prepared["context_chars"] <= prepared["budget_chars"]


def test_context_anchor_is_the_first_candidate_that_passes_gate(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path), llm=DisabledLLM(), retriever=FakeRetriever([]), checkpointer=InMemorySaver()
    )
    weak = Candidate(chunk_id="weak", text="unrelated", metadata={"source": "weak.md"}, dense_score=0.01)
    strong = evidence_candidate()
    prepared = agent.prepare_context(
        {"question": "哪些证据？", "candidates": [weak.to_dict(), strong.to_dict()]}
    )
    assert prepared["sources"][0]["chunk_id"] == strong.chunk_id
    assert prepared["context_stats"]["diversified"] is True


def test_diversity_falls_back_when_anchor_metadata_exceeds_fair_share(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path, max_context_chars=1000),
        llm=DisabledLLM(),
        retriever=FakeRetriever([]),
        checkpointer=InMemorySaver(),
    )
    anchor = Candidate(
        chunk_id="anchor",
        text="strong evidence",
        dense_score=0.9,
        metadata={"source": "x" * 120 + ".md", "heading": "y" * 200},
    )
    others = [
        Candidate(chunk_id=str(i), text="weak evidence", dense_score=0.01, metadata={"source": f"{i}.md"})
        for i in range(2)
    ]
    prepared = agent.prepare_context(
        {"question": "比较这几份资料", "candidates": [c.to_dict() for c in [anchor, *others]]}
    )
    assert [source["chunk_id"] for source in prepared["sources"]] == ["anchor"]
    assert prepared["context_stats"]["selection_fallback"] == "anchor_only"
    assert prepared["context_stats"]["input_count"] == 3


def test_skiplist_fact_question_does_not_trigger_diversity(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path), llm=DisabledLLM(), retriever=FakeRetriever([]), checkpointer=InMemorySaver()
    )
    prepared = agent.prepare_context(
        {"question": "Redis skiplist 查询复杂度是多少", "candidates": [evidence_candidate().to_dict()]}
    )
    assert prepared["context_stats"]["diversified"] is False


def test_unfittable_anchor_does_not_generate_from_only_weak_sources(tmp_path):
    anchor = evidence_candidate()
    anchor.metadata = {"source": "&" * 400, "heading": "<" * 200}
    weak = Candidate(chunk_id="weak", text="unrelated", metadata={"source": "weak.md"}, dense_score=0.01)
    agent = RAGAgent(
        make_settings(tmp_path, max_context_chars=1000),
        llm=DisabledLLM(),
        retriever=FakeRetriever([anchor, weak]),
        checkpointer=InMemorySaver(),
    )
    result = agent.ask("比较这些资料")
    assert result["failure_kind"] == "generation_failure"
    assert result["status"] == "error"
    assert result["sources"] == []
    generated = next(event for event in result["trace"] if event["node"] == "generate_answer")
    assert generated["model_called"] is False


def test_agent_repairs_missing_citation_once(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path),
        llm=FakeLLM(["没有引用的结论", "修复后的结论 [S1]"]),
        retriever=FakeRetriever([evidence_candidate()]),
        checkpointer=InMemorySaver(),
    )

    result = agent.ask("如何校验引用？")

    assert result["answer"] == "修复后的结论 [S1]"
    assert result["citation_validation"]["valid"] is True
    assert any(event["node"] == "repair_citations" for event in result["trace"])


def test_evidence_gate_does_not_treat_top_rrf_rank_as_absolute_relevance(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path),
        llm=DisabledLLM(),
        retriever=FakeRetriever([]),
        checkpointer=InMemorySaver(),
    )
    weak = Candidate(
        chunk_id="weak",
        text="unrelated",
        metadata={"source": "weak.md"},
        score=1.0,
        fusion_score=1.0,
        dense_score=0.1,
        sparse_score=0.1,
    )
    strong_lexical = Candidate(
        chunk_id="strong",
        text="ERR-1042",
        metadata={"source": "runbook.md"},
        score=1.0,
        fusion_score=1.0,
        sparse_score=0.9,
    )

    weak_result = agent.grade_evidence({"candidates": [weak.to_dict()]})
    strong_result = agent.grade_evidence({"candidates": [strong_lexical.to_dict()]})

    assert weak_result["evidence"]["sufficient"] is False
    assert strong_result["evidence"]["sufficient"] is True
    assert strong_result["evidence"]["score_kind"] == "sparse_token_coverage"


def test_evidence_gate_does_not_allow_reranker_to_veto_dense_or_sparse(tmp_path):
    app_settings = make_settings(
        tmp_path,
        min_rerank_relevance=0.55,
        min_dense_relevance=0.5,
        min_sparse_coverage=0.45,
    )
    candidate = Candidate(
        chunk_id="multi-signal",
        text="relevant project evidence",
        metadata={"source": "portfolio.docx"},
        score=0.08,
        rerank_score=-2.45,
        dense_score=0.56,
        sparse_score=0.5,
    )

    assessment = assess_evidence([candidate], app_settings)

    assert assessment.sufficient is True
    assert assessment.score_kind == "dense_cosine"
    assert "reranker_normalized=0.080/0.550:fail" in assessment.reason
    assert "dense_cosine=0.560/0.500:pass" in assessment.reason
    assert "sparse_token_coverage=0.500/0.450:pass" in assessment.reason
    assert "gate=ANY threshold" in assessment.reason


def test_evidence_gate_rejects_when_every_absolute_signal_is_below_threshold(tmp_path):
    app_settings = make_settings(
        tmp_path,
        min_rerank_relevance=0.55,
        min_dense_relevance=0.5,
        min_sparse_coverage=0.45,
    )
    candidate = Candidate(
        chunk_id="weak-signals",
        text="unrelated",
        metadata={"source": "other.docx"},
        score=0.04,
        rerank_score=-3.18,
        dense_score=0.3,
        sparse_score=0.1,
        fusion_score=1.0,
    )

    assessment = assess_evidence([candidate], app_settings)

    assert assessment.sufficient is False
    assert ":pass" not in assessment.reason


def test_generation_failure_is_not_reported_as_insufficient_evidence(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path),
        llm=FailingAnswerLLM([]),
        retriever=FakeRetriever([evidence_candidate()]),
        checkpointer=InMemorySaver(),
    )

    result = agent.ask("如何校验引用？")

    assert result["status"] == "error"
    assert result["failure_kind"] == "generation_failure"
    assert result["evidence"]["sufficient"] is True
    assert result["sources"]
    assert "未能生成有效答案" in result["answer"]


def test_citation_failure_is_not_reported_as_insufficient_evidence(tmp_path):
    agent = RAGAgent(
        make_settings(tmp_path),
        llm=FakeLLM(["没有引用的答案", "仍然没有引用"]),
        retriever=FakeRetriever([evidence_candidate()]),
        checkpointer=InMemorySaver(),
    )

    result = agent.ask("如何校验引用？")

    assert result["status"] == "error"
    assert result["failure_kind"] == "citation_failure"
    assert result["evidence"]["sufficient"] is True
    assert result["sources"]
    assert "引用未通过校验" in result["answer"]


def test_sqlite_checkpoint_persists_history_across_agent_instances(tmp_path):
    settings = make_settings(tmp_path)
    first_agent = RAGAgent(
        settings,
        llm=FakeLLM(["first answer [S1]"]),
        retriever=FakeRetriever([evidence_candidate()]),
    )
    first = first_agent.ask("first question", thread_id="durable-thread")
    first_agent.close()

    second_agent = RAGAgent(
        settings,
        llm=FakeLLM(["second answer [S1]"]),
        retriever=FakeRetriever([evidence_candidate()]),
    )
    second = second_agent.ask("follow-up question", thread_id="durable-thread")
    second_agent.close()

    assert first["trace"][0]["history_turns"] == 0
    assert second["trace"][0]["history_turns"] == 1


def test_same_thread_id_is_single_flight(tmp_path):
    """Concurrent requests cannot overwrite one conversation checkpoint."""

    agent = RAGAgent(
        make_settings(tmp_path),
        llm=DisabledLLM(),
        retriever=FakeRetriever([]),
        checkpointer=InMemorySaver(),
    )
    first_entered = threading.Event()
    release_first = threading.Event()
    second_attempting = threading.Event()
    second_entered = threading.Event()

    def first_request():
        with agent._thread_singleflight("shared-thread"):
            first_entered.set()
            assert release_first.wait(timeout=2)

    def second_request():
        second_attempting.set()
        with agent._thread_singleflight("shared-thread"):
            second_entered.set()

    first = threading.Thread(target=first_request)
    second = threading.Thread(target=second_request)
    first.start()
    assert first_entered.wait(timeout=1)
    second.start()
    assert second_attempting.wait(timeout=1)
    assert not second_entered.wait(timeout=0.05)

    release_first.set()
    first.join(timeout=1)
    second.join(timeout=1)
    assert second_entered.is_set()
    assert not first.is_alive()
    assert not second.is_alive()
