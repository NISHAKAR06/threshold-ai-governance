"""
vector_record_builder.py — Constructs VectorRecord domain models binding chunk data with vector embeddings.
"""
from datetime import datetime, timezone
from typing import Union, Dict, Any, List, Optional

from app.models.chunk import Chunk
from app.models.embedding_record import VectorRecord


class VectorRecordBuilder:
    """Builds VectorRecord objects with complete governance metadata preservation."""

    @staticmethod
    def build_record(
        chunk: Union[Chunk, Dict[str, Any]],
        embedding: List[float],
        embedding_provider: str,
        embedding_model: str,
        embedding_dimension: Optional[int] = None,
    ) -> VectorRecord:
        """
        Assemble a complete VectorRecord binding chunk content, governance metadata, and embedding vector.

        Args:
            chunk: Chunk domain model or dictionary representation.
            embedding: List of float values representing the dense embedding vector.
            embedding_provider: Name of the generating embedding provider.
            embedding_model: Model name/identifier.
            embedding_dimension: Optional dimension (defaults to len(embedding)).

        Returns:
            VectorRecord instance.
        """
        if isinstance(chunk, Chunk):
            data = chunk.to_dict()
        else:
            data = dict(chunk)

        chunk_id = data.get("chunk_id", "UNKNOWN_CHUNK")
        vector_id = f"{chunk_id}_VEC"
        document_id = data.get("document_id", "UNKNOWN_DOC")
        text = data.get("text", "")

        # Extract and preserve governance metadata
        raw_meta = data.get("metadata", {})
        governance_metadata: Dict[str, Any] = {
            "department": raw_meta.get("department", ""),
            "classification": raw_meta.get("classification", ""),
            "allowed_roles": list(raw_meta.get("allowed_roles", [])),
            "document_type": raw_meta.get("document_type", ""),
            "status": raw_meta.get("status", ""),
            "title": raw_meta.get("title", ""),
            "version": raw_meta.get("version", "1.0"),
            "summary": raw_meta.get("summary", ""),
            "keywords": list(raw_meta.get("keywords", [])),
        }

        # Source provenance
        raw_source = data.get("source", {})
        source_info: Dict[str, Any] = {
            "file_path": raw_source.get("file_path", ""),
            "file_format": raw_source.get("file_format", ""),
        }

        dim = embedding_dimension or len(embedding)
        indexed_at = datetime.now(timezone.utc).isoformat()

        return VectorRecord(
            vector_id=vector_id,
            embedding=embedding,
            chunk_id=chunk_id,
            document_id=document_id,
            text=text,
            metadata=governance_metadata,
            source=source_info,
            parent_content_hash=data.get("parent_content_hash", ""),
            chunk_content_hash=data.get("chunk_content_hash", ""),
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            embedding_dimension=dim,
            indexed_at=indexed_at,
        )
