"""Lazy cross-encoder reranking with calibrated relevance scores."""

from __future__ import annotations

import math
from typing import Any

from rag_agent.schemas import Candidate
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)


class Reranker:
    """CrossEncoder reranker 封装。"""

    def __init__(
        self,
        model_name: str,
        enabled: bool = True,
        *,
        score_mode: str = "logit",
    ):
        self.enabled = enabled
        self.model_name = model_name
        self.score_mode = score_mode
        self.model: Any | None = None
        self.load_error: str | None = None

    def _ensure_model(self) -> bool:
        """Load on first use so API liveness does not depend on model download."""

        if not self.enabled:
            return False
        if self.model is not None:
            return True
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading reranker: %s", self.model_name)
            self.model = CrossEncoder(self.model_name)
            return True
        except Exception as exc:  # pragma: no cover - depends on model/network
            self.load_error = str(exc)
            self.enabled = False
            logger.warning("Reranker unavailable; using fusion ranking: %s", exc)
            return False

    @staticmethod
    def _normalize(raw_scores: list[float], score_mode: str) -> list[float]:
        """Map an explicitly declared score contract to ``[0, 1]``.

        This is normalization, not statistical calibration. True calibration
        requires a labeled relevance set. Crucially, the transform never
        changes based on which other candidates happen to share the batch.
        """

        if score_mode == "probability":
            return [min(max(score, 0.0), 1.0) for score in raw_scores]
        if score_mode != "logit":
            raise ValueError(f"unsupported reranker score mode: {score_mode}")

        normalized: list[float] = []
        for value in raw_scores:
            # Stable sigmoid avoids overflow for large negative logits.
            if value >= 0:
                normalized.append(1.0 / (1.0 + math.exp(-value)))
            else:
                exp_value = math.exp(value)
                normalized.append(exp_value / (1.0 + exp_value))
        return normalized

    @staticmethod
    def _fusion_fallback(candidates: list[Candidate], top_k: int) -> list[Candidate]:
        """Keep the deterministic fusion order when reranking is unavailable."""

        return sorted(candidates, key=lambda item: item.score, reverse=True)[:top_k]

    def rerank_with_debug(
        self,
        query: str,
        candidates: list[Candidate],
        top_k: int,
    ) -> tuple[list[Candidate], str | None]:
        """Rerank candidates and return a request-local degradation reason."""

        if not candidates:
            return [], None

        # 如果 reranker 不可用，就直接按已归一化的 fusion score 返回。
        if not self._ensure_model() or self.model is None:
            error = "model_load_failed" if self.load_error else None
            return self._fusion_fallback(candidates, top_k), error

        try:
            # CrossEncoder 输入是 (问题, 文档片段) 对。
            pairs = [(query, candidate.text) for candidate in candidates]
            predicted = self.model.predict(pairs, show_progress_bar=False)
            raw_scores = [float(score) for score in predicted]
            if len(raw_scores) != len(candidates):
                raise RuntimeError("reranker returned a different number of scores than candidates")
            normalized = self._normalize(raw_scores, self.score_mode)
        except Exception as exc:
            # Inference can fail after a successful model load (for example an
            # OOM). Preserve availability and expose only the exception class in
            # request diagnostics; the full detail remains in server logs.
            logger.exception("Reranker inference failed; using fusion ranking")
            reason = f"inference_failed:{type(exc).__name__}"
            return self._fusion_fallback(candidates, top_k), reason

        for candidate, raw, relevance in zip(candidates, raw_scores, normalized, strict=True):
            candidate.rerank_score = raw
            candidate.score = relevance
            candidate.debug["rerank_relevance"] = relevance
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:top_k], None

    def rerank(self, query: str, candidates: list[Candidate], top_k: int) -> list[Candidate]:
        """Compatibility API for callers that do not need degradation details."""

        reranked, _ = self.rerank_with_debug(query, candidates, top_k)
        return reranked
