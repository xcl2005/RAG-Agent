"""SQLite metadata store and FTS5 lexical retrieval.

SQLite remains intentionally small and local for a portfolio/demo deployment,
but the implementation still applies production-minded basics: WAL mode,
bounded lock waits, batched reads, a document manifest, and transactional
replacement of all chunks belonging to one document.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from rag_agent.schemas import Candidate, Chunk
from rag_agent.utils.logging import get_logger

CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
WORD_RE = re.compile(r"[A-Za-z0-9_\-]{2,}")
UPLOAD_STORED_NAME_RE = re.compile(r"^[0-9a-f]{12}-(?P<name>.+)$", re.IGNORECASE)
logger = get_logger(__name__)


def cjk_bigrams(text: str) -> list[str]:
    """Build bigrams inside each contiguous Chinese run.

    Splitting by runs prevents false tokens from being formed across punctuation
    or paragraph boundaries.
    """

    tokens: list[str] = []
    for run in CJK_RUN_RE.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


def tokenize_for_fts(text: str) -> list[str]:
    """Create stable lexical tokens for mixed Chinese/English technical text."""

    raw_tokens = [word.lower() for word in WORD_RE.findall(text)] + cjk_bigrams(text)
    return list(dict.fromkeys(raw_tokens))


def fts_query(text: str) -> str:
    """Convert user text to a safely quoted, recall-oriented FTS5 query."""

    tokens = tokenize_for_fts(text)
    if not tokens:
        return '"__empty_query__"'
    safe = [f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens[:24]]
    return " OR ".join(safe)


def search_shadow_text(text: str) -> str:
    """Append Chinese bigrams to the indexed text without changing source text."""

    return f"{text}\n\n{' '.join(cjk_bigrams(text))}"


def display_name_from_source(source: str) -> str:
    """Return a human-facing name without exposing upload storage prefixes.

    Uploaded files use a deterministic 12-character hash prefix on disk so
    repeated uploads of the same logical filename replace the same target.
    That prefix is an implementation detail and should never become the title
    shown in the UI or in citations.
    """

    filename = Path(source).name or source
    match = UPLOAD_STORED_NAME_RE.fullmatch(filename)
    if not match:
        return filename

    stored_name = match.group("name")
    # Old versions did not persist the original filename. For the common case
    # where sanitization only changed spaces to underscores, the stored hash
    # lets us recover it exactly instead of guessing. Limit the search so a
    # malicious or unusually long filename cannot create exponential work.
    underscore_positions = [index for index, char in enumerate(stored_name) if char == "_"]
    if len(underscore_positions) <= 12:
        recovered: list[str] = []
        for mask in range(1 << len(underscore_positions)):
            chars = list(stored_name)
            for bit, position in enumerate(underscore_positions):
                chars[position] = " " if mask & (1 << bit) else "_"
            candidate = "".join(chars)
            candidate_hash = hashlib.sha256(candidate.casefold().encode("utf-8")).hexdigest()[:12]
            if candidate_hash == match.group(0)[:12].lower():
                recovered.append(candidate)
                if len(recovered) > 1:
                    break
        if len(recovered) == 1:
            return recovered[0]
    return stored_name


class SQLiteChunkStore:
    """Thread-safe local document manifest, chunk store, and lexical index."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=10000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.init_schema()

    def init_schema(self) -> None:
        """Create the current schema and migrate the original demo schema."""

        with self._lock, self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL DEFAULT '',
                    content_hash TEXT NOT NULL,
                    index_fingerprint TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            document_columns = {
                str(row["name"]) for row in self.conn.execute("PRAGMA table_info(documents)").fetchall()
            }
            if "index_fingerprint" not in document_columns:
                self.conn.execute(
                    "ALTER TABLE documents ADD COLUMN index_fingerprint TEXT NOT NULL DEFAULT ''"
                )
            if "display_name" not in document_columns:
                self.conn.execute("ALTER TABLE documents ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
            # Older databases only know the physical upload path. Recover the
            # readable part of those filenames during the migration so the fix
            # is visible immediately, without forcing users to re-upload data.
            unnamed_rows = self.conn.execute(
                """
                SELECT document_id, source
                FROM documents
                WHERE display_name IS NULL OR TRIM(display_name) = ''
                """
            ).fetchall()
            for row in unnamed_rows:
                self.conn.execute(
                    "UPDATE documents SET display_name = ? WHERE document_id = ?",
                    (display_name_from_source(str(row["source"])), str(row["document_id"])),
                )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    text TEXT NOT NULL,
                    source TEXT,
                    metadata TEXT NOT NULL
                )
                """
            )
            columns = {str(row["name"]) for row in self.conn.execute("PRAGMA table_info(chunks)").fetchall()}
            if "document_id" not in columns:
                self.conn.execute("ALTER TABLE chunks ADD COLUMN document_id TEXT")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
            self.conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    text,
                    source
                )
                """
            )
            # The original demo schema had no stable document identity. Keeping
            # those rows would make a later same-source replacement leave
            # searchable ghost chunks forever. Legacy indexes are derived data,
            # so discard only unmigratable rows and require a clean re-ingest.
            legacy_rows = self.conn.execute(
                "SELECT chunk_id FROM chunks WHERE document_id IS NULL OR document_id = ''"
            ).fetchall()
            legacy_ids = [str(row["chunk_id"]) for row in legacy_rows]
            if legacy_ids:
                logger.warning(
                    "Removing %d legacy chunk(s) without document identity; "
                    "re-run ingestion to rebuild the knowledge index",
                    len(legacy_ids),
                )
                placeholders = ",".join("?" for _ in legacy_ids)
                self.conn.execute(
                    f"DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})",
                    legacy_ids,
                )
                self.conn.execute(
                    f"DELETE FROM chunks WHERE chunk_id IN ({placeholders})",
                    legacy_ids,
                )

            # Repair evidence titles from earlier upload versions as well as
            # the manifest label. Hybrid retrieval resolves candidates through
            # this SQLite metadata, so existing citations become readable as
            # soon as the service restarts.
            uploaded_documents = self.conn.execute(
                "SELECT document_id, source, display_name FROM documents"
            ).fetchall()
            for document in uploaded_documents:
                if not UPLOAD_STORED_NAME_RE.fullmatch(Path(str(document["source"])).name):
                    continue
                chunk_rows = self.conn.execute(
                    "SELECT chunk_id, metadata FROM chunks WHERE document_id = ?",
                    (str(document["document_id"]),),
                ).fetchall()
                for chunk_row in chunk_rows:
                    try:
                        metadata = json.loads(str(chunk_row["metadata"]))
                    except json.JSONDecodeError:
                        continue
                    display_name = str(document["display_name"])
                    if metadata.get("title") == display_name and metadata.get("display_name") == display_name:
                        continue
                    metadata["title"] = display_name
                    metadata["display_name"] = display_name
                    self.conn.execute(
                        "UPDATE chunks SET metadata = ? WHERE chunk_id = ?",
                        (
                            json.dumps(metadata, ensure_ascii=False),
                            str(chunk_row["chunk_id"]),
                        ),
                    )

    def reset(self) -> None:
        """Drop local indexes. Callers must protect this destructive operation."""

        with self._lock, self.conn:
            self.conn.execute("DROP TABLE IF EXISTS chunks")
            self.conn.execute("DROP TABLE IF EXISTS chunks_fts")
            self.conn.execute("DROP TABLE IF EXISTS documents")
        self.init_schema()

    def document_is_current(
        self,
        document_id: str,
        content_hash: str,
        index_fingerprint: str,
    ) -> bool:
        with self._lock:
            row = self.conn.execute(
                """
                SELECT content_hash, index_fingerprint, status
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        return bool(
            row
            and row["content_hash"] == content_hash
            and row["index_fingerprint"] == index_fingerprint
            and row["status"] == "ready"
        )

    def get_document(self, document_id: str) -> dict | None:
        with self._lock:
            row = self.conn.execute(
                """
                SELECT document_id, source, display_name, content_hash, index_fingerprint,
                       status, chunk_count, error, updated_at
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def mark_document_failed(
        self,
        *,
        document_id: str,
        source: str,
        content_hash: str,
        index_fingerprint: str,
        error: str,
        display_name: str | None = None,
    ) -> None:
        """Record a per-file failure without losing the rest of an ingest batch."""

        now = datetime.now(timezone.utc).isoformat()
        resolved_display_name = display_name or display_name_from_source(source)
        with self._lock, self.conn:
            self.conn.execute(
                """
                INSERT INTO documents(
                    document_id, source, display_name, content_hash, index_fingerprint,
                    status, chunk_count, error, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'failed', 0, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    source=excluded.source,
                    display_name=excluded.display_name,
                    content_hash=excluded.content_hash,
                    index_fingerprint=excluded.index_fingerprint,
                    status='failed',
                    error=excluded.error,
                    updated_at=excluded.updated_at
                """,
                (
                    document_id,
                    source,
                    resolved_display_name,
                    content_hash,
                    index_fingerprint,
                    error[:2000],
                    now,
                ),
            )

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        source: str,
        content_hash: str,
        index_fingerprint: str,
        chunks: list[Chunk],
        display_name: str | None = None,
    ) -> list[str]:
        """Atomically replace the lexical/chunk side of one document.

        Returns stale chunk IDs so the vector side can remove them after this
        transaction commits.
        """

        now = datetime.now(timezone.utc).isoformat()
        resolved_display_name = display_name or display_name_from_source(source)
        with self._lock, self.conn:
            stale_rows = self.conn.execute(
                "SELECT chunk_id FROM chunks WHERE document_id = ?",
                (document_id,),
            ).fetchall()
            stale_ids = [str(row["chunk_id"]) for row in stale_rows]

            if stale_ids:
                placeholders = ",".join("?" for _ in stale_ids)
                self.conn.execute(
                    f"DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})",
                    stale_ids,
                )
                self.conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

            for chunk in chunks:
                metadata = dict(chunk.metadata)
                metadata["document_id"] = document_id
                chunk.metadata = metadata
                self.conn.execute(
                    """
                    INSERT INTO chunks(chunk_id, document_id, text, source, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        document_id,
                        chunk.text,
                        source,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
                self.conn.execute(
                    "INSERT INTO chunks_fts(chunk_id, text, source) VALUES (?, ?, ?)",
                    (chunk.chunk_id, search_shadow_text(chunk.text), source),
                )

            self.conn.execute(
                """
                INSERT INTO documents(
                    document_id, source, display_name, content_hash, index_fingerprint,
                    status, chunk_count, error, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'ready', ?, NULL, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    source=excluded.source,
                    display_name=excluded.display_name,
                    content_hash=excluded.content_hash,
                    index_fingerprint=excluded.index_fingerprint,
                    status='ready',
                    chunk_count=excluded.chunk_count,
                    error=NULL,
                    updated_at=excluded.updated_at
                """,
                (
                    document_id,
                    source,
                    resolved_display_name,
                    content_hash,
                    index_fingerprint,
                    len(chunks),
                    now,
                ),
            )
        return [chunk_id for chunk_id in stale_ids if chunk_id not in {chunk.chunk_id for chunk in chunks}]

    def update_document_display_name(self, document_id: str, display_name: str) -> None:
        """Update manifest and citation titles without rebuilding embeddings."""

        with self._lock, self.conn:
            self.conn.execute(
                "UPDATE documents SET display_name = ? WHERE document_id = ?",
                (display_name, document_id),
            )
            chunk_rows = self.conn.execute(
                "SELECT chunk_id, metadata FROM chunks WHERE document_id = ?",
                (document_id,),
            ).fetchall()
            for chunk_row in chunk_rows:
                try:
                    metadata = json.loads(str(chunk_row["metadata"]))
                except json.JSONDecodeError:
                    continue
                metadata["title"] = display_name
                metadata["display_name"] = display_name
                self.conn.execute(
                    "UPDATE chunks SET metadata = ? WHERE chunk_id = ?",
                    (
                        json.dumps(metadata, ensure_ascii=False),
                        str(chunk_row["chunk_id"]),
                    ),
                )

    def delete_document(self, document_id: str) -> dict | None:
        """Atomically remove one document manifest and every lexical chunk.

        The returned chunk IDs let the indexing service clean the corresponding
        vector points after SQLite—the authoritative retrieval store—commits.
        """

        with self._lock, self.conn:
            row = self.conn.execute(
                """
                SELECT document_id, source, display_name, content_hash,
                       index_fingerprint, status, chunk_count, error, updated_at
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
            if row is None:
                return None

            chunk_rows = self.conn.execute(
                "SELECT chunk_id FROM chunks WHERE document_id = ?",
                (document_id,),
            ).fetchall()
            chunk_ids = [str(chunk_row["chunk_id"]) for chunk_row in chunk_rows]
            if chunk_ids:
                placeholders = ",".join("?" for _ in chunk_ids)
                self.conn.execute(
                    f"DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})",
                    chunk_ids,
                )
            self.conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            self.conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))

        result = dict(row)
        result["chunk_ids"] = chunk_ids
        return result

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> None:
        """Compatibility helper for tests/legacy callers without a manifest."""

        with self._lock, self.conn:
            for chunk in chunks:
                source = str(chunk.metadata.get("source", ""))
                document_id = str(chunk.metadata.get("document_id", ""))
                metadata = json.dumps(chunk.metadata, ensure_ascii=False)
                self.conn.execute(
                    """
                    INSERT INTO chunks(chunk_id, document_id, text, source, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                        document_id=excluded.document_id,
                        text=excluded.text,
                        source=excluded.source,
                        metadata=excluded.metadata
                    """,
                    (chunk.chunk_id, document_id, chunk.text, source, metadata),
                )
                self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk.chunk_id,))
                self.conn.execute(
                    "INSERT INTO chunks_fts(chunk_id, text, source) VALUES (?, ?, ?)",
                    (chunk.chunk_id, search_shadow_text(chunk.text), source),
                )

    @staticmethod
    def _candidate_from_row(row: sqlite3.Row) -> Candidate:
        return Candidate(
            chunk_id=row["chunk_id"],
            text=row["text"],
            metadata=json.loads(row["metadata"]),
            score=0.0,
        )

    def get_chunk(self, chunk_id: str) -> Candidate | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT chunk_id, text, metadata FROM chunks WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()
        return self._candidate_from_row(row) if row else None

    def get_chunks(self, chunk_ids: Iterable[str]) -> dict[str, Candidate]:
        """Fetch all candidates in one query instead of the original N+1 loop."""

        ids = list(dict.fromkeys(chunk_ids))
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            rows = self.conn.execute(
                f"SELECT chunk_id, text, metadata FROM chunks WHERE chunk_id IN ({placeholders})",
                ids,
            ).fetchall()
        return {str(row["chunk_id"]): self._candidate_from_row(row) for row in rows}

    def search(self, query: str, limit: int = 40) -> list[Candidate]:
        q = fts_query(query)
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT c.chunk_id, c.text, c.metadata, bm25(chunks_fts) AS rank_score
                FROM chunks_fts
                JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
                WHERE chunks_fts MATCH ?
                ORDER BY rank_score ASC
                LIMIT ?
                """,
                (q, limit),
            ).fetchall()

        candidates: list[Candidate] = []
        query_tokens = set(tokenize_for_fts(query))
        for row in rows:
            raw_rank = float(row["rank_score"])
            text_tokens = set(tokenize_for_fts(row["text"]))
            # FTS5 bm25 values are ranking signals whose scale depends on the
            # corpus. Token coverage provides a bounded, query-local signal for
            # the evidence gate while bm25 still determines result order.
            sparse_score = len(query_tokens & text_tokens) / len(query_tokens) if query_tokens else 0.0
            candidates.append(
                Candidate(
                    chunk_id=row["chunk_id"],
                    text=row["text"],
                    metadata=json.loads(row["metadata"]),
                    score=sparse_score,
                    sparse_score=sparse_score,
                    debug={"bm25_raw": raw_rank},
                )
            )
        return candidates

    def count(self) -> int:
        with self._lock:
            return int(self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def list_sources(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT document_id, source, display_name, content_hash, index_fingerprint,
                       status, chunk_count, error, updated_at
                FROM documents
                ORDER BY display_name COLLATE NOCASE, source
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def ready(self) -> tuple[bool, str]:
        try:
            with self._lock:
                self.conn.execute("SELECT 1").fetchone()
            return True, "sqlite ready"
        except sqlite3.Error as exc:  # pragma: no cover - filesystem dependent
            return False, str(exc)

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def __enter__(self) -> SQLiteChunkStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
