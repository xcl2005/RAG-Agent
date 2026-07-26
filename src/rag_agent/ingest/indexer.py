"""Idempotent, per-document indexing pipeline.

The original demo wrote SQLite first and Qdrant second. A Qdrant failure could
therefore expose half-indexed data. This version writes new vectors first,
atomically swaps the SQLite/FTS document version, and finally removes stale
vectors. Orphan vectors are harmless because results must resolve through the
authoritative SQLite chunk table.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rag_agent.config import Settings, settings
from rag_agent.ingest.chunker import chunk_documents
from rag_agent.ingest.loaders import iter_files, load_document
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore, display_name_from_source
from rag_agent.retrieval.vector_store import QdrantVectorStore
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)
INDEX_SCHEMA_VERSION = 4


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _document_id(source: str) -> str:
    # normcase folds paths on Windows but preserves case on POSIX, matching the
    # host filesystem instead of merging distinct Linux files such as A.md/a.md.
    normalized = os.path.normcase(source)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _index_fingerprint(app_settings: Settings) -> str:
    """Identify every setting/code contract that changes persisted vectors."""

    value = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "chunk_size": app_settings.chunk_size,
        "chunk_overlap": app_settings.chunk_overlap,
        "embedding_model": app_settings.embedding_model,
        "qdrant_collection": app_settings.qdrant_collection,
    }
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Indexer:
    """Index supported files with content-hash based idempotency."""

    def __init__(
        self,
        app_settings: Settings = settings,
        *,
        sqlite_store: SQLiteChunkStore | None = None,
        vector_store: QdrantVectorStore | None = None,
    ):
        self.settings = app_settings
        self.sqlite = sqlite_store or SQLiteChunkStore(app_settings.sqlite_path)
        self.vector = vector_store or QdrantVectorStore(
            url=app_settings.qdrant_url,
            api_key=app_settings.qdrant_api_key,
            collection_name=app_settings.qdrant_collection,
            embedding_model=app_settings.embedding_model,
        )
        self._owns_sqlite = sqlite_store is None

    def reset(self) -> None:
        """Clear both indexes.

        Qdrant is reset first. If it is unavailable, the authoritative SQLite
        index is left intact instead of destroying half the system.
        """

        logger.warning("Resetting Qdrant and SQLite indexes")
        self.vector.reset()
        self.sqlite.reset()

    def is_managed_upload(self, source: str | Path) -> bool:
        """Return whether a source belongs to the browser-managed upload area."""

        upload_root = (Path(self.settings.allowed_ingest_root) / "uploads").resolve()
        try:
            return Path(source).resolve().is_relative_to(upload_root)
        except OSError:
            return False

    def ingest_file(
        self,
        path: str | Path,
        *,
        force: bool = False,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Index one file and return an explainable status record."""

        # One physical file gets one identity whether the caller used a
        # relative CLI path or an absolute API path.
        file = Path(path).resolve()
        source = file.as_posix()
        document_id = _document_id(source)
        content_hash = _sha256_file(file)
        index_fingerprint = _index_fingerprint(self.settings)
        # The source path is an internal storage identity. Keep a separate,
        # stable presentation name so upload hashes never leak into the UI,
        # prompts, citations, or résumé-demo screenshots.
        resolved_display_name = (
            Path(display_name).name.strip() if display_name else display_name_from_source(source)
        ) or display_name_from_source(source)

        if not force and self.sqlite.document_is_current(
            document_id,
            content_hash,
            index_fingerprint,
        ):
            manifest = self.sqlite.get_document(document_id) or {}
            expected_vectors = int(manifest.get("chunk_count", 0))
            try:
                actual_vectors = self.vector.count_document(document_id)
            except Exception as exc:
                logger.warning("Cannot verify vectors for %s; rebuilding: %s", source, exc)
            else:
                if actual_vectors == expected_vectors:
                    if display_name and manifest.get("display_name") != resolved_display_name:
                        self.sqlite.update_document_display_name(
                            document_id,
                            resolved_display_name,
                        )
                    return {
                        "document_id": document_id,
                        "source": source,
                        "display_name": resolved_display_name,
                        "status": "skipped",
                        "reason": "content and index fingerprint unchanged",
                        "chunks": 0,
                    }
                logger.warning(
                    "Vector count mismatch for %s: expected=%s actual=%s; rebuilding",
                    source,
                    expected_vectors,
                    actual_vectors,
                )

        try:
            docs = load_document(file)
            for doc in docs:
                doc.metadata.update(
                    {
                        "source": source,
                        "title": resolved_display_name,
                        "display_name": resolved_display_name,
                        "document_id": document_id,
                        "content_hash": content_hash,
                    }
                )
            chunks = chunk_documents(
                docs,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )

            # 1) Make the new dense version available.
            if chunks:
                self.vector.upsert_chunks(chunks)

            # 2) Atomically replace source text + FTS + manifest.
            stale_ids = self.sqlite.replace_document_chunks(
                document_id=document_id,
                source=source,
                content_hash=content_hash,
                index_fingerprint=index_fingerprint,
                chunks=chunks,
                display_name=resolved_display_name,
            )

            # 3) Best-effort cleanup. Stale vector hits are filtered out because
            #    they can no longer resolve through SQLite.
            if stale_ids:
                try:
                    self.vector.delete_chunks(stale_ids)
                except Exception as cleanup_exc:  # pragma: no cover - external service
                    logger.warning("Stale vector cleanup deferred for %s: %s", source, cleanup_exc)

            # Reconcile all point IDs for this document, including Qdrant-only
            # orphans from failures older than the current SQLite manifest.
            try:
                orphan_count = self.vector.reconcile_document(
                    document_id,
                    (chunk.chunk_id for chunk in chunks),
                )
                if orphan_count:
                    logger.info("Removed %d orphan vector(s) for %s", orphan_count, source)
            except Exception as cleanup_exc:  # pragma: no cover - external service
                logger.warning(
                    "Full vector reconciliation deferred for %s: %s",
                    source,
                    cleanup_exc,
                )

            return {
                "document_id": document_id,
                "source": source,
                "display_name": resolved_display_name,
                "status": "indexed",
                "documents": len(docs),
                "chunks": len(chunks),
                "content_hash": content_hash,
                "index_fingerprint": index_fingerprint,
            }
        except Exception as exc:
            self.sqlite.mark_document_failed(
                document_id=document_id,
                source=source,
                content_hash=content_hash,
                index_fingerprint=index_fingerprint,
                error=str(exc),
                display_name=resolved_display_name,
            )
            raise

    def delete_document(self, document_id: str) -> dict[str, Any] | None:
        """Delete one source from lexical, vector, and managed upload storage.

        SQLite is authoritative for retrieval, so it is removed first in one
        transaction. Qdrant and the managed upload file are then cleaned up on
        a best-effort basis and any deferred cleanup is reported explicitly.
        Files ingested from arbitrary server paths are never unlinked here.
        """

        manifest = self.sqlite.get_document(document_id)
        if manifest is None:
            return None
        if not self.is_managed_upload(str(manifest["source"])):
            raise PermissionError("only browser-managed uploads can be deleted with the app key")

        record = self.sqlite.delete_document(document_id)
        if record is None:
            return None

        deferred: list[str] = []
        vector_chunks_removed = 0
        try:
            vector_chunks_removed = self.vector.reconcile_document(document_id, [])
        except Exception as exc:  # pragma: no cover - external service
            deferred.append("vector")
            logger.warning("Vector cleanup deferred for deleted document %s: %s", document_id, exc)

        file_removed = False
        source_path = Path(str(record["source"]))
        try:
            resolved_source = source_path.resolve()
            if self.is_managed_upload(resolved_source) and resolved_source.is_file():
                resolved_source.unlink()
                file_removed = True
        except OSError as exc:  # pragma: no cover - filesystem dependent
            deferred.append("file")
            logger.warning("File cleanup deferred for deleted document %s: %s", document_id, exc)

        return {
            "document_id": document_id,
            "display_name": record["display_name"],
            "source": record["source"],
            "removed_chunks": len(record["chunk_ids"]),
            "vector_chunks_removed": vector_chunks_removed,
            "file_removed": file_removed,
            "cleanup_deferred": deferred,
        }

    def ingest_path(
        self,
        path: str | Path,
        *,
        reset: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Index all supported files while isolating per-file failures."""

        if reset:
            self.reset()

        files = iter_files(path)
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for file in files:
            try:
                results.append(self.ingest_file(file, force=force))
            except Exception as exc:
                logger.exception("Failed to index %s", file)
                errors.append({"source": file.as_posix(), "error": str(exc)})

        return {
            "scanned_files": len(files),
            "indexed_files": sum(item["status"] == "indexed" for item in results),
            "skipped_files": sum(item["status"] == "skipped" for item in results),
            "failed_files": len(errors),
            "chunks": sum(int(item.get("chunks", 0)) for item in results),
            "results": results,
            "errors": errors,
        }

    def close(self) -> None:
        if self._owns_sqlite:
            self.sqlite.close()
