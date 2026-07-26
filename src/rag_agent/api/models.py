"""Pydantic HTTP contracts shown in the generated OpenAPI documentation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=100_000, description="用户问题")
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="复用该 ID 可启用 LangGraph 多轮状态",
    )
    include_trace: bool = Field(default=True, description="是否返回节点级调试事件")


class SourceResponse(BaseModel):
    id: str
    chunk_id: str
    title: str
    source: str
    page: int | None = None
    heading: str | None = None
    chunk_index: int | None = None
    score: float
    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    matched_queries: list[str] = Field(default_factory=list)
    security_flags: list[str] = Field(default_factory=list)
    quote: str


class ChatResponse(BaseModel):
    question: str
    thread_id: str
    trace_id: str
    status: str
    answer: str
    abstained: bool
    confidence: float
    query: str
    queries: list[str]
    sources: list[SourceResponse]
    evidence: dict[str, Any]
    citation_validation: dict[str, Any]
    usage: dict[str, Any]
    error: str | None = None
    trace: list[dict[str, Any]] | None = None
    model_calls: list[dict[str, Any]] | None = None


class IngestPathRequest(BaseModel):
    path: str = Field(default="data/raw", min_length=1, max_length=1000)
    force: bool = Field(default=False, description="内容哈希未变化时也重新索引")
    reset: bool = Field(default=False, description="危险操作：先清空整个索引")
