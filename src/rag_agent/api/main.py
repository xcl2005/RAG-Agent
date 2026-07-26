"""FastAPI application for chat, safe ingestion, jobs, and workflow streaming."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from rag_agent import __version__
from rag_agent.agent.graph import RAGAgent
from rag_agent.agent.guardrails import sanitize_question
from rag_agent.api.jobs import JobRegistry
from rag_agent.api.models import ChatRequest, ChatResponse, IngestPathRequest
from rag_agent.config import Settings, settings
from rag_agent.ingest.indexer import Indexer
from rag_agent.ingest.loaders import SUPPORTED_SUFFIXES
from rag_agent.utils.logging import get_logger

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+")
DOCUMENT_ID_RE = re.compile(r"^[0-9a-f]{64}$")
logger = get_logger(__name__)


@dataclass(slots=True)
class Services:
    agent: RAGAgent
    indexer: Indexer
    jobs: JobRegistry
    ingest_lock: threading.Lock


def get_services(request: Request) -> Services:
    """Resolve application-scoped services for FastAPI dependencies.

    This callable intentionally lives at module scope. With postponed type
    annotations enabled, FastAPI resolves annotation names from module globals;
    a closure-local dependency can otherwise be mistaken for a query field.
    """

    return request.app.state.services


def _resolve_ingest_path(raw_path: str, allowed_root: Path) -> Path:
    """Resolve a user path and prove it remains under the configured root."""

    root = allowed_root.resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"ingest path must stay inside {root}",
        )
    return resolved


def _valid_magic(path: Path, expected_suffix: str | None = None) -> bool:
    """Reject obvious extension spoofing for binary formats."""

    with path.open("rb") as stream:
        prefix = stream.read(8)
    suffix = expected_suffix or path.suffix.lower()
    if suffix == ".pdf":
        return prefix.startswith(b"%PDF-")
    if suffix == ".docx":
        return prefix.startswith(b"PK")
    return True


def _stable_upload_target(upload_dir: Path, original: str) -> Path:
    """Map one logical filename to a stable, sanitized knowledge source."""

    suffix = Path(original).suffix.lower()
    safe_stem = SAFE_FILENAME_RE.sub("_", Path(original).stem).strip("._") or "document"
    name_hash = hashlib.sha256(original.casefold().encode("utf-8")).hexdigest()[:12]
    return upload_dir / f"{name_hash}-{safe_stem[:120]}{suffix}"


def _sse(events: Iterator[dict[str, Any]]) -> Iterator[str]:
    """Serialize workflow events and always terminate failures explicitly."""

    trace_id: str | None = None
    try:
        for event in events:
            trace_id = str(event["trace_id"])
            payload = json.dumps(event["data"], ensure_ascii=False, default=str)
            yield f"event: {event['event']}\nid: {trace_id}\ndata: {payload}\n\n"
    except GeneratorExit:
        raise
    except Exception:
        # HTTP 200 may already have been sent. An explicit terminal error event
        # lets browsers distinguish failure from a clean end-of-stream.
        logger.exception("Workflow stream failed")
        trace_id = trace_id or str(uuid.uuid4())
        payload = json.dumps(
            {
                "status": "error",
                "error": {
                    "code": "stream_failed",
                    "message": "The workflow stream ended unexpectedly.",
                },
            },
            ensure_ascii=False,
        )
        yield f"event: error\nid: {trace_id}\ndata: {payload}\n\n"


def create_app(app_settings: Settings = settings) -> FastAPI:
    """Application factory used by the CLI and tests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        agent = RAGAgent(app_settings)
        # Reuse the same loaded embedding model and SQLite connection for chat
        # and ingestion instead of loading a duplicate model per request.
        indexer = Indexer(
            app_settings,
            sqlite_store=agent.retriever.sqlite,
            vector_store=agent.retriever.vector,
        )
        app.state.services = Services(
            agent=agent,
            indexer=indexer,
            jobs=JobRegistry(),
            ingest_lock=threading.Lock(),
        )
        yield
        agent.close()

    app = FastAPI(
        title="Adaptive RAG Agent",
        version=__version__,
        description=(
            "LangGraph durable workflow + multi-query hybrid retrieval + "
            "rerank + evidence gate + server-validated citations."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=app_settings.allowed_hosts,
    )

    async def require_access(
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        """Optional shared-key boundary for non-local deployments."""

        expected = app_settings.api_access_key
        if expected and (x_api_key is None or not secrets.compare_digest(x_api_key, expected)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid X-API-Key",
            )

    async def require_admin_access(
        x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
    ) -> None:
        """Protect server-path ingestion and global reset with a separate key."""

        expected = app_settings.admin_api_key
        if not expected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="server-path ingestion is disabled; configure ADMIN_API_KEY",
            )
        if x_admin_key is None or not secrets.compare_digest(x_admin_key, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid X-Admin-Key",
            )

    async def require_upload_access(
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        """Uploads are disabled until an explicit key closes browser CSRF."""

        expected = app_settings.api_access_key
        if not expected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="document upload is disabled; configure API_ACCESS_KEY",
            )
        if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid X-API-Key",
            )

    def run_ingest_job(
        service: Services,
        job_id: str,
        paths: list[str],
        *,
        reset: bool,
        force: bool,
        upload_snapshots: dict[str, str] | None = None,
        display_names: dict[str, str] | None = None,
    ) -> None:
        service.jobs.update(job_id, status="running")
        try:
            with service.ingest_lock:
                if reset:
                    service.indexer.reset()
                results: list[dict[str, Any]] = []
                errors: list[dict[str, str]] = []
                for path in paths:
                    try:
                        if upload_snapshots and (snapshot := upload_snapshots.get(path)):
                            # Commit the immutable request snapshot and ingest it
                            # while holding the same lock. Concurrent revisions
                            # of one logical filename can no longer change bytes
                            # between hashing and parsing.
                            Path(snapshot).replace(Path(path))
                        results.append(
                            service.indexer.ingest_file(
                                path,
                                force=force,
                                display_name=(display_names or {}).get(path),
                            )
                        )
                    except Exception as exc:
                        errors.append({"source": path, "error": str(exc)})

            # One malformed document should not erase the successful work from
            # the rest of a batch. A fully failed batch is still reported as a
            # failed job; partial failures remain visible in the result.
            if errors and not results:
                service.jobs.update(
                    job_id,
                    status="failed",
                    error=f"all {len(errors)} document(s) failed",
                    result={"files": [], "failed_files": len(errors), "errors": errors},
                )
                return
            service.jobs.update(
                job_id,
                status="succeeded",
                result={
                    "files": results,
                    "indexed_files": sum(item["status"] == "indexed" for item in results),
                    "skipped_files": sum(item["status"] == "skipped" for item in results),
                    "failed_files": len(errors),
                    "chunks": sum(int(item.get("chunks", 0)) for item in results),
                    "errors": errors,
                },
            )
        except Exception as exc:  # Job failure is surfaced through /jobs/{id}.
            service.jobs.update(job_id, status="failed", error=str(exc))
        finally:
            # A successfully committed snapshot no longer exists; failed or
            # unprocessed snapshots are safe to remove here.
            for snapshot in (upload_snapshots or {}).values():
                Path(snapshot).unlink(missing_ok=True)

    def validated_question(question: str) -> str:
        """Apply the deploy-time length limit before starting any response."""

        try:
            return sanitize_question(question, app_settings.max_question_chars)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # ------------------------------------------------------------------
    # Health endpoints stay unauthenticated for container orchestrators.
    # ------------------------------------------------------------------
    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    @app.get("/health/ready", tags=["health"])
    async def ready(service: Annotated[Services, Depends(get_services)]) -> JSONResponse:
        dependencies = await run_in_threadpool(service.agent.ready)
        is_ready = all(bool(item["ready"]) for item in dependencies.values())
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={
                "status": "ready" if is_ready else "degraded",
                "dependencies": dependencies,
            },
        )

    # Backward-compatible health alias.
    @app.get("/health", deprecated=True, include_in_schema=False)
    async def legacy_health(service: Annotated[Services, Depends(get_services)]) -> dict[str, Any]:
        return {
            "status": "ok",
            "chunks": service.agent.retriever.sqlite.count(),
            "collection": app_settings.qdrant_collection,
        }

    @app.get("/api/v1/capabilities", tags=["system"])
    async def capabilities() -> dict[str, Any]:
        """Expose non-secret client limits so the UI can validate before upload."""

        return {
            "version": app.version,
            "auth": {
                "access_key_required": bool(app_settings.api_access_key),
            },
            "upload": {
                "enabled": bool(app_settings.api_access_key),
                "max_files": app_settings.max_upload_files,
                "max_file_mb": app_settings.max_upload_mb,
                "supported_extensions": sorted(SUPPORTED_SUFFIXES),
            },
            "sources": {
                "delete_enabled": bool(app_settings.api_access_key),
                "managed_uploads_only": True,
            },
        }

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    @app.post(
        "/api/v1/chat",
        response_model=ChatResponse,
        dependencies=[Depends(require_access)],
        tags=["chat"],
    )
    async def chat(
        body: ChatRequest,
        service: Annotated[Services, Depends(get_services)],
    ) -> dict[str, Any]:
        question = validated_question(body.question)
        try:
            return await run_in_threadpool(
                service.agent.ask,
                question,
                thread_id=body.thread_id,
                include_trace=body.include_trace,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/api/v1/chat/stream",
        dependencies=[Depends(require_access)],
        tags=["chat"],
    )
    async def chat_stream(
        body: ChatRequest,
        service: Annotated[Services, Depends(get_services)],
    ) -> StreamingResponse:
        # Validate before constructing StreamingResponse. Once HTTP 200 headers
        # are sent, a generator exception can only produce a truncated stream.
        question = validated_question(body.question)
        events = service.agent.stream(
            question,
            thread_id=body.thread_id,
            include_trace=body.include_trace,
        )
        return StreamingResponse(
            _sse(events),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post(
        "/ask",
        response_model=ChatResponse,
        deprecated=True,
        include_in_schema=False,
        dependencies=[Depends(require_access)],
    )
    async def legacy_ask(
        body: ChatRequest,
        service: Annotated[Services, Depends(get_services)],
    ) -> dict[str, Any]:
        return await chat(body, service)

    # ------------------------------------------------------------------
    # Ingestion and job status
    # ------------------------------------------------------------------
    @app.post(
        "/api/v1/ingest",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_admin_access)],
        tags=["documents"],
    )
    async def ingest_path(
        body: IngestPathRequest,
        background: BackgroundTasks,
        service: Annotated[Services, Depends(get_services)],
    ) -> dict[str, Any]:
        path = _resolve_ingest_path(body.path, app_settings.allowed_ingest_root)
        if not path.exists():
            raise HTTPException(status_code=404, detail="ingest path does not exist")
        if path.is_file():
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise HTTPException(status_code=415, detail="unsupported file type")
            paths = [path.as_posix()]
        else:
            allowed_root = app_settings.allowed_ingest_root.resolve()
            paths = []
            for file in path.rglob("*"):
                if not file.is_file() or file.suffix.lower() not in SUPPORTED_SUFFIXES:
                    continue
                resolved_file = file.resolve()
                # A file symlink inside the ingest tree may still point outside
                # it. Validate every resolved file, not just the requested root.
                if resolved_file.is_relative_to(allowed_root):
                    paths.append(resolved_file.as_posix())
            paths.sort()
        if not paths:
            raise HTTPException(status_code=422, detail="no supported documents found")
        job = service.jobs.create("path_ingest", paths)
        background.add_task(
            run_ingest_job,
            service,
            job["job_id"],
            paths,
            reset=body.reset,
            force=body.force,
        )
        return job

    @app.post(
        "/api/v1/documents",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_upload_access)],
        tags=["documents"],
    )
    async def upload_documents(
        background: BackgroundTasks,
        service: Annotated[Services, Depends(get_services)],
        files: Annotated[list[UploadFile], File(description="PDF/Word/Markdown/TXT/HTML")],
        force: Annotated[bool, Form()] = False,
    ) -> dict[str, Any]:
        if len(files) > app_settings.max_upload_files:
            raise HTTPException(
                status_code=413,
                detail=f"at most {app_settings.max_upload_files} files per request",
            )

        upload_dir = app_settings.allowed_ingest_root / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        pending: list[tuple[Path, Path]] = []
        target_paths: set[Path] = set()
        display_names: dict[str, str] = {}
        try:
            for upload in files:
                original = Path(upload.filename or "upload.txt").name
                suffix = Path(original).suffix.lower()
                if suffix not in SUPPORTED_SUFFIXES:
                    raise HTTPException(status_code=415, detail=f"unsupported file type: {suffix}")

                target = _stable_upload_target(upload_dir, original)
                if target in target_paths:
                    raise HTTPException(
                        status_code=409,
                        detail=f"duplicate filename in one request: {original}",
                    )
                target_paths.add(target)
                display_names[target.as_posix()] = original
                # Keep the snapshot's suffix unsupported so an overlapping
                # administrator directory scan cannot index a half-finished
                # upload before its background job acquires ingest_lock.
                temporary = upload_dir / f".{uuid.uuid4().hex}.upload.tmp"
                pending.append((temporary, target))
                size = 0
                with temporary.open("xb") as output:
                    while chunk := await upload.read(1024 * 1024):
                        size += len(chunk)
                        if size > app_settings.max_upload_bytes:
                            raise HTTPException(
                                status_code=413,
                                detail=f"{original} exceeds {app_settings.max_upload_mb} MB",
                            )
                        output.write(chunk)
                if size == 0:
                    raise HTTPException(status_code=400, detail=f"{original} is empty")
                if not _valid_magic(temporary, suffix):
                    raise HTTPException(
                        status_code=415,
                        detail=f"{original} content does not match its extension",
                    )

            # Do not replace stable logical targets here. Background ingestion
            # commits each immutable snapshot under the same single-flight lock
            # used for hashing, parsing and indexing.
        except Exception:
            for temporary, _ in pending:
                temporary.unlink(missing_ok=True)
            raise
        finally:
            for upload in files:
                await upload.close()

        paths = [target.as_posix() for _, target in pending]
        upload_snapshots = {target.as_posix(): temporary.as_posix() for temporary, target in pending}
        job = service.jobs.create("upload_ingest", paths)
        background.add_task(
            run_ingest_job,
            service,
            job["job_id"],
            paths,
            reset=False,
            force=force,
            upload_snapshots=upload_snapshots,
            display_names=display_names,
        )
        return job

    @app.get(
        "/api/v1/jobs/{job_id}",
        dependencies=[Depends(require_access)],
        tags=["documents"],
    )
    async def get_job(
        job_id: str,
        service: Annotated[Services, Depends(get_services)],
    ) -> dict[str, Any]:
        job = service.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.get(
        "/api/v1/sources",
        dependencies=[Depends(require_access)],
        tags=["documents"],
    )
    async def list_sources(
        service: Annotated[Services, Depends(get_services)],
    ) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        for manifest in service.agent.retriever.sqlite.list_sources():
            managed_upload = service.indexer.is_managed_upload(str(manifest["source"]))
            display_name = str(manifest["display_name"])
            # Keep filesystem paths, parser errors and index fingerprints out
            # of the browser-facing registry. They are operational internals,
            # not useful UI metadata.
            sources.append(
                {
                    "document_id": manifest["document_id"],
                    "display_name": display_name,
                    "source": display_name,
                    "origin": "upload" if managed_upload else "server_path",
                    "deletable": managed_upload and bool(app_settings.api_access_key),
                    "status": manifest["status"],
                    "chunk_count": manifest["chunk_count"],
                    "updated_at": manifest["updated_at"],
                }
            )
        return {"sources": sources}

    @app.delete(
        "/api/v1/sources/{document_id}",
        dependencies=[Depends(require_upload_access)],
        tags=["documents"],
    )
    async def delete_source(
        document_id: str,
        service: Annotated[Services, Depends(get_services)],
    ) -> dict[str, Any]:
        """Remove one indexed source and its managed upload, if applicable."""

        if not DOCUMENT_ID_RE.fullmatch(document_id):
            raise HTTPException(status_code=422, detail="invalid document id")

        def delete_under_ingest_lock() -> dict[str, Any] | None:
            # Serialize deletion with indexing so a background upload cannot
            # recreate half of the document while its other store is removed.
            with service.ingest_lock:
                return service.indexer.delete_document(document_id)

        try:
            result = await run_in_threadpool(delete_under_ingest_lock)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="source not found")
        return {"deleted": True, **result}

    # ------------------------------------------------------------------
    # Zero-build demo UI.
    # ------------------------------------------------------------------
    web_dir = Path(__file__).resolve().parents[1] / "web"
    app.mount("/static", StaticFiles(directory=web_dir, check_dir=False), name="static")

    @app.get("/", include_in_schema=False)
    async def demo_ui() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()


def run() -> None:
    """Console-script entry point."""

    import uvicorn

    uvicorn.run(
        "rag_agent.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        app_dir="src",
    )


if __name__ == "__main__":
    run()
