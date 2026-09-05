"""Run the bounded tool-agent demo from a terminal.

This is intentionally separate from the main RAG workflow so the project can
teach tool-runtime mechanics without silently changing the stable chat path.
"""

from __future__ import annotations

import argparse
import json

from rag_agent.agent.tooling import BoundedToolAgent, build_knowledge_tool_registry
from rag_agent.config import settings
from rag_agent.llm.client import LLMClient
from rag_agent.retrieval.hybrid import HybridRetriever


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded read-only tool Agent.")
    parser.add_argument("question", help="Question for the Agent.")
    parser.add_argument("--max-steps", type=int, default=4, help="Maximum model/tool decisions.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    retriever = HybridRetriever(settings)
    registry = build_knowledge_tool_registry(retriever)
    try:
        result = BoundedToolAgent(
            LLMClient(settings),
            registry,
            max_steps=args.max_steps,
        ).run(args.question)
    finally:
        registry.close()
        retriever.close()

    payload = {
        "answer": result.answer,
        "failure_kind": result.failure_kind,
        "steps": result.steps,
        "llm_calls": result.llm_calls,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if result.answer:
            print(result.answer)
        else:
            print(f"Agent failed: {result.failure_kind}")
        for step in result.steps:
            print(f"- step {step['step']}: {step['tool_name']} -> {step['status']} ({step['latency_ms']} ms)")
    return 0 if result.failure_kind is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
