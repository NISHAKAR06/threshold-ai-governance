"""
document_normalizer.py — Document text normalizer for Phase 8 ingestion.
"""
from dataclasses import dataclass
from app.utils.text_utils import clean_and_normalize_text


@dataclass
class NormalizationResult:
    """Outcome of document text normalization with statistical metrics."""
    raw_text: str
    normalized_text: str
    raw_character_count: int
    raw_word_count: int
    normalized_character_count: int
    normalized_word_count: int


class DocumentNormalizer:
    """Normalizes raw document text into standardized clean UTF-8 text."""

    def normalize(self, raw_text: str) -> NormalizationResult:
        """
        Execute full normalization pipeline:
        - Line ending standardization
        - Null byte and non-printable control character elimination
        - Excessive horizontal whitespace reduction
        - Multi-blank-line collapsing preserving paragraphs & section headers
        - Computes character and word counts before and after
        """
        raw = raw_text or ""
        raw_char_count = len(raw)
        raw_word_count = len(raw.split())

        normalized = clean_and_normalize_text(raw)
        norm_char_count = len(normalized)
        norm_word_count = len(normalized.split())

        return NormalizationResult(
            raw_text=raw,
            normalized_text=normalized,
            raw_character_count=raw_char_count,
            raw_word_count=raw_word_count,
            normalized_character_count=norm_char_count,
            normalized_word_count=norm_word_count,
        )
