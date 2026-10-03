"""
embedding_record.py — Domain dataclass representing an indexed vector record.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class VectorRecord:
    """Represents a validated vector embedding record bound to chunk provenance and governance metadata."""
    vector_id: str
    embedding: List[float]
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict[str, Any]
    source: Dict[str, Any]
    parent_content_hash: str
    chunk_content_hash: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    indexed_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert VectorRecord to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorRecord":
        """Reconstruct VectorRecord dataclass from a dictionary."""
        return cls(
            vector_id=data["vector_id"],
            embedding=list(data["embedding"]),
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            text=data["text"],
            metadata=data.get("metadata", {}),
            source=data.get("source", {}),
            parent_content_hash=data.get("parent_content_hash", ""),
            chunk_content_hash=data.get("chunk_content_hash", ""),
            embedding_provider=data.get("embedding_provider", ""),
            embedding_model=data.get("embedding_model", ""),
            embedding_dimension=int(data.get("embedding_dimension", len(data.get("embedding", [])))),
            indexed_at=data.get("indexed_at", ""),
        )
