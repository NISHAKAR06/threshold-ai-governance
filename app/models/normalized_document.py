"""
normalized_document.py — Domain dataclass for normalized documents.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class NormalizedDocument:
    """Represents a fully ingested, cleaned, and validated enterprise document."""
    document_id: str
    title: str
    department: str
    classification: str
    version: str
    status: str
    effective_date: str
    allowed_roles: List[str]
    document_type: str
    summary: str
    keywords: List[str]
    file_path: str
    file_format: str
    raw_character_count: int
    raw_word_count: int
    normalized_character_count: int
    normalized_word_count: int
    content_hash: str
    content: str
    ingested_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert normalized document dataclass to dictionary."""
        return asdict(self)
