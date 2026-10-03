"""
test_vector_record_builder.py — Unit tests for VectorRecordBuilder.
"""
from app.engines.embeddings.vector_record_builder import VectorRecordBuilder
from app.models.chunk import Chunk


def test_build_vector_record_from_chunk_dataclass():
    """Verify VectorRecordBuilder correctly preserves all chunk and governance fields."""
    chunk = Chunk(
        chunk_id="HR-001_CHUNK_0001",
        document_id="HR-001",
        chunk_index=1,
        text="Employee handbook general conduct policy.",
        metadata={
            "department": "Human Resources",
            "classification": "INTERNAL",
            "allowed_roles": ["EMPLOYEE", "MANAGER"],
            "document_type": "HANDBOOK",
            "status": "ACTIVE",
            "title": "Employee Handbook",
            "version": "1.0",
        },
        source={
            "file_path": "source_documents/hr/handbook.docx",
            "file_format": "DOCX",
        },
        parent_content_hash="a" * 64,
        chunk_content_hash="b" * 64,
        created_at="2026-09-06T12:00:00Z",
    )

    embedding = [0.1, 0.2, 0.3, 0.4]
    builder = VectorRecordBuilder()
    record = builder.build_record(
        chunk=chunk,
        embedding=embedding,
        embedding_provider="mock",
        embedding_model="mock-768",
        embedding_dimension=4,
    )

    # 1. Deterministic vector ID
    assert record.vector_id == "HR-001_CHUNK_0001_VEC"
    assert record.chunk_id == "HR-001_CHUNK_0001"
    assert record.document_id == "HR-001"
    assert record.embedding == embedding
    assert record.text == "Employee handbook general conduct policy."

    # 2. Governance metadata preservation
    assert record.metadata["department"] == "Human Resources"
    assert record.metadata["classification"] == "INTERNAL"
    assert record.metadata["allowed_roles"] == ["EMPLOYEE", "MANAGER"]
    assert record.metadata["document_type"] == "HANDBOOK"
    assert record.metadata["status"] == "ACTIVE"

    # 3. Provenance & hashes
    assert record.source["file_path"] == "source_documents/hr/handbook.docx"
    assert record.parent_content_hash == "a" * 64
    assert record.chunk_content_hash == "b" * 64

    # 4. Provider metadata
    assert record.embedding_provider == "mock"
    assert record.embedding_model == "mock-768"
    assert record.embedding_dimension == 4
    assert len(record.indexed_at) > 0


def test_build_vector_record_from_dict():
    """Verify builder works seamlessly with dictionary input."""
    chunk_dict = {
        "chunk_id": "SEC-002_CHUNK_0005",
        "document_id": "SEC-002",
        "text": "Firewall configuration requirements.",
        "metadata": {
            "department": "Security",
            "classification": "CONFIDENTIAL",
            "allowed_roles": ["SECURITY_ENGINEER"],
            "document_type": "POLICY",
            "status": "ACTIVE",
        },
        "source": {"file_path": "sec/firewall.pdf", "file_format": "PDF"},
        "parent_content_hash": "c" * 64,
        "chunk_content_hash": "d" * 64,
    }

    record = VectorRecordBuilder.build_record(
        chunk=chunk_dict,
        embedding=[0.5, -0.5],
        embedding_provider="gemini",
        embedding_model="text-embedding-004",
    )

    assert record.vector_id == "SEC-002_CHUNK_0005_VEC"
    assert record.document_id == "SEC-002"
    assert record.embedding_dimension == 2
    assert record.metadata["department"] == "Security"
