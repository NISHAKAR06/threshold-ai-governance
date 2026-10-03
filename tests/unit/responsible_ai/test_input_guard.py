"""
test_input_guard.py — Unit tests for Responsible AI input validation and safety guardrails.
"""
import pytest
from app.responsible_ai.input_guard import (
    ResponsibleAIInputGuard,
    GuardDecision,
)


def test_normal_technical_request():
    """Verify standard enterprise questions pass the input guard cleanly."""
    guard = ResponsibleAIInputGuard(max_length=1000)
    query = "How do we configure database connection pooling for PostgreSQL in production?"

    res = guard.validate_input(query)
    assert res.decision == GuardDecision.ALLOW
    assert res.risk_score == 0.0
    assert len(res.violations) == 0
    assert res.sanitized_text == query


def test_empty_or_whitespace_request():
    """Verify empty input is rejected."""
    guard = ResponsibleAIInputGuard()
    res_empty = guard.validate_input("")
    assert res_empty.decision == GuardDecision.BLOCK
    assert "EMPTY_INPUT" in res_empty.violations

    res_ws = guard.validate_input("    \n\t  ")
    assert res_ws.decision == GuardDecision.BLOCK
    assert "EMPTY_INPUT" in res_ws.violations


def test_oversized_request():
    """Verify requests exceeding maximum character boundary are blocked."""
    guard = ResponsibleAIInputGuard(max_length=200)
    huge_text = "A" * 250

    res = guard.validate_input(huge_text)
    assert res.decision == GuardDecision.BLOCK
    assert "EXCESSIVE_LENGTH" in res.violations


def test_malformed_null_byte_request():
    """Verify requests with null byte control codes are blocked."""
    guard = ResponsibleAIInputGuard()
    malformed = "What is the policy\x00 for user access?"

    res = guard.validate_input(malformed)
    assert res.decision == GuardDecision.BLOCK
    assert "MALFORMED_NULL_BYTES" in res.violations


def test_non_string_data_type():
    """Verify non-string inputs are cleanly rejected without unhandled exceptions."""
    guard = ResponsibleAIInputGuard()
    res = guard.validate_input({"query": "test"})
    assert res.decision == GuardDecision.BLOCK
    assert "INVALID_DATA_TYPE" in res.violations
