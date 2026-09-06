"""
test_hash_utils.py — Unit tests for SHA-256 hash utilities.
"""
import pytest
from pathlib import Path
from app.utils.hash_utils import compute_sha256, compute_file_sha256


def test_compute_sha256_deterministic():
    text = "Threshold Enterprise Systems - AI Governance Platform"
    hash1 = compute_sha256(text)
    hash2 = compute_sha256(text)
    assert hash1 == hash2
    assert len(hash1) == 64
    assert isinstance(hash1, str)


def test_compute_sha256_different_content():
    hash1 = compute_sha256("Content A")
    hash2 = compute_sha256("Content B")
    assert hash1 != hash2


def test_compute_sha256_bytes_and_str_match():
    text = "Hello Threshold"
    assert compute_sha256(text) == compute_sha256(text.encode("utf-8"))


def test_compute_file_sha256(tmp_path: Path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("SHA-256 test file content", encoding="utf-8")
    expected_hash = compute_sha256("SHA-256 test file content")
    assert compute_file_sha256(test_file) == expected_hash
