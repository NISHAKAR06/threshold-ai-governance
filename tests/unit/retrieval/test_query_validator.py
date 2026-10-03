"""
test_query_validator.py — Unit tests for QueryValidator.
"""
import pytest
from app.engines.retrieval.query_validator import QueryValidator
from app.core.exceptions import InvalidRetrievalQueryError, QueryValidationError
from app.config import settings


def test_validator_valid_query_and_top_k():
    validator = QueryValidator(min_query_length=3, max_query_length=100, max_top_k=20, default_top_k=5)
    res = validator.validate(query="  What is the leave policy?  ", top_k=10)

    assert res.is_valid is True
    assert res.sanitized_query == "What is the leave policy?"
    assert res.effective_top_k == 10
    assert len(res.errors) == 0


def test_validator_default_top_k_when_none():
    validator = QueryValidator(default_top_k=5)
    res = validator.validate(query="Explain compliance audit")

    assert res.is_valid is True
    assert res.effective_top_k == 5


def test_validator_empty_query_raises():
    validator = QueryValidator()
    with pytest.raises(InvalidRetrievalQueryError) as exc_info:
        validator.validate(query="", raise_on_error=True)
    assert exc_info.value.code == "EMPTY_QUERY"


def test_validator_none_query_raises():
    validator = QueryValidator()
    with pytest.raises(InvalidRetrievalQueryError) as exc_info:
        validator.validate(query=None, raise_on_error=True)
    assert exc_info.value.code == "EMPTY_QUERY"


def test_validator_whitespace_only_query():
    validator = QueryValidator()
    with pytest.raises(InvalidRetrievalQueryError) as exc_info:
        validator.validate(query="    \t \n   ", raise_on_error=True)
    assert exc_info.value.code == "EMPTY_QUERY"


def test_validator_query_too_short():
    validator = QueryValidator(min_query_length=5)
    with pytest.raises(QueryValidationError) as exc_info:
        validator.validate(query="ab", raise_on_error=True)
    assert exc_info.value.code == "QUERY_TOO_SHORT"


def test_validator_query_too_long():
    validator = QueryValidator(max_query_length=50)
    long_query = "a" * 55
    with pytest.raises(QueryValidationError) as exc_info:
        validator.validate(query=long_query, raise_on_error=True)
    assert exc_info.value.code == "QUERY_TOO_LONG"


def test_validator_invalid_top_k_negative_or_zero():
    validator = QueryValidator()
    with pytest.raises(QueryValidationError) as exc_info:
        validator.validate(query="Valid query", top_k=0, raise_on_error=True)
    assert exc_info.value.code == "INVALID_TOP_K"

    with pytest.raises(QueryValidationError) as exc_info:
        validator.validate(query="Valid query", top_k=-3, raise_on_error=True)
    assert exc_info.value.code == "INVALID_TOP_K"


def test_validator_top_k_above_maximum():
    validator = QueryValidator(max_top_k=20)
    with pytest.raises(QueryValidationError) as exc_info:
        validator.validate(query="Valid query", top_k=25, raise_on_error=True)
    assert exc_info.value.code == "INVALID_TOP_K"
    assert "cannot exceed 20" in exc_info.value.message


def test_validator_non_raising_mode():
    validator = QueryValidator(max_top_k=10, min_query_length=5)
    res = validator.validate(query="hi", top_k=15, raise_on_error=False)

    assert res.is_valid is False
    assert len(res.errors) >= 2
    assert any("too short" in err for err in res.errors)
    assert any("cannot exceed" in err for err in res.errors)
