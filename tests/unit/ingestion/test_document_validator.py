"""
test_document_validator.py — Unit tests for DocumentValidator.
"""
import pytest
from app.engines.ingestion.document_validator import DocumentValidator
from app.schemas.document_schema import DocumentMetadataSchema
from app.core.exceptions import DocumentValidationError


@pytest.fixture
def valid_metadata():
    return DocumentMetadataSchema(
        document_id="HR-001",
        title="Employee Handbook",
        department="Human Resources",
        classification="INTERNAL",
        version="1.0",
        status="ACTIVE",
        effective_date="2026-01-15",
        allowed_roles=["EMPLOYEE", "MANAGER"],
        document_type="HANDBOOK",
        summary="Standard comprehensive employee handbook.",
        keywords=["handbook", "hr"],
        file_path="source_documents/hr/employee_handbook.docx",
        file_format="DOCX",
    )


def test_validator_success(valid_metadata):
    validator = DocumentValidator(min_word_count=10)
    text = "Word " * 50
    assert validator.validate(valid_metadata, text, "source_documents/hr/employee_handbook.docx") is True


def test_validator_invalid_doc_id(valid_metadata):
    valid_metadata.document_id = "INVALID_ID"
    validator = DocumentValidator(min_word_count=10)
    with pytest.raises(DocumentValidationError) as exc_info:
        validator.validate(valid_metadata, "Word " * 50)
    assert "Document ID 'INVALID_ID' is invalid" in str(exc_info.value)


def test_validator_empty_content(valid_metadata):
    validator = DocumentValidator(min_word_count=10)
    with pytest.raises(DocumentValidationError) as exc_info:
        validator.validate(valid_metadata, "   ")
    assert "content is empty" in str(exc_info.value)


def test_validator_word_count_too_low(valid_metadata):
    validator = DocumentValidator(min_word_count=100)
    with pytest.raises(DocumentValidationError) as exc_info:
        validator.validate(valid_metadata, "Only five little words here.")
    assert "below minimum required" in str(exc_info.value)


def test_validator_format_mismatch(valid_metadata):
    validator = DocumentValidator(min_word_count=10)
    with pytest.raises(DocumentValidationError) as exc_info:
        validator.validate(valid_metadata, "Word " * 50, "source_documents/hr/employee_handbook.pdf")
    assert "File format mismatch" in str(exc_info.value)
