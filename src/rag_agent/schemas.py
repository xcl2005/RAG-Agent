"""Small, explicit data contracts shared by the ingestion and agent layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RawDocument:
    """A text unit produced by a file loader.

    A PDF page is one unit, while a Markdown file is usually one unit. Metadata
    is carried through every later stage so an answer can always be traced back
    to its source.
    """

    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class Chunk:
    """A stable, retrievable piece of a document."""

    chunk_id: str
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class Candidate:
    """One piece of candidate evidence with transparent ranking signals.

    ``score`` is always normalized to the ``[0, 1]`` range. Raw scores remain
    available in their dedicated fields/debug map so ranking can be audited.
    """

    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float = 0.0
    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    matched_queries: list[str] = field(default_factory=list)
    security_flags: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/checkpoint-friendly representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Candidate:
        """Rebuild a candidate after a durable checkpoint round trip."""

        return cls(**value)


@dataclass(slots=True)
class EvidenceAssessment:
    """Decision made by the evidence gate before generation."""

    sufficient: bool
    best_score: float
    score_kind: str
    candidate_count: int
    source_count: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
