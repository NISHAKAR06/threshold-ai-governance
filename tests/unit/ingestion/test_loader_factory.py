"""
test_loader_factory.py — Unit tests for LoaderFactory.
"""
import pytest
from app.engines.ingestion.loader_factory import LoaderFactory
from app.engines.ingestion.loaders.pdf_loader import PDFLoader
from app.engines.ingestion.loaders.docx_loader import DOCXLoader
from app.engines.ingestion.loaders.txt_loader import TXTLoader
from app.core.exceptions import UnsupportedFormatError


def test_loader_factory_by_format():
    factory = LoaderFactory()
    assert isinstance(factory.get_loader_for_format("PDF"), PDFLoader)
    assert isinstance(factory.get_loader_for_format("docx"), DOCXLoader)
    assert isinstance(factory.get_loader_for_format("TXT"), TXTLoader)


def test_loader_factory_by_path():
    factory = LoaderFactory()
    assert isinstance(factory.get_loader_for_path("document.pdf"), PDFLoader)
    assert isinstance(factory.get_loader_for_path("/path/to/doc.docx"), DOCXLoader)
    assert isinstance(factory.get_loader_for_path("C:\\folder\\notes.txt"), TXTLoader)


def test_loader_factory_unsupported_format():
    factory = LoaderFactory()
    with pytest.raises(UnsupportedFormatError):
        factory.get_loader_for_format("XLSX")

    with pytest.raises(UnsupportedFormatError):
        factory.get_loader_for_path("document.unknown")
