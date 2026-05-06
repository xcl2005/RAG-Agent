
"""SQLite 存储与关键词检索模块。

这个文件做两件事：
1. 用普通表 chunks 保存 chunk 原文和 metadata。
2. 用 SQLite FTS5 虚拟表 chunks_fts 做关键词检索。

为什么不用 Elasticsearch？
- ES/OpenSearch 更像企业级方案，但本项目为了降低部署难度，用 SQLite FTS5。
- 面试时可以说：如果数据量更大，可以把 SQLite FTS5 替换为 Elasticsearch / OpenSearch。
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from rag_agent.schemas import Candidate, Chunk

# 匹配中文字符。SQLite FTS5 默认对中文分词不友好，所以这里自己补中文 bigram。
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 匹配英文、数字、下划线、连字符组成的词。适合技术文档中的 API 名、错误码等。
WORD_RE = re.compile(r"[A-Za-z0-9_\-]{2,}")


def cjk_bigrams(text: str) -> list[str]:
    """把中文文本转成相邻双字 token。

    例子：“向量数据库” -> “向量 / 量数 / 数据 / 据库”。
    这样即使没有中文分词器，也能提高中文关键词召回率。
    """

    chars = CJK_RE.findall(text)
    return [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]


def tokenize_for_fts(text: str) -> list[str]:
    """为 FTS5 查询生成 token。"""

    words = [w.lower() for w in WORD_RE.findall(text)]
    grams = cjk_bigrams(text)

    # 去重但保留顺序，避免 query 太长。
    seen: set[str] = set()
    tokens: list[str] = []
    for token in words + grams:
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def fts_query(text: str) -> str:
    """把用户问题转成 SQLite FTS5 的 MATCH 查询语句。

    这里用 OR 连接多个 token，目的是提高召回率。
    RAG 检索第一阶段宁可多召回一点，再交给 reranker 精排。
    """

    tokens = tokenize_for_fts(text)
    if not tokens:
        # 给一个几乎不可能匹配的 token，避免空查询导致 SQL 报错。
        return '"__empty_query__"'

    safe = []
    for t in tokens[:32]:
        # FTS 查询里双引号需要转义，避免用户输入破坏查询语法。
        t = t.replace('"', '""')
        safe.append(f'"{t}"')
    return " OR ".join(safe)


def search_shadow_text(text: str) -> str:
    """为中文搜索额外加入 bigram 影子文本。

    入库时把原文 + 中文 bigram 一起写入 FTS 表。
    用户搜中文词时，更容易命中。
    """

    grams = " ".join(cjk_bigrams(text))
    return f"{text}\n\n{grams}"


class SQLiteChunkStore:
    """SQLite chunk 仓库。"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # check_same_thread=False 是为了 FastAPI 多线程请求时也能使用同一个连接。
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        """初始化表结构。"""

        cur = self.conn.cursor()

        # chunks：存真正要展示/喂给 LLM 的原文。
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                source TEXT,
                metadata TEXT NOT NULL
            )
            """
        )

        # chunks_fts：FTS5 虚拟表，用于 BM25 关键词检索。
        # chunk_id 设置为 UNINDEXED，因为它只是用来回表查原文，不参与全文检索。
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                text,
                source
            )
            """
        )
        self.conn.commit()

    def reset(self) -> None:
        """删除索引并重新建表。"""

        cur = self.conn.cursor()
        cur.execute("DROP TABLE IF EXISTS chunks")
        cur.execute("DROP TABLE IF EXISTS chunks_fts")
        self.conn.commit()
        self.init_schema()

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> None:
        """插入或更新 chunks。

        同一个 chunk_id 重复导入时，用 ON CONFLICT 更新，避免重复数据。
        """

        cur = self.conn.cursor()
        for chunk in chunks:
            source = str(chunk.metadata.get("source", ""))
            metadata = json.dumps(chunk.metadata, ensure_ascii=False)

            # 先写普通表，保证可以根据 chunk_id 找回原文和 metadata。
            cur.execute(
                """
                INSERT INTO chunks(chunk_id, text, source, metadata)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    text=excluded.text,
                    source=excluded.source,
                    metadata=excluded.metadata
                """,
                (chunk.chunk_id, chunk.text, source, metadata),
            )

            # FTS5 不支持像普通表那样优雅 upsert，所以先删后插。
            cur.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk.chunk_id,))
            cur.execute(
                "INSERT INTO chunks_fts(chunk_id, text, source) VALUES (?, ?, ?)",
                (chunk.chunk_id, search_shadow_text(chunk.text), source),
            )
        self.conn.commit()

    def get_chunk(self, chunk_id: str) -> Candidate | None:
        """根据 chunk_id 取回一个候选证据。"""

        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        if row is None:
            return None
        return Candidate(
            chunk_id=row["chunk_id"],
            text=row["text"],
            metadata=json.loads(row["metadata"]),
            score=0.0,
        )

    def get_chunks(self, chunk_ids: Iterable[str]) -> dict[str, Candidate]:
        """批量取回 chunk，返回 {chunk_id: Candidate}。"""

        return {cid: c for cid in chunk_ids if (c := self.get_chunk(cid)) is not None}

    def search(self, query: str, limit: int = 40) -> list[Candidate]:
        """关键词检索。

        SQLite FTS5 的 bm25 分数越小表示越相关。
        为了和其他分数展示习惯一致，这里转换成越大越好的 sparse_score。
        """

        q = fts_query(query)
        cur = self.conn.cursor()
        rows = cur.execute(
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
        for row in rows:
            sparse_score = 1.0 / (1.0 + abs(float(row["rank_score"])))
            candidates.append(
                Candidate(
                    chunk_id=row["chunk_id"],
                    text=row["text"],
                    metadata=json.loads(row["metadata"]),
                    score=sparse_score,
                    sparse_score=sparse_score,
                )
            )
        return candidates

    def count(self) -> int:
        """返回当前入库的 chunk 数量。"""

        cur = self.conn.cursor()
        return int(cur.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def list_sources(self) -> list[dict]:
        """按文件来源统计 chunk 数量。"""

        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT source, COUNT(*) AS chunks
            FROM chunks
            GROUP BY source
            ORDER BY source
            """
        ).fetchall()
        return [dict(row) for row in rows]
