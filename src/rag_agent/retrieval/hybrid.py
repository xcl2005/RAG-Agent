"""Multi-query dense + lexical retrieval with weighted RRF and reranking."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from rag_agent.config import Settings
from rag_agent.retrieval.fusion import normalize_rrf_scores, weighted_reciprocal_rank_fusion
from rag_agent.retrieval.reranker import Reranker
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore
from rag_agent.retrieval.vector_store import QdrantVectorStore
from rag_agent.schemas import Candidate
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)


class HybridRetriever:
    """Retrieve broad candidates, fuse ranks, then apply an optional reranker."""

    def __init__(self, app_settings: Settings):
        self.settings = app_settings
        self.sqlite = SQLiteChunkStore(app_settings.sqlite_path)
        self.vector = QdrantVectorStore(
            url=app_settings.qdrant_url,
            api_key=app_settings.qdrant_api_key,
            collection_name=app_settings.qdrant_collection,
            embedding_model=app_settings.embedding_model,
        )
        self.reranker = Reranker(
            app_settings.reranker_model,
            enabled=app_settings.enable_reranker,
            score_mode=app_settings.reranker_score_mode,
        )
        self.last_debug: dict[str, Any] = {}

    def retrieve(self, query: str, rerank_top_k: int | None = None) -> list[Candidate]:
        """Compatibility entry point for a single query."""

        return self.retrieve_many(
            [query],
            rerank_query=query,
            rerank_top_k=rerank_top_k,
        )

    def retrieve_many(
        self,
        queries: list[str],
        *,
        rerank_query: str,
        rerank_top_k: int | None = None,
    ) -> list[Candidate]:
        """Compatibility list-only API used by CLI/MCP callers."""

        candidates, debug = self.retrieve_many_with_debug(
            queries,
            rerank_query=rerank_query,
            rerank_top_k=rerank_top_k,
        )
        self.last_debug = debug
        return candidates

    def retrieve_many_with_debug(
        self,
        queries: list[str],
        *,
        rerank_query: str,
        rerank_top_k: int | None = None,
    ) -> tuple[list[Candidate], dict[str, Any]]:
        """Search complementary query variants and transparently fuse all ranks."""

        unique_queries = list(dict.fromkeys(query.strip() for query in queries if query.strip()))
        if not unique_queries:
            return [], {"queries": [], "backend_errors": []}

        top_k = rerank_top_k or self.settings.rerank_top_k
        rankings: list[tuple[list[str], float]] = []
        dense_scores: dict[str, float] = {}
        sparse_scores: dict[str, float] = {}
        matched_queries: dict[str, set[str]] = defaultdict(set)
        rank_debug: dict[str, list[dict[str, Any]]] = defaultdict(list)
        backend_errors: list[str] = []

        for query_index, query in enumerate(unique_queries):
            # Generated variants are useful for recall but should not overpower
            # exact entities/error codes in the original user wording.
            query_weight = 1.0 if query_index == 0 else max(0.45, 0.7 - 0.1 * (query_index - 1))

            try:
                dense_hits = self.vector.search(query, limit=self.settings.dense_top_k)
            except Exception as exc:  # Allow lexical degradation if Qdrant is down.
                dense_hits = []
                backend_errors.append(f"dense[{query_index}]: {type(exc).__name__}")
                # Do not write a potentially confidential user query to logs.
                logger.warning("Dense retrieval failed for query index %d: %s", query_index, exc)

            dense_ids = [str(hit["chunk_id"]) for hit in dense_hits]
            if dense_ids:
                weight = self.settings.dense_weight * query_weight
                rankings.append((dense_ids, weight))
                for rank, hit in enumerate(dense_hits, start=1):
                    chunk_id = str(hit["chunk_id"])
                    dense_scores[chunk_id] = max(
                        dense_scores.get(chunk_id, float("-inf")),
                        float(hit["score"]),
                    )
                    matched_queries[chunk_id].add(query)
                    rank_debug[chunk_id].append(
                        {"backend": "dense", "query": query, "rank": rank, "weight": weight}
                    )

            try:
                sparse_hits = self.sqlite.search(query, limit=self.settings.sparse_top_k)
            except Exception as exc:
                sparse_hits = []
                backend_errors.append(f"sparse[{query_index}]: {type(exc).__name__}")
                logger.warning("Sparse retrieval failed for query index %d: %s", query_index, exc)

            sparse_ids = [candidate.chunk_id for candidate in sparse_hits]
            if sparse_ids:
                weight = self.settings.sparse_weight * query_weight
                rankings.append((sparse_ids, weight))
                for rank, candidate in enumerate(sparse_hits, start=1):
                    sparse_scores[candidate.chunk_id] = max(
                        sparse_scores.get(candidate.chunk_id, float("-inf")),
                        float(candidate.sparse_score or 0.0),
                    )
                    matched_queries[candidate.chunk_id].add(query)
                    rank_debug[candidate.chunk_id].append(
                        {"backend": "sparse", "query": query, "rank": rank, "weight": weight}
                    )

        if not rankings:
            return [], {"queries": unique_queries, "backend_errors": backend_errors}

        raw_fusion = weighted_reciprocal_rank_fusion(rankings, k=self.settings.rrf_k)
        total_weight = sum(weight for _, weight in rankings)
        normalized = normalize_rrf_scores(
            raw_fusion,
            total_weight=total_weight,
            k=self.settings.rrf_k,
        )
        fused_ids = sorted(
            normalized,
            key=lambda chunk_id: normalized[chunk_id],
            reverse=True,
        )
        fused_ids = fused_ids[: self.settings.fusion_top_k]
        chunk_map = self.sqlite.get_chunks(fused_ids)

        candidates: list[Candidate] = []
        for chunk_id in fused_ids:
            resolved_candidate = chunk_map.get(chunk_id)
            if resolved_candidate is None:
                continue
            resolved_candidate.score = normalized[chunk_id]
            resolved_candidate.fusion_score = normalized[chunk_id]
            resolved_candidate.dense_score = dense_scores.get(chunk_id)
            resolved_candidate.sparse_score = sparse_scores.get(chunk_id)
            resolved_candidate.matched_queries = sorted(matched_queries[chunk_id])
            resolved_candidate.debug = {
                "rrf_raw": raw_fusion[chunk_id],
                "rank_hits": rank_debug[chunk_id],
            }
            candidates.append(resolved_candidate)

        reranked, reranker_error = self.reranker.rerank_with_debug(
            rerank_query,
            candidates,
            top_k=top_k,
        )
        if reranker_error:
            backend_errors.append(f"reranker: {reranker_error}")
        debug = {
            "queries": unique_queries,
            "ranking_count": len(rankings),
            "fused_count": len(candidates),
            "returned_count": len(reranked),
            "reranker_enabled": self.reranker.enabled,
            "backend_errors": backend_errors,
        }
        return reranked, debug

    def ready(self) -> dict[str, dict[str, str | bool]]:
        sqlite_ok, sqlite_detail = self.sqlite.ready()
        qdrant_ok, qdrant_detail = self.vector.ready()
        return {
            "sqlite": {"ready": sqlite_ok, "detail": sqlite_detail},
            "qdrant": {"ready": qdrant_ok, "detail": qdrant_detail},
        }

    def close(self) -> None:
        self.sqlite.close()
