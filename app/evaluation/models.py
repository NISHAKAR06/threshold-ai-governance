"""
models.py — Data models for RAG, Retrieval, and Governance Evaluation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set


@dataclass
class EvaluationTestCase:
    """A single evaluation benchmark test case."""
    evaluation_id: str
    question: str
    expected_document_ids: List[str] = field(default_factory=list)
    expected_chunk_ids: List[str] = field(default_factory=list)
    expected_answer: Optional[str] = None
    access_context: Dict[str, Any] = field(default_factory=dict)
    expected_authorization: str = "ALLOW"  # "ALLOW", "DENY", "REQUIRES_REVIEW"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvaluationTestCase:
        return cls(
            evaluation_id=data.get("evaluation_id") or str(uuid.uuid4()),
            question=data.get("question", ""),
            expected_document_ids=list(data.get("expected_document_ids", [])),
            expected_chunk_ids=list(data.get("expected_chunk_ids", [])),
            expected_answer=data.get("expected_answer"),
            access_context=dict(data.get("access_context", {})),
            expected_authorization=data.get("expected_authorization", "ALLOW"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "question": self.question,
            "expected_document_ids": self.expected_document_ids,
            "expected_chunk_ids": self.expected_chunk_ids,
            "expected_answer": self.expected_answer,
            "access_context": self.access_context,
            "expected_authorization": self.expected_authorization,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalEvaluationResult:
    """Evaluation result for retrieval metrics on a single query."""
    precision_at_k: float
    recall_at_k: float
    mrr: float
    authorized_retrieval_accuracy: float
    unauthorized_retrieval_rate: float
    k: int
    retrieved_chunk_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "mrr": round(self.mrr, 4),
            "authorized_retrieval_accuracy": round(self.authorized_retrieval_accuracy, 4),
            "unauthorized_retrieval_rate": round(self.unauthorized_retrieval_rate, 4),
            "k": self.k,
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
        }


@dataclass
class RAGEvaluationResult:
    """Evaluation result for grounded RAG answer generation."""
    answer_generated: bool
    source_citations_present: bool
    citations_valid: bool
    grounding_score: float
    similarity_score: Optional[float] = None
    generated_answer: str = ""
    citations_found: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_generated": self.answer_generated,
            "source_citations_present": self.source_citations_present,
            "citations_valid": self.citations_valid,
            "grounding_score": round(self.grounding_score, 4),
            "similarity_score": round(self.similarity_score, 4) if self.similarity_score is not None else None,
            "citations_found": self.citations_found,
        }


@dataclass
class GovernanceEvaluationResult:
    """Evaluation result for enterprise governance enforcement."""
    authorization_decision: str  # "ALLOW", "DENY", "REQUIRES_REVIEW"
    expected_decision: str
    decision_matches: bool
    unauthorized_exposure: bool  # True if any protected chunk leaked
    denied_chunks_count: int
    leaked_chunks_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authorization_decision": self.authorization_decision,
            "expected_decision": self.expected_decision,
            "decision_matches": self.decision_matches,
            "unauthorized_exposure": self.unauthorized_exposure,
            "denied_chunks_count": self.denied_chunks_count,
            "leaked_chunks_count": self.leaked_chunks_count,
        }


@dataclass
class CaseEvaluationResult:
    """Aggregated evaluation results for a single test case."""
    test_case: EvaluationTestCase
    retrieval_result: Optional[RetrievalEvaluationResult] = None
    rag_result: Optional[RAGEvaluationResult] = None
    governance_result: Optional[GovernanceEvaluationResult] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.test_case.evaluation_id,
            "question": self.test_case.question,
            "retrieval": self.retrieval_result.to_dict() if self.retrieval_result else None,
            "rag": self.rag_result.to_dict() if self.rag_result else None,
            "governance": self.governance_result.to_dict() if self.governance_result else None,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


@dataclass
class EvaluationReport:
    """Complete summary report of an evaluation run across all test cases."""
    evaluation_run_id: str
    timestamp: str
    total_cases: int
    retrieval_metrics: Dict[str, float] = field(default_factory=dict)
    rag_metrics: Dict[str, float] = field(default_factory=dict)
    governance_metrics: Dict[str, float] = field(default_factory=dict)
    case_results: List[CaseEvaluationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_run_id": self.evaluation_run_id,
            "timestamp": self.timestamp,
            "total_cases": self.total_cases,
            "retrieval_metrics": self.retrieval_metrics,
            "rag_metrics": self.rag_metrics,
            "governance_metrics": self.governance_metrics,
            "case_results": [c.to_dict() for c in self.case_results],
        }
