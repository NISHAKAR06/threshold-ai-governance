"""
test_context_validator.py — Unit tests for ContextValidator.
"""
import pytest

from app.engines.rag.context_builder import BuildContextResult
from app.engines.rag.context_validator import ContextValidator
from app.models.rag_source import RAGSource


def test_context_validator_valid():
    validator = ContextValidator()
    ctx_result = BuildContextResult(
        formatted_context="[SOURCE_1]\nDocument ID: D1\nChunk ID: C1\nContent:\nValid text",
        sources=[
            RAGSource(
                source_id="SOURCE_1",
                document_id="D1",
                chunk_id="C1",
            )
        ],
        chunks_used=1,
        total_chunks_available=1,
        total_length=50,
    )
    res = validator.validate(ctx_result)
    assert res.is_valid is True
    assert res.chunk_count == 1


def test_context_validator_empty_or_none():
    validator = ContextValidator()

    res_none = validator.validate(None)
    assert res_none.is_valid is False
    assert "None" in res_none.reason

    res_empty = validator.validate(
        BuildContextResult(
            formatted_context="   \n\t  ",
            sources=[],
            chunks_used=0,
        )
    )
    assert res_empty.is_valid is False
    assert "empty" in res_empty.reason.lower()


def test_context_validator_missing_ids():
    validator = ContextValidator()

    # Missing document_id
    ctx_missing_doc = BuildContextResult(
        formatted_context="[SOURCE_1] text",
        sources=[RAGSource(source_id="SOURCE_1", document_id="", chunk_id="C1")],
        chunks_used=1,
    )
    assert validator.validate(ctx_missing_doc).is_valid is False

    # Missing chunk_id
    ctx_missing_chunk = BuildContextResult(
        formatted_context="[SOURCE_1] text",
        sources=[RAGSource(source_id="SOURCE_1", document_id="D1", chunk_id="")],
        chunks_used=1,
    )
    assert validator.validate(ctx_missing_chunk).is_valid is False


def test_context_validator_duplicate_sources():
    validator = ContextValidator()
    ctx_dup = BuildContextResult(
        formatted_context="[SOURCE_1] text\n[SOURCE_1] text",
        sources=[
            RAGSource(source_id="SOURCE_1", document_id="D1", chunk_id="C1"),
            RAGSource(source_id="SOURCE_1", document_id="D2", chunk_id="C2"),
        ],
        chunks_used=2,
    )
    res = validator.validate(ctx_dup)
    assert res.is_valid is False
    assert "duplicate" in res.reason.lower()
