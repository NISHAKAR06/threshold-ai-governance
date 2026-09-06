"""
text_utils.py — Text normalization and sanitation utilities for THRESHOLD AI document ingestion.
"""
import re


def normalize_line_endings(text: str) -> str:
    """Normalize Windows (\r\n) and classic Mac (\r) line endings to standard Unix (\n)."""
    if not text:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def remove_null_bytes(text: str) -> str:
    """Remove null characters (\x00) and other non-printable control characters (except \n, \t, \r)."""
    if not text:
        return ""
    # Strip \x00
    cleaned = text.replace("\x00", "")
    # Remove control characters in range 0x01-0x08, 0x0B-0x0C, 0x0E-0x1F, 0x7F
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    return cleaned


def normalize_whitespace(text: str) -> str:
    """
    Normalize excessive horizontal whitespace (spaces and tabs) while preserving line breaks.
    Replaces sequences of multiple horizontal spaces/tabs with a single space.
    Strips trailing whitespace from each line.
    """
    if not text:
        return ""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Replace multiple spaces/tabs with single space
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(cleaned_line)
    return "\n".join(cleaned_lines)


def normalize_repeated_blank_lines(text: str, max_consecutive: int = 2) -> str:
    """
    Collapse sequences of more than `max_consecutive` consecutive blank lines down to `max_consecutive`.
    Preserves intentional paragraph and section breaks.
    """
    if not text:
        return ""
    pattern = r"\n{" + str(max_consecutive + 2) + r",}"
    replacement = "\n" * (max_consecutive + 1)
    return re.sub(pattern, replacement, text)


def clean_and_normalize_text(text: str) -> str:
    """
    Full text cleaning and normalization pipeline:
    1. Line ending normalization
    2. Null byte and control char removal
    3. Horizontal whitespace normalization
    4. Repeated blank line reduction
    5. Overall leading/trailing whitespace stripping
    """
    if not text:
        return ""
    step1 = normalize_line_endings(text)
    step2 = remove_null_bytes(step1)
    step3 = normalize_whitespace(step2)
    step4 = normalize_repeated_blank_lines(step3, max_consecutive=2)
    return step4.strip()
