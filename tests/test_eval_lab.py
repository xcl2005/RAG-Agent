"""Contract tests for a real offline experiment, not snapshot score targets."""

import json
import shutil
import socket
from pathlib import Path

import pytest

from rag_agent.evaluation import lab
from rag_agent.evaluation.metrics import aggregate_rankings, answerability_metrics

DATASET = Path(__file__).resolve().parents[1] / "data/eval/portfolio"


def test_dataset_has_traceable_positive_cross_source_and_hard_negative_cases():
    documents, cases, digest = lab.load_dataset(DATASET)
    assert len(documents) == 8
    assert len(cases) >= 24
    assert len(digest) == 64
    assert sum(case["should_answer"] for case in cases) > 0
    assert sum(not case["should_answer"] for case in cases) > 0
    assert any(len(case["relevant_sources"]) > 1 for case in cases)
    assert any("hard_negative" in case["tags"] for case in cases)


def test_dataset_digest_is_location_independent_and_detects_edits(tmp_path):
    original = lab.load_dataset(DATASET)[2]
    copy = tmp_path / "copy"
    shutil.copytree(DATASET, copy)
    assert lab.load_dataset(copy)[2] == original
    source = copy / "corpus/api.md"
    source.write_text(source.read_text(encoding="utf-8") + "\nAn added note.\n", encoding="utf-8")
    assert lab.load_dataset(copy)[2] != original


@pytest.mark.parametrize(
    "mutation", ["unknown_source", "unsupported_excerpt", "duplicate_id", "label_conflict"]
)
def test_dataset_rejects_unverifiable_labels(tmp_path, mutation):
    copy = tmp_path / "invalid"
    shutil.copytree(DATASET, copy)
    path = copy / "cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "unknown_source":
        cases[0]["relevant_sources"] = ["missing.md"]
    elif mutation == "unsupported_excerpt":
        cases[0]["evidence"]["release.md"] = "There is no such fact in this document."
    elif mutation == "duplicate_id":
        cases[1]["id"] = cases[0]["id"]
    else:
        cases[0]["should_answer"] = False
    path.write_text(json.dumps(cases), encoding="utf-8")
    with pytest.raises(ValueError):
        lab.load_dataset(copy)


def test_offline_run_uses_real_index_and_metrics_match_case_evidence(tmp_path, monkeypatch):
    def reject_network(*args, **kwargs):
        raise AssertionError("offline lab must not connect to any server")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)
    # A database-shaped file outside the temporary lab is never opened or reset.
    sentinel = tmp_path / "chunks.db"
    sentinel.write_bytes(b"existing user database")
    report = lab.run_lab(DATASET, repo=tmp_path)
    assert sentinel.read_bytes() == b"existing user database"
    assert report["dataset"]["chunks"] > report["dataset"]["documents"]
    assert report["git"]["revision"] is None
    assert report["profile"] == "sparse"
    for variant in report["variants"].values():
        cases = variant["cases"]
        assert variant["gate"] == answerability_metrics(
            (row["should_answer"], row["gate_should_answer"]) for row in cases
        )
        assert variant["ranking"] == aggregate_rankings(
            [(row["ranked_sources"], set(row["relevant_sources"])) for row in cases if row["should_answer"]],
            k_values=(1, 5),
        )
        assert any(row["retrieved_chunks"] for row in cases)
        for row in cases:
            assert len(row["ranked_sources"]) == len(set(row["ranked_sources"]))
            assert row["latency_ms"] >= 0
        assert variant["gate"]["labeled_cases"] == 32


def test_labels_do_not_influence_retrieval_and_threshold_does_not_change_ranking(tmp_path):
    baseline = lab.run_lab(DATASET, repo=tmp_path)
    copy = tmp_path / "relabelled"
    shutil.copytree(DATASET, copy)
    path = copy / "cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    cases[0]["relevant_sources"] = ["api.md"]
    cases[0]["evidence"] = {"api.md": "question 最长 2000 字符"}
    path.write_text(json.dumps(cases), encoding="utf-8")
    changed = lab.run_lab(copy, config=lab.LabConfig(sparse_threshold=0.8), repo=tmp_path)
    for name in baseline["variants"]:
        before = baseline["variants"][name]["cases"]
        after = changed["variants"][name]["cases"]
        assert [row["ranked_sources"] for row in before] == [row["ranked_sources"] for row in after]
        assert [row["queries"] for row in before] == [row["queries"] for row in after]
        assert sum(row["gate_should_answer"] for row in after) <= sum(
            row["gate_should_answer"] for row in before
        )


def test_temporary_index_is_cleaned_up_even_if_retrieval_fails(monkeypatch, tmp_path):
    original = lab.tempfile.TemporaryDirectory
    paths = []

    def tracked_directory(**kwargs):
        directory = original(dir=tmp_path, **kwargs)
        paths.append(Path(directory.name))
        return directory

    def fail(*args, **kwargs):
        raise RuntimeError("simulated retrieval failure")

    monkeypatch.setattr(lab.tempfile, "TemporaryDirectory", tracked_directory)
    monkeypatch.setattr(lab, "retrieve_sparse", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        lab.run_lab(DATASET, repo=tmp_path)
    assert paths and all(not path.exists() for path in paths)


def test_reports_preserve_previous_runs_and_include_limitations(tmp_path):
    report = lab.run_lab(DATASET, repo=tmp_path)
    first_json, first_md = lab.write_report(report, tmp_path)
    second_json, second_md = lab.write_report(report, tmp_path)
    assert first_json != second_json and first_md != second_md
    loaded = json.loads(first_json.read_text(encoding="utf-8"))
    assert loaded["dataset_sha256"] == report["dataset_sha256"]
    markdown = first_md.read_text(encoding="utf-8")
    assert "没有调用 LLM" in markdown
    assert "false_answer_rate" in markdown
    assert "false_refusal_rate" in markdown
    assert "dirty" in markdown
    assert all(path.exists() for path in (first_json, first_md, second_json, second_md))


@pytest.mark.parametrize(
    "kwargs", [{"top_k": 0}, {"chunk_overlap": 300}, {"sparse_threshold": 0}, {"top_k": 21}]
)
def test_invalid_configuration_fails_before_indexing(kwargs):
    with pytest.raises(ValueError):
        lab.LabConfig(**kwargs)
