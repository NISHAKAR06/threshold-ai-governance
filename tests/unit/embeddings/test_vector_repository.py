"""
test_vector_repository.py — Unit tests for VectorRepository and VectorStore implementations.
"""
from pathlib import Path
from app.database.vector_store import InMemoryVectorStore, ChromaVectorStore
from app.repositories.vector_repository import VectorRepository
from app.models.embedding_record import VectorRecord


def _create_sample_record(vector_id: str, doc_id: str, text: str = "sample") -> VectorRecord:
    return VectorRecord(
        vector_id=vector_id,
        embedding=[0.1, 0.2, 0.3, 0.4],
        chunk_id=vector_id.replace("_VEC", ""),
        document_id=doc_id,
        text=text,
        metadata={
            "department": "Engineering",
            "classification": "INTERNAL",
            "allowed_roles": ["ENGINEER"],
            "document_type": "GUIDE",
            "status": "ACTIVE",
        },
        source={"file_path": "test.txt", "file_format": "TXT"},
        parent_content_hash="a" * 64,
        chunk_content_hash="b" * 64,
        embedding_provider="mock",
        embedding_model="mock-768",
        embedding_dimension=4,
        indexed_at="2026-09-06T12:00:00Z",
    )


def test_in_memory_vector_repository():
    """Verify in-memory repository operations: init, upsert, count, get, delete."""
    store = InMemoryVectorStore(collection_name="test_col")
    repo = VectorRepository(store=store)

    repo.initialize()
    assert repo.health_check() is True
    assert repo.count() == 0

    # 1. Upsert
    rec1 = _create_sample_record("DOC-1_CHUNK_0001_VEC", "DOC-1")
    rec2 = _create_sample_record("DOC-1_CHUNK_0002_VEC", "DOC-1")
    rec3 = _create_sample_record("DOC-2_CHUNK_0001_VEC", "DOC-2")

    upserted = repo.upsert_records([rec1, rec2, rec3])
    assert upserted == 3
    assert repo.count() == 3

    # 2. Idempotent re-run
    re_upserted = repo.upsert_records([rec1, rec2])
    assert re_upserted == 2
    assert repo.count() == 3  # Count stays 3! No uncontrolled duplicates!

    # 3. Retrieve
    fetched = repo.get_record("DOC-1_CHUNK_0001_VEC")
    assert fetched is not None
    assert fetched.document_id == "DOC-1"

    # 4. Delete document vectors
    deleted = repo.delete_document_vectors("DOC-1")
    assert deleted == 2
    assert repo.count() == 1
    assert repo.get_record("DOC-2_CHUNK_0001_VEC") is not None


def test_chroma_vector_repository(tmp_path: Path):
    """Verify ChromaDB repository operations: init, upsert, idempotent update, and metadata retrieval."""
    store = ChromaVectorStore(path=tmp_path / "chroma_db", collection_name="test_chroma_col")
    repo = VectorRepository(store=store)

    repo.initialize()
    assert repo.health_check() is True
    assert repo.count() == 0

    # 1. Upsert records
    rec1 = _create_sample_record("SEC-1_CHUNK_0001_VEC", "SEC-1", "Security policy chunk 1")
    rec2 = _create_sample_record("SEC-1_CHUNK_0002_VEC", "SEC-1", "Security policy chunk 2")

    upserted = repo.upsert_records([rec1, rec2])
    assert upserted == 2
    assert repo.count() == 2

    # 2. Idempotent re-run
    repo.upsert_records([rec1, rec2])
    assert repo.count() == 2

    # 3. Lookup and governance metadata verification
    fetched = repo.get_record("SEC-1_CHUNK_0001_VEC")
    assert fetched is not None
    assert fetched.vector_id == "SEC-1_CHUNK_0001_VEC"
    assert fetched.metadata["department"] == "Engineering"
    assert fetched.metadata["allowed_roles"] == ["ENGINEER"]
    assert len(fetched.embedding) == 4
