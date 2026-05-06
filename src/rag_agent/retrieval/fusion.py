
"""多路召回结果融合。

Hybrid search 会产生两个排序列表：
- dense：向量检索结果。
- sparse：关键词检索结果。

RRF（Reciprocal Rank Fusion）不直接比较两种检索的原始分数，
只看排名，所以很适合融合不同来源的检索结果。
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

    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return dict(scores)
