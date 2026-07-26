"""Ask the RAG agent from a terminal.

Examples:
    python scripts/query.py "这个系统如何避免没有证据的回答？"
    python scripts/query.py "继续解释上一条" --thread-id demo-thread --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_agent.agent.graph import RAGAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the adaptive RAG agent.")
    parser.add_argument("question", help="Question to ask")
    parser.add_argument("--thread-id", help="Stable conversation ID for checkpointed memory")
    parser.add_argument("--no-trace", action="store_true", help="Omit the node trace from output")
    parser.add_argument("--json", action="store_true", help="Print the complete machine-readable result")
    args = parser.parse_args()

    agent = RAGAgent()
    try:
        result = agent.ask(
            args.question,
            thread_id=args.thread_id,
            include_trace=not args.no_trace,
        )
    finally:
        agent.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("\n回答:")
    print(result["answer"])
    print(f"\n检索查询: {', '.join(result['queries'])}")
    print(f"状态: {result['status']} | 置信度: {result['confidence']:.3f} | trace_id: {result['trace_id']}")
    print("\n来源:")
    for source in result["sources"]:
        print(
            f"[{source['id']}] {source.get('source')} page={source.get('page')} score={source.get('score')}"
        )
        print(f"    {source.get('quote', '')}")


if __name__ == "__main__":
    main()
