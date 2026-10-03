"""
retrieval_result.py — Domain model representing an individual retrieved chunk item.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class RetrievalResultItem:
    """Represents a ranked, similarity-scored chunk retrieved from vector search."""
    rank: int
    score: float
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict[str, Any]
    source: Dict[str, Any]
    distance: Optional[float] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result item to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalResultItem":
        """Reconstruct result item from dictionary."""
        return cls(
            rank=data["rank"],
            score=data["score"],
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            text=data["text"],
            metadata=data.get("metadata", {}),
            source=data.get("source", {}),
            distance=data.get("distance"),
            embedding_provider=data.get("embedding_provider"),
            embedding_model=data.get("embedding_model"),
        )
