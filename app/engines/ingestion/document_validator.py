"""
document_validator.py — Validates normalized document content and metadata consistency.
"""
import re
from pathlib import Path
from typing import Union, Optional
from app.schemas.registry_schema import (
    VALID_CLASSIFICATIONS,
    VALID_STATUSES,
    VALID_ROLES,
    VALID_FORMATS,
)
from app.schemas.document_schema import DocumentMetadataSchema
from app.utils.file_utils import get_file_extension
from app.core.exceptions import DocumentValidationError

DOC_ID_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3}$")


class DocumentValidator:
    """Validates document metadata and extracted text content for enterprise compliance."""

    def __init__(self, min_word_count: int = 200):
        self.min_word_count = min_word_count

    def validate(
        self,
        metadata: DocumentMetadataSchema,
        normalized_text: str,
        resolved_file_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        Validate document metadata and normalized text content:
        - document_id follows pattern (e.g. HR-001, SEC-001)
        - title is non-empty
        - content is non-empty and meets minimum word count
        - classification is valid
        - status is valid
        - allowed_roles contains valid enterprise roles
        - file_format matches resolved file extension
        """
        doc_id = metadata.document_id

        # 1. Document ID format
        if not DOC_ID_PATTERN.match(doc_id):
            raise DocumentValidationError(
                f"Document ID '{doc_id}' is invalid. Expected format like 'HR-001', 'SEC-001', 'AIG-001', etc.",
                document_id=doc_id,
            )

        # 2. Title non-empty
        if not metadata.title or len(metadata.title.strip()) < 2:
            raise DocumentValidationError(
                f"Document title '{metadata.title}' is missing or too short.",
                document_id=doc_id,
            )

        # 3. Content non-empty
        if not normalized_text or not normalized_text.strip():
            raise DocumentValidationError(
                "Document content is empty after normalization.",
                document_id=doc_id,
            )

        # 4. Word count check
        word_count = len(normalized_text.split())
        if word_count < self.min_word_count:
            raise DocumentValidationError(
                f"Document content word count ({word_count}) is below minimum required ({self.min_word_count}).",
                document_id=doc_id,
            )

        # 5. Classification
        if metadata.classification.upper() not in VALID_CLASSIFICATIONS:
            raise DocumentValidationError(
                f"Invalid classification '{metadata.classification}'.",
                document_id=doc_id,
            )

        # 6. Status
        if metadata.status.upper() not in VALID_STATUSES:
            raise DocumentValidationError(
                f"Invalid document status '{metadata.status}'.",
                document_id=doc_id,
            )

        # 7. Allowed roles
        if not metadata.allowed_roles:
            raise DocumentValidationError(
                "Document has no allowed roles configured.",
                document_id=doc_id,
            )
        for role in metadata.allowed_roles:
            if role not in VALID_ROLES:
                raise DocumentValidationError(
                    f"Invalid allowed role '{role}'.",
                    document_id=doc_id,
                )

        # 8. File format consistency with actual extension
        if metadata.file_format.upper() not in VALID_FORMATS:
            raise DocumentValidationError(
                f"Invalid file format '{metadata.file_format}'.",
                document_id=doc_id,
            )

        if resolved_file_path:
            actual_ext = get_file_extension(resolved_file_path).upper()
            if actual_ext != metadata.file_format.upper():
                raise DocumentValidationError(
                    f"File format mismatch: metadata declares '{metadata.file_format}' but file has extension '.{actual_ext.lower()}'.",
                    document_id=doc_id,
                )

        return True
