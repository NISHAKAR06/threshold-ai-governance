"""
test_keyword_search_engine.py — Unit tests for KeywordSearchEngine (BM25Okapi).
"""
import pytest
from app.engines.governance_retrieval.keyword_search_engine import KeywordSearchEngine, tokenize


def test_tokenize():
    tokens = tokenize("Information Security Policy: Version 2.0 (2026)")
    assert "information" in tokens
    assert "security" in tokens
    assert "policy" in tokens
    assert "2" in tokens or "2.0" not in tokens
    assert "2026" in tokens


def test_keyword_search_engine_basic_retrieval():
    engine = KeywordSearchEngine(auto_index=False)
    sample_chunks = [
        {
            "chunk_id": "SEC-001_CHUNK_0001",
            "document_id": "SEC-001",
            "text": "Information security policy covering access control, multi-factor authentication, and encryption.",
            "metadata": {"department": "Security", "classification": "INTERNAL", "allowed_roles": ["EMPLOYEE"]},
            "source": {"file_path": "sec_001.pdf"},
        },
        {
            "chunk_id": "HR-001_CHUNK_0001",
            "document_id": "HR-001",
            "text": "Employee annual leave, sick leave, paid time off, and bereavement guidelines.",
            "metadata": {"department": "HR", "classification": "INTERNAL", "allowed_roles": ["EMPLOYEE"]},
            "source": {"file_path": "hr_001.pdf"},
        },
        {
            "chunk_id": "ENG-001_CHUNK_0001",
            "document_id": "ENG-001",
            "text": "Production database deployment pipelines, Kubernetes cluster maintenance, and Docker containers.",
            "metadata": {"department": "Engineering", "classification": "RESTRICTED", "allowed_roles": ["ENGINEER"]},
            "source": {"file_path": "eng_001.pdf"},
        },
    ]

    engine.index_chunks(sample_chunks)
    assert engine.total_docs == 3

    # Search for security topics
    results = engine.search(query="encryption and multi-factor authentication", top_k=2)
    assert len(results) >= 1
    top = results[0]
    assert top["chunk_id"] == "SEC-001_CHUNK_0001"
    assert top["document_id"] == "SEC-001"
    assert top["score"] > 0.0
    assert "department" in top["metadata"]
    assert top["source"]["file_path"] == "sec_001.pdf"


def test_keyword_search_engine_no_match():
    engine = KeywordSearchEngine(auto_index=False)
    sample_chunks = [
        {
            "chunk_id": "HR-001_CHUNK_0001",
            "document_id": "HR-001",
            "text": "Remote work guidelines and equipment reimbursement.",
            "metadata": {},
            "source": {},
        }
    ]
    engine.index_chunks(sample_chunks)

    results = engine.search(query="quantum supercomputing gravitational physics", top_k=5)
    assert results == []


def test_keyword_search_engine_empty_query():
    engine = KeywordSearchEngine(auto_index=False)
    results = engine.search(query="", top_k=5)
    assert results == []

    results_ws = engine.search(query="   \t  \n  ", top_k=5)
    assert results_ws == []


def test_keyword_search_engine_score_ordering():
    engine = KeywordSearchEngine(auto_index=False)
    sample_chunks = [
        {
            "chunk_id": "DOC-1",
            "document_id": "DOC-1",
            "text": "audit compliance audit compliance audit logs",
            "metadata": {},
            "source": {},
        },
        {
            "chunk_id": "DOC-2",
            "document_id": "DOC-2",
            "text": "regular routine maintenance without special keywords",
            "metadata": {},
            "source": {},
        },
    ]
    engine.index_chunks(sample_chunks)

    results = engine.search(query="audit compliance", top_k=2)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "DOC-1"
