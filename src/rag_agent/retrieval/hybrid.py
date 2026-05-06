
"""混合检索模块。

这是 RAG 质量的核心模块之一。
流程：
1. 向量检索 dense search：找语义相近内容。
2. 关键词检索 sparse search：找精确术语、错误码、专有名词。
3. RRF 融合两路结果。
4. 从 SQLite 取回 chunk 原文。
5. reranker 二次排序，选出最终证据。
"""

from __future__ import annotations

from rag_agent.config import Settings
from rag_agent.retrieval.fusion import reciprocal_rank_fusion
from rag_agent.retrieval.reranker import Reranker
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore
from rag_agent.retrieval.vector_store import QdrantVectorStore
from rag_agent.schemas import Candidate


class HybridRetriever:
    """混合检索器。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sqlite = SQLiteChunkStore(settings.sqlite_path)
        self.vector = QdrantVectorStore(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            embedding_model=settings.embedding_model,
        )
        self.reranker = Reranker(settings.reranker_model, enabled=settings.enable_reranker)

    def retrieve(self, query: str, rerank_top_k: int | None = None) -> list[Candidate]:
        """执行完整检索流程。"""

        rerank_top_k = rerank_top_k or self.settings.rerank_top_k

        # 1. Dense search：向量语义召回。
        dense_hits = self.vector.search(query, limit=self.settings.dense_top_k)

        # 2. Sparse search：关键词召回。
        sparse_hits = self.sqlite.search(query, limit=self.settings.sparse_top_k)

        # 3. 提取两个 ranked list 的 chunk_id，用于 RRF。
        dense_ids = [h["chunk_id"] for h in dense_hits]
        sparse_ids = [c.chunk_id for c in sparse_hits]

        # 保存原始分数，方便 API 返回 debug 信息，也方便调参排查。
        dense_score_map = {h["chunk_id"]: h["score"] for h in dense_hits}
        sparse_score_map = {c.chunk_id: c.sparse_score for c in sparse_hits}

        # 4. RRF 融合。注意 fused 是 {chunk_id: rrf_score}。
        fused = reciprocal_rank_fusion([dense_ids, sparse_ids], k=self.settings.rrf_k)
        fused_ids = [doc_id for doc_id, _ in sorted(fused.items(), key=lambda x: x[1], reverse=True)]
        fused_ids = fused_ids[: self.settings.fusion_top_k]

        # 5. 根据 chunk_id 回 SQLite 取原文。
        chunk_map = self.sqlite.get_chunks(fused_ids)
        candidates: list[Candidate] = []
        for cid in fused_ids:
            c = chunk_map.get(cid)
            if c is None:
                continue
            c.score = fused[cid]
            c.dense_score = dense_score_map.get(cid)
            c.sparse_score = sparse_score_map.get(cid)
            c.debug = {"rrf_score": fused[cid]}
            candidates.append(c)

        # 6. Rerank 精排，返回最终给 LLM 的 topK 证据。
        return self.reranker.rerank(query, candidates, top_k=rerank_top_k)
