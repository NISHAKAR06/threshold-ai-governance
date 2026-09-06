"""
test_txt_loader.py — Unit tests for TXTLoader.
"""
import pytest
from pathlib import Path
from app.engines.ingestion.loaders.txt_loader import TXTLoader
from app.core.exceptions import LoaderError


def test_txt_loader_success(tmp_path: Path):
    f = tmp_path / "sample.txt"
    sample_text = "Threshold Enterprise Systems Policy Document\nSection 1: Overview"
    f.write_text(sample_text, encoding="utf-8")

    loader = TXTLoader()
    extracted = loader.load(f)
    assert extracted == sample_text


def test_txt_loader_missing_file(tmp_path: Path):
    loader = TXTLoader()
    with pytest.raises(LoaderError) as exc_info:
        loader.load(tmp_path / "non_existent.txt")
    assert "does not exist" in str(exc_info.value)


def test_txt_loader_empty_file(tmp_path: Path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")

    loader = TXTLoader()
    with pytest.raises(LoaderError) as exc_info:
        loader.load(f)
    assert "is empty" in str(exc_info.value)
