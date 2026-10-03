"""
test_chunking_engine.py — Unit tests for ChunkingEngine.
"""
from app.engines.chunking.chunking_engine import ChunkingEngine


def test_process_valid_document():
    """Verify end-to-end processing of a valid document dict."""
    doc_data = {
        "document_id": "OPS-001",
        "title": "Incident Management Protocol",
        "department": "Operations",
        "classification": "CONFIDENTIAL",
        "version": "1.0",
        "status": "ACTIVE",
        "effective_date": "2026-01-01",
        "allowed_roles": ["OPERATIONS_MANAGER", "ADMIN"],
        "document_type": "PROTOCOL",
        "summary": "Protocol for high severity incident management.",
        "keywords": ["incident", "escalation", "sev-1"],
        "file_path": "source_documents/ops/incident.pdf",
        "file_format": "PDF",
        "content_hash": "e" * 64,
        "content": (
            "1. Overview\n"
            "This document establishes the incident management lifecycle.\n\n"
            "2. Severity Classifications\n"
            "SEV-1 represents complete system unavailability.\n\n"
            "3. Incident Commander Roles\n"
            "The incident commander coordinates all remediation actions."
        ),
    }

    engine = ChunkingEngine(chunk_size=150, chunk_overlap=30)
    result = engine.process_document(doc_data)

    assert result.status == "SUCCESS"
    assert result.document_id == "OPS-001"
    assert result.chunks_created >= 2
    assert len(result.chunks) == result.chunks_created
    assert result.error_message is None
    assert len(result.validation_errors) == 0

    # Verify chunk ordering and deterministic IDs
    for idx, chunk in enumerate(result.chunks, start=1):
        assert chunk.chunk_index == idx
        assert chunk.chunk_id == f"OPS-001_CHUNK_{idx:04d}"
        assert chunk.document_id == "OPS-001"
        assert chunk.metadata["department"] == "Operations"
        assert chunk.parent_content_hash == "e" * 64
        assert len(chunk.chunk_content_hash) == 64


def test_process_empty_document():
    """Verify empty document is caught and marked as FAILED with error message."""
    doc_data = {
        "document_id": "OPS-002",
        "title": "Empty Document",
        "department": "Operations",
        "classification": "INTERNAL",
        "allowed_roles": ["EMPLOYEE"],
        "document_type": "NOTE",
        "status": "DRAFT",
        "file_path": "source_documents/ops/empty.txt",
        "file_format": "TXT",
        "content_hash": "f" * 64,
        "content": "   \n\t  ",
    }

    engine = ChunkingEngine()
    result = engine.process_document(doc_data)

    assert result.status == "FAILED"
    assert result.chunks_created == 0
    assert result.error_message is not None
    assert "empty or whitespace-only" in result.error_message


def test_chunking_ordering_preservation():
    """Verify that chunk sequence matches the text sequence in the parent document."""
    sections = [f"Section {i}: Content block describing requirement {i}." for i in range(1, 10)]
    doc_data = {
        "document_id": "ENG-001",
        "title": "Architecture Charter",
        "department": "Engineering",
        "classification": "INTERNAL",
        "allowed_roles": ["ENGINEER"],
        "document_type": "CHARTER",
        "status": "ACTIVE",
        "file_path": "source_documents/eng/charter.txt",
        "file_format": "TXT",
        "content_hash": "1" * 64,
        "content": "\n\n".join(sections),
    }

    engine = ChunkingEngine(chunk_size=120, chunk_overlap=20)
    result = engine.process_document(doc_data)

    assert result.status == "SUCCESS"
    assert len(result.chunks) > 1

    # Check ascending indexes
    indexes = [c.chunk_index for c in result.chunks]
    assert indexes == list(range(1, len(result.chunks) + 1))
