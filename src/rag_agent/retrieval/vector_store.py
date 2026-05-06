
"""Qdrant 向量检索模块。

向量检索解决的是“语义相似”问题：
用户问“如何降低幻觉”，文档里可能写的是“证据不足时拒答”。
关键词未必完全一致，但 embedding 向量可以把意思相近的文本召回。
"""

from __future__ import annotations

import uuid
from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from rag_agent.schemas import Chunk


def point_id_from_chunk_id(chunk_id: str) -> str:
    """把 sha256 chunk_id 转成 Qdrant 支持的 UUID 字符串。"""

    # Qdrant 支持 UUID 字符串作为 point id。
    # chunk_id 是 64 位 hex，这里取前 32 位转 UUID，稳定且足够用。
    return str(uuid.UUID(chunk_id[:32]))


class QdrantVectorStore:
    """Qdrant 向量数据库封装。"""

    def __init__(self, url: str, collection_name: str, embedding_model: str):
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name

        # SentenceTransformer 会在首次运行时下载模型。
        # 面试时可以说：生产环境可提前把模型缓存到镜像或服务器。
        self.model = SentenceTransformer(embedding_model)
        self.vector_size = int(self.model.get_sentence_embedding_dimension())
        self.ensure_collection()

    def ensure_collection(self) -> None:
        """确保 Qdrant collection 存在。"""

        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if exists:
            return

        # distance=COSINE 表示用余弦相似度检索文本语义相似性。
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
        for chunk, vector in zip(chunks, vectors):
            points.append(
                models.PointStruct(
                    id=point_id_from_chunk_id(chunk.chunk_id),
                    vector=vector,
                    # payload 里只放检索阶段需要的轻量信息。
                    # 原文仍然从 SQLite 取，避免 Qdrant payload 太大。
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "source": chunk.metadata.get("source", ""),
                        "page": chunk.metadata.get("page"),
                        "chunk_index": chunk.metadata.get("chunk_index"),
                    },
                )
            )
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query: str, limit: int = 40) -> list[dict]:
        """向量检索：问题 -> embedding -> Qdrant topK。"""

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
