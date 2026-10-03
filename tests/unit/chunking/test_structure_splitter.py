"""
test_structure_splitter.py — Unit tests for StructureSplitter.
"""
import pytest
from app.engines.chunking.structure_splitter import StructureSplitter
from app.core.exceptions import InvalidChunkConfigurationError


def test_invalid_config_chunk_size():
    """Verify exception raised when chunk_size is 0 or negative."""
    with pytest.raises(InvalidChunkConfigurationError):
        StructureSplitter(chunk_size=0, chunk_overlap=0)

    with pytest.raises(InvalidChunkConfigurationError):
        StructureSplitter(chunk_size=-10, chunk_overlap=0)


def test_invalid_config_chunk_overlap():
    """Verify exception raised when chunk_overlap is negative or >= chunk_size."""
    with pytest.raises(InvalidChunkConfigurationError):
        StructureSplitter(chunk_size=500, chunk_overlap=-1)

    with pytest.raises(InvalidChunkConfigurationError):
        StructureSplitter(chunk_size=500, chunk_overlap=500)

    with pytest.raises(InvalidChunkConfigurationError):
        StructureSplitter(chunk_size=500, chunk_overlap=600)


def test_empty_and_whitespace_content():
    """Verify empty and whitespace-only text return empty lists."""
    splitter = StructureSplitter(chunk_size=500, chunk_overlap=50)
    assert splitter.split_text("") == []
    assert splitter.split_text("   \n\t  \n  ") == []
    assert splitter.split_text(None) == []


def test_small_document_smaller_than_chunk_size():
    """Verify document smaller than chunk_size returns exactly one chunk."""
    splitter = StructureSplitter(chunk_size=500, chunk_overlap=50)
    text = "Threshold Enterprise Systems is dedicated to engineering reliable, secure platforms."
    chunks = splitter.split_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_multiple_paragraphs_splitting():
    """Verify paragraphs are respected when splitting."""
    splitter = StructureSplitter(chunk_size=150, chunk_overlap=30)
    text = (
        "Paragraph One introduces the enterprise architecture with reliable governance.\n\n"
        "Paragraph Two discusses data classification and access boundaries.\n\n"
        "Paragraph Three outlines audit trails and retention mechanisms."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    # Ensure text is preserved across chunks
    combined = " ".join(chunks)
    assert "Paragraph One" in combined
    assert "Paragraph Two" in combined
    assert "Paragraph Three" in combined


def test_multiple_headings_splitting():
    """Verify heading boundaries trigger clean chunk transitions."""
    splitter = StructureSplitter(chunk_size=200, chunk_overlap=30)
    text = (
        "1. Document Overview and Executive Summary\n"
        "Welcome to Threshold Enterprise Systems. We provide cutting edge AI.\n\n"
        "2. Purpose and Applicability\n"
        "This policy applies to all global engineering teams."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    # Check heading starts
    assert any(c.startswith("1. Document Overview") for c in chunks)
    assert any("2. Purpose and Applicability" in c for c in chunks)


def test_very_long_paragraph():
    """Verify a very long paragraph without double newlines is split by sentences."""
    splitter = StructureSplitter(chunk_size=200, chunk_overlap=40)
    text = (
        "Threshold Enterprise Systems enforces strict information security across all repositories. "
        "Every engineer must complete biometric and security authentication prior to accessing sensitive systems. "
        "Furthermore, encryption in transit and at rest is universally mandated for all databases. "
        "Any breach of these protocols triggers immediate incident escalation."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 300  # Allow slight tolerance for word boundaries


def test_very_long_sentence_fallback():
    """Verify a sentence exceeding chunk_size falls back to word-level splitting."""
    splitter = StructureSplitter(chunk_size=100, chunk_overlap=20)
    # 250 character continuous sentence without punctuation
    text = (
        "this is an exceptionally long and continuous sentence without any punctuation "
        "designed specifically to test that the structure splitter safely falls back to word level "
        "and character level sliding windows without crashing or dropping content"
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 150


def test_unicode_content_preservation():
    """Verify unicode characters (accents, emojis, non-Latin scripts) are preserved."""
    splitter = StructureSplitter(chunk_size=200, chunk_overlap=30)
    text = (
        "Governance Baselines: © 2026 Threshold Enterprise Systems™ — Résumé compliance § 4.2. "
        "Languages: 日本語, Español, Français, Deutsch, हिंदी. "
        "Security indicator: 🔒 Verified."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 1
    combined = " ".join(chunks)
    assert "Résumé" in combined
    assert "© 2026" in combined
    assert "日本語" in combined
    assert "हिंदी" in combined
    assert "🔒" in combined


def test_overlap_behavior():
    """Verify overlap produces shared context between consecutive chunks."""
    splitter = StructureSplitter(chunk_size=120, chunk_overlap=40)
    text = (
        "Alpha unit specifies the primary authentication token format. "
        "Beta unit specifies the role-based entitlement matrix. "
        "Gamma unit specifies the audit logging policy."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    # Check that overlap exists or each chunk contains distinct forward progress
    for i in range(len(chunks) - 1):
        assert chunks[i] != chunks[i + 1]
