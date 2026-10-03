"""
chunk_validator.py — Validates generated Chunk objects against enterprise governance rules.
"""
import re
from dataclasses import dataclass, field
from typing import List, Union, Dict, Any

from app.models.chunk import Chunk
from app.core.exceptions import ChunkValidationError


@dataclass
class ChunkValidationResult:
    """Structured result of chunk validation."""
    is_valid: bool
    chunk_id: str
    errors: List[str] = field(default_factory=list)


class ChunkValidator:
    """Validates Chunk domain models against schema, governance, and integrity constraints."""

    HEX_64_PATTERN = re.compile(r"^[a-f0-9]{64}$", re.IGNORECASE)
    CHUNK_ID_PATTERN = re.compile(r"^[A-Z0-9_-]+_CHUNK_\d{4}$")

    REQUIRED_GOVERNANCE_FIELDS = [
        "department",
        "classification",
        "allowed_roles",
        "document_type",
        "status",
    ]

    def validate(self, chunk: Union[Chunk, Dict[str, Any]], raise_exception: bool = False) -> ChunkValidationResult:
        """
        Validate a chunk object.

        Args:
            chunk: Chunk instance or dictionary.
            raise_exception: If True, raises ChunkValidationError on first error.

        Returns:
            ChunkValidationResult with status and error list.
        """
        if isinstance(chunk, Chunk):
            data = chunk.to_dict()
        else:
            data = dict(chunk)

        errors: List[str] = []
        chunk_id = data.get("chunk_id", "")
        doc_id = data.get("document_id", "")

        # 1. Chunk ID validation
        if not chunk_id:
            errors.append("chunk_id is missing or empty")
        elif not self.CHUNK_ID_PATTERN.match(chunk_id):
            errors.append(f"chunk_id '{chunk_id}' does not match expected pattern {{doc_id}}_CHUNK_{{idx:04d}}")

        # 2. Document ID validation
        if not doc_id:
            errors.append("document_id is missing or empty")

        # 3. Chunk Index validation
        chunk_index = data.get("chunk_index")
        if chunk_index is None or not isinstance(chunk_index, int) or chunk_index < 1:
            errors.append(f"chunk_index must be an integer >= 1, got {chunk_index}")

        # 4. Text content validation
        text = data.get("text", "")
        if not text or not str(text).strip():
            errors.append("chunk text is empty or contains only whitespace")

        # 5. Metadata validation
        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            errors.append("metadata must be a dictionary")
        else:
            for req_field in self.REQUIRED_GOVERNANCE_FIELDS:
                val = metadata.get(req_field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append(f"metadata.{req_field} is missing or empty")

            allowed_roles = metadata.get("allowed_roles")
            if not isinstance(allowed_roles, list):
                errors.append("metadata.allowed_roles must be a list")
            elif len(allowed_roles) == 0:
                errors.append("metadata.allowed_roles cannot be empty")
            elif not all(isinstance(r, str) and r.strip() for r in allowed_roles):
                errors.append("all entries in metadata.allowed_roles must be non-empty strings")

        # 6. Source provenance validation
        source = data.get("source")
        if not isinstance(source, dict):
            errors.append("source must be a dictionary")
        else:
            if not source.get("file_path"):
                errors.append("source.file_path is missing or empty")
            if not source.get("file_format"):
                errors.append("source.file_format is missing or empty")

        # 7. Parent content hash validation
        parent_hash = data.get("parent_content_hash", "")
        if not parent_hash:
            errors.append("parent_content_hash is missing")
        elif not self.HEX_64_PATTERN.match(parent_hash):
            errors.append("parent_content_hash is not a valid 64-character SHA-256 hex string")

        # 8. Chunk content hash validation
        chunk_hash = data.get("chunk_content_hash", "")
        if not chunk_hash:
            errors.append("chunk_content_hash is missing")
        elif not self.HEX_64_PATTERN.match(chunk_hash):
            errors.append("chunk_content_hash is not a valid 64-character SHA-256 hex string")

        is_valid = len(errors) == 0

        if not is_valid and raise_exception:
            raise ChunkValidationError(
                f"Chunk validation failed for {chunk_id or 'UNKNOWN'}: {'; '.join(errors)}",
                chunk_id=chunk_id,
            )

        return ChunkValidationResult(
            is_valid=is_valid,
            chunk_id=chunk_id,
            errors=errors,
        )
