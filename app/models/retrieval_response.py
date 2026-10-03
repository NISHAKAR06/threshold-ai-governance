"""
retrieval_response.py — Domain model representing the structured semantic retrieval response.
"""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from app.models.retrieval_result import RetrievalResultItem


@dataclass
class RetrievalResponse:
    """Structured response container for semantic retrieval results."""
    query: str
    result_count: int
    results: List[RetrievalResultItem] = field(default_factory=list)
    execution_time_ms: float = 0.0
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None

    @property
    def query_time_ms(self) -> float:
        return self.execution_time_ms

    @property
    def model_name(self) -> Optional[str]:
        return self.embedding_model

    @property
    def provider_name(self) -> Optional[str]:
        return self.embedding_provider

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary representation."""
        return {
            "query": self.query,
            "result_count": self.result_count,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "results": [item.to_dict() for item in self.results],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalResponse":
        """Reconstruct response from dictionary."""
        return cls(
            query=data["query"],
            result_count=data.get("result_count", len(data.get("results", []))),
            results=[RetrievalResultItem.from_dict(r) for r in data.get("results", [])],
            execution_time_ms=data.get("execution_time_ms", 0.0),
            embedding_provider=data.get("embedding_provider"),
            embedding_model=data.get("embedding_model"),
        )
