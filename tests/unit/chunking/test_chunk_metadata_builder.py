"""
test_chunk_metadata_builder.py — Unit tests for ChunkMetadataBuilder.
"""
from app.engines.chunking.chunk_metadata_builder import ChunkMetadataBuilder
from app.models.normalized_document import NormalizedDocument
from app.utils.hash_utils import compute_sha256


def test_chunk_metadata_builder_with_dict():
    """Verify metadata builder correctly creates Chunk from dictionary."""
    doc_dict = {
        "document_id": "SEC-001",
        "title": "Access Control Standard",
        "department": "Security",
        "classification": "RESTRICTED",
        "version": "2.1",
        "status": "ACTIVE",
        "effective_date": "2026-02-01",
        "allowed_roles": ["SECURITY_ENGINEER", "ADMIN"],
        "document_type": "STANDARD",
        "summary": "Mandatory access controls.",
        "keywords": ["access control", "rbac"],
        "file_path": "source_documents/sec/access_control.pdf",
        "file_format": "PDF",
        "content_hash": "a" * 64,
    }

    chunk_text = "All engineers must use hardware security keys."
    builder = ChunkMetadataBuilder()
    chunk = builder.build_chunk(
        parent_doc=doc_dict,
        chunk_text=chunk_text,
        chunk_index=1,
    )

    # 1. Deterministic Chunk ID
    assert chunk.chunk_id == "SEC-001_CHUNK_0001"
    assert chunk.document_id == "SEC-001"
    assert chunk.chunk_index == 1
    assert chunk.text == chunk_text

    # 2. Inherited governance metadata
    assert chunk.metadata["department"] == "Security"
    assert chunk.metadata["classification"] == "RESTRICTED"
    assert chunk.metadata["allowed_roles"] == ["SECURITY_ENGINEER", "ADMIN"]
    assert chunk.metadata["document_type"] == "STANDARD"
    assert chunk.metadata["status"] == "ACTIVE"
    assert chunk.metadata["title"] == "Access Control Standard"

    # 3. Source provenance
    assert chunk.source["file_path"] == "source_documents/sec/access_control.pdf"
    assert chunk.source["file_format"] == "PDF"

    # 4. Hash propagation
    assert chunk.parent_content_hash == "a" * 64
    assert chunk.chunk_content_hash == compute_sha256(chunk_text)

    # 5. Timestamp
    assert len(chunk.created_at) > 0


def test_chunk_metadata_builder_with_dataclass():
    """Verify metadata builder works with NormalizedDocument dataclass."""
    norm_doc = NormalizedDocument(
        document_id="HR-002",
        title="Leave Policy",
        department="Human Resources",
        classification="INTERNAL",
        version="1.0",
        status="ACTIVE",
        effective_date="2026-01-01",
        allowed_roles=["EMPLOYEE", "MANAGER"],
        document_type="POLICY",
        summary="Leave guidelines.",
        keywords=["annual leave", "sick leave"],
        file_path="source_documents/hr/leave.docx",
        file_format="DOCX",
        raw_character_count=1000,
        raw_word_count=150,
        normalized_character_count=1000,
        normalized_word_count=150,
        content_hash="b" * 64,
        content="Leave policy content...",
        ingested_at="2026-09-06T12:00:00Z",
    )

    builder = ChunkMetadataBuilder()
    chunk = builder.build_chunk(
        parent_doc=norm_doc,
        chunk_text="Annual leave entitlement is 20 days.",
        chunk_index=4,
    )

    assert chunk.chunk_id == "HR-002_CHUNK_0004"
    assert chunk.chunk_index == 4
    assert chunk.document_id == "HR-002"
    assert chunk.parent_content_hash == "b" * 64
    assert chunk.metadata["department"] == "Human Resources"
    assert chunk.source["file_format"] == "DOCX"


def test_chunk_id_zero_padding():
    """Verify chunk ID maintains 4-digit zero padding."""
    builder = ChunkMetadataBuilder()
    doc_dict = {"document_id": "ENG-005", "content_hash": "c" * 64}

    chunk_1 = builder.build_chunk(doc_dict, "sample text", 1)
    chunk_42 = builder.build_chunk(doc_dict, "sample text", 42)
    chunk_999 = builder.build_chunk(doc_dict, "sample text", 999)

    assert chunk_1.chunk_id == "ENG-005_CHUNK_0001"
    assert chunk_42.chunk_id == "ENG-005_CHUNK_0042"
    assert chunk_999.chunk_id == "ENG-005_CHUNK_0999"
