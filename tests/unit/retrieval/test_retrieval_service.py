"""
test_retrieval_service.py — Unit tests for RetrievalService with mock dependencies.
"""
from unittest.mock import MagicMock, patch
import pytest

from app.services.retrieval_service import RetrievalService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, MockEmbeddingProvider
from app.repositories.vector_repository import VectorRepository
from app.database.vector_store import InMemoryVectorStore
from app.models.vector_record import VectorRecord
from app.core.exceptions import (
    InvalidRetrievalQueryError,
    QueryValidationError,
    QueryEmbeddingError,
    VectorSearchError,
)


def _create_sample_records():
    return [
        VectorRecord(
            vector_id="DOC-1_CHUNK_0001_VEC",
            chunk_id="DOC-1_CHUNK_0001",
            document_id="DOC-1",
            text="Employee handbook code of conduct and remote guidelines.",
            embedding=[0.1] * 384,
            embedding_model="mock-model",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={"department": "HR", "allowed_roles": ["ALL"]},
            source={"file_name": "hr_handbook.txt"},
            parent_content_hash="hash_doc1",
            chunk_content_hash="hash_c1",
            indexed_at="2026-09-07T00:00:00Z",
        ),
        VectorRecord(
            vector_id="DOC-2_CHUNK_0001_VEC",
            chunk_id="DOC-2_CHUNK_0001",
            document_id="DOC-2",
            text="Security access protocol for internal databases.",
            embedding=[0.2] * 384,
            embedding_model="mock-model",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={"department": "Security", "allowed_roles": ["ADMIN"]},
            source={"file_name": "security.txt"},
            parent_content_hash="hash_doc2",
            chunk_content_hash="hash_c2",
            indexed_at="2026-09-07T00:00:00Z",
        ),
    ]


def test_retrieval_service_success():
    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)
    store = InMemoryVectorStore()
    repo = VectorRepository(vector_store=store)

    # Upsert test records
    repo.upsert_records(_create_sample_records())

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    response = service.retrieve(query="What are the security access protocols?", top_k=2)

    assert response.query == "What are the security access protocols?"
    assert response.result_count >= 1
    assert len(response.results) <= 2
    assert response.results[0].rank == 1
    assert 0.0 <= response.results[0].score <= 1.0
    assert response.results[0].chunk_id in ("DOC-1_CHUNK_0001", "DOC-2_CHUNK_0001")
    assert "department" in response.results[0].metadata


def test_retrieval_service_empty_store_returns_empty_results():
    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)
    store = InMemoryVectorStore()
    repo = VectorRepository(vector_store=store)

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    # Search in empty store
    response = service.retrieve(query="Any random query", top_k=5)

    assert response.result_count == 0
    assert response.results == []
    assert response.query == "Any random query"


def test_retrieval_service_validation_failure():
    service = RetrievalService()

    with pytest.raises((InvalidRetrievalQueryError, QueryValidationError)):
        service.retrieve(query="", top_k=5)

    with pytest.raises(QueryValidationError):
        service.retrieve(query="Valid query", top_k=-1)


def test_retrieval_service_embedding_failure_raises_query_embedding_error():
    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)
    store = InMemoryVectorStore()
    repo = VectorRepository(vector_store=store)

    # Simulate provider failure
    engine.generate_embeddings = MagicMock(side_effect=RuntimeError("Provider offline"))

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    with pytest.raises(QueryEmbeddingError):
        service.retrieve(query="Test query", top_k=3)


def test_retrieval_service_vector_search_failure():
    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)
    repo = MagicMock(spec=VectorRepository)
    repo.count.return_value = 10
    repo.get_record.return_value = _create_sample_records()[0]
    repo.search.side_effect = RuntimeError("Database connection dropped")

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    with pytest.raises(VectorSearchError) as exc_info:
        service.retrieve(query="Test query", top_k=3)

    assert exc_info.value.code == "VECTOR_SEARCH_FAILED"


def test_retrieval_service_malformed_result_exclusion():
    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)
    repo = MagicMock(spec=VectorRepository)
    repo.count.return_value = 10
    repo.get_record.return_value = _create_sample_records()[0]

    # Return search results with one malformed entry (empty chunk_id) and one valid entry
    repo.search.return_value = [
        {
            "vector_id": "V1",
            "chunk_id": "",  # Malformed
            "document_id": "DOC-1",
            "text": "Malformed chunk",
            "score": 0.99,
            "metadata": {},
            "source": {},
        },
        {
            "vector_id": "V2",
            "chunk_id": "DOC-2_CHUNK_0001",
            "document_id": "DOC-2",
            "text": "Valid chunk",
            "score": 0.85,
            "metadata": {"department": "Legal"},
            "source": {"file_name": "legal.txt"},
        },
    ]

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    response = service.retrieve(query="Test query", top_k=5)
    # The malformed item must be excluded, leaving 1 valid result
    assert response.result_count == 1
    assert response.results[0].chunk_id == "DOC-2_CHUNK_0001"
    assert response.results[0].rank == 1
