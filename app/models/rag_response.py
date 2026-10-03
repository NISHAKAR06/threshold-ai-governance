"""
rag_response.py — Domain model representing the structured, source-attributed RAG response.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.models.rag_source import RAGSource


@dataclass
class RAGResponse:
    """Complete, governance-aware RAG generation response."""
    question: str
    answer: str
    status: str                                    # SUCCESS, INSUFFICIENT_CONTEXT, ERROR
    sources: List[RAGSource] = field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    model_used: Optional[str] = None
    provider_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary representation."""
        return {
            "question": self.question,
            "answer": self.answer,
            "status": self.status,
            "sources": [s.to_dict() for s in self.sources],
            "retrieval_metadata": self.retrieval_metadata,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "model_used": self.model_used,
            "provider_used": self.provider_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGResponse":
        """Reconstruct from dictionary."""
        return cls(
            question=data["question"],
            answer=data["answer"],
            status=data.get("status", "SUCCESS"),
            sources=[RAGSource.from_dict(s) for s in data.get("sources", [])],
            retrieval_metadata=data.get("retrieval_metadata", {}),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            model_used=data.get("model_used"),
            provider_used=data.get("provider_used"),
        )
