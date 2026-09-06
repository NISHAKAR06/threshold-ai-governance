"""
txt_loader.py — Plaintext (.txt) document loader.
"""
from pathlib import Path
from typing import Union
from app.engines.ingestion.loaders.base_loader import BaseLoader
from app.utils.file_utils import read_text_file
from app.core.exceptions import LoaderError


class TXTLoader(BaseLoader):
    """Extracts text content from plaintext (.txt) files."""

    def load(self, file_path: Union[str, Path]) -> str:
        p = Path(file_path)
        if not p.exists():
            raise LoaderError(f"TXT file does not exist: {p}", str(p))

        try:
            text = read_text_file(p)
            if not text.strip():
                raise LoaderError(f"TXT file is empty: {p}", str(p))
            return text
        except Exception as e:
            if isinstance(e, LoaderError):
                raise e
            raise LoaderError(f"Failed to read TXT file '{p}': {str(e)}", str(p))
