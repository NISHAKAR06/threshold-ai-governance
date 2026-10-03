"""
governance_retrieval_result.py — Domain model representing an authorized, fused chunk result.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class GovernanceRetrievalResultItem:
    """Represents a single authorized chunk with fusion scores and governance metadata."""
    rank: int
    fused_score: float
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict[str, Any]
    source: Dict[str, Any]
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result item to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceRetrievalResultItem":
        """Reconstruct result item from dictionary."""
        return cls(
            rank=data["rank"],
            fused_score=data["fused_score"],
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            text=data["text"],
            metadata=data.get("metadata", {}),
            source=data.get("source", {}),
            semantic_score=data.get("semantic_score"),
            keyword_score=data.get("keyword_score"),
        )
