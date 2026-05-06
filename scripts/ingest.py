
"""命令行导入脚本。

用法：
python scripts/ingest.py --path data/raw --reset

它会调用 Indexer，把指定路径下的资料导入 SQLite + Qdrant。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 让脚本可以直接从项目根目录运行，不必先 pip install -e .
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_agent.ingest.indexer import Indexer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant and SQLite indexes.")
    parser.add_argument("--path", default="data/raw", help="File or directory path to ingest")
    parser.add_argument("--reset", action="store_true", help="Reset existing indexes before ingesting")
    args = parser.parse_args()

    result = Indexer().ingest_path(args.path, reset=args.reset)
    print(result)


if __name__ == "__main__":
    main()
