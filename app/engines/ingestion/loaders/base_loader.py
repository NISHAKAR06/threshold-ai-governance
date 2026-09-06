"""
base_loader.py — Abstract base loader interface for document ingestion.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union


class BaseLoader(ABC):
    """Abstract base class for all file format document loaders."""

    @abstractmethod
    def load(self, file_path: Union[str, Path]) -> str:
        """
        Extract raw text content from the file at file_path.
        Must raise LoaderError if extraction fails.
        """
        pass
