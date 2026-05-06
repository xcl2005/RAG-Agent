
"""项目中的核心数据结构。

这里用 dataclass 而不是复杂 ORM，是为了让你更容易看懂 RAG 流程中的数据传递：
RawDocument -> Chunk -> Candidate。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawDocument:
    """刚从文件解析出来的原始文档单元。

    例子：
    - PDF 通常按页解析，所以一页就是一个 RawDocument。
    - Markdown/TXT 通常整个文件就是一个 RawDocument。
    """

    text: str
    metadata: dict[str, Any]


@dataclass
class Chunk:
    """切分后的文本片段。

    RAG 不会把整本 PDF 全塞给模型，而是先切成 chunk。
    检索时找到最相关的几个 chunk，再交给 LLM 回答。
    """

    chunk_id: str
    text: str
    metadata: dict[str, Any]


@dataclass
class Candidate:
    """检索阶段返回的候选证据。

    一个 Candidate 基本就是“一个可能有用的 chunk + 各种分数”。
    dense_score：向量检索分数。
    sparse_score：关键词检索分数。
    rerank_score：重排模型分数。
    score：当前排序时使用的最终分数。
    """

    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float = 0.0
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    debug: dict[str, Any] = field(default_factory=dict)
