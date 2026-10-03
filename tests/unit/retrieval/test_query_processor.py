"""
test_query_processor.py — Unit tests for QueryProcessor.
"""
from app.engines.retrieval.query_processor import QueryProcessor


def test_query_processor_whitespace_normalization():
    processor = QueryProcessor()
    raw = "   What   is   the   retention \t policy \n\n for   logs?   "
    res = processor.process(raw)

    assert res.normalized_query == "What is the retention policy for logs?"
    assert res.original_query == raw
    assert res.was_modified is True
    assert res.token_count == 7


def test_query_processor_already_clean_query():
    processor = QueryProcessor()
    clean = "Who has access to the database?"
    res = processor.process(clean)

    assert res.normalized_query == clean
    assert res.original_query == clean
    assert res.was_modified is False
    assert res.token_count == 6


def test_query_processor_preserves_all_terms():
    processor = QueryProcessor()
    query = "SEC-001 AI governance risk framework 2026 GDPR & HIPAA"
    res = processor.process(query)

    terms = ["SEC-001", "AI", "governance", "risk", "framework", "2026", "GDPR", "&", "HIPAA"]
    for term in terms:
        assert term in res.normalized_query


def test_query_processor_empty_or_whitespace():
    processor = QueryProcessor()
    res = processor.process("    ")
    assert res.normalized_query == ""
    assert res.token_count == 0
