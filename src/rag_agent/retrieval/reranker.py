
"""Reranker 重排序模块。

为什么有了向量检索还要 rerank？
- 向量检索适合快速召回，但排序不一定精确。
- CrossEncoder 会同时看 query 和 chunk，判断这段文本是否真的能回答问题。
- 典型流程是：先 top40 粗召回，再 rerank 选 top8 给 LLM。
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from rag_agent.schemas import Candidate
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)


class Reranker:
    """CrossEncoder reranker 封装。"""

    def __init__(self, model_name: str, enabled: bool = True):
        self.enabled = enabled
        self.model_name = model_name
        self.model: CrossEncoder | None = None

        # reranker 模型首次下载可能失败，所以这里做降级处理。
        # 降级后项目仍可运行，只是不做二阶段精排。
        if enabled:
            try:
                logger.info("Loading reranker: %s", model_name)
                self.model = CrossEncoder(model_name)
            except Exception as exc:  # pragma: no cover - depends on local model download
                logger.warning("Reranker failed to load, fallback to fusion score. Error: %s", exc)
                self.enabled = False
                self.model = None

    def rerank(self, query: str, candidates: list[Candidate], top_k: int) -> list[Candidate]:
        """对候选 chunk 重新排序。"""

        if not candidates:
            return []

        # 如果 reranker 不可用，就直接按 RRF 融合分数返回。
        if not self.enabled or self.model is None:
            return sorted(candidates, key=lambda x: x.score, reverse=True)[:top_k]

        # CrossEncoder 输入是 (问题, 文档片段) 对。
        pairs = [(query, c.text) for c in candidates]
        scores = self.model.predict(pairs)
        for c, s in zip(candidates, scores):
            c.rerank_score = float(s)
            c.score = float(s)
        return sorted(candidates, key=lambda x: x.score, reverse=True)[:top_k]
