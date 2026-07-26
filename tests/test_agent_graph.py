import threading

from langgraph.checkpoint.memory import InMemorySaver

from rag_agent.agent.graph import RAGAgent
from rag_agent.config import Settings
from rag_agent.llm.client import LLMCall, QueryPlan
from rag_agent.schemas import Candidate


class FakeRetriever:
    def __init__(self, candidates):
        self.candidates = candidates
        self.last_debug = {"backend": "fake"}
        self.calls = 0

    def retrieve_many(self, queries, *, rerank_query, rerank_top_k=None):
        self.calls += 1
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
    assert retriever.calls == 2
    assert [event["node"] for event in result["trace"]].count("plan_queries") == 2


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
