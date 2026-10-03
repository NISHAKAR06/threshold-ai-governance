"""
chunk_schema.py — Pydantic schemas for Chunk objects and persisted chunk files.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ChunkGovernanceMetadataSchema(BaseModel):
    """Schema validating the governance metadata embedded in each chunk."""
    department: str = Field(..., min_length=1, description="Department owner")
    classification: str = Field(..., min_length=1, description="Data classification level")
    allowed_roles: List[str] = Field(..., min_length=1, description="Roles permitted to access chunk")
    document_type: str = Field(..., min_length=1, description="Type of document")
    status: str = Field(..., min_length=1, description="Document governance status")
    title: str = Field(default="", description="Parent document title")
    version: str = Field(default="1.0", description="Document version")
    summary: str = Field(default="", description="Parent document summary")
    keywords: List[str] = Field(default_factory=list, description="Associated keywords")

    model_config = {"extra": "allow"}


class ChunkSourceSchema(BaseModel):
    """Schema validating source traceability in each chunk."""
    file_path: str = Field(..., min_length=1, description="Original source file path")
    file_format: str = Field(..., min_length=1, description="Original file format")

    model_config = {"extra": "allow"}


class ChunkSchema(BaseModel):
    """Schema for validating an individual generated chunk object."""
    chunk_id: str = Field(
        ...,
        pattern=r"^[A-Z0-9_-]+_CHUNK_\d{4}$",
        description="Deterministic chunk identifier",
    )
    document_id: str = Field(..., min_length=1, description="Parent document ID")
    chunk_index: int = Field(..., ge=1, description="1-indexed sequential position")
    text: str = Field(..., min_length=1, description="Cleaned chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Inherited governance metadata")
    source: Dict[str, Any] = Field(..., description="Source provenance metadata")
    parent_content_hash: str = Field(..., min_length=64, max_length=64, description="Parent document SHA-256")
    chunk_content_hash: str = Field(..., min_length=64, max_length=64, description="Chunk text SHA-256")
    created_at: str = Field(..., min_length=1, description="ISO-8601 UTC timestamp")

    @field_validator("text")
    @classmethod
    def validate_meaningful_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Chunk text cannot be empty or whitespace only")
        return v


class DocumentChunksFileSchema(BaseModel):
    """Schema validating the persisted chunk JSON file for a document."""
    document_id: str = Field(..., min_length=1)
    chunks: List[ChunkSchema] = Field(..., min_length=1)
