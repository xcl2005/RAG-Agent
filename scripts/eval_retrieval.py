
"""简单检索评估脚本。

RAG 调优不能只凭感觉，要有一个小评估集。
本脚本读取 JSONL：
{"question": "...", "expected_keywords": ["关键词1", "关键词2"]}

然后检查检索出来的 top chunks 里是否包含这些关键词。
这不是严格学术评估，但足够帮你比较 chunk_size、top_k、rerank 开关等参数。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_agent.config import settings  # noqa: E402
from rag_agent.retrieval.hybrid import HybridRetriever  # noqa: E402


def hit_expected_keywords(text: str, keywords: list[str]) -> bool:
    """判断检索内容是否覆盖期望关键词。"""

    return all(k.lower() in text.lower() for k in keywords)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple retrieval evaluation by expected keywords.")
    parser.add_argument("--file", required=True, help="JSONL file: {question, expected_keywords}")
    args = parser.parse_args()

    retriever = HybridRetriever(settings)
    total = 0
    hit = 0

    with open(args.file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            item = json.loads(line)
            question = item["question"]
            expected = item.get("expected_keywords", [])
            candidates = retriever.retrieve(question)
            joined = "\n".join(c.text for c in candidates)
            ok = hit_expected_keywords(joined, expected)

            total += 1
            hit += int(ok)
            print(f"question={question} hit={ok} top_sources={[c.metadata.get('source') for c in candidates[:3]]}")

    print({"total": total, "hit": hit, "hit_rate": hit / total if total else 0})


if __name__ == "__main__":
    main()
