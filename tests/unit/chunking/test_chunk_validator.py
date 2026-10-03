"""
test_chunk_validator.py — Unit tests for ChunkValidator.
"""
import pytest
from app.engines.chunking.chunk_validator import ChunkValidator
from app.models.chunk import Chunk
from app.core.exceptions import ChunkValidationError


@pytest.fixture
def valid_chunk():
    return Chunk(
        chunk_id="HR-001_CHUNK_0001",
        document_id="HR-001",
        chunk_index=1,
        text="Threshold Enterprise Systems employee expectations.",
        metadata={
            "department": "Human Resources",
            "classification": "INTERNAL",
            "allowed_roles": ["EMPLOYEE", "MANAGER"],
            "document_type": "HANDBOOK",
            "status": "ACTIVE",
            "title": "Employee Handbook",
        },
        source={
            "file_path": "source_documents/hr/handbook.docx",
            "file_format": "DOCX",
        },
        parent_content_hash="a" * 64,
        chunk_content_hash="b" * 64,
        created_at="2026-09-06T12:00:00Z",
    )


def test_valid_chunk(valid_chunk):
    """Verify that a properly constructed chunk passes validation."""
    validator = ChunkValidator()
    result = validator.validate(valid_chunk)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_missing_chunk_id(valid_chunk):
    """Verify validation fails when chunk_id is missing or malformed."""
    validator = ChunkValidator()

    # Empty chunk ID
    valid_chunk.chunk_id = ""
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("chunk_id is missing" in e for e in result.errors)

    # Malformed chunk ID (missing index or prefix)
    valid_chunk.chunk_id = "HR-001_invalid"
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("does not match expected pattern" in e for e in result.errors)


def test_missing_document_id(valid_chunk):
    """Verify validation fails when document_id is missing."""
    validator = ChunkValidator()
    valid_chunk.document_id = ""
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("document_id is missing" in e for e in result.errors)


def test_invalid_chunk_index(valid_chunk):
    """Verify chunk_index must be integer >= 1."""
    validator = ChunkValidator()
    valid_chunk.chunk_index = 0
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("chunk_index must be an integer >= 1" in e for e in result.errors)


def test_empty_chunk_text(valid_chunk):
    """Verify empty or whitespace-only text fails validation."""
    validator = ChunkValidator()
    valid_chunk.text = "   \n\t  "
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("chunk text is empty" in e for e in result.errors)


def test_missing_required_metadata(valid_chunk):
    """Verify missing required governance metadata fields fail validation."""
    validator = ChunkValidator()
    del valid_chunk.metadata["classification"]
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("metadata.classification is missing" in e for e in result.errors)


def test_invalid_allowed_roles(valid_chunk):
    """Verify allowed_roles must be non-empty list of strings."""
    validator = ChunkValidator()

    # Empty list
    valid_chunk.metadata["allowed_roles"] = []
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("allowed_roles cannot be empty" in e for e in result.errors)

    # Not a list
    valid_chunk.metadata["allowed_roles"] = "EMPLOYEE"
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("must be a list" in e for e in result.errors)


def test_invalid_hashes(valid_chunk):
    """Verify 64-char hex format requirement for hashes."""
    validator = ChunkValidator()

    valid_chunk.chunk_content_hash = "short_hash"
    result = validator.validate(valid_chunk)
    assert result.is_valid is False
    assert any("chunk_content_hash is not a valid 64-character SHA-256" in e for e in result.errors)


def test_raise_exception_flag(valid_chunk):
    """Verify ChunkValidationError is raised when raise_exception=True."""
    validator = ChunkValidator()
    valid_chunk.text = ""
    with pytest.raises(ChunkValidationError):
        validator.validate(valid_chunk, raise_exception=True)
