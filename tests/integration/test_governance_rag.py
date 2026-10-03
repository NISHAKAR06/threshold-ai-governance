"""
test_governance_rag.py — End-to-end integration tests for Phase 13 Governance-Aware RAG Answer Generation.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.access_context import AccessContext
from app.models.vector_record import VectorRecord
from app.services.retrieval_service import RetrievalService
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.rag_service import RAGService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, MockEmbeddingProvider
from app.engines.governance_retrieval.keyword_search_engine import KeywordSearchEngine
from app.providers.llm.mock_provider import MockLLMProvider
from app.database.vector_store import ChromaVectorStore
from app.repositories.vector_repository import VectorRepository
from app.api.rag_routes import get_rag_service


@pytest.fixture
def test_rag_environment(tmp_path: Path):
    """
    Sets up an integrated RAG environment with populated vector repository,
    indexed keyword search engine, HybridRetrievalService, and RAGService.
    """
    # 1. Populate Vector Repository
    db_path = tmp_path / "integration_chroma_rag"
    store = ChromaVectorStore(path=db_path, collection_name="test_rag_chunks")
    repo = VectorRepository(store=store)

    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)

    text_sec = "Access control protocols, encryption standards, and threat modeling for high-risk autonomous AI systems."
    text_hr = "Employee remote work policy, core business hours from 10am to 4pm, and home office stipend reimbursement."
    text_ir = "Critical CSIRT incident response containment playbooks, forensic analysis, and breach notification."

    records = [
        VectorRecord(
            vector_id="SEC-001_CHUNK_0001_VEC",
            chunk_id="SEC-001_CHUNK_0001",
            document_id="SEC-001",
            text=text_sec,
            embedding=provider.embed_texts([text_sec])[0],
            embedding_model="mock-embedding-384",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={
                "department": "Information Security",
                "classification": "RESTRICTED",
                "allowed_roles": ["SECURITY_ENGINEER", "ADMIN"],
                "document_type": "POLICY",
                "title": "Information Security Policy",
                "status": "ACTIVE",
            },
            source={"file_path": "policies/sec_001.pdf", "file_format": "PDF"},
            parent_content_hash="p_sec",
            chunk_content_hash="c_sec",
            indexed_at="2026-09-08T00:00:00Z",
        ),
        VectorRecord(
            vector_id="HR-001_CHUNK_0001_VEC",
            chunk_id="HR-001_CHUNK_0001",
            document_id="HR-001",
            text=text_hr,
            embedding=provider.embed_texts([text_hr])[0],
            embedding_model="mock-embedding-384",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={
                "department": "Human Resources",
                "classification": "INTERNAL",
                "allowed_roles": ["EMPLOYEE", "MANAGER", "ADMIN", "ALL_EMPLOYEES"],
                "document_type": "HANDBOOK",
                "title": "Employee Handbook",
                "status": "ACTIVE",
            },
            source={"file_path": "hr/handbook.pdf", "file_format": "PDF"},
            parent_content_hash="p_hr",
            chunk_content_hash="c_hr",
            indexed_at="2026-09-08T00:00:00Z",
        ),
        VectorRecord(
            vector_id="SEC-004_CHUNK_0001_VEC",
            chunk_id="SEC-004_CHUNK_0001",
            document_id="SEC-004",
            text=text_ir,
            embedding=provider.embed_texts([text_ir])[0],
            embedding_model="mock-embedding-384",
            embedding_provider="mock",
            embedding_dimension=384,
            metadata={
                "department": "Information Security",
                "classification": "CONFIDENTIAL",
                "allowed_roles": ["SECURITY_ENGINEER", "MANAGER", "ADMIN"],
                "document_type": "PROCEDURE",
                "title": "Incident Response Procedure",
                "status": "ACTIVE",
            },
            source={"file_path": "policies/sec_004.pdf", "file_format": "PDF"},
            parent_content_hash="p_ir",
            chunk_content_hash="c_ir",
            indexed_at="2026-09-08T00:00:00Z",
        ),
    ]
    repo.upsert_records(records)

    # 2. Populate Keyword Index
    keyword_chunks = [
        {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "text": r.text,
            "metadata": r.metadata,
            "source": r.source,
        }
        for r in records
    ]
    kw_engine = KeywordSearchEngine(auto_index=False)
    kw_engine.index_chunks(keyword_chunks)

    # 3. Assemble Services
    semantic_service = RetrievalService(embedding_engine=engine, vector_repository=repo)
    retrieval_service = HybridRetrievalService(
        semantic_service=semantic_service,
        keyword_engine=kw_engine,
    )

    rag_service = RAGService(
        retrieval_service=retrieval_service,
        llm_provider=MockLLMProvider(),
    )

    return rag_service


def test_governance_rag_authorized_generation(test_rag_environment):
    """
    Verify that an authorized Security Engineer with RESTRICTED clearance receives a grounded
    answer citing authorized restricted sources.
    """
    service = test_rag_environment
    ctx = AccessContext(
        user_id="SEC-001",
        role="SECURITY_ENGINEER",
        department="Information Security",
        clearance_level="RESTRICTED",
    )

    response = service.generate_answer(
        question="What are the access control protocols for AI systems?",
        access_context=ctx,
        top_k=3,
    )

    assert response.status == "SUCCESS"
    assert response.answer is not None
    assert len(response.answer) > 0
    assert len(response.sources) > 0

    # Ensure SEC-001 is included in the sources
    sec_source = next((s for s in response.sources if s.document_id == "SEC-001"), None)
    assert sec_source is not None
    assert sec_source.classification == "RESTRICTED"
    assert sec_source.source_reference == "policies/sec_001.pdf"


def test_governance_rag_unauthorized_chunks_excluded(test_rag_environment):
    """
    Verify that an Employee with INTERNAL clearance asking about AI access controls
    never has RESTRICTED (SEC-001) or CONFIDENTIAL (SEC-004) chunks in context or citations.
    """
    service = test_rag_environment
    ctx = AccessContext(
        user_id="EMP-001",
        role="EMPLOYEE",
        department="Operations",
        clearance_level="INTERNAL",
    )

    response = service.generate_answer(
        question="What are the access control protocols for AI systems?",
        access_context=ctx,
        top_k=3,
    )

    # SEC-001 is RESTRICTED and must NEVER appear in the sources or answer
    for src in response.sources:
        assert src.document_id != "SEC-001"
        assert src.document_id != "SEC-004"
        assert src.classification != "RESTRICTED"

    assert "threat modeling for high-risk autonomous AI systems" not in response.answer


def test_governance_rag_insufficient_context(test_rag_environment):
    """
    Verify that when no authorized chunks exist, the pipeline returns an INSUFFICIENT_CONTEXT status
    with no fabricated answers or citations.
    """
    service = test_rag_environment
    # Contractor with PUBLIC clearance searching for restricted materials
    ctx = AccessContext(
        user_id="CONTRACTOR-001",
        role="CONTRACTOR",
        department="External",
        clearance_level="PUBLIC",
    )

    response = service.generate_answer(
        question="What are the access control protocols for AI systems?",
        access_context=ctx,
    )

    assert response.status == "INSUFFICIENT_CONTEXT"
    assert "insufficient information" in response.answer.lower()
    assert response.sources == []
    assert response.retrieval_metadata["authorized_result_count"] == 0


def test_rag_api_endpoints(test_rag_environment):
    """
    Test FastAPI endpoints POST /rag/ask and POST /api/v1/rag/ask.
    """
    service = test_rag_environment
    app.dependency_overrides[get_rag_service] = lambda: service

    client = TestClient(app)

    try:
        payload = {
            "question": "What are the rules for remote work core hours?",
            "top_k": 3,
            "access_context": {
                "user_id": "EMP-100",
                "role": "EMPLOYEE",
                "department": "Human Resources",
                "clearance_level": "INTERNAL",
            },
        }

        # 1. Direct /rag/ask
        res = client.post("/rag/ask", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["question"] == payload["question"]
        assert data["status"] in ("SUCCESS", "INSUFFICIENT_CONTEXT")
        assert "answer" in data
        assert "sources" in data
        assert "retrieval_metadata" in data

        # 2. Prefixed /api/v1/rag/ask
        res_v1 = client.post("/api/v1/rag/ask", json=payload)
        assert res_v1.status_code == 200, res_v1.text
        data_v1 = res_v1.json()
        assert data_v1["status"] in ("SUCCESS", "INSUFFICIENT_CONTEXT")

        # 3. Validation error: empty question
        bad_res = client.post(
            "/rag/ask",
            json={
                "question": "   ",
                "access_context": {"user_id": "U1", "role": "EMPLOYEE"},
            },
        )
        assert bad_res.status_code in (400, 422)

        # 4. Validation error: invalid top_k
        bad_k_res = client.post(
            "/rag/ask",
            json={
                "question": "Valid question?",
                "top_k": -1,
                "access_context": {"user_id": "U1", "role": "EMPLOYEE"},
            },
        )
        assert bad_k_res.status_code in (400, 422)

        # 5. Validation error: missing access_context
        missing_ctx = client.post(
            "/rag/ask",
            json={"question": "Valid question?"},
        )
        assert missing_ctx.status_code in (400, 422)

    finally:
        app.dependency_overrides.clear()
