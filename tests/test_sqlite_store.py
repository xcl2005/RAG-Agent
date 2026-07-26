import hashlib
import json
import sqlite3

from rag_agent.retrieval.sqlite_store import (
    SQLiteChunkStore,
    cjk_bigrams,
    display_name_from_source,
)
from rag_agent.schemas import Chunk


def test_cjk_bigrams_do_not_cross_punctuation():
    assert cjk_bigrams("向量，数据库") == ["向量", "数据", "据库"]


def test_upload_storage_prefix_is_not_a_display_name():
    original = "Project Report.pdf"
    prefix = hashlib.sha256(original.casefold().encode("utf-8")).hexdigest()[:12]
    assert display_name_from_source(f"data/raw/uploads/{prefix}-Project_Report.pdf") == original
    assert display_name_from_source("data/raw/guide.md") == "guide.md"


def test_manifest_replace_is_idempotent_and_searchable(tmp_path):
    store = SQLiteChunkStore(tmp_path / "rag.db")
    try:
        first = Chunk(
            chunk_id="a" * 64,
            text="RAG 使用证据门控和引用校验。",
            metadata={"source": "sample.md", "document_id": "doc-1"},
        )
        stale = store.replace_document_chunks(
            document_id="doc-1",
            source="sample.md",
            display_name="项目说明.md",
            content_hash="hash-1",
            index_fingerprint="index-v1",
            chunks=[first],
        )
        assert stale == []
        assert store.document_is_current("doc-1", "hash-1", "index-v1")
        assert not store.document_is_current("doc-1", "hash-1", "index-v2")
        assert store.get_document("doc-1")["chunk_count"] == 1
        assert store.get_document("doc-1")["display_name"] == "项目说明.md"
        assert store.search("引用校验")[0].chunk_id == first.chunk_id

        second = Chunk(
            chunk_id="b" * 64,
            text="新版文档使用混合检索。",
            metadata={"source": "sample.md", "document_id": "doc-1"},
        )
        stale = store.replace_document_chunks(
            document_id="doc-1",
            source="sample.md",
            content_hash="hash-2",
            index_fingerprint="index-v1",
            chunks=[second],
        )
        assert stale == [first.chunk_id]
        assert store.get_chunk(first.chunk_id) is None
        assert store.get_chunk(second.chunk_id) is not None
        store.update_document_display_name("doc-1", "重命名资料.md")
        assert store.get_document("doc-1")["display_name"] == "重命名资料.md"
        assert store.get_chunk(second.chunk_id).metadata["title"] == "重命名资料.md"

        deleted = store.delete_document("doc-1")
        assert deleted["chunk_ids"] == [second.chunk_id]
        assert deleted["display_name"] == "重命名资料.md"
        assert store.get_document("doc-1") is None
        assert store.get_chunk(second.chunk_id) is None
        assert store.search("混合检索") == []
        assert store.delete_document("doc-1") is None
    finally:
        store.close()


def test_legacy_rows_without_document_identity_are_purged(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            source TEXT,
            metadata TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            chunk_id UNINDEXED,
            text,
            source
        );
        INSERT INTO chunks VALUES ('old', 'legacy ghost', 'guide.md', '{}');
        INSERT INTO chunks_fts VALUES ('old', 'legacy ghost', 'guide.md');
        """
    )
    connection.commit()
    connection.close()

    store = SQLiteChunkStore(path)
    try:
        assert store.count() == 0
        assert store.search("legacy") == []
    finally:
        store.close()


def test_manifest_migration_recovers_upload_name_and_repairs_chunk_title(tmp_path):
    path = tmp_path / "legacy-manifest.db"
    original = "Project Report.pdf"
    prefix = hashlib.sha256(original.casefold().encode("utf-8")).hexdigest()[:12]
    stored = (tmp_path / "uploads" / f"{prefix}-Project_Report.pdf").as_posix()
    metadata = json.dumps({"title": f"{prefix}-Project_Report.pdf", "source": stored})
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            source TEXT NOT NULL UNIQUE,
            content_hash TEXT NOT NULL,
            index_fingerprint TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT,
            text TEXT NOT NULL,
            source TEXT,
            metadata TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            chunk_id UNINDEXED,
            text,
            source
        );
        """
    )
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, 'ready', 1, NULL, ?)",
        ("doc-1", stored, "hash", "index", "2026-01-01T00:00:00+00:00"),
    )
    connection.execute(
        "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
        ("chunk-1", "doc-1", "evidence", stored, metadata),
    )
    connection.execute(
        "INSERT INTO chunks_fts VALUES (?, ?, ?)",
        ("chunk-1", "evidence", stored),
    )
    connection.commit()
    connection.close()

    store = SQLiteChunkStore(path)
    try:
        assert store.get_document("doc-1")["display_name"] == original
        candidate = store.get_chunk("chunk-1")
        assert candidate is not None
        assert candidate.metadata["title"] == original
        assert candidate.metadata["display_name"] == original
    finally:
        store.close()
