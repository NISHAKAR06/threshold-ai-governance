"""
document_schema.py — Pydantic schemas for DocumentMetadata and NormalizedDocument in THRESHOLD AI.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentMetadataSchema(BaseModel):
    """Schema representing validated document metadata."""
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


class NormalizedDocumentSchema(BaseModel):
    """Schema representing the serialized normalized JSON document stored in data/normalized_documents/."""
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
    content_hash: str = Field(..., description="SHA-256 hash of normalized text content")
    content: str = Field(..., description="Normalized document text content")
    ingested_at: str = Field(..., description="ISO 8601 UTC timestamp of ingestion")
