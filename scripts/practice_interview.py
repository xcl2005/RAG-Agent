"""Offline practice entry point: python scripts/practice_interview.py list."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from rag_agent.learning.coach import main

if __name__ == "__main__":
    # Windows may choose the legacy locale encoding when output is piped to
    # PyCharm or another process. Keep Chinese practice text portable as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main(default_progress=REPO_ROOT / "reports/learning-progress.json"))
