"""
embedding_validator.py — Validates embedding vectors and associated metadata.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Any

from app.core.exceptions import EmbeddingValidationError


@dataclass
class EmbeddingValidationResult:
    """Structured result of embedding validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)


class EmbeddingValidator:
    """Validates vector embeddings for numeric consistency, dimensionality, and finiteness."""

    def __init__(self, expected_dimension: Optional[int] = None):
        self.expected_dimension = expected_dimension

    def validate(
        self,
        embedding: Any,
        expected_dimension: Optional[int] = None,
        raise_exception: bool = False,
    ) -> EmbeddingValidationResult:
        """
        Validate an embedding vector.

        Args:
            embedding: The vector to validate (expected List[float] or array).
            expected_dimension: Expected dimension override.
            raise_exception: If True, raises EmbeddingValidationError on failure.

        Returns:
            EmbeddingValidationResult
        """
        errors: List[str] = []

        # 1. Existence check
        if embedding is None:
            errors.append("Embedding is None")
            return self._finalize(errors, raise_exception)

        # 2. Type check
        if not isinstance(embedding, (list, tuple)):
            errors.append(f"Embedding must be a list or tuple of numbers, got {type(embedding)}")
            return self._finalize(errors, raise_exception)

        # 3. Non-empty check
        if len(embedding) == 0:
            errors.append("Embedding vector is empty (0 dimensions)")
            return self._finalize(errors, raise_exception)

        # 4. Dimensionality check
        target_dim = expected_dimension or self.expected_dimension
        if target_dim is not None and len(embedding) != target_dim:
            errors.append(
                f"Embedding dimension mismatch: expected {target_dim}, got {len(embedding)}"
            )

        # 5. Numeric and finite checks
        for idx, val in enumerate(embedding):
            if not isinstance(val, (int, float)):
                errors.append(f"Element at index {idx} is non-numeric: {type(val)}")
                break  # Don't flood errors

            if math.isnan(val):
                errors.append(f"Element at index {idx} is NaN")
                break

            if math.isinf(val):
                errors.append(f"Element at index {idx} is Infinite ({val})")
                break

        return self._finalize(errors, raise_exception)

    @staticmethod
    def _finalize(errors: List[str], raise_exception: bool) -> EmbeddingValidationResult:
        is_valid = len(errors) == 0
        if not is_valid and raise_exception:
            raise EmbeddingValidationError(f"Embedding validation failed: {'; '.join(errors)}")
        return EmbeddingValidationResult(is_valid=is_valid, errors=errors)
