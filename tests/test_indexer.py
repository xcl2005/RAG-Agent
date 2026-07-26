import os

import pytest

from rag_agent.config import Settings
from rag_agent.ingest.indexer import Indexer, _document_id
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore


class FakeSQLite:
    def __init__(self):
        self.current = False
        self.replaced = []
        self.failed = []
        self.reset_called = False
        self.closed = False
        self.chunk_count = 0
        self.display_name_updates = []

    def document_is_current(self, document_id, content_hash, index_fingerprint):
        return self.current

    def get_document(self, document_id):
        return {"chunk_count": self.chunk_count}

    def replace_document_chunks(self, **kwargs):
        self.replaced.append(kwargs)
        self.chunk_count = len(kwargs["chunks"])
        return ["f" * 64]

    def mark_document_failed(self, **kwargs):
        self.failed.append(kwargs)

    def update_document_display_name(self, document_id, display_name):
        self.display_name_updates.append((document_id, display_name))

    def reset(self):
        self.reset_called = True

    def close(self):
        self.closed = True


class FakeVector:
    def __init__(self, *, fail_upsert=False):
        self.fail_upsert = fail_upsert
        self.upserted = []
        self.deleted = []
        self.reconciled = []
        self.reset_called = False

    def upsert_chunks(self, chunks):
        if self.fail_upsert:
            raise RuntimeError("vector write failed")
        self.upserted.extend(chunks)

    def delete_chunks(self, chunk_ids):
        self.deleted.extend(chunk_ids)

    def reset(self):
        self.reset_called = True

    def count_document(self, document_id):
        return len(self.upserted)

    def reconcile_document(self, document_id, keep_chunk_ids):
        self.reconciled.append((document_id, list(keep_chunk_ids)))
        return 0


def make_indexer(tmp_path, sqlite, vector):
    return Indexer(
        Settings(
            sqlite_path=tmp_path / "rag.db",
            checkpoint_path=tmp_path / "checkpoints.db",
            allowed_ingest_root=tmp_path,
            chunk_size=128,
            chunk_overlap=16,
        ),
        sqlite_store=sqlite,
        vector_store=vector,
    )


def test_ingest_file_is_idempotent_and_cleans_stale_vectors(tmp_path):
    path = tmp_path / "guide.md"
    path.write_text("# Safety\nUse validated citations. " * 20, encoding="utf-8")
    sqlite = FakeSQLite()
    vector = FakeVector()
    indexer = make_indexer(tmp_path, sqlite, vector)

    result = indexer.ingest_file(path, display_name="原始 Guide.md")

    assert result["status"] == "indexed"
    assert result["chunks"] > 0
    assert vector.upserted
    assert vector.deleted == ["f" * 64]
    assert vector.reconciled[0][0] == result["document_id"]
    assert vector.reconciled[0][1]
    assert sqlite.replaced[0]["chunks"][0].metadata["content_hash"] == result["content_hash"]
    assert sqlite.replaced[0]["display_name"] == "原始 Guide.md"
    assert sqlite.replaced[0]["chunks"][0].metadata["title"] == "原始 Guide.md"

    sqlite.current = True
    skipped = indexer.ingest_file(path, display_name="原始 Guide.md")
    assert skipped["status"] == "skipped"
    assert skipped["reason"] == "content and index fingerprint unchanged"


def test_vector_failure_marks_document_failed_without_sqlite_swap(tmp_path):
    path = tmp_path / "guide.txt"
    path.write_text("retrievable content " * 20, encoding="utf-8")
    sqlite = FakeSQLite()
    indexer = make_indexer(tmp_path, sqlite, FakeVector(fail_upsert=True))

    with pytest.raises(RuntimeError, match="vector write failed"):
        indexer.ingest_file(path)

    assert sqlite.replaced == []
    assert sqlite.failed[0]["source"].endswith("guide.txt")


def test_ingest_path_isolates_bad_files_and_reset_order(tmp_path, monkeypatch):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("A", encoding="utf-8")
    second.write_text("B", encoding="utf-8")
    sqlite = FakeSQLite()
    vector = FakeVector()
    indexer = make_indexer(tmp_path, sqlite, vector)

    def fake_ingest(path, *, force=False):
        if path.name == "b.txt":
            raise RuntimeError("broken document")
        return {"status": "indexed", "chunks": 2, "source": path.as_posix()}

    monkeypatch.setattr(indexer, "ingest_file", fake_ingest)
    result = indexer.ingest_path(tmp_path, reset=True, force=True)

    assert vector.reset_called is True
    assert sqlite.reset_called is True
    assert result["indexed_files"] == 1
    assert result["failed_files"] == 1
    assert result["chunks"] == 2
    assert result["errors"][0]["source"].endswith("b.txt")


def test_owned_sqlite_connection_is_closed(tmp_path, monkeypatch):
    fake_sqlite = FakeSQLite()
    monkeypatch.setattr("rag_agent.ingest.indexer.SQLiteChunkStore", lambda _: fake_sqlite)
    indexer = Indexer(
        Settings(sqlite_path=tmp_path / "rag.db"),
        vector_store=FakeVector(),
    )

    indexer.close()

    assert fake_sqlite.closed is True


def test_document_identity_follows_host_filesystem_case_rules():
    """Linux keeps A.md/a.md distinct; Windows treats them as one path."""

    first = _document_id("C:/knowledge/A.md")
    second = _document_id("C:/knowledge/a.md")

    assert (first == second) is (
        os.path.normcase("C:/knowledge/A.md") == os.path.normcase("C:/knowledge/a.md")
    )


def test_delete_document_cleans_all_stores_and_only_managed_uploads(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    upload = upload_dir / "abc123-portfolio.md"
    upload.write_text("# Portfolio\nGrounded evidence. " * 20, encoding="utf-8")
    sqlite = SQLiteChunkStore(tmp_path / "delete.db")
    vector = FakeVector()
    indexer = make_indexer(tmp_path, sqlite, vector)

    try:
        indexed = indexer.ingest_file(upload, display_name="Portfolio Notes.md")
        deleted = indexer.delete_document(indexed["document_id"])

        assert deleted["display_name"] == "Portfolio Notes.md"
        assert deleted["removed_chunks"] == indexed["chunks"]
        assert deleted["file_removed"] is True
        assert deleted["cleanup_deferred"] == []
        assert upload.exists() is False
        assert sqlite.get_document(indexed["document_id"]) is None
        assert vector.reconciled[-1] == (indexed["document_id"], [])

        server_file = tmp_path / "server-owned.md"
        server_file.write_text("admin managed source " * 20, encoding="utf-8")
        server_indexed = indexer.ingest_file(server_file)
        with pytest.raises(PermissionError, match="browser-managed"):
            indexer.delete_document(server_indexed["document_id"])
        assert server_file.exists() is True
        assert sqlite.get_document(server_indexed["document_id"]) is not None
    finally:
        sqlite.close()
