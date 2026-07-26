from types import SimpleNamespace

import numpy as np
import pytest

from rag_agent.retrieval.vector_store import (
    IndexSchemaMismatch,
    QdrantVectorStore,
    point_id_from_chunk_id,
)
from rag_agent.schemas import Chunk


class FakeEmbedding:
    def get_sentence_embedding_dimension(self):
        return 2

    def encode(self, texts, **kwargs):
        return np.array([[float(index), 1.0] for index, _ in enumerate(texts, start=1)])


class FakeQdrant:
    def __init__(
        self,
        *,
        existing_size=None,
        existing_distance="Cosine",
        named_vectors=False,
        fail_ready=False,
    ):
        self.existing_size = existing_size
        self.existing_distance = existing_distance
        self.named_vectors = named_vectors
        self.fail_ready = fail_ready
        self.created = []
        self.upserted = []
        self.deleted = []
        self.collection_deleted = False

    def get_collections(self):
        if self.fail_ready:
            raise RuntimeError("offline")
        names = ["chunks"] if self.existing_size is not None else []
        return SimpleNamespace(collections=[SimpleNamespace(name=name) for name in names])

    def get_collection(self, name):
        params = SimpleNamespace(
            size=self.existing_size,
            distance=self.existing_distance,
        )
        vectors = {"dense": params} if self.named_vectors else params
        return SimpleNamespace(config=SimpleNamespace(params=SimpleNamespace(vectors=vectors)))

    def create_collection(self, **kwargs):
        self.created.append(kwargs)

    def delete_collection(self, **kwargs):
        self.collection_deleted = True
        self.existing_size = None

    def upsert(self, **kwargs):
        self.upserted.extend(kwargs["points"])

    def query_points(self, **kwargs):
        return SimpleNamespace(
            points=[
                SimpleNamespace(payload={"chunk_id": "a" * 64}, score=0.9),
                SimpleNamespace(payload={}, score=0.8),
            ]
        )

    def delete(self, **kwargs):
        self.deleted.extend(kwargs["points_selector"].points)

    def count(self, **kwargs):
        return SimpleNamespace(count=len(self.upserted))

    def scroll(self, **kwargs):
        points = [SimpleNamespace(id=point.id, payload=point.payload) for point in self.upserted]
        return points, None


def make_store(client, *, vector_size=2):
    store = QdrantVectorStore.__new__(QdrantVectorStore)
    store.client = client
    store.collection_name = "chunks"
    store.embedding_model_name = "fake/embedding"
    store.model = FakeEmbedding()
    store.vector_size = vector_size
    return store


def test_point_id_is_stable_uuid():
    chunk_id = "a" * 64
    assert point_id_from_chunk_id(chunk_id) == point_id_from_chunk_id(chunk_id)
    assert len(point_id_from_chunk_id(chunk_id)) == 36


def test_collection_creation_and_schema_mismatch():
    client = FakeQdrant()
    store = make_store(client)
    store.ensure_collection()
    assert client.created[0]["vectors_config"].size == 2

    mismatched = make_store(FakeQdrant(existing_size=3))
    with pytest.raises(IndexSchemaMismatch, match="dimension 3"):
        mismatched.ensure_collection()

    wrong_distance = make_store(FakeQdrant(existing_size=2, existing_distance="Dot"))
    with pytest.raises(IndexSchemaMismatch, match="requires cosine"):
        wrong_distance.ensure_collection()

    named = make_store(FakeQdrant(existing_size=2, named_vectors=True))
    with pytest.raises(IndexSchemaMismatch, match="named vectors"):
        named.ensure_collection()


def test_embedding_upsert_search_delete_and_ready():
    client = FakeQdrant(existing_size=2)
    store = make_store(client)
    chunks = [
        Chunk(
            chunk_id="a" * 64,
            text="first",
            metadata={"source": "guide.md", "document_id": "doc-1", "chunk_index": 0},
        ),
        Chunk(
            chunk_id="b" * 64,
            text="second",
            metadata={"source": "guide.md", "document_id": "doc-1", "chunk_index": 1},
        ),
    ]

    assert store.embed_texts(["a", "b"]) == [[1.0, 1.0], [2.0, 1.0]]
    store.upsert_chunks(chunks, batch_size=1)
    assert len(client.upserted) == 2
    assert client.upserted[0].payload["source"] == "guide.md"

    hits = store.search("question", limit=2)
    assert [hit["chunk_id"] for hit in hits] == ["a" * 64]

    store.delete_chunks([])
    store.delete_chunks(["a" * 64])
    assert client.deleted == [point_id_from_chunk_id("a" * 64)]
    assert store.count_document("doc-1") == 2

    client.upserted.append(SimpleNamespace(id="orphan-point", payload={"document_id": "doc-1"}))
    assert store.reconcile_document("doc-1", ["a" * 64, "b" * 64]) == 1
    assert client.deleted[-1] == "orphan-point"

    ready, detail = store.ready()
    assert ready is True
    assert "compatible" in detail


def test_reset_recreates_existing_collection_and_ready_can_degrade():
    client = FakeQdrant(existing_size=2)
    store = make_store(client)
    store.reset()
    assert client.collection_deleted is True
    assert client.created

    offline = make_store(FakeQdrant(fail_ready=True))
    ready, detail = offline.ready()
    assert ready is False
    assert "offline" in detail
