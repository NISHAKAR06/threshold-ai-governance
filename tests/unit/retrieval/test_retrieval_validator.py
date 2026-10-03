"""
test_retrieval_validator.py — Unit tests for RetrievalValidator.
"""
from app.engines.retrieval.retrieval_validator import RetrievalValidator


def test_retrieval_validator_valid_candidates():
    validator = RetrievalValidator()
    candidates = [
        {
            "chunk_id": "SEC-001_CHUNK_0001",
            "document_id": "SEC-001",
            "text": "Access control security requirements.",
            "score": 0.88,
            "metadata": {"department": "Security", "allowed_roles": ["ANALYST"]},
            "source": {"file_name": "sec.pdf"},
        },
        {
            "chunk_id": "SEC-001_CHUNK_0002",
            "document_id": "SEC-001",
            "text": "Incident response guidelines.",
            "score": 0.94,
            "metadata": {"department": "Security", "allowed_roles": ["ADMIN"]},
            "source": {"file_name": "sec.pdf"},
        },
    ]

    results = validator.validate_and_rank(candidates, top_k=5)

    assert len(results) == 2
    # Should be sorted descending by score
    assert results[0].chunk_id == "SEC-001_CHUNK_0002"
    assert results[0].rank == 1
    assert results[0].score == 0.94
    assert results[1].chunk_id == "SEC-001_CHUNK_0001"
    assert results[1].rank == 2
    assert results[1].score == 0.88


def test_retrieval_validator_missing_ids_excluded():
    validator = RetrievalValidator()
    candidates = [
        {
            "chunk_id": "",
            "document_id": "SEC-001",
            "text": "Valid text but missing chunk_id",
            "score": 0.85,
        },
        {
            "chunk_id": "SEC-001_CHUNK_0002",
            "document_id": "",
            "text": "Valid text but missing document_id",
            "score": 0.80,
        },
        {
            "chunk_id": "SEC-001_CHUNK_0003",
            "document_id": "SEC-001",
            "text": "Completely valid candidate",
            "score": 0.75,
        },
    ]

    results = validator.validate_and_rank(candidates)
    assert len(results) == 1
    assert results[0].chunk_id == "SEC-001_CHUNK_0003"
    assert results[0].rank == 1


def test_retrieval_validator_empty_text_excluded():
    validator = RetrievalValidator()
    candidates = [
        {
            "chunk_id": "DOC-1_CHUNK_0001",
            "document_id": "DOC-1",
            "text": "   \n  ",
            "score": 0.9,
        },
        {
            "chunk_id": "DOC-1_CHUNK_0002",
            "document_id": "DOC-1",
            "text": "Valid chunk content here",
            "score": 0.85,
        },
    ]

    results = validator.validate_and_rank(candidates)
    assert len(results) == 1
    assert results[0].chunk_id == "DOC-1_CHUNK_0002"


def test_retrieval_validator_invalid_scores():
    validator = RetrievalValidator()
    candidates = [
        {
            "chunk_id": "DOC-1_CHUNK_0001",
            "document_id": "DOC-1",
            "text": "Invalid string score",
            "score": "not-a-score",
        },
        {
            "chunk_id": "DOC-1_CHUNK_0002",
            "document_id": "DOC-1",
            "text": "Negative score",
            "score": -0.5,
        },
        {
            "chunk_id": "DOC-1_CHUNK_0003",
            "document_id": "DOC-1",
            "text": "Score above 1 clamped or valid",
            "score": 1.05,
        },
    ]

    results = validator.validate_and_rank(candidates)
    assert len(results) == 1
    assert results[0].chunk_id == "DOC-1_CHUNK_0003"
    assert results[0].score == 1.0  # Clamped to 1.0


def test_retrieval_validator_duplicate_chunk_ids():
    validator = RetrievalValidator()
    candidates = [
        {
            "chunk_id": "DOC-1_CHUNK_0001",
            "document_id": "DOC-1",
            "text": "Duplicate chunk lower score",
            "score": 0.70,
        },
        {
            "chunk_id": "DOC-1_CHUNK_0001",
            "document_id": "DOC-1",
            "text": "Duplicate chunk higher score",
            "score": 0.92,
        },
    ]

    results = validator.validate_and_rank(candidates)
    assert len(results) == 1
    assert results[0].chunk_id == "DOC-1_CHUNK_0001"
    assert results[0].score == 0.92


def test_retrieval_validator_preserves_metadata():
    validator = RetrievalValidator()
    raw_meta = {
        "department": "Engineering",
        "classification": "RESTRICTED",
        "allowed_roles": ["ENG_LEAD", "SECURITY_ADMIN"],
        "document_type": "ARCHITECTURE",
        "status": "APPROVED",
    }
    candidate = {
        "chunk_id": "ENG-001_CHUNK_0001",
        "document_id": "ENG-001",
        "text": "Architecture specs",
        "score": 0.89,
        "metadata": raw_meta,
        "source": {"file_path": "eng.md"},
    }

    results = validator.validate_and_rank([candidate])
    assert len(results) == 1
    meta = results[0].metadata
    assert meta["department"] == "Engineering"
    assert meta["classification"] == "RESTRICTED"
    assert meta["allowed_roles"] == ["ENG_LEAD", "SECURITY_ADMIN"]
    assert meta["document_type"] == "ARCHITECTURE"
    assert meta["status"] == "APPROVED"
