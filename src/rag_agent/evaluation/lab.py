"""A small, offline retrieval experiment that a beginner can inspect end to end.

Only the query expansion switch changes between the two runs. Both use the real
project chunker, SQLite FTS5 search and RRF function. No answer is generated, so
the gate metrics describe retrieval decisions, never LLM answer correctness.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sqlite3
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag_agent.evaluation.metrics import aggregate_rankings, answerability_metrics, mean
from rag_agent.ingest.chunker import chunk_document
from rag_agent.retrieval.fusion import weighted_reciprocal_rank_fusion
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore
from rag_agent.schemas import Candidate, RawDocument

# This is an explicit teaching baseline, not a learned planner. Keep the rules
# in the report so an interviewer can see exactly what the ablation changed.
EXPANSION_RULES = (
    (("backoff", "退避"), "重试 指数退避 随机抖动"),
    (("chunk", "overlap"), "分块 重叠"),
    (("prompt injection", "提示注入"), "提示注入 系统规则 文档指令"),
    (("上线", "deployment"), "发布 部署 预发布 检查"),
    (("rollback", "回滚"), "回滚 稳定镜像 错误率"),
    (("idempotency", "幂等"), "幂等 request_id 重试 缓存"),
)


@dataclass(frozen=True)
class LabConfig:
    """Explicit parameters; intentionally does not read the application's .env."""

    chunk_size: int = 300
    chunk_overlap: int = 40
    candidate_k: int = 20
    top_k: int = 5
    sparse_threshold: float = 0.45
    rrf_k: int = 60
    expansion_weight: float = 0.7

    def __post_init__(self) -> None:
        if self.chunk_size < 1 or not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("chunk_overlap must be nonnegative and smaller than chunk_size")
        if self.top_k < 1 or self.candidate_k < self.top_k or self.rrf_k < 1:
            raise ValueError("require candidate_k >= top_k >= 1 and rrf_k >= 1")
        if not 0 < self.sparse_threshold <= 1 or not 0 < self.expansion_weight <= 1:
            raise ValueError("threshold and expansion_weight must be in (0, 1]")


def expand_query(question: str) -> list[str]:
    """Preserve the original wording; append at most two terminology variants."""

    variants = [question]
    for triggers, expansion in EXPANSION_RULES:
        if any(trigger in question.casefold() for trigger in triggers):
            variants.append(expansion)
    return list(dict.fromkeys(variants))[:3]


