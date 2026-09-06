"""
loader_factory.py — Factory for instantiating format-specific document loaders.
"""
from pathlib import Path
from typing import Union, Dict, Type
from app.engines.ingestion.loaders.base_loader import BaseLoader
from app.engines.ingestion.loaders.pdf_loader import PDFLoader
from app.engines.ingestion.loaders.docx_loader import DOCXLoader
from app.engines.ingestion.loaders.txt_loader import TXTLoader
from app.utils.file_utils import get_file_extension
from app.core.exceptions import UnsupportedFormatError


class LoaderFactory:
    """Factory creating appropriate document loaders based on format identifier or file extension."""

    _LOADER_REGISTRY: Dict[str, Type[BaseLoader]] = {
        "pdf": PDFLoader,
        "docx": DOCXLoader,
        "txt": TXTLoader,
    }

    def __init__(self):
        self._cached_loaders: Dict[str, BaseLoader] = {}

    def get_loader_for_format(self, format_name: str) -> BaseLoader:
        """Return loader instance for format name e.g. 'PDF', 'DOCX', 'TXT'."""
        fmt_key = format_name.strip().lower()
        if fmt_key not in self._LOADER_REGISTRY:
            raise UnsupportedFormatError(format_name)

        if fmt_key not in self._cached_loaders:
            loader_cls = self._LOADER_REGISTRY[fmt_key]
            self._cached_loaders[fmt_key] = loader_cls()

        return self._cached_loaders[fmt_key]

    def get_loader_for_path(self, file_path: Union[str, Path]) -> BaseLoader:
        """Return loader instance based on the file extension."""
        ext = get_file_extension(file_path)
        return self.get_loader_for_format(ext)
