"""
query_processor.py — Normalizes and prepares query strings for embedding generation.
"""
import re
from dataclasses import dataclass


@dataclass
class ProcessedQuery:
    """Encapsulates processed query text and traceability information."""
    normalized_query: str
    original_query: str
    was_modified: bool
    token_count: int


class QueryProcessor:
    """Prepares validated search query text for dense embedding generation."""

    def process(self, query: str) -> ProcessedQuery:
        """
        Normalize excessive horizontal/vertical whitespace while preserving semantic terms.
        Returns structured ProcessedQuery.
        """
        if not query:
            return ProcessedQuery(
                normalized_query="",
                original_query=query,
                was_modified=False,
                token_count=0,
            )

        # Normalize internal whitespace sequences (tabs, multiple spaces, linebreaks) to single space
        normalized = re.sub(r"\s+", " ", str(query).strip())
        tokens = normalized.split() if normalized else []

        return ProcessedQuery(
            normalized_query=normalized,
            original_query=query,
            was_modified=(normalized != query),
            token_count=len(tokens),
        )

    def process_query(self, query: str) -> str:
        """
        Convenience method returning just the normalized query string.
        """
        return self.process(query).normalized_query
