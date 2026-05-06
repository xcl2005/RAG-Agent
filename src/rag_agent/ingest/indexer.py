
"""索引构建模块。

Indexer 负责把“资料”导入到检索系统里：
文件 -> 文本 -> chunk -> SQLite 关键词索引 + Qdrant 向量索引。

你面试时可以把它叫做 ingestion pipeline / indexing pipeline。
"""

from __future__ import annotations

from pathlib import Path
from tqdm import tqdm

from rag_agent.config import settings
from rag_agent.ingest.chunker import chunk_documents
from rag_agent.ingest.loaders import load_documents
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore
from rag_agent.retrieval.vector_store import QdrantVectorStore
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)


class Indexer:
    """资料入库器。

    SQLite 和 Qdrant 都要写：
    - SQLite：保存 chunk 原文，做关键词检索。
    - Qdrant：保存向量，做语义检索。
    """

    def __init__(self):
        self.sqlite = SQLiteChunkStore(settings.sqlite_path)
        self.vector = QdrantVectorStore(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            embedding_model=settings.embedding_model,
        )

    def reset(self) -> None:
        """清空旧索引。

        开发阶段经常调整 chunk_size / overlap。
        参数变了以后，建议 reset 后重新导入，否则旧 chunk 和新 chunk 会混在一起。
        """

        logger.info("Resetting SQLite and Qdrant indexes")
        self.sqlite.reset()
        self.vector.reset()

    def ingest_path(self, path: str | Path, reset: bool = False) -> dict:
        """导入一个文件或目录。"""

        if reset:
            self.reset()

        logger.info("Loading documents from %s", path)
        docs = load_documents(path)
        logger.info("Loaded %s document units", len(docs))

        # 先切 chunk，再同时写入稀疏索引和向量索引。
        chunks = chunk_documents(docs, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        logger.info("Created %s chunks", len(chunks))

        if not chunks:
            return {"documents": len(docs), "chunks": 0}

        logger.info("Writing chunks to SQLite")
        self.sqlite.upsert_chunks(tqdm(chunks, desc="sqlite"))

        logger.info("Writing vectors to Qdrant")
        self.vector.upsert_chunks(tqdm(chunks, desc="qdrant"))

        return {"documents": len(docs), "chunks": len(chunks)}
