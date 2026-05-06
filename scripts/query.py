
"""命令行问答脚本。

用法：
python scripts/query.py "这个系统如何降低幻觉？"

适合在没有前端时快速测试 Agent 效果。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_agent.agent.graph import RAGAgent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the RAG agent from command line.")
    parser.add_argument("question", help="Question to ask")
    args = parser.parse_args()

    result = RAGAgent().ask(args.question)
    print("\n回答：")
    print(result["answer"])
    print("\n检索查询：")
    print(result["query"])
    print("\n来源：")
    for src in result["sources"]:
        print(f"[{src['id']}] {src.get('source')} page={src.get('page')} score={src.get('score')}")
        print(f"    {src.get('preview')}...")


if __name__ == "__main__":
    main()
