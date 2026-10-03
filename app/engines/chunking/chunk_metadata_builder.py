"""
chunk_metadata_builder.py — Constructs Chunk domain objects with complete governance metadata.
Combines parent normalized document context, raw chunk text, and chunk sequence index.
"""
from datetime import datetime, timezone
from typing import Union, Dict, Any

from app.models.chunk import Chunk
from app.models.normalized_document import NormalizedDocument
from app.utils.hash_utils import compute_sha256


class ChunkMetadataBuilder:
    """Builds complete, deterministic Chunk domain models with governance inheritance."""

    @staticmethod
    def build_chunk(
        parent_doc: Union[NormalizedDocument, Dict[str, Any]],
        chunk_text: str,
        chunk_index: int,
    ) -> Chunk:
        """
        Build an individual Chunk from parent document data, raw text, and 1-based index.

        Args:
            parent_doc: Normalized document dataclass or dictionary.
            chunk_text: Text content of this chunk.
            chunk_index: 1-indexed integer indicating sequence position.

        Returns:
            Chunk domain object.
        """
        # Normalize access between dataclass and dict
        if isinstance(parent_doc, NormalizedDocument):
            doc_dict = parent_doc.to_dict()
        elif hasattr(parent_doc, "model_dump"):
            doc_dict = parent_doc.model_dump()
        else:
            doc_dict = dict(parent_doc)

        document_id = doc_dict.get("document_id", "UNKNOWN")
        chunk_id = f"{document_id}_CHUNK_{chunk_index:04d}"

        # Clean text
        cleaned_text = chunk_text.strip()

        # Compute deterministic SHA-256 content hash of chunk text
        chunk_content_hash = compute_sha256(cleaned_text)

        # Extract governance metadata
        governance_metadata: Dict[str, Any] = {
            "department": doc_dict.get("department", ""),
            "classification": doc_dict.get("classification", ""),
            "allowed_roles": list(doc_dict.get("allowed_roles", [])),
            "document_type": doc_dict.get("document_type", ""),
            "status": doc_dict.get("status", ""),
            "title": doc_dict.get("title", ""),
            "version": doc_dict.get("version", "1.0"),
            "effective_date": doc_dict.get("effective_date", ""),
            "summary": doc_dict.get("summary", ""),
            "keywords": list(doc_dict.get("keywords", [])),
        }

        # Extract source provenance
        source_info: Dict[str, Any] = {
            "file_path": doc_dict.get("file_path", ""),
            "file_format": doc_dict.get("file_format", ""),
        }

        # Parent content hash
        parent_content_hash = doc_dict.get("content_hash", "")

        # Creation timestamp
        created_at = datetime.now(timezone.utc).isoformat()

        return Chunk(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            text=cleaned_text,
            metadata=governance_metadata,
            source=source_info,
            parent_content_hash=parent_content_hash,
            chunk_content_hash=chunk_content_hash,
            created_at=created_at,
        )
