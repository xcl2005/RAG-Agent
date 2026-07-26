"""RRF 融合算法测试。

同一个文档如果在多个检索列表中都靠前，融合后应该比只在一个列表中出现的文档更占优。
"""

from rag_agent.retrieval.fusion import (
    normalize_rrf_scores,
    reciprocal_rank_fusion,
    weighted_reciprocal_rank_fusion,
)


def test_rrf_fusion_prefers_docs_ranked_in_multiple_lists():
    scores = reciprocal_rank_fusion([["a", "b", "c"], ["b", "d", "a"]], k=60)
    assert scores["b"] > scores["c"]
    assert scores["a"] > scores["c"]


def test_weighted_rrf_preserves_original_query_priority_and_normalizes():
    raw = weighted_reciprocal_rank_fusion(
        [(["exact-code", "other"], 1.0), (["other", "exact-code"], 0.25)],
        k=60,
    )
    normalized = normalize_rrf_scores(raw, total_weight=1.25, k=60)

    assert raw["exact-code"] > raw["other"]
    assert all(0 <= score <= 1 for score in normalized.values())
