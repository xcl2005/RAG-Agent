from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

import rag_agent.api.main as api_main
from rag_agent import __version__
from rag_agent.api.jobs import JobRegistry
from rag_agent.api.main import (
    _resolve_ingest_path,
    _sse,
    _stable_upload_target,
    _valid_magic,
)
from rag_agent.config import Settings


def test_ingest_path_must_remain_in_allowed_root(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    inside = allowed / "doc.md"
    inside.write_text("safe", encoding="utf-8")

    assert _resolve_ingest_path(str(inside), allowed) == inside.resolve()
    with pytest.raises(HTTPException) as exc_info:
        _resolve_ingest_path(str(tmp_path / "outside.md"), allowed)
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize(
    ("suffix", "content", "expected"),
    [
        (".pdf", b"%PDF-1.7", True),
        (".pdf", b"not-pdf", False),
        (".docx", b"PK\x03\x04data", True),
        (".docx", b"not-zip", False),
        (".md", b"# text", True),
    ],
)
def test_binary_magic_checks(tmp_path, suffix, content, expected):
    path = tmp_path / f"document{suffix}"
    path.write_bytes(content)
    assert _valid_magic(path) is expected


def test_sse_serializes_unicode_and_trace_id():
    output = "".join(_sse([{"event": "node", "trace_id": "trace-1", "data": {"message": "完成"}}]))
    assert "event: node" in output
    assert "id: trace-1" in output
    assert '"message": "完成"' in output


def test_sse_emits_terminal_error_event_when_workflow_raises():
    def broken_events():
        yield {"event": "node", "trace_id": "trace-1", "data": {"node": "retrieve"}}
        raise RuntimeError("private backend detail")

    output = "".join(_sse(broken_events()))

    assert "event: node" in output
    assert "event: error" in output
    assert '"code": "stream_failed"' in output
    assert "private backend detail" not in output


def test_upload_target_is_stable_for_one_logical_filename(tmp_path):
    first = _stable_upload_target(tmp_path, "季度 报告.pdf")
    second = _stable_upload_target(tmp_path, "季度 报告.pdf")
    other = _stable_upload_target(tmp_path, "其他报告.pdf")

    assert first == second
    assert first != other
    assert first.suffix == ".pdf"
    assert first.parent == tmp_path


def test_job_registry_lifecycle_is_copy_safe():
    jobs = JobRegistry()
    created = jobs.create("upload", ["a.md"])
    created["status"] = "tampered"

    stored = jobs.get(created["job_id"])
    assert stored["status"] == "queued"
    updated = jobs.update(created["job_id"], status="running")
    assert updated["status"] == "running"
    assert jobs.get("missing") is None


def test_invalid_retrieval_settings_fail_fast(tmp_path):
    with pytest.raises(ValidationError, match="chunk_overlap"):
        Settings(sqlite_path=tmp_path / "rag.db", chunk_size=128, chunk_overlap=128)
    with pytest.raises(ValidationError, match="rerank_top_k"):
        Settings(sqlite_path=tmp_path / "rag.db", fusion_top_k=2, rerank_top_k=3)


def test_fastapi_dependency_resolution_auth_and_chat_smoke(monkeypatch, tmp_path):
    class FakeSQLite:
        def count(self):
            return 1

        def list_sources(self):
            return [
                {
                    "document_id": "a" * 64,
                    "source": "guide.md",
                    "display_name": "Guide.md",
                    "status": "ready",
                    "chunk_count": 1,
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]

    class FakeAgent:
        def __init__(self, settings):
            self.retriever = type(
                "Retriever",
                (),
                {"sqlite": FakeSQLite(), "vector": object()},
            )()
            self.closed = False

        def ready(self):
            return {
                "sqlite": {"ready": True, "detail": "ready"},
                "qdrant": {"ready": True, "detail": "ready"},
            }

        def ask(self, question, *, thread_id=None, include_trace=True):
            result = {
                "question": question,
                "thread_id": thread_id or "generated-thread",
                "trace_id": "trace-1",
                "status": "answered",
                "answer": "Grounded [S1]",
                "abstained": False,
                "confidence": 0.9,
                "query": question,
                "queries": [question],
                "sources": [],
                "evidence": {"sufficient": True},
                "citation_validation": {"valid": True},
                "usage": {"model_calls": 1, "input_tokens": 2, "output_tokens": 1},
                "error": None,
            }
            if include_trace:
                result.update(trace=[], model_calls=[])
            return result

        def stream(self, question, *, thread_id=None, include_trace=True):
            yield {
                "event": "node",
                "trace_id": "trace-1",
                "data": {"node": "retrieve", "latency_ms": 1.0},
            }
            yield {
                "event": "final",
                "trace_id": "trace-1",
                "data": self.ask(
                    question,
                    thread_id=thread_id,
                    include_trace=include_trace,
                ),
            }

        def close(self):
            self.closed = True

    class FakeIndexer:
        def __init__(self, settings, **kwargs):
            self.settings = settings

        def is_managed_upload(self, source):
            return source == "guide.md"

        def delete_document(self, document_id):
            if document_id == "c" * 64:
                raise PermissionError("only browser-managed uploads can be deleted")
            if document_id != "a" * 64:
                return None
            return {
                "document_id": document_id,
                "display_name": "Guide.md",
                "source": "guide.md",
                "removed_chunks": 1,
                "vector_chunks_removed": 1,
                "file_removed": True,
                "cleanup_deferred": [],
            }

    monkeypatch.setattr(api_main, "RAGAgent", FakeAgent)
    monkeypatch.setattr(api_main, "Indexer", FakeIndexer)
    app = api_main.create_app(
        Settings(
            api_access_key="secret",
            admin_api_key="admin-secret",
            max_question_chars=64,
            max_upload_files=10,
            max_upload_mb=20,
            allowed_ingest_root=tmp_path,
            sqlite_path=tmp_path / "rag.db",
            checkpoint_path=tmp_path / "checkpoint.db",
        )
    )

    with TestClient(app) as client:
        web = client.get("/")
        assert web.status_code == 200
        assert "Evidence Workbench" in web.text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/styles.css").status_code == 200

        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.json()["version"] == __version__
        assert client.get("/health/live", headers={"Host": "evil.example"}).status_code == 400
        assert client.get("/health/ready").status_code == 200
        capabilities = client.get("/api/v1/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json()["upload"]["max_files"] == 10
        assert capabilities.json()["upload"]["max_file_mb"] == 20
        assert capabilities.json()["auth"]["access_key_required"] is True
        assert capabilities.json()["sources"]["delete_enabled"] is True
        assert client.post("/api/v1/chat", json={"question": "hello"}).status_code == 401
        assert (
            client.post(
                "/api/v1/ingest",
                headers={"X-API-Key": "secret"},
                json={"path": str(tmp_path)},
            ).status_code
            == 401
        )

        response = client.post(
            "/api/v1/chat",
            headers={"X-API-Key": "secret"},
            json={"question": "hello", "include_trace": False},
        )
        assert response.status_code == 200
        assert response.json()["trace_id"] == "trace-1"

        stream = client.post(
            "/api/v1/chat/stream",
            headers={"X-API-Key": "secret"},
            json={"question": "hello", "include_trace": False},
        )
        assert stream.status_code == 200
        assert "event: node" in stream.text
        assert "event: final" in stream.text

        oversized = "x" * 65
        assert (
            client.post(
                "/api/v1/chat",
                headers={"X-API-Key": "secret"},
                json={"question": oversized},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/chat/stream",
                headers={"X-API-Key": "secret"},
                json={"question": oversized},
            ).status_code
            == 422
        )

        sources = client.get("/api/v1/sources", headers={"X-API-Key": "secret"})
        assert sources.status_code == 200
        assert sources.json()["sources"][0]["source"] == "Guide.md"
        assert sources.json()["sources"][0]["deletable"] is True
        assert "index_fingerprint" not in sources.json()["sources"][0]

        assert client.delete(f"/api/v1/sources/{'a' * 64}").status_code == 401
        invalid_delete = client.delete(
            "/api/v1/sources/not-a-document-id",
            headers={"X-API-Key": "secret"},
        )
        assert invalid_delete.status_code == 422
        deleted = client.delete(
            f"/api/v1/sources/{'a' * 64}",
            headers={"X-API-Key": "secret"},
        )
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        missing = client.delete(
            f"/api/v1/sources/{'b' * 64}",
            headers={"X-API-Key": "secret"},
        )
        assert missing.status_code == 404
        unmanaged = client.delete(
            f"/api/v1/sources/{'c' * 64}",
            headers={"X-API-Key": "secret"},
        )
        assert unmanaged.status_code == 403

    upload_disabled_app = api_main.create_app(
        Settings(
            api_access_key="",
            allowed_ingest_root=tmp_path,
            sqlite_path=tmp_path / "no-key.db",
            checkpoint_path=tmp_path / "no-key-checkpoint.db",
        )
    )
    with TestClient(upload_disabled_app) as client:
        disabled = client.post(
            "/api/v1/documents",
            files={"files": ("note.md", b"# safe", "text/markdown")},
        )
        assert disabled.status_code == 403
        assert "configure API_ACCESS_KEY" in disabled.json()["detail"]


def test_upload_round_trip_preserves_the_original_display_name(monkeypatch, tmp_path):
    original_name = "abcdef123456-project-report.md"

    class FakeSQLite:
        def __init__(self):
            self.manifests = []

        def list_sources(self):
            return list(self.manifests)

    class FakeAgent:
        def __init__(self, settings):
            del settings
            self.retriever = SimpleNamespace(sqlite=FakeSQLite(), vector=object())

        def close(self):
            return None

    class FakeIndexer:
        def __init__(self, settings, *, sqlite_store, vector_store):
            del vector_store
            self.settings = settings
            self.sqlite = sqlite_store
            self.received_display_name = None

        def ingest_file(self, path, *, force=False, display_name=None):
            del force
            self.received_display_name = display_name
            self.sqlite.manifests.append(
                {
                    "document_id": "d" * 64,
                    "source": path,
                    "display_name": display_name,
                    "status": "ready",
                    "chunk_count": 1,
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            )
            return {
                "document_id": "d" * 64,
                "status": "indexed",
                "chunks": 1,
                "display_name": display_name,
            }

        def is_managed_upload(self, source):
            upload_root = (self.settings.allowed_ingest_root / "uploads").resolve()
            return Path(source).resolve().is_relative_to(upload_root)

    monkeypatch.setattr(api_main, "RAGAgent", FakeAgent)
    monkeypatch.setattr(api_main, "Indexer", FakeIndexer)
    app = api_main.create_app(
        Settings(
            api_access_key="secret",
            allowed_ingest_root=tmp_path / "ingest",
            sqlite_path=tmp_path / "rag.db",
            checkpoint_path=tmp_path / "checkpoint.db",
        )
    )

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/v1/documents",
            headers={"X-API-Key": "secret"},
            files={"files": (original_name, b"# Portfolio", "text/markdown")},
        )
        assert uploaded.status_code == 202
        job_id = uploaded.json()["job_id"]
        job = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": "secret"},
        )
        assert job.json()["status"] == "succeeded"
        assert client.app.state.services.indexer.received_display_name == original_name

        listed = client.get("/api/v1/sources", headers={"X-API-Key": "secret"})
        source = listed.json()["sources"][0]
        assert source["display_name"] == original_name
        assert source["source"] == original_name
        assert source["origin"] == "upload"
        assert source["deletable"] is True
