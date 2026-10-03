"""
rag_source.py — Domain model representing an authorized context source cited in a RAG answer.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class RAGSource:
    """Represents an authorized document chunk included in the LLM generation context."""
    source_id: str                   # Deterministic identifier e.g. "SOURCE_1"
    document_id: str                 # Parent document ID e.g. "SEC-001"
    chunk_id: str                    # Chunk identifier e.g. "SEC-001_CHUNK_0001"
    document_type: str = "DOCUMENT"  # Document type e.g. "POLICY", "GUIDELINE"
    source_reference: str = ""       # Source provenance e.g. file path or document title
    classification: Optional[str] = None
    department: Optional[str] = None
    fused_score: Optional[float] = None
    is_cited: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGSource":
        """Reconstruct from dictionary."""
        return cls(
            source_id=data["source_id"],
            document_id=data["document_id"],
            chunk_id=data["chunk_id"],
            document_type=data.get("document_type", "DOCUMENT"),
            source_reference=data.get("source_reference", ""),
            classification=data.get("classification"),
            department=data.get("department"),
            fused_score=data.get("fused_score"),
            is_cited=data.get("is_cited", False),
        )
