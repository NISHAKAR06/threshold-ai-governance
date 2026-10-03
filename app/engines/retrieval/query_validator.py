"""
query_validator.py — Validates user search query strings and top_k parameters.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings
from app.core.exceptions import InvalidRetrievalQueryError, QueryValidationError


@dataclass
class QueryValidationResult:
    """Structured validation outcome for a retrieval query."""
    is_valid: bool
    cleaned_query: str
    cleaned_top_k: int
    errors: List[str] = field(default_factory=list)

    @property
    def sanitized_query(self) -> str:
        """Compatibility property for cleaned query."""
        return self.cleaned_query

    @property
    def effective_top_k(self) -> int:
        """Compatibility property for resolved top_k."""
        return self.cleaned_top_k


class QueryValidator:
    """Validates query content, text lengths, and top_k bounds."""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        default_top_k: Optional[int] = None,
        max_top_k: Optional[int] = None,
        min_query_length: Optional[int] = None,
        max_query_length: Optional[int] = None,
    ):
        min_len = min_length if min_length is not None else min_query_length
        max_len = max_length if max_length is not None else max_query_length

        self.min_length = min_len if min_len is not None else settings.RETRIEVAL_MIN_QUERY_LENGTH
        self.max_length = max_len if max_len is not None else settings.RETRIEVAL_MAX_QUERY_LENGTH
        self.default_top_k = default_top_k if default_top_k is not None else settings.RETRIEVAL_DEFAULT_TOP_K
        self.max_top_k = max_top_k if max_top_k is not None else settings.RETRIEVAL_MAX_TOP_K

    def validate(
        self,
        query: Optional[str],
        top_k: Optional[int] = None,
        raise_exception: bool = False,
        raise_on_error: bool = False,
    ) -> QueryValidationResult:
        """
        Validate query string and top_k value.

        Args:
            query: The raw search string.
            top_k: Desired number of results.
            raise_exception: If True, raises domain exception on failure.
            raise_on_error: Alias for raise_exception.

        Returns:
            QueryValidationResult with cleaned inputs and error messages.
        """
        should_raise = raise_exception or raise_on_error
        errors: List[str] = []

        # 1. Existence and empty checks
        if query is None:
            if should_raise:
                raise InvalidRetrievalQueryError("Query string is missing (None)", code="EMPTY_QUERY")
            errors.append("Query string is missing (None)")
            return QueryValidationResult(
                is_valid=False,
                cleaned_query="",
                cleaned_top_k=self.default_top_k,
                errors=errors,
            )

        cleaned_query = str(query).strip()
        if not cleaned_query:
            if should_raise:
                raise InvalidRetrievalQueryError("Query cannot be empty or whitespace only", code="EMPTY_QUERY")
            errors.append("Query cannot be empty or whitespace only")

        # 2. Length checks
        if cleaned_query and len(cleaned_query) < self.min_length:
            msg = f"Query length ({len(cleaned_query)}) is too short (minimum {self.min_length})"
            if should_raise:
                raise QueryValidationError(msg, code="QUERY_TOO_SHORT")
            errors.append(msg)

        if cleaned_query and len(cleaned_query) > self.max_length:
            msg = f"Query length ({len(cleaned_query)}) exceeds maximum allowed ({self.max_length})"
            if should_raise:
                raise QueryValidationError(msg, code="QUERY_TOO_LONG")
            errors.append(msg)

        # 3. top_k bounds checks
        resolved_top_k = top_k if top_k is not None else self.default_top_k
        if not isinstance(resolved_top_k, int) or resolved_top_k <= 0:
            msg = f"top_k must be a positive integer > 0, got {resolved_top_k}"
            if should_raise:
                raise QueryValidationError(msg, code="INVALID_TOP_K")
            errors.append(msg)
        elif resolved_top_k > self.max_top_k:
            msg = f"top_k ({resolved_top_k}) cannot exceed {self.max_top_k}"
            if should_raise:
                raise QueryValidationError(msg, code="INVALID_TOP_K")
            errors.append(msg)

        is_valid = len(errors) == 0
        if not is_valid and should_raise:
            raise QueryValidationError(f"Query validation failed: {'; '.join(errors)}")

        return QueryValidationResult(
            is_valid=is_valid,
            cleaned_query=cleaned_query,
            cleaned_top_k=resolved_top_k,
            errors=errors,
        )
