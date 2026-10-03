"""
chunk.py — Domain dataclass for document text chunks and associated metadata.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class Chunk:
    """Represents a validated text chunk with complete governance metadata and provenance."""
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    metadata: Dict[str, Any]
    source: Dict[str, Any]
    parent_content_hash: str
    chunk_content_hash: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk dataclass to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Reconstruct Chunk dataclass from a dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            chunk_index=data["chunk_index"],
            text=data["text"],
            metadata=data.get("metadata", {}),
            source=data.get("source", {}),
            parent_content_hash=data.get("parent_content_hash", ""),
            chunk_content_hash=data.get("chunk_content_hash", ""),
            created_at=data.get("created_at", ""),
        )