def load_dataset(root: Path) -> tuple[dict[str, str], list[dict[str, Any]], str]:
    """Validate source labels and evidence excerpts before any retrieval runs.

    A digest covers exact corpus/case bytes AND relative filenames. Absolute
    machine paths are excluded, so copying the dataset preserves its identity.
    """

    files = sorted((root / "corpus").glob("*.md"))
    if not files:
        raise ValueError("dataset needs corpus/*.md")
    documents = {path.name: path.read_text(encoding="utf-8") for path in files}
    cases_path = root / "cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases.json must be a nonempty list")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("every case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("case IDs must be unique nonempty strings")
        seen.add(case_id)
        if not isinstance(case.get("question"), str) or not case["question"].strip():
            raise ValueError(f"{case_id}: question required")
        sources = case.get("relevant_sources")
        if not isinstance(sources, list) or any(not isinstance(item, str) for item in sources):
            raise ValueError(f"{case_id}: relevant_sources must be a string list")
        if len(sources) != len(set(sources)) or not set(sources) <= documents.keys():
            raise ValueError(f"{case_id}: duplicate or unknown relevant source")
        if not isinstance(case.get("should_answer"), bool) or case["should_answer"] != bool(sources):
            raise ValueError(f"{case_id}: answerability and source labels disagree")
        evidence = case.get("evidence", {})
        if not isinstance(evidence, dict) or set(evidence) != set(sources):
            raise ValueError(f"{case_id}: evidence must cover exactly the relevant sources")
        for name, excerpt in evidence.items():
            if not isinstance(excerpt, str) or not excerpt or excerpt not in documents[name]:
                raise ValueError(f"{case_id}: evidence excerpt missing in {name}")
        if not sources and not case.get("reason"):
            raise ValueError(f"{case_id}: negative case needs an explanation")
        if not isinstance(case.get("tags"), list) or any(not isinstance(tag, str) for tag in case["tags"]):
            raise ValueError(f"{case_id}: tags must be a string list")
    digest = hashlib.sha256()
    for path in sorted([*files, cases_path]):
        for part in (path.relative_to(root).as_posix().encode(), path.read_bytes()):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return documents, cases, digest.hexdigest()


def _index_documents(store: SQLiteChunkStore, documents: dict[str, str], config: LabConfig) -> None:
    for source, text in sorted(documents.items()):
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        document_id = hashlib.sha256(source.encode("utf-8")).hexdigest()
        raw = RawDocument(text, {"source": source, "document_id": document_id, "title": source})
        chunks = chunk_document(raw, config.chunk_size, config.chunk_overlap)
        store.replace_document_chunks(
            document_id=document_id,
            source=source,
            content_hash=content_hash,
            index_fingerprint=json.dumps(asdict(config), sort_keys=True),
            chunks=chunks,
        )


def retrieve_sparse(store: SQLiteChunkStore, queries: list[str], config: LabConfig) -> list[Candidate]:
    """Fuse real FTS rankings; max token coverage remains separate from RRF."""

    rankings: list[tuple[list[str], float]] = []
    candidates: dict[str, Candidate] = {}
    for index, query in enumerate(queries):
        hits = store.search(query, limit=config.candidate_k)
        rankings.append(([hit.chunk_id for hit in hits], 1.0 if index == 0 else config.expansion_weight))
        for hit in hits:
            previous = candidates.get(hit.chunk_id)
            if previous is None or (hit.sparse_score or 0) > (previous.sparse_score or 0):
                candidates[hit.chunk_id] = hit
    scores = weighted_reciprocal_rank_fusion(rankings, k=config.rrf_k)
    ranked_ids = sorted(scores, key=lambda item: (-scores[item], item))
    for chunk_id, score in scores.items():
        candidates[chunk_id].fusion_score = score
    return [candidates[item] for item in ranked_ids[: config.candidate_k]]


def _measure_case(
    store: SQLiteChunkStore, case: dict[str, Any], config: LabConfig, *, expanded: bool
) -> dict[str, Any]:
    started = time.perf_counter()
    queries = expand_query(case["question"]) if expanded else [case["question"]]
    candidates = retrieve_sparse(store, queries, config)
    # Keep unjudged sources in the ranked list: removing them would artificially
    # improve MRR. Deduplicate before K because labels are document-level.
    ranked_sources = list(dict.fromkeys(str(hit.metadata["source"]) for hit in candidates))[: config.top_k]
    selected = [hit for hit in candidates if hit.metadata["source"] in ranked_sources]
    best_coverage = max((hit.sparse_score or 0 for hit in selected), default=0.0)
    gate_passed = bool(selected) and best_coverage >= config.sparse_threshold
    latency_ms = (time.perf_counter() - started) * 1000
    relevant = set(case["relevant_sources"])
    return {
        "id": case["id"],
        "question": case["question"],
        "tags": case["tags"],
        "queries": queries,
        "relevant_sources": sorted(relevant),
        "ranked_sources": ranked_sources,
        "should_answer": case["should_answer"],
        "gate_should_answer": gate_passed,
        "best_sparse_coverage": round(best_coverage, 6),
        "all_relevant_retrieved": relevant <= set(ranked_sources) if relevant else None,
        "latency_ms": round(latency_ms, 4),
        "retrieved_chunks": [
            {
                "chunk_id": hit.chunk_id,
                "source": hit.metadata["source"],
                "sparse_coverage": hit.sparse_score,
                "rrf_raw": hit.fusion_score,
            }
            for hit in selected
        ],
    }


def _aggregate(rows: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    answerable = [row for row in rows if row["should_answer"]]
    rankings = [(row["ranked_sources"], set(row["relevant_sources"])) for row in answerable]
    latencies = sorted(row["latency_ms"] for row in rows)
    metrics = aggregate_rankings(rankings, k_values=tuple(sorted({1, top_k})))
    return {
        "case_count": len(rows),
        "ranking_case_count": len(answerable),
        "ranking": metrics,
        "gate": answerability_metrics((row["should_answer"], row["gate_should_answer"]) for row in rows),
        "all_relevant_retrieved_rate": round(mean(row["all_relevant_retrieved"] for row in answerable), 6),
        "latency_ms": {
            "mean": round(mean(latencies), 4),
            "p50": latencies[max(0, math.ceil(len(latencies) * 0.5) - 1)] if latencies else 0,
            "p95": latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)] if latencies else 0,
        },
    }


