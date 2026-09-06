"""
file_utils.py — File system operations and path resolution utilities for THRESHOLD AI.
"""
import os
from pathlib import Path
from typing import Union, List, Optional


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory and any intermediate parents exist. Returns Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_file_extension(path: Union[str, Path]) -> str:
    """Return lowercase extension without dot (e.g. 'pdf', 'docx', 'txt')."""
    p = Path(path)
    suffix = p.suffix.lower()
    return suffix[1:] if suffix.startswith(".") else suffix


def get_file_size(path: Union[str, Path]) -> int:
    """Return file size in bytes."""
    return Path(path).stat().st_size


def read_text_file(path: Union[str, Path], encodings: Optional[List[str]] = None) -> str:
    """Read a text file trying multiple encodings (default: utf-8, utf-8-sig, latin-1, cp1252)."""
    if encodings is None:
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    p = Path(path)
    last_error = None
    for enc in encodings:
        try:
            with open(p, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue

    raise last_error or IOError(f"Could not read text file {path}")


def resolve_path(base_dir: Union[str, Path], relative_path: Union[str, Path]) -> Path:
    """Resolve a relative path against base_dir, ensuring canonical absolute Path."""
    base = Path(base_dir).resolve()
    target = Path(relative_path)
    if target.is_absolute():
        return target.resolve()
    return (base / target).resolve()
