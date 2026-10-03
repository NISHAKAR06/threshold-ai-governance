"""
test_semantic_retrieval.py — Integration test for Phase 11 Semantic Retrieval pipeline.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.services.retrieval_service import RetrievalService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, MockEmbeddingProvider
from app.database.vector_store import ChromaVectorStore, InMemoryVectorStore
from app.repositories.vector_repository import VectorRepository
from app.models.vector_record import VectorRecord


@pytest.fixture
def populated_test_repo(tmp_path: Path):
    """Fixture providing a ChromaVectorStore populated with sample governance records."""
    db_path = tmp_path / "integration_chroma"
    store = ChromaVectorStore(path=db_path, collection_name="test_retrieval_chunks")
    repo = VectorRepository(store=store)

    provider = MockEmbeddingProvider(dimension=384)

    records = [
        VectorRecord(
            vector_id="SEC-001_CHUNK_0001_VEC",
            chunk_id="SEC-001_CHUNK_0001",
            document_id="SEC-001",
            text="Access control protocol for high-risk autonomous AI systems.",
            embedding=provider.embed_texts(["Access control protocol for high-risk autonomous AI systems."])[0],
            embedding_model="mock-embedding-384",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={
                "department": "Security",
                "classification": "RESTRICTED",
                "allowed_roles": ["SECURITY_OFFICER", "ADMIN"],
                "document_type": "POLICY",
                "status": "ACTIVE",
            },
            source={"file_name": "sec_001.pdf", "path": "policies/sec_001.pdf"},
            parent_content_hash="p_hash_sec",
            chunk_content_hash="c_hash_sec",
            indexed_at="2026-09-07T00:00:00Z",
        ),
        VectorRecord(
            vector_id="HR-001_CHUNK_0001_VEC",
            chunk_id="HR-001_CHUNK_0001",
            document_id="HR-001",
            text="Remote work policy guidelines, core hours, and workspace safety.",
            embedding=provider.embed_texts(["Remote work policy guidelines, core hours, and workspace safety."])[0],
            embedding_model="mock-embedding-384",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={
                "department": "Human Resources",
                "classification": "INTERNAL",
                "allowed_roles": ["ALL_EMPLOYEES"],
                "document_type": "HANDBOOK",
                "status": "ACTIVE",
            },
            source={"file_name": "hr_001.pdf", "path": "handbooks/hr_001.pdf"},
            parent_content_hash="p_hash_hr",
            chunk_content_hash="c_hash_hr",
            indexed_at="2026-09-07T00:00:00Z",
        ),
        VectorRecord(
            vector_id="FIN-001_CHUNK_0001_VEC",
            chunk_id="FIN-001_CHUNK_0001",
            document_id="FIN-001",
            text="Financial audit procedures, procurement thresholds, and budget approvals.",
            embedding=provider.embed_texts(["Financial audit procedures, procurement thresholds, and budget approvals."])[0],
            embedding_model="mock-embedding-384",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={
                "department": "Finance",
                "classification": "CONFIDENTIAL",
                "allowed_roles": ["FINANCE_DIRECTOR", "AUDITOR"],
                "document_type": "PROCEDURE",
                "status": "ACTIVE",
            },
            source={"file_name": "fin_001.pdf", "path": "finance/fin_001.pdf"},
            parent_content_hash="p_hash_fin",
            chunk_content_hash="c_hash_fin",
            indexed_at="2026-09-07T00:00:00Z",
        ),
    ]

    repo.upsert_records(records)
    return repo, provider


def test_end_to_end_semantic_retrieval(populated_test_repo):
    """
    Validates complete retrieval pipeline:
    User Query -> Query Validation -> Processing -> Embedding -> Vector Search -> Retrieval Validation -> Response.
    """
    repo, provider = populated_test_repo
    engine = EmbeddingEngine(provider=provider)

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    query = "  What are the security protocols for accessing sensitive AI systems?  "
    response = service.retrieve(query=query, top_k=2)

    # Validate response structure
    assert response.query == "What are the security protocols for accessing sensitive AI systems?"
    assert response.result_count == 2
    assert len(response.results) == 2
    assert response.query_time_ms > 0.0

    # Validate ranking & scores
    top_result = response.results[0]
    assert top_result.rank == 1
    assert 0.0 <= top_result.score <= 1.0

    # Validate governance metadata preservation
    assert "department" in top_result.metadata
    assert "classification" in top_result.metadata
    assert "allowed_roles" in top_result.metadata
    assert "document_type" in top_result.metadata
    assert "status" in top_result.metadata

    # Validate source traceability
    assert top_result.source is not None
    assert "file_name" in top_result.source


def test_empty_vector_store_retrieval(tmp_path: Path):
    """Verify that searching an empty vector repository returns a clean empty response."""
    db_path = tmp_path / "empty_chroma"
    store = ChromaVectorStore(path=db_path, collection_name="empty_chunks")
    repo = VectorRepository(store=store)

    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)

    service = RetrievalService(
        embedding_engine=engine,
        vector_repository=repo,
    )

    response = service.retrieve(query="Any governance topic", top_k=5)

    assert response.result_count == 0
    assert response.results == []
    assert response.query == "Any governance topic"


def test_retrieval_api_endpoint(populated_test_repo):
    """Test API endpoint POST /retrieval/search and POST /api/v1/retrieval/search."""
    repo, provider = populated_test_repo
    engine = EmbeddingEngine(provider=provider)
    service = RetrievalService(embedding_engine=engine, vector_repository=repo)

    from app.api.retrieval_routes import get_retrieval_service
    app.dependency_overrides[get_retrieval_service] = lambda: service

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_access_token('admin-test', extra={'role': 'admin', 'dept': 'Security'})}"}

    try:
        # Test direct /retrieval/search
        payload = {
            "query": "remote work policy guidelines",
            "top_k": 2,
        }
        res = client.post("/retrieval/search", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "remote work policy guidelines"
        assert data["result_count"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["rank"] == 1
        assert "department" in data["results"][0]["metadata"]

        # Test /api/v1/retrieval/search
        res_v1 = client.post("/api/v1/retrieval/search", json=payload, headers=headers)
        assert res_v1.status_code == 200
        data_v1 = res_v1.json()
        assert data_v1["result_count"] == 2

        # Test validation error on empty query
        err_res = client.post("/retrieval/search", json={"query": "   ", "top_k": 5}, headers=headers)
        assert err_res.status_code in (400, 422)

        # Test validation error on invalid top_k
        err_k_res = client.post("/retrieval/search", json={"query": "Valid query", "top_k": -1}, headers=headers)
        assert err_k_res.status_code == 422 or err_k_res.status_code == 400

    finally:
        app.dependency_overrides.clear()
