"""
retrieval_query.py — Domain model representing an incoming semantic retrieval query.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class RetrievalQuery:
    """Represents a validated query request for semantic search."""
    query: str
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert RetrievalQuery to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalQuery":
        """Reconstruct RetrievalQuery from dictionary."""
        return cls(
            query=data["query"],
            top_k=data.get("top_k", 5),
            filters=data.get("filters"),
        )
