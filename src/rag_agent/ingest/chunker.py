
"""Chunk 切分模块。

这部分是 RAG 项目的面试高频点。
为什么要切 chunk？
- 大模型上下文有限，不能把所有资料都塞进去。
- 检索的基本单位太大，会召回很多无关内容；太小，又可能语义不完整。

本项目实现的是“递归字符切分 + overlap”：
优先按段落切，再按换行、中文句号、英文句号、空格切，最后才按字符切。
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

from rag_agent.schemas import Chunk, RawDocument


def normalize_text(text: str) -> str:
    """做基础文本清洗。

    这里只做轻量清洗，避免把文档结构破坏掉。
    """

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_by_separator(text: str, separator: str) -> list[str]:
    """按指定分隔符切分，并尽量保留分隔符。

    保留分隔符的原因：句号、换行本身能帮助模型理解文本结构。
    """

    if separator == "":
        return list(text)
    parts = text.split(separator)
    return [p + separator for p in parts[:-1]] + parts[-1:]


def recursive_split(text: str, chunk_size: int, separators: list[str] | None = None) -> list[str]:
    """递归切分文本。

    算法直觉：
    1. 先尝试用“大的语义边界”切，比如段落。 
    2. 如果某一段仍然太长，再用更小的边界切，比如句号、空格。
    3. 如果还太长，最后按字符硬切。

    这样比简单 text[i:i+chunk_size] 更不容易切断语义。
    """

    if separators is None:
        separators = ["\n\n", "\n", "。", "！", "？", ". ", " ", ""]

    text = normalize_text(text)
    if len(text) <= chunk_size:
        return [text] if text else []

    sep = separators[0]
    parts = _split_by_separator(text, sep)

    chunks: list[str] = []
    current = ""
    for part in parts:
        # 当前 part 自己就超过 chunk_size，说明这个分隔符还不够细，继续递归使用下一级分隔符。
        if len(part) > chunk_size and len(separators) > 1:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            chunks.extend(recursive_split(part, chunk_size, separators[1:]))
            continue

        # 能放进当前 chunk 就继续累积。
        if len(current) + len(part) <= chunk_size:
            current += part
        else:
            # 放不下就结束当前 chunk，开一个新的 chunk。
            if current.strip():
                chunks.append(current.strip())
            current = part

    if current.strip():
        chunks.append(current.strip())
    return chunks


def add_overlap(chunks: list[str], overlap: int) -> list[str]:
    """给相邻 chunk 添加重叠文本。

    例子：
    chunk1 结尾解释了一个名词，chunk2 开头继续说细节。
    如果没有 overlap，检索到 chunk2 时可能缺少前文定义。
    """

    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    result: list[str] = []
    prev_tail = ""
    for chunk in chunks:
        merged = (prev_tail + "\n" + chunk).strip() if prev_tail else chunk
        result.append(merged)
        prev_tail = chunk[-overlap:]
    return result


def make_chunk_id(source: str, index: int, text: str, metadata: dict) -> str:
    """生成稳定的 chunk_id。

    使用 sha256 的好处：
    - 同一个文件、同一段文本重复导入时 ID 一样，方便 upsert。
    - 不暴露原文内容。
    """

    page = metadata.get("page", "")
    raw = f"{source}|{page}|{index}|{text[:120]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chunk_document(doc: RawDocument, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """把一个 RawDocument 切成多个 Chunk。"""

    base_chunks = recursive_split(doc.text, chunk_size=chunk_size)
    with_overlap = add_overlap(base_chunks, chunk_overlap)

    chunks: list[Chunk] = []
    source = str(doc.metadata.get("source", "unknown"))
    for i, text in enumerate(with_overlap):
        metadata = dict(doc.metadata)
        metadata["chunk_index"] = i
        chunk_id = make_chunk_id(source, i, text, metadata)
        chunks.append(Chunk(chunk_id=chunk_id, text=text, metadata=metadata))
    return chunks


def chunk_documents(docs: Iterable[RawDocument], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """批量切分多个文档。"""

    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, chunk_size, chunk_overlap))
    return all_chunks
