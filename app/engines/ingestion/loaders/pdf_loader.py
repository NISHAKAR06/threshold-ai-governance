"""
pdf_loader.py — PDF document loader using pypdf.
"""
from pathlib import Path
from typing import Union
from pypdf import PdfReader
from app.engines.ingestion.loaders.base_loader import BaseLoader
from app.core.exceptions import LoaderError


class PDFLoader(BaseLoader):
    """Extracts text content from PDF documents."""

    def load(self, file_path: Union[str, Path]) -> str:
        p = Path(file_path)
        if not p.exists():
            raise LoaderError(f"PDF file does not exist: {p}", str(p))

        try:
            reader = PdfReader(str(p))
            extracted_pages = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text.strip())

            full_text = "\n\n".join(extracted_pages)
            if not full_text.strip():
                raise LoaderError(f"PDF file contains no readable text: {p}", str(p))

            return full_text
        except Exception as e:
            if isinstance(e, LoaderError):
                raise e
            raise LoaderError(f"Failed to extract text from PDF '{p}': {str(e)}", str(p))
