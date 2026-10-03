"""
rag_answer.py — Domain model representing the raw and validated generated answer.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RAGAnswer:
    """Encapsulates the generated answer text, extracted citations, and validation metadata."""
    text: str
    raw_answer: str
    cited_source_ids: List[str] = field(default_factory=list)
    invalid_source_ids: List[str] = field(default_factory=list)
    is_grounded: bool = True
    is_insufficient_context: bool = False
    validation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "raw_answer": self.raw_answer,
            "cited_source_ids": self.cited_source_ids,
            "invalid_source_ids": self.invalid_source_ids,
            "is_grounded": self.is_grounded,
            "is_insufficient_context": self.is_insufficient_context,
            "validation_notes": self.validation_notes,
        }
