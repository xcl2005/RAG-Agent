import pytest

from rag_agent.evaluation.metrics import (
    aggregate_rankings,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_ranking_metrics_have_expected_values():
    ranked = ["x", "a", "b"]
    relevant = {"a", "b"}

    assert recall_at_k(ranked, relevant, 2) == 0.5
    assert reciprocal_rank(ranked, relevant) == 0.5
    assert ndcg_at_k(ranked, relevant, 3) == pytest.approx(0.693426, rel=1e-5)


def test_aggregate_rankings_reports_reproducible_metric_names():
    result = aggregate_rankings(
        [(["a", "x"], {"a"}), (["x", "b"], {"b"})],
        k_values=(1, 2),
    )
    assert result == {
        "mrr": 0.75,
        "recall@1": 0.5,
        "ndcg@1": 0.5,
        "recall@2": 1.0,
        "ndcg@2": 0.815465,
    }


def test_ndcg_does_not_double_count_duplicate_source_labels():
    score = ndcg_at_k(["source:a", "source:a"], {"source:a"}, 2)
    assert score == 1.0
