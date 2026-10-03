"""
hybrid_retrieval_response.py — Domain model representing the structured hybrid governance retrieval response.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from app.models.governance_retrieval_result import GovernanceRetrievalResultItem


@dataclass
class HybridRetrievalResponse:
    """Structured response containing authorized hybrid search results and aggregate audit metrics."""
    query: str
    requested_top_k: int
    authorized_result_count: int
    denied_count: int = 0
    execution_time_ms: float = 0.0
    results: List[GovernanceRetrievalResultItem] = field(default_factory=list)
    fusion_strategy: str = "RRF"
    semantic_candidate_count: int = 0
    keyword_candidate_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary representation."""
        return {
            "query": self.query,
            "requested_top_k": self.requested_top_k,
            "authorized_result_count": self.authorized_result_count,
            "denied_count": self.denied_count,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "fusion_strategy": self.fusion_strategy,
            "semantic_candidate_count": self.semantic_candidate_count,
            "keyword_candidate_count": self.keyword_candidate_count,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridRetrievalResponse":
        """Reconstruct response from dictionary."""
        return cls(
            query=data["query"],
            requested_top_k=data.get("requested_top_k", 5),
            authorized_result_count=data.get("authorized_result_count", len(data.get("results", []))),
            denied_count=data.get("denied_count", 0),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            results=[GovernanceRetrievalResultItem.from_dict(r) for r in data.get("results", [])],
            fusion_strategy=data.get("fusion_strategy", "RRF"),
            semantic_candidate_count=data.get("semantic_candidate_count", 0),
            keyword_candidate_count=data.get("keyword_candidate_count", 0),
        )
