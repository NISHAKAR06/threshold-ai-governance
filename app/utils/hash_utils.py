"""
hash_utils.py — Cryptographic hash functions (SHA-256) for content verification and deduplication.
"""
import hashlib
from pathlib import Path
from typing import Union


def compute_sha256(content: Union[str, bytes]) -> str:
    """Compute SHA-256 hexadecimal hash string for given text or bytes."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def compute_file_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash for a file reading in chunks."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()
