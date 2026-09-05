"""Run the offline portfolio lab: python scripts/eval_portfolio.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from rag_agent.evaluation.lab import LabConfig, run_lab, write_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline SQLite FTS5 portfolio experiment; no API key or Docker."
    )
    parser.add_argument(
        "--profile",
        choices=["sparse"],
        default="sparse",
        help="Only measured offline sparse retrieval is supported.",
    )
    parser.add_argument("--dataset-dir", type=Path, default=REPO_ROOT / "data/eval/portfolio")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "reports/portfolio")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--sparse-threshold", type=float, default=0.45)
    parser.add_argument("--chunk-size", type=int, default=300)
    parser.add_argument("--chunk-overlap", type=int, default=40)
    args = parser.parse_args()
    try:
        config = LabConfig(
            top_k=args.top_k,
            sparse_threshold=args.sparse_threshold,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        report = run_lab(args.dataset_dir, config=config, repo=REPO_ROOT)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    json_path, markdown_path = write_report(report, args.output_dir)
    print(
        json.dumps(
            {
                name: {"ranking": value["ranking"], "gate": value["gate"]}
                for name, value in report["variants"].items()
            },
            indent=2,
        )
    )
    print(f"JSON: {json_path}\nMarkdown: {markdown_path}")


if __name__ == "__main__":
    main()
