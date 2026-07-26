from rag_agent.config import Settings
from rag_agent.retrieval.hybrid import HybridRetriever
from rag_agent.retrieval.reranker import Reranker
from rag_agent.schemas import Candidate


def candidate(chunk_id: str, *, sparse_score: float = 0.0) -> Candidate:
    return Candidate(
        chunk_id=chunk_id,
        text=f"evidence-{chunk_id}",
        metadata={"source": f"{chunk_id}.md"},
        sparse_score=sparse_score,
    )


class FakeVector:
    def __init__(self, hits_by_query, failing=()):
        self.hits_by_query = hits_by_query
        self.failing = set(failing)

    def search(self, query, limit):
        if query in self.failing:
            raise RuntimeError("qdrant unavailable")
        return self.hits_by_query.get(query, [])[:limit]

    def ready(self):
        return True, "ready"


class FakeSQLite:
    def __init__(self, sparse_by_query, chunks, failing=()):
        self.sparse_by_query = sparse_by_query
        self.chunks = chunks
        self.failing = set(failing)
        self.closed = False

    def search(self, query, limit):
        if query in self.failing:
            raise RuntimeError("fts unavailable")
        return self.sparse_by_query.get(query, [])[:limit]

    def get_chunks(self, chunk_ids):
        return {chunk_id: self.chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in self.chunks}

    def ready(self):
        return True, "ready"

    def close(self):
        self.closed = True


def make_retriever(tmp_path, *, vector, sqlite) -> HybridRetriever:
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.settings = Settings(
        sqlite_path=tmp_path / "rag.db",
        dense_top_k=5,
        sparse_top_k=5,
        fusion_top_k=5,
        rerank_top_k=3,
        enable_reranker=False,
    )
    retriever.vector = vector
    retriever.sqlite = sqlite
    retriever.reranker = Reranker("unused", enabled=False)
    retriever.last_debug = {}
    return retriever


def test_multi_query_fusion_preserves_signals_and_deduplicates_queries(tmp_path):
    chunks = {key: candidate(key) for key in ("a", "b", "c")}
    vector = FakeVector(
        {
            "exact": [{"chunk_id": "a", "score": 0.95}, {"chunk_id": "b", "score": 0.8}],
            "semantic": [{"chunk_id": "c", "score": 0.91}, {"chunk_id": "a", "score": 0.7}],
        }
    )
    sqlite = FakeSQLite(
        {
            "exact": [candidate("b", sparse_score=3.0)],
            "semantic": [candidate("a", sparse_score=2.0)],
        },
        chunks,
    )
    retriever = make_retriever(tmp_path, vector=vector, sqlite=sqlite)

    results = retriever.retrieve_many(
        ["exact", "semantic", "exact", "  "],
        rerank_query="exact",
    )

    assert {item.chunk_id for item in results} == {"a", "b", "c"}
    assert all(0.0 <= item.score <= 1.0 for item in results)
    assert results[0].score >= results[-1].score
    assert set(next(item for item in results if item.chunk_id == "a").matched_queries) == {
        "exact",
        "semantic",
    }
    assert retriever.last_debug["ranking_count"] == 4


def test_retrieval_degrades_to_remaining_backend_and_reports_errors(tmp_path):
    chunk = candidate("lexical")
    vector = FakeVector({}, failing={"query"})
    sqlite = FakeSQLite({"query": [candidate("lexical", sparse_score=1.0)]}, {"lexical": chunk})
    retriever = make_retriever(tmp_path, vector=vector, sqlite=sqlite)

    results = retriever.retrieve("query")

    assert [item.chunk_id for item in results] == ["lexical"]
    assert retriever.last_debug["backend_errors"][0].startswith("dense[0]")


def test_no_backend_results_returns_empty_debug_record(tmp_path):
    retriever = make_retriever(
        tmp_path,
        vector=FakeVector({}, failing={"query"}),
        sqlite=FakeSQLite({}, {}, failing={"query"}),
    )

    assert retriever.retrieve("query") == []
    assert len(retriever.last_debug["backend_errors"]) == 2


def test_reranker_normalization_is_explicit_and_batch_independent():
    assert Reranker._normalize([0.1, 0.9], "probability") == [0.1, 0.9]
    normalized = Reranker._normalize([-1000.0, 0.0, 1000.0], "logit")
    assert normalized[0] == 0.0
    assert normalized[1] == 0.5
    assert normalized[2] == 1.0
    assert Reranker._normalize([0.5], "logit")[0] == Reranker._normalize([0.5, 2.0], "logit")[0]


def test_reranker_inference_failure_falls_back_and_is_reported(tmp_path):
    class BrokenModel:
        def predict(self, pairs, **kwargs):
            raise RuntimeError("simulated OOM with private detail")

    chunks = {"a": candidate("a"), "b": candidate("b")}
    retriever = make_retriever(
        tmp_path,
        vector=FakeVector(
            {
                "query": [
                    {"chunk_id": "a", "score": 0.9},
                    {"chunk_id": "b", "score": 0.8},
                ]
            }
        ),
        sqlite=FakeSQLite({}, chunks),
    )
    retriever.reranker.enabled = True
    retriever.reranker.model = BrokenModel()

    results, debug = retriever.retrieve_many_with_debug(
        ["query"],
        rerank_query="query",
    )

    assert [item.chunk_id for item in results] == ["a", "b"]
    assert debug["backend_errors"] == ["reranker: inference_failed:RuntimeError"]
    assert "private detail" not in debug["backend_errors"][0]
