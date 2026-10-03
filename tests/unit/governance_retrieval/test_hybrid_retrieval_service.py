"""
test_hybrid_retrieval_service.py — Unit tests for HybridRetrievalService using mock dependencies.
"""
from unittest.mock import MagicMock
import pytest

from app.models.access_context import AccessContext
from app.models.retrieval_response import RetrievalResponse
from app.models.retrieval_result import RetrievalResultItem
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.core.exceptions import (
    AccessContextValidationError,
    InvalidRetrievalQueryError,
)


@pytest.fixture
def mock_dependencies():
    semantic_service = MagicMock()
    keyword_engine = MagicMock()

    # Sample semantic response
    sample_sem_item = RetrievalResultItem(
        rank=1,
        score=0.92,
        chunk_id="SEC-001_CHUNK_0001",
        document_id="SEC-001",
        text="Information security policy for employees.",
        metadata={
            "department": "Information Security",
            "classification": "INTERNAL",
            "allowed_roles": ["EMPLOYEE", "SECURITY_ENGINEER", "ADMIN"],
            "status": "ACTIVE",
        },
        source={"file_path": "sec_001.pdf", "file_format": "PDF"},
        embedding_model="text-embedding-004",
        embedding_provider="mock",
    )
    semantic_service.retrieve.return_value = RetrievalResponse(
        query="security policy",
        result_count=1,
        results=[sample_sem_item],
        execution_time_ms=10.0,
    )

    # Sample keyword candidate
    sample_kw_item = {
        "chunk_id": "SEC-001_CHUNK_0001",
        "document_id": "SEC-001",
        "text": "Information security policy for employees.",
        "score": 3.45,
        "lexical_score": 3.45,
        "metadata": {
            "department": "Information Security",
            "classification": "INTERNAL",
            "allowed_roles": ["EMPLOYEE", "SECURITY_ENGINEER", "ADMIN"],
            "status": "ACTIVE",
        },
        "source": {"file_path": "sec_001.pdf", "file_format": "PDF"},
    }
    keyword_engine.search.return_value = [sample_kw_item]

    return semantic_service, keyword_engine


def test_hybrid_retrieval_service_success(mock_dependencies):
    sem_svc, kw_engine = mock_dependencies
    service = HybridRetrievalService(semantic_service=sem_svc, keyword_engine=kw_engine)

    ctx = AccessContext(user_id="U1", role="EMPLOYEE", clearance_level="INTERNAL")
    response = service.retrieve(query="security policy", access_context=ctx, top_k=5)

    assert response.query == "security policy"
    assert response.authorized_result_count == 1
    assert response.denied_count == 0
    assert len(response.results) == 1

    item = response.results[0]
    assert item.chunk_id == "SEC-001_CHUNK_0001"
    assert item.rank == 1
    assert item.semantic_score == 0.92
    assert item.keyword_score == 3.45
    assert item.metadata["department"] == "Information Security"
    assert item.source["file_path"] == "sec_001.pdf"


def test_hybrid_retrieval_service_no_semantic_results(mock_dependencies):
    sem_svc, kw_engine = mock_dependencies
    sem_svc.retrieve.return_value = RetrievalResponse(
        query="keyword only test",
        result_count=0,
        results=[],
        execution_time_ms=5.0,
    )
    service = HybridRetrievalService(semantic_service=sem_svc, keyword_engine=kw_engine)

    ctx = AccessContext(user_id="U1", role="EMPLOYEE", clearance_level="INTERNAL")
    response = service.retrieve(query="keyword only test", access_context=ctx)

    assert response.authorized_result_count == 1
    assert response.results[0].semantic_score is None
    assert response.results[0].keyword_score == 3.45


def test_hybrid_retrieval_service_no_keyword_results(mock_dependencies):
    sem_svc, kw_engine = mock_dependencies
    kw_engine.search.return_value = []
    service = HybridRetrievalService(semantic_service=sem_svc, keyword_engine=kw_engine)

    ctx = AccessContext(user_id="U1", role="EMPLOYEE", clearance_level="INTERNAL")
    response = service.retrieve(query="semantic only test", access_context=ctx)

    assert response.authorized_result_count == 1
    assert response.results[0].semantic_score == 0.92
    assert response.results[0].keyword_score is None


def test_hybrid_retrieval_service_partial_search_failure(mock_dependencies):
    sem_svc, kw_engine = mock_dependencies
    # Semantic service raises an exception; keyword engine still succeeds
    sem_svc.retrieve.side_effect = RuntimeError("Vector DB connection error")
    service = HybridRetrievalService(semantic_service=sem_svc, keyword_engine=kw_engine)

    ctx = AccessContext(user_id="U1", role="EMPLOYEE", clearance_level="INTERNAL")
    response = service.retrieve(query="resilience test", access_context=ctx)

    assert response.authorized_result_count == 1
    assert response.results[0].chunk_id == "SEC-001_CHUNK_0001"


def test_hybrid_retrieval_service_all_results_denied(mock_dependencies):
    sem_svc, kw_engine = mock_dependencies
    service = HybridRetrievalService(semantic_service=sem_svc, keyword_engine=kw_engine)

    # User has an unauthorized role ("INTERN" not in allowed_roles)
    ctx = AccessContext(user_id="U-DENIED", role="INTERN", clearance_level="PUBLIC")
    response = service.retrieve(query="security policy", access_context=ctx)

    assert response.authorized_result_count == 0
    assert response.denied_count == 1
    assert response.results == []


def test_hybrid_retrieval_service_access_context_validation_error():
    service = HybridRetrievalService()

    # None context
    with pytest.raises(AccessContextValidationError):
        service.retrieve(query="valid query", access_context=None)

    # Missing role
    with pytest.raises(AccessContextValidationError):
        service.retrieve(query="valid query", access_context={"user_id": "U1", "role": ""})


def test_hybrid_retrieval_service_invalid_query():
    service = HybridRetrievalService()
    ctx = AccessContext(user_id="U1", role="EMPLOYEE")

    # Empty query raises InvalidRetrievalQueryError
    with pytest.raises(InvalidRetrievalQueryError):
        service.retrieve(query="", access_context=ctx)
