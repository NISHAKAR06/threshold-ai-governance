"""
rag_request.py — Domain model representing a user RAG query with security context.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from app.models.access_context import AccessContext


@dataclass
class RAGRequest:
    """Encapsulates a user question and requester access credentials."""
    question: str
    access_context: AccessContext
    top_k: Optional[int] = 5
    max_context_chunks: Optional[int] = None
    generation_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.question:
            self.question = self.question.strip()
