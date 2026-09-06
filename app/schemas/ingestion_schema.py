"""
ingestion_schema.py — Pydantic schemas for IngestionResult and IngestionManifest.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class IngestionResultSchema(BaseModel):
    """Schema for the result of ingesting an individual document."""
    document_id: str
    status: str = Field(..., description="'SUCCESS' or 'FAILED'")
    file_path: str
    file_format: str
    content_hash: Optional[str] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    execution_time_ms: float
    error_message: Optional[str] = None


class IngestionManifestSchema(BaseModel):
    """Schema for the comprehensive batch ingestion manifest."""
    manifest_id: str
    timestamp: str
    total_documents: int
    success_count: int
    failure_count: int
    execution_time_seconds: float
    pipeline_version: str = "1.0.0"
    documents: List[IngestionResultSchema]
