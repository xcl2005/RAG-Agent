"""chunker 的单元测试。

测试目标不是覆盖所有情况，而是确认最核心的事情：
长文档能被切成多个 chunk，每个 chunk 有 id，并且 metadata 不丢。
"""

from rag_agent.ingest.chunker import chunk_document, chunk_documents
from rag_agent.schemas import RawDocument


def test_chunk_document_creates_chunks():
    doc = RawDocument(text="第一段。" * 200, metadata={"source": "test.md"})
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(c.chunk_id for c in chunks)
    assert all(c.metadata["source"] == "test.md" for c in chunks)
    assert all(len(c.text) <= 100 for c in chunks)


def test_chunk_id_uses_full_text_not_only_prefix():
    prefix = "相同开头" * 30
    first = RawDocument(text=prefix + "A", metadata={"source": "test.md"})
    second = RawDocument(text=prefix + "B", metadata={"source": "test.md"})

    first_id = chunk_document(first, chunk_size=1000, chunk_overlap=0)[0].chunk_id
    second_id = chunk_document(second, chunk_size=1000, chunk_overlap=0)[0].chunk_id

    assert first_id != second_id


def test_repeated_document_units_get_distinct_chunk_ids():
    """Repeated headings/pages must not overwrite each other in SQLite."""

    docs = [
        RawDocument(
            text="# FAQ\nSame answer.",
            metadata={"source": "faq.md", "heading": "FAQ"},
        ),
        RawDocument(
            text="# FAQ\nSame answer.",
            metadata={"source": "faq.md", "heading": "FAQ"},
        ),
    ]

    chunks = chunk_documents(docs, chunk_size=128, chunk_overlap=16)

    assert len(chunks) == 2
    assert len({chunk.chunk_id for chunk in chunks}) == 2
    assert [chunk.metadata["document_unit_index"] for chunk in chunks] == [0, 1]
