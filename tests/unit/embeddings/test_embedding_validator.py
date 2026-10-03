"""
test_embedding_validator.py — Unit tests for EmbeddingValidator.
"""
import pytest
from app.engines.embeddings.embedding_validator import EmbeddingValidator
from app.core.exceptions import EmbeddingValidationError


def test_valid_vector():
    """Verify standard float vector passes validation."""
    validator = EmbeddingValidator(expected_dimension=4)
    result = validator.validate([0.1, -0.5, 0.8, -0.2])
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_none_or_non_list_vector():
    """Verify None or non-list types fail validation."""
    validator = EmbeddingValidator()
    assert validator.validate(None).is_valid is False
    assert validator.validate("not_a_vector").is_valid is False
    assert validator.validate(12345).is_valid is False


def test_empty_vector():
    """Verify empty vector fails validation."""
    validator = EmbeddingValidator()
    result = validator.validate([])
    assert result.is_valid is False
    assert any("empty" in e for e in result.errors)


def test_dimension_mismatch():
    """Verify dimension mismatch fails validation."""
    validator = EmbeddingValidator(expected_dimension=768)
    result = validator.validate([0.1, 0.2, 0.3])
    assert result.is_valid is False
    assert any("dimension mismatch" in e for e in result.errors)


def test_non_numeric_elements():
    """Verify string or non-numeric elements inside vector fail validation."""
    validator = EmbeddingValidator()
    result = validator.validate([0.1, "string_element", 0.5])
    assert result.is_valid is False
    assert any("non-numeric" in e for e in result.errors)


def test_nan_value_rejection():
    """Verify NaN values fail validation."""
    validator = EmbeddingValidator()
    result = validator.validate([0.1, float("nan"), 0.5])
    assert result.is_valid is False
    assert any("NaN" in e for e in result.errors)


def test_infinity_value_rejection():
    """Verify positive and negative infinity values fail validation."""
    validator = EmbeddingValidator()
    res_pos = validator.validate([0.1, float("inf"), 0.5])
    assert res_pos.is_valid is False
    assert any("Infinite" in e for e in res_pos.errors)

    res_neg = validator.validate([0.1, float("-inf"), 0.5])
    assert res_neg.is_valid is False
    assert any("Infinite" in e for e in res_neg.errors)


def test_raise_exception_flag():
    """Verify EmbeddingValidationError is raised when raise_exception=True."""
    validator = EmbeddingValidator()
    with pytest.raises(EmbeddingValidationError):
        validator.validate([], raise_exception=True)
