"""
test_document_normalizer.py — Unit tests for DocumentNormalizer and text utilities.
"""
import pytest
from app.engines.ingestion.document_normalizer import DocumentNormalizer
from app.utils.text_utils import (
    normalize_line_endings,
    remove_null_bytes,
    normalize_whitespace,
    normalize_repeated_blank_lines,
)


def test_normalize_line_endings():
    text = "Line 1\r\nLine 2\rLine 3\nLine 4"
    result = normalize_line_endings(text)
    assert result == "Line 1\nLine 2\nLine 3\nLine 4"
    assert "\r" not in result


def test_remove_null_bytes():
    text = "Hello\x00World\x01\x02Test\x00!"
    result = remove_null_bytes(text)
    assert "\x00" not in result
    assert result == "HelloWorldTest!"


def test_normalize_whitespace():
    text = "This   has \t\t multiple   spaces   \nNext   line"
    result = normalize_whitespace(text)
    assert result == "This has multiple spaces\nNext line"


def test_normalize_repeated_blank_lines():
    text = "Paragraph 1\n\n\n\n\n\nParagraph 2"
    result = normalize_repeated_blank_lines(text, max_consecutive=2)
    assert result == "Paragraph 1\n\n\nParagraph 2"


def test_document_normalizer_full_pipeline():
    normalizer = DocumentNormalizer()
    raw = "Header 1\r\n\r\n\r\n\r\nSome  text  with \t spaces and \x00nulls.\r\n\r\nFooter"
    res = normalizer.normalize(raw)

    assert "\r" not in res.normalized_text
    assert "\x00" not in res.normalized_text
    assert "Some text with spaces and nulls." in res.normalized_text
    assert res.raw_character_count > 0
    assert res.normalized_word_count > 0
