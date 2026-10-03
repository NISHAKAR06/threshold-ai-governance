"""
chunking_schema.py — Pydantic schemas for chunking results and manifests.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentChunkResultSchema(BaseModel):
    """Schema for individual document chunking result."""
    document_id: str
    status: str = Field(..., description="'SUCCESS' or 'FAILED'")
    chunks_created: int = Field(ge=0)
    output_file: Optional[str] = None
    execution_time_ms: float = Field(ge=0.0)
    error_message: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)


class ChunkingManifestSchema(BaseModel):
    """Schema validating the batch chunking manifest."""
    chunking_run_id: str
    started_at: str
    completed_at: str
    pipeline_version: str = "1.0.0"
    total_documents: int = Field(ge=0)
    successful_documents: int = Field(ge=0)
    failed_documents: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    configuration: Dict[str, Any]
    results: List[DocumentChunkResultSchema]
