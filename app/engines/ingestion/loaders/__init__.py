"""
Loaders package for THRESHOLD AI document ingestion.
"""
from app.engines.ingestion.loaders.base_loader import BaseLoader
from app.engines.ingestion.loaders.pdf_loader import PDFLoader
from app.engines.ingestion.loaders.docx_loader import DOCXLoader
from app.engines.ingestion.loaders.txt_loader import TXTLoader

__all__ = ["BaseLoader", "PDFLoader", "DOCXLoader", "TXTLoader"]
