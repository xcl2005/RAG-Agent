"""Run a versioned offline retrieval benchmark and write JSON/Markdown reports.

Dataset JSONL schema:
    {
      "id": "citation-001",
      "question": "...",
      "relevant_sources": ["sample.md"],
      "expected_keywords": ["引用", "证据"],
      "should_answer": true,
      "tags": ["semantic"]
    }

Source judgments are preferred. Expected keywords remain a convenient fallback
for tiny demo datasets whose chunk IDs are not stable across chunking profiles.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_agent.config import settings
from rag_agent.evaluation.metrics import aggregate_rankings
from rag_agent.retrieval.hybrid import HybridRetriever


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not case.get("question"):
                raise ValueError(f"{path}:{line_number}: question is required")
            cases.append(case)
    return cases


def candidate_keys(candidate: Any, case: dict[str, Any]) -> set[str]:
    """Map one result to relevant labels for source or keyword judgments."""

    keys: set[str] = set()
    judged_sources = {Path(value).name for value in case.get("relevant_sources", [])}
    source = Path(str(candidate.metadata.get("source", ""))).name
    if judged_sources:
        if source in judged_sources:
            keys.add(f"source:{source}")
    else:
        text = candidate.text.casefold()
        keywords = [str(value).casefold() for value in case.get("expected_keywords", [])]
        if keywords and all(keyword in text for keyword in keywords):
            keys.add("keyword_match")
    return keys


def relevant_keys(case: dict[str, Any]) -> set[str]:
    keys = {f"source:{Path(value).name}" for value in case.get("relevant_sources", [])}
    if not keys and case.get("expected_keywords"):
        keys.add("keyword_match")
    return keys


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * ratio), len(ordered) - 1)
    return ordered[index]


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Retrieval Evaluation Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Cases: `{report['case_count']}`",
        f"- Model: `{report['config']['embedding_model']}`",
        f"- Reranker: `{report['config']['reranker_model']}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {value:.4f} |" for name, value in metrics.items())
    lines.extend(
        [
            "",
            "## Latency",
            "",
            f"- mean: `{report['latency_ms']['mean']:.2f} ms`",
            f"- p50: `{report['latency_ms']['p50']:.2f} ms`",
            f"- p95: `{report['latency_ms']['p95']:.2f} ms`",
            "",
            "## Per-case",
            "",
            "| ID | Results | Latency |",
            "|---|---:|---:|",
        ]
    )
    lines.extend(
        f"| {case['id']} | {case['result_count']} | {case['latency_ms']:.2f} ms |" for case in report["cases"]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ranked retrieval with Recall/MRR/nDCG.")
    parser.add_argument(
        "--file",
        default="data/eval/sample_retrieval.jsonl",
        help="Versioned JSONL evaluation set",
    )
    parser.add_argument("--output-dir", default="reports", help="Report directory")
    args = parser.parse_args()

    cases = load_cases(Path(args.file))
    retriever = HybridRetriever(settings)
    rankings: list[tuple[list[str], set[str]]] = []
    case_reports: list[dict[str, Any]] = []
    latencies: list[float] = []

    try:
        for index, case in enumerate(cases, start=1):
            started = time.perf_counter()
            candidates = retriever.retrieve(case["question"])
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)

            ranked_labels: list[str] = []
            for candidate in candidates:
                labels = candidate_keys(candidate, case)
                ranked_labels.append(next(iter(labels), f"irrelevant:{candidate.chunk_id}"))

            judgments = relevant_keys(case)
            if judgments:
                rankings.append((ranked_labels, judgments))
            case_reports.append(
                {
                    "id": case.get("id", f"case-{index:03d}"),
                    "question": case["question"],
                    "tags": case.get("tags", []),
                    "result_count": len(candidates),
                    "latency_ms": round(latency_ms, 2),
                    "top_sources": [candidate.metadata.get("source") for candidate in candidates[:3]],
                }
            )
    finally:
        retriever.close()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "metrics": aggregate_rankings(rankings),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 2) if latencies else 0.0,
            "p50": round(percentile(latencies, 0.5), 2),
            "p95": round(percentile(latencies, 0.95), 2),
        },
        "config": {
            "python": platform.python_version(),
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
            "dense_top_k": settings.dense_top_k,
            "sparse_top_k": settings.sparse_top_k,
            "fusion_top_k": settings.fusion_top_k,
            "rerank_top_k": settings.rerank_top_k,
        },
        "cases": case_reports,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "retrieval-eval.json"
    markdown_path = output_dir / "retrieval-eval.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print(f"wrote {json_path} and {markdown_path}")


if __name__ == "__main__":
    main()
