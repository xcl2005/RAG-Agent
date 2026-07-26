import pytest

from rag_agent.evaluation.metrics import (
    aggregate_rankings,
    answerability_metrics,
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


def test_answerability_metrics_separate_false_refusals_from_false_answers():
    result = answerability_metrics(
        [
            (True, True),
            (True, False),
            (False, False),
            (False, True),
        ]
    )

    assert result == {
        "labeled_cases": 4,
        "true_answer": 1,
        "true_refusal": 1,
        "false_answer": 1,
        "false_refusal": 1,
        "answer_precision": 0.5,
        "answer_recall": 0.5,
        "refusal_precision": 0.5,
        "refusal_recall": 0.5,
        "false_answer_rate": 0.5,
        "false_refusal_rate": 0.5,
    }
