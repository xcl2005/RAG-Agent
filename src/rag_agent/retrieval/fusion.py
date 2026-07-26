"""Rank-fusion utilities used by multi-query hybrid retrieval.

RRF compares ranks instead of incompatible raw dense/BM25 scores. Weighted RRF
extends the same idea so the original user query can contribute more than
automatically generated query variants.
"""

from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """使用 RRF 融合多个 ranked list。

    公式：score(doc) = sum(1 / (k + rank))
    rank 从 1 开始。

    直觉：
    一个文档如果在多个召回列表里都排名靠前，最终分数就会更高。
    """

    return weighted_reciprocal_rank_fusion([(ranking, 1.0) for ranking in rankings], k=k)


def weighted_reciprocal_rank_fusion(
    rankings: list[tuple[list[str], float]],
    *,
    k: int = 60,
) -> dict[str, float]:
    """Fuse ``(ranked_ids, weight)`` pairs into raw weighted-RRF scores."""

    if k < 1:
        raise ValueError("k must be positive")

    scores: dict[str, float] = defaultdict(float)
    for ranking, weight in rankings:
        if weight <= 0:
            raise ValueError("ranking weights must be positive")

        # A backend should not emit duplicates, but ignoring them here prevents a
        # malformed list from receiving artificial extra credit.
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranking, start=1):
            if doc_id in seen:
                continue
            seen.add(doc_id)
            scores[doc_id] += weight / (k + rank)
    return dict(scores)


def normalize_rrf_scores(
    scores: dict[str, float],
    *,
    total_weight: float,
    k: int = 60,
) -> dict[str, float]:
    """Normalize raw RRF values to an interpretable ``[0, 1]`` range.

    The theoretical maximum occurs when one document ranks first in every list.
    This normalization makes evidence thresholds independent of how many query
    variants were generated.
    """

    if total_weight <= 0:
        raise ValueError("total_weight must be positive")
    maximum = total_weight / (k + 1)
    return {doc_id: min(max(score / maximum, 0.0), 1.0) for doc_id, score in scores.items()}
