"""Qdrant dense retrieval with lazy model loading and schema checks."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models

from rag_agent.schemas import Chunk


class IndexSchemaMismatch(RuntimeError):
    """The existing collection was built with an incompatible vector schema."""


def point_id_from_chunk_id(chunk_id: str) -> str:
    """把 sha256 chunk_id 转成 Qdrant 支持的 UUID 字符串。"""

    # Qdrant 支持 UUID 字符串作为 point id。
    # chunk_id 是 64 位 hex，这里取前 32 位转 UUID，稳定且足够用。
    return str(uuid.UUID(chunk_id[:32]))


class QdrantVectorStore:
    """Qdrant 向量数据库封装。"""

    def __init__(
        self,
        url: str,
        collection_name: str,
        embedding_model: str,
        api_key: str = "",
    ):
        self.client = QdrantClient(url=url, api_key=api_key or None, timeout=15)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.model = None
        self.vector_size: int | None = None

    def _ensure_model(self) -> None:
        """Load the embedding model only when indexing/search is requested."""

        if self.model is not None:
            return
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.embedding_model_name)
        self.model = model
        self.vector_size = int(model.get_sentence_embedding_dimension())

    def _validate_vector_config(
        self,
        vectors: object,
        *,
        expected_size: int | None,
    ) -> None:
        """Enforce the single-vector cosine contract used by this retriever."""

        if isinstance(vectors, dict):
            names = ", ".join(sorted(str(name) for name in vectors)) or "<empty>"
            raise IndexSchemaMismatch(
                f"collection {self.collection_name!r} uses named vectors ({names}); "
                "this service requires one unnamed cosine vector"
            )

        actual_size = getattr(vectors, "size", None)
        if expected_size is not None and (actual_size is None or int(actual_size) != expected_size):
            raise IndexSchemaMismatch(
                f"collection {self.collection_name!r} has dimension {actual_size}, "
                f"but {self.embedding_model_name!r} produces {expected_size}; "
                "use a new versioned collection or rebuild the index"
            )

        actual_distance = getattr(vectors, "distance", None)
        expected_distance = models.Distance.COSINE
        if (
            actual_distance != expected_distance
            and str(actual_distance).casefold() != str(expected_distance.value).casefold()
        ):
            raise IndexSchemaMismatch(
                f"collection {self.collection_name!r} uses distance {actual_distance!r}; "
                "this service requires cosine distance"
            )

    def ensure_collection(self) -> None:
        """Create the collection or reject an incompatible existing schema."""

        self._ensure_model()
        assert self.vector_size is not None
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if exists:
            info = self.client.get_collection(self.collection_name)
            vectors = info.config.params.vectors
            self._validate_vector_config(vectors, expected_size=self.vector_size)
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def reset(self) -> None:
        """删除并重建 collection。"""

        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if exists:
            self.client.delete_collection(collection_name=self.collection_name)
        self.ensure_collection()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding。

        normalize_embeddings=True 后，余弦相似度计算更稳定。
        batch_size 可以根据显存/内存调整。
        """

        self._ensure_model()
        assert self.model is not None
        vectors = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def upsert_chunks(self, chunks: Iterable[Chunk], batch_size: int = 64) -> None:
        """批量写入向量。

        批量写入比一条一条写快很多，真实项目必须注意这一点。
        """

        self.ensure_collection()
        batch: list[Chunk] = []
        for chunk in chunks:
            batch.append(chunk)
            if len(batch) >= batch_size:
                self._upsert_batch(batch)
                batch = []
        if batch:
            self._upsert_batch(batch)

    def _upsert_batch(self, chunks: list[Chunk]) -> None:
        """写入一个 batch。"""

        vectors = self.embed_texts([c.text for c in chunks])
        points = []
        # embed_texts must preserve cardinality; fail loudly instead of silently
        # dropping chunks when a custom embedding backend violates the contract.
        for chunk, vector in zip(chunks, vectors, strict=True):
            points.append(
                models.PointStruct(
                    id=point_id_from_chunk_id(chunk.chunk_id),
                    vector=vector,
                    # payload 里只放检索阶段需要的轻量信息。
                    # 原文仍然从 SQLite 取，避免 Qdrant payload 太大。
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "source": chunk.metadata.get("source", ""),
                        "document_id": chunk.metadata.get("document_id", ""),
                        "content_hash": chunk.metadata.get("content_hash", ""),
                        "page": chunk.metadata.get("page"),
                        "heading": chunk.metadata.get("heading"),
                        "chunk_index": chunk.metadata.get("chunk_index"),
                        "embedding_model": self.embedding_model_name,
                    },
                )
            )
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query: str, limit: int = 40) -> list[dict]:
        """向量检索：问题 -> embedding -> Qdrant topK。"""

        self.ensure_collection()
        query_vector = self.embed_texts([query])[0]

        # client.search 在很多 qdrant-client 版本里仍常用；如果新版本提示弃用，可换成 query_points。
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        hits = result.points

        results: list[dict] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "chunk_id": payload.get("chunk_id"),
                    "score": float(hit.score),
                    "payload": payload,
                }
            )
        return [r for r in results if r["chunk_id"]]

    def delete_chunks(self, chunk_ids: Iterable[str]) -> None:
        """Remove stale vectors after a document version is replaced."""

        point_ids: list[int | str | uuid.UUID] = [point_id_from_chunk_id(chunk_id) for chunk_id in chunk_ids]
        if not point_ids:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=point_ids),
            wait=True,
        )

    def reconcile_document(self, document_id: str, keep_chunk_ids: Iterable[str]) -> int:
        """Remove every orphan vector for one document after a successful swap.

        SQLite can name stale IDs from the immediately previous version, but it
        cannot know about older Qdrant-only orphans left by a historic partial
        failure. Scrolling by ``document_id`` closes that gap and prevents a
        vector-count mismatch from forcing a rebuild on every ingestion.
        """

        keep_point_ids = {point_id_from_chunk_id(chunk_id) for chunk_id in keep_chunk_ids}
        offset: int | str | uuid.UUID | None = None
        stale_point_ids: list[int | str | uuid.UUID] = []
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                ),
                limit=256,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            stale_point_ids.extend(point.id for point in points if str(point.id) not in keep_point_ids)
            if next_offset is None:
                break
            offset = next_offset

        if stale_point_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=stale_point_ids),
                wait=True,
            )
        return len(stale_point_ids)

    def count_document(self, document_id: str) -> int:
        """Count vectors for one manifest document to detect partial index loss."""

        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            ),
            exact=True,
        )
        return int(result.count)

    def ready(self) -> tuple[bool, str]:
        """Validate reachability plus the persisted collection contract.

        The check intentionally does not download/load the embedding model. If
        the model has already been loaded, its expected dimension is checked too.
        """

        try:
            collections = self.client.get_collections().collections
            if not any(item.name == self.collection_name for item in collections):
                return False, f"collection {self.collection_name!r} is missing; run ingestion"
            info = self.client.get_collection(self.collection_name)
            self._validate_vector_config(
                info.config.params.vectors,
                expected_size=self.vector_size,
            )
            return True, f"collection {self.collection_name!r} is compatible"
        except Exception as exc:  # pragma: no cover - depends on external service
            return False, str(exc)
