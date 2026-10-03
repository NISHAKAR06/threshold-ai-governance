"""
test_rag_service.py — Unit tests for RAGService with mock dependencies.
"""
from unittest.mock import MagicMock
import pytest

from app.models.access_context import AccessContext
from app.models.governance_retrieval_result import GovernanceRetrievalResultItem
from app.models.hybrid_retrieval_response import HybridRetrievalResponse
from app.services.rag_service import RAGService
from app.providers.llm.mock_provider import MockLLMProvider
from app.core.exceptions import (
    AccessContextValidationError,
    InvalidRetrievalQueryError,
    RAGError,
    LLMGenerationError,
)


@pytest.fixture
def mock_dependencies():
    retrieval_service = MagicMock()

    sample_items = [
        GovernanceRetrievalResultItem(
            rank=1,
            fused_score=0.035,
            chunk_id="SEC-001_CHUNK_0001",
            document_id="SEC-001",
            text="Access control protocol for high-risk autonomous AI systems.",
            metadata={
                "department": "Information Security",
                "classification": "RESTRICTED",
                "allowed_roles": ["SECURITY_ENGINEER", "ADMIN"],
                "document_type": "POLICY",
                "title": "Information Security Policy",
            },
            source={"file_path": "policies/sec_001.pdf"},
            semantic_score=0.92,
            keyword_score=5.0,
        )
    ]

    retrieval_service.retrieve.return_value = HybridRetrievalResponse(
        query="security protocol",
        requested_top_k=5,
        authorized_result_count=1,
        denied_count=2,
        execution_time_ms=12.0,
        results=sample_items,
        fusion_strategy="RRF",
    )

    llm_provider = MockLLMProvider()
    return retrieval_service, llm_provider


def test_rag_service_successful_grounded_response(mock_dependencies):
    retrieval_svc, llm_prov = mock_dependencies
    service = RAGService(retrieval_service=retrieval_svc, llm_provider=llm_prov)

    ctx = AccessContext(user_id="U1", role="SECURITY_ENGINEER", clearance_level="RESTRICTED")
    response = service.generate_answer(
        question="What are the security protocols for AI systems?",
        access_context=ctx,
    )

    assert response.status == "SUCCESS"
    assert "SOURCE_1" in response.answer
    assert len(response.sources) == 1
    assert response.sources[0].source_id == "SOURCE_1"
    assert response.sources[0].is_cited is True
    assert response.retrieval_metadata["authorized_result_count"] == 1
    assert response.retrieval_metadata["context_chunks_used"] == 1
    assert response.retrieval_metadata["denied_count"] == 2


def test_rag_service_insufficient_context_no_results(mock_dependencies):
    retrieval_svc, llm_prov = mock_dependencies
    # Simulate zero authorized results returned by Phase 12
    retrieval_svc.retrieve.return_value = HybridRetrievalResponse(
        query="unknown policy",
        requested_top_k=5,
        authorized_result_count=0,
        denied_count=3,
        execution_time_ms=8.0,
        results=[],
    )

    # Spy on LLM provider generate method
    llm_prov.generate = MagicMock()

    service = RAGService(retrieval_service=retrieval_svc, llm_provider=llm_prov)
    ctx = AccessContext(user_id="U2", role="EMPLOYEE", clearance_level="INTERNAL")

    response = service.generate_answer(
        question="What is the quantum encryption protocol?",
        access_context=ctx,
    )

    assert response.status == "INSUFFICIENT_CONTEXT"
    assert "insufficient information" in response.answer.lower()
    assert response.sources == []
    assert response.retrieval_metadata["authorized_result_count"] == 0
    assert response.retrieval_metadata["context_chunks_used"] == 0

    # Critical security rule: LLM provider must NOT be called when context is empty!
    llm_prov.generate.assert_not_called()


def test_rag_service_retrieval_failure(mock_dependencies):
    retrieval_svc, llm_prov = mock_dependencies
    retrieval_svc.retrieve.side_effect = RuntimeError("Retrieval DB connection timed out")

    service = RAGService(retrieval_service=retrieval_svc, llm_provider=llm_prov)
    ctx = AccessContext(user_id="U1", role="ADMIN")

    with pytest.raises(RAGError):
        service.generate_answer(question="Any valid question", access_context=ctx)


def test_rag_service_llm_failure(mock_dependencies):
    retrieval_svc, _ = mock_dependencies
    failing_llm = MockLLMProvider(should_raise=RuntimeError("API quota exceeded"))

    service = RAGService(retrieval_service=retrieval_svc, llm_provider=failing_llm)
    ctx = AccessContext(user_id="U1", role="ADMIN")

    with pytest.raises(LLMGenerationError):
        service.generate_answer(question="Valid question", access_context=ctx)


def test_rag_service_invalid_citations_sanitized(mock_dependencies):
    retrieval_svc, _ = mock_dependencies
    # LLM hallucinates [SOURCE_99] which is not in context
    hallucinating_llm = MockLLMProvider(
        canned_response="Policy details [SOURCE_1] and invented rule [SOURCE_99]."
    )

    service = RAGService(retrieval_service=retrieval_svc, llm_provider=hallucinating_llm)
    ctx = AccessContext(user_id="U1", role="ADMIN")

    response = service.generate_answer(question="Valid question", access_context=ctx)
    assert response.status == "SUCCESS"
    assert "[SOURCE_1]" in response.answer
    assert "[SOURCE_99]" not in response.answer  # Sanitized


def test_rag_service_input_validations():
    service = RAGService()
    ctx = AccessContext(user_id="U1", role="EMPLOYEE")

    # Empty question
    with pytest.raises(InvalidRetrievalQueryError):
        service.generate_answer(question="", access_context=ctx)

    # Whitespace question
    with pytest.raises(InvalidRetrievalQueryError):
        service.generate_answer(question="    \n   ", access_context=ctx)

    # Missing access context
    with pytest.raises(AccessContextValidationError):
        service.generate_answer(question="Valid question", access_context=None)
