
"""chunker 的单元测试。

测试目标不是覆盖所有情况，而是确认最核心的事情：
长文档能被切成多个 chunk，每个 chunk 有 id，并且 metadata 不丢。
"""

from rag_agent.ingest.chunker import chunk_document
from rag_agent.schemas import RawDocument


def test_chunk_document_creates_chunks():
    doc = RawDocument(text="第一段。" * 200, metadata={"source": "test.md"})
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(c.chunk_id for c in chunks)
    assert all(c.metadata["source"] == "test.md" for c in chunks)
