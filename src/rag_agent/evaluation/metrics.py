"""Deterministic information-retrieval metrics.

Keeping these metrics in the repository makes quality regressions reproducible
without depending on a hosted LLM judge.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Fraction of all relevant items found in the first ``k`` results."""

    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first relevant result."""

    for rank, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Binary normalized discounted cumulative gain at ``k``."""

    if not relevant:
        return 0.0
    # Source-level judgments may map multiple chunks to the same source label.
    # A relevant source earns gain only once; otherwise duplicate chunks can
    # inflate nDCG above its mathematical upper bound of 1.
    seen: set[str] = set()
    dcg = 0.0
    for rank, item in enumerate(ranked[:k], start=1):
        if item in relevant and item not in seen:
            dcg += 1.0 / math.log2(rank + 1)
            seen.add(item)
    ideal_count = min(len(relevant), k)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal if ideal else 0.0


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def answerability_metrics(
    outcomes: Iterable[tuple[bool, bool]],
) -> dict[str, float | int]:
    """Measure evidence-gate decisions against ``should_answer`` labels.

    Each tuple is ``(expected_should_answer, predicted_should_answer)``.
    Separating false refusals from false answers is important for RAG systems:
    lowering one error rate can easily increase the other.
    """

    pairs = list(outcomes)
    true_positive = sum(expected and predicted for expected, predicted in pairs)
    true_negative = sum(not expected and not predicted for expected, predicted in pairs)
    false_positive = sum(not expected and predicted for expected, predicted in pairs)
    false_negative = sum(expected and not predicted for expected, predicted in pairs)

    def ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 6) if denominator else 0.0

    return {
        "labeled_cases": len(pairs),
        "true_answer": true_positive,
        "true_refusal": true_negative,
        "false_answer": false_positive,
        "false_refusal": false_negative,
        "answer_precision": ratio(true_positive, true_positive + false_positive),
        "answer_recall": ratio(true_positive, true_positive + false_negative),
        "refusal_precision": ratio(true_negative, true_negative + false_negative),
        "refusal_recall": ratio(true_negative, true_negative + false_positive),
        "false_answer_rate": ratio(false_positive, true_negative + false_positive),
        "false_refusal_rate": ratio(false_negative, true_positive + false_negative),
    }


def aggregate_rankings(
    rankings: list[tuple[list[str], set[str]]],
    *,
    k_values: tuple[int, ...] = (5, 10),
) -> dict[str, float]:
    """Aggregate Recall@K, MRR, and nDCG@K over an evaluation set."""

    metrics: dict[str, float] = {
        "mrr": mean(reciprocal_rank(ranked, relevant) for ranked, relevant in rankings)
    }
    for k in k_values:
        metrics[f"recall@{k}"] = mean(recall_at_k(ranked, relevant, k) for ranked, relevant in rankings)
        metrics[f"ndcg@{k}"] = mean(ndcg_at_k(ranked, relevant, k) for ranked, relevant in rankings)
    return {name: round(value, 6) for name, value in metrics.items()}
