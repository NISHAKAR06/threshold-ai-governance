"""
test_governance_retrieval.py — End-to-end integration tests for Phase 12 Hybrid Search & Governance-Aware Retrieval.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.models.access_context import AccessContext
from app.models.vector_record import VectorRecord
from app.services.retrieval_service import RetrievalService
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, MockEmbeddingProvider
from app.engines.governance_retrieval.keyword_search_engine import KeywordSearchEngine
from app.engines.governance_retrieval.hybrid_fusion_engine import HybridFusionEngine
from app.engines.governance_retrieval.governance_filter_engine import GovernanceFilterEngine
from app.engines.governance_retrieval.ranking_engine import RankingEngine
from app.database.vector_store import ChromaVectorStore
from app.repositories.vector_repository import VectorRepository
from app.api.retrieval_routes import get_hybrid_retrieval_service


@pytest.fixture
def test_hybrid_environment(tmp_path: Path):
    """
    Sets up an integrated environment with:
    1. A populated vector store for semantic search.
    2. An indexed BM25 keyword search engine for lexical search.
    """
    # 1. Populate Vector Store
    db_path = tmp_path / "integration_chroma_hybrid"
    store = ChromaVectorStore(path=db_path, collection_name="test_hybrid_chunks")
    repo = VectorRepository(store=store)

    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider)

    # Document 1: Restricted AI Security Protocol (Overlaps semantic & keyword)
    text_sec = "Access control protocols, encryption standards, and threat modeling for high-risk autonomous AI systems."
    # Document 2: Internal HR Policy (Keyword & semantic)
    text_hr = "Employee remote work policy, core business hours, and home office stipend reimbursement."
    # Document 3: Confidential Incident Response (Semantic focus)
    text_ir = "Critical CSIRT incident response containment playbooks, forensic analysis, and breach notification."
    # Document 4: Engineering Deployment (Keyword focus)
    text_eng = "Kubernetes cluster maintenance, CI/CD automated deployment pipelines, and Docker containers."

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
                "status": "ACTIVE",
            },
            source={"file_path": "sec_001.pdf", "file_format": "PDF"},
            parent_content_hash="p_sec",
            chunk_content_hash="c_sec",
            indexed_at="2026-09-07T00:00:00Z",
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
                "status": "ACTIVE",
            },
            source={"file_path": "hr_001.pdf", "file_format": "PDF"},
            parent_content_hash="p_hr",
            chunk_content_hash="c_hr",
            indexed_at="2026-09-07T00:00:00Z",
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
                "status": "ACTIVE",
            },
            source={"file_path": "sec_004.pdf", "file_format": "PDF"},
            parent_content_hash="p_ir",
            chunk_content_hash="c_ir",
            indexed_at="2026-09-07T00:00:00Z",
        ),
    ]
    repo.upsert_records(records)

    # 2. Populate Keyword Index with all 4 documents
    keyword_chunks = [
        {
            "chunk_id": "SEC-001_CHUNK_0001",
            "document_id": "SEC-001",
            "text": text_sec,
            "metadata": records[0].metadata,
            "source": records[0].source,
        },
        {
            "chunk_id": "HR-001_CHUNK_0001",
            "document_id": "HR-001",
            "text": text_hr,
            "metadata": records[1].metadata,
            "source": records[1].source,
        },
        {
            "chunk_id": "ENG-001_CHUNK_0001",
            "document_id": "ENG-001",
            "text": text_eng,
            "metadata": {
                "department": "Engineering",
                "classification": "INTERNAL",
                "allowed_roles": ["ENGINEER", "ADMIN"],
                "document_type": "GUIDELINE",
                "status": "ACTIVE",
            },
            "source": {"file_path": "eng_001.pdf", "file_format": "PDF"},
        },
    ]

    kw_engine = KeywordSearchEngine(auto_index=False)
    kw_engine.index_chunks(keyword_chunks)

    # 3. Assemble HybridRetrievalService
    semantic_service = RetrievalService(embedding_engine=engine, vector_repository=repo)
    service = HybridRetrievalService(
        semantic_service=semantic_service,
        keyword_engine=kw_engine,
        candidate_multiplier=2,
    )

    return service


def test_hybrid_governance_retrieval_authorized_flow(test_hybrid_environment):
    """
    Verify that an authorized Security Engineer with RESTRICTED clearance retrieves
    fused results from both semantic and keyword branches, including restricted chunks.
    """
    service = test_hybrid_environment
    ctx = AccessContext(
        user_id="SEC-USER-01",
        role="SECURITY_ENGINEER",
        department="Information Security",
        clearance_level="RESTRICTED",
    )

    response = service.retrieve(
        query="Access control protocols and threat modeling for AI systems",
        access_context=ctx,
        top_k=3,
    )

    assert response.authorized_result_count > 0
    assert len(response.results) <= 3
    assert response.query == "Access control protocols and threat modeling for AI systems"

    retrieved_chunk_ids = [r.chunk_id for r in response.results]
    assert "SEC-001_CHUNK_0001" in retrieved_chunk_ids

    # Check top result details
    top_item = response.results[0]
    assert top_item.rank == 1
    assert top_item.fused_score > 0.0
    assert top_item.metadata["classification"] in ("RESTRICTED", "CONFIDENTIAL", "INTERNAL")
    assert top_item.source["file_path"] is not None


def test_hybrid_governance_retrieval_unauthorized_chunks_filtered(test_hybrid_environment):
    """
    Verify that an Employee with INTERNAL clearance NEVER receives RESTRICTED or CONFIDENTIAL chunks,
    even if those chunks match the query with high similarity.
    """
    service = test_hybrid_environment
    ctx = AccessContext(
        user_id="EMP-USER-01",
        role="EMPLOYEE",
        department="Operations",
        clearance_level="INTERNAL",
    )

    response = service.retrieve(
        query="Access control protocols, encryption standards, and remote work hours",
        access_context=ctx,
        top_k=5,
    )

    # Ensure restricted/confidential chunk text NEVER appears in results
    for item in response.results:
        assert item.chunk_id != "SEC-001_CHUNK_0001", "SEC-001 is RESTRICTED and must be denied"
        assert item.chunk_id != "SEC-004_CHUNK_0001", "SEC-004 is CONFIDENTIAL and must be denied"
        assert item.metadata["classification"] != "RESTRICTED"
        assert "threat modeling for high-risk autonomous AI systems" not in item.text

    # Denied count should be positive because security chunks were filtered
    assert response.denied_count > 0


def test_hybrid_governance_retrieval_empty_when_all_denied(test_hybrid_environment):
    """
    Verify that when all candidate matches are denied for a user's role/clearance,
    the response is an empty list with authorized_result_count=0, and denied_count reflects the candidates.
    """
    service = test_hybrid_environment
    # An external contractor with PUBLIC clearance searching for restricted AI security
    ctx = AccessContext(
        user_id="CONTRACTOR-01",
        role="CONTRACTOR",
        department="External",
        clearance_level="PUBLIC",
    )

    response = service.retrieve(
        query="Access control protocols and threat modeling for autonomous AI systems",
        access_context=ctx,
        top_k=5,
    )

    assert response.authorized_result_count == 0
    assert response.results == []
    assert response.denied_count > 0


def test_hybrid_governance_retrieval_deduplication(test_hybrid_environment):
    """
    Verify that chunks retrieved by BOTH semantic and keyword branches are deduplicated
    and receive accumulated RRF scores.
    """
    service = test_hybrid_environment
    ctx = AccessContext(
        user_id="ADMIN-01",
        role="ADMIN",
        clearance_level="RESTRICTED",
    )

    response = service.retrieve(
        query="remote work policy guidelines core hours",
        access_context=ctx,
        top_k=5,
    )

    chunk_ids = [r.chunk_id for r in response.results]
    # Verify no duplicates in results
    assert len(chunk_ids) == len(set(chunk_ids))

    # HR-001 exists in both branches -> both scores should be present
    hr_item = next((r for r in response.results if r.chunk_id == "HR-001_CHUNK_0001"), None)
    if hr_item:
        assert hr_item.semantic_score is not None
        assert hr_item.keyword_score is not None
        assert hr_item.fused_score > 0.0


def test_governance_search_api_endpoint(test_hybrid_environment):
    """
    Integration test for FastAPI endpoint POST /retrieval/governance-search
    and POST /api/v1/retrieval/governance-search.
    """
    service = test_hybrid_environment
    app.dependency_overrides[get_hybrid_retrieval_service] = lambda: service

    client = TestClient(app)

    try:
        # 1. Authorized Request
        payload = {
            "query": "remote work guidelines and core hours",
            "top_k": 3,
            "access_context": {
                "user_id": "EMP-001",
                "role": "EMPLOYEE",
                "department": "Human Resources",
                "clearance_level": "INTERNAL",
            },
        }
        employee_headers = {"Authorization": f"Bearer {create_access_token('EMP-001', extra={'role': 'EMPLOYEE', 'dept': 'Human Resources'})}"}

        # Direct /retrieval/governance-search
        res = client.post("/retrieval/governance-search", json=payload, headers=employee_headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["query"] == "remote work guidelines and core hours"
        assert data["requested_top_k"] == 3
        assert "authorized_result_count" in data
        assert "results" in data
        assert isinstance(data["results"], list)

        # 2. Prefixed /api/v1/retrieval/governance-search
        res_v1 = client.post("/api/v1/retrieval/governance-search", json=payload, headers=employee_headers)
        assert res_v1.status_code == 200, res_v1.text
        data_v1 = res_v1.json()
        assert data_v1["requested_top_k"] == 3

        # 3. Unauthorized access check (e.g. searching restricted topic with low clearance)
        sec_payload = {
            "query": "Access control protocols and threat modeling for autonomous AI systems",
            "top_k": 3,
            "access_context": {
                "user_id": "EMP-GUEST",
                "role": "GUEST",
                "clearance_level": "PUBLIC",
            },
        }
        guest_headers = {"Authorization": f"Bearer {create_access_token('EMP-GUEST', extra={'role': 'GUEST'})}"}
        res_sec = client.post("/retrieval/governance-search", json=sec_payload, headers=guest_headers)
        assert res_sec.status_code == 200
        sec_data = res_sec.json()
        assert sec_data["authorized_result_count"] == 0
        assert sec_data["results"] == []

        # 4. Validation error: empty query
        bad_query_res = client.post(
            "/retrieval/governance-search",
            json={
                "query": "   ",
                "top_k": 5,
                "access_context": {"user_id": "U1", "role": "EMPLOYEE"},
            }, headers=employee_headers,
        )
        assert bad_query_res.status_code in (400, 422)

        # 5. Validation error: invalid top_k
        bad_k_res = client.post(
            "/retrieval/governance-search",
            json={
                "query": "Valid query",
                "top_k": -5,
                "access_context": {"user_id": "U1", "role": "EMPLOYEE"},
            }, headers=employee_headers,
        )
        assert bad_k_res.status_code in (400, 422)

        # 6. Validation error: missing access_context
        missing_ctx_res = client.post(
            "/retrieval/governance-search",
            json={"query": "Valid query", "top_k": 5},
            headers=employee_headers,
        )
        assert missing_ctx_res.status_code in (400, 422)

    finally:
        app.dependency_overrides.clear()
