import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rag_agent.learning import coach


def test_questions_have_real_code_and_answers_are_opt_in(capsys):
    root = Path(__file__).resolve().parents[1]
    assert [item["id"] for item in coach.QUESTIONS] == [f"q{index:02}" for index in range(1, 13)]
    for item in coach.QUESTIONS:
        assert all((root / source).is_file() for source in item["code"])
        coach.main(["show", item["id"]])
        assert item["answer"] not in capsys.readouterr().out
        coach.main(["show", item["id"], "--reveal"])
        assert item["answer"] in capsys.readouterr().out


def test_record_and_status_keep_self_assessment_explicit(tmp_path, capsys):
    progress = tmp_path / "progress.json"
    coach.main(
        ["record", "q01", "--score", "2", "--note", "I can draw the graph.", "--progress", str(progress)]
    )
    value = json.loads(progress.read_text(encoding="utf-8"))
    assert value["self_assessment_only"] is True
    assert value["records"]["q01"]["score"] == 2
    coach.main(["--progress", str(progress), "status"])
    output = capsys.readouterr().out
    assert "1/12" in output and "本人自评" in output
    assert "q02" in output and "未自评" in output


@pytest.mark.parametrize(
    "content",
    [
        "{broken",
        "[]",
        '{"version":2}',
        '{"version":1,"self_assessment_only":true,"records":{"q01":{"score":true,"note":"","updated_at":"now"}}}',
    ],
)
def test_bad_progress_is_never_overwritten(tmp_path, content):
    path = tmp_path / "progress.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        coach.record_progress(path, "q01", 2, "new note")
    assert path.read_text(encoding="utf-8") == content


def test_failed_atomic_replace_preserves_previous_progress(tmp_path, monkeypatch):
    path = tmp_path / "progress.json"
    coach.record_progress(path, "q01", 1, "first")
    original = path.read_bytes()

    def fail(*args):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(coach.os, "replace", fail)
    with pytest.raises(OSError):
        coach.record_progress(path, "q02", 2, "second")
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_score_and_unknown_question_do_not_create_progress(tmp_path):
    path = tmp_path / "progress.json"
    for question_id, score in (("q99", 2), ("q01", 4), ("q01", True)):
        with pytest.raises(ValueError):
            coach.record_progress(path, question_id, score, "")
    assert not path.exists()


def test_cli_entrypoint_emits_utf8_even_under_legacy_windows_encoding(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/practice_interview.py"
    progress = tmp_path / "progress.json"
    result = subprocess.run(
        [sys.executable, str(script), "show", "q01", "--progress", str(progress)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "cp936"},
        check=True,
        timeout=15,
    )
    assert "一次请求怎样走完系统" in result.stdout
    assert "参考答案：" not in result.stdout
    assert not progress.exists()
