"""Index local documents into the SQLite + Qdrant hybrid knowledge base.

Examples:
    python scripts/ingest.py --path data/raw
    python scripts/ingest.py --path data/raw --force --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_agent.ingest.indexer import Indexer


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into the hybrid index.")
    parser.add_argument("--path", default="data/raw", help="Supported file or directory to ingest")
    parser.add_argument("--reset", action="store_true", help="Clear both indexes before ingestion")
    parser.add_argument("--force", action="store_true", help="Re-index unchanged documents")
    parser.add_argument("--json", action="store_true", help="Print a formatted JSON report")
    args = parser.parse_args()

    indexer = Indexer()
    try:
        result = indexer.ingest_path(args.path, reset=args.reset, force=args.force)
    finally:
        indexer.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "Ingestion complete: "
            f"indexed={result['indexed_files']} "
            f"skipped={result['skipped_files']} "
            f"failed={result['failed_files']} "
            f"chunks={result['chunks']}"
        )


if __name__ == "__main__":
    main()
