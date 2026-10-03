"""
indexing_schema.py — Pydantic schemas validating indexing results and manifests.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentIndexingResultSchema(BaseModel):
    """Schema for document-level indexing outcome."""
    document_id: str = Field(..., min_length=1)
    chunks_processed: int = Field(ge=0)
    chunks_indexed: int = Field(ge=0)
    chunks_failed: int = Field(ge=0)
    status: str = Field(..., description="'SUCCESS' or 'FAILED'")
    error_message: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)
    execution_time_ms: float = Field(ge=0.0)


class IndexingManifestSchema(BaseModel):
    """Schema validating the complete batch indexing manifest."""
    indexing_run_id: str = Field(..., min_length=1)
    started_at: str = Field(..., min_length=1)
    completed_at: str = Field(..., min_length=1)
    embedding_provider: str = Field(..., min_length=1)
    embedding_model: str = Field(..., min_length=1)
    vector_store_provider: str = Field(..., min_length=1)
    collection_name: str = Field(..., min_length=1)
    total_documents: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    successful_chunks: int = Field(ge=0)
    failed_chunks: int = Field(ge=0)
    vectors_upserted: int = Field(ge=0)
    pipeline_version: str = "1.0.0"
    results: List[DocumentIndexingResultSchema]