def _git_metadata(repo: Path) -> dict[str, str | bool | None]:
    def run(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL, timeout=5
        ).strip()

    try:
        return {"revision": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty": None}


def run_lab(
    dataset_dir: Path, *, config: LabConfig | None = None, repo: Path | None = None
) -> dict[str, Any]:
    """Build a disposable index and measure paired baseline/expansion cases.

    Labels are used only after retrieval, never as query hints or ranking input.
    TemporaryDirectory owns only this run's new index and cleans up on failure.
    """

    config = config or LabConfig()
    documents, cases, digest = load_dataset(dataset_dir)
    runs: dict[str, list[dict[str, Any]]] = {"baseline": [], "expanded": []}
    started = time.perf_counter()
    with (
        tempfile.TemporaryDirectory(prefix="rag-portfolio-eval-") as directory,
        SQLiteChunkStore(Path(directory) / "chunks.db") as store,
    ):
        _index_documents(store, documents, config)
        chunk_count = store.count()
        # Initialize SQLite's search path; startup is reported separately.
        store.search("__lab_warmup__", limit=1)
        setup_ms = (time.perf_counter() - started) * 1000
        for index, case in enumerate(cases):
            # Alternation reduces a consistent first-run cache advantage.
            order = ("baseline", "expanded") if index % 2 == 0 else ("expanded", "baseline")
            for name in order:
                runs[name].append(_measure_case(store, case, config, expanded=name == "expanded"))
    variants: dict[str, Any] = {}
    for name, rows in runs.items():
        variants[name] = {
            **_aggregate(rows, config.top_k),
            "by_tag": {
                tag: _aggregate([row for row in rows if tag in row["tags"]], config.top_k)
                for tag in sorted({tag for row in rows for tag in row["tags"]})
            },
            "cases": rows,
        }
    delta = {
        metric: round(variants["expanded"]["ranking"][metric] - value, 6)
        for metric, value in variants["baseline"]["ranking"].items()
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": "sparse",
        "scope": "Synthetic development set; FTS5 retrieval + lexical gate only; no dense, reranker or LLM.",
        "dataset_sha256": digest,
        "dataset": {
            "documents": len(documents),
            "chunks": chunk_count,
            "cases": len(cases),
            "split": "development",
        },
        "git": _git_metadata(repo or Path.cwd()),
        "environment": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.system(),
        },
        "config": {**asdict(config), "expansion_rules": EXPANSION_RULES},
        "timing": {
            "setup_ms": round(setup_ms, 4),
            "query_scope": "query expansion + search + fusion + source deduplication + gate; excludes index setup/report I/O",
            "schedule": "one paired pass; alternating baseline/expanded order; nearest-rank percentiles",
        },
        "variants": variants,
        "expanded_minus_baseline": delta,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Readable evidence, including failures rather than just headline scores."""

    lines = [
        "# 离线检索实验报告",
        "",
        "这是虚构开发集上的真实 FTS5 检索测量；没有调用 LLM，也没有测量 dense 或重排效果。",
        "门控错误放行是风险代理指标，不等于模型已生成错误答案。参数和术语表未经过独立测试集验证。",
        "",
        f"- 数据：{report['dataset']['documents']} 份文档 / {report['dataset']['chunks']} 块 / {report['dataset']['cases']} 问题",
        f"- 数据集 SHA256：`{report['dataset_sha256']}`",
        f"- Git：`{report['git']['revision']}`；dirty：`{report['git']['dirty']}`",
        f"- 生成时间：`{report['generated_at']}`；建库耗时：{report['timing']['setup_ms']:.2f} ms",
        "",
        "| 指标 | 原问题 baseline | 术语扩展 expanded |",
        "|---|---:|---:|",
    ]
    baseline, expanded = (report["variants"][name] for name in ("baseline", "expanded"))
    for group in ("ranking", "gate", "latency_ms"):
        for metric, value in baseline[group].items():
            lines.append(f"| {group}.{metric} | {value} | {expanded[group][metric]} |")
    lines.extend(
        [
            "",
            "排序指标只统计可回答问题；先按来源去重再截取 K。门控指标统计所有问题。",
            "延迟仅包含查询扩展、检索、融合、来源去重和门控，不是 API 或生成答案的耗时。单次小样本时延仅供本机实验参考。",
            "",
            "## 逐题结果",
            "",
            "| 变体 | ID | 应放行 | 实际放行 | 找齐相关来源 | 返回来源 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for name, variant in report["variants"].items():
        for row in variant["cases"]:
            lines.append(
                f"| {name} | {row['id']} | {row['should_answer']} | {row['gate_should_answer']} | "
                f"{row['all_relevant_retrieved']} | {', '.join(row['ranked_sources'])} |"
            )
    lines.extend(
        [
            "",
            "## 参数与环境",
            "",
            "```json",
            json.dumps(
                {
                    "config": report["config"],
                    "environment": report["environment"],
                    "timing": report["timing"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "逐题问题、查询变体、分块 ID、覆盖分数和按类别指标见同名 JSON。",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write a new timestamped pair, preserving previous experiment reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stem = f"portfolio-{report['profile']}-{stamp}"
    json_path, markdown_path = output_dir / f"{stem}.json", output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path
