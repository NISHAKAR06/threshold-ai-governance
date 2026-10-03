"""
embedding_schema.py — Pydantic schemas validating vector records and embeddings.
"""
import math
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class VectorRecordSchema(BaseModel):
    """Schema validating an individual VectorRecord before storage or after retrieval."""
    vector_id: str = Field(..., min_length=1, description="Unique deterministic vector identifier")
    embedding: List[float] = Field(..., min_length=1, description="Dense vector embedding values")
    chunk_id: str = Field(..., min_length=1, description="Originating chunk identifier")
    document_id: str = Field(..., min_length=1, description="Originating document identifier")
    text: str = Field(..., min_length=1, description="Cleaned chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Preserved governance metadata")
    source: Dict[str, Any] = Field(..., description="Source file provenance metadata")
    parent_content_hash: str = Field(..., min_length=64, max_length=64, description="Parent document SHA-256")
    chunk_content_hash: str = Field(..., min_length=64, max_length=64, description="Chunk text SHA-256")
    embedding_provider: str = Field(..., min_length=1, description="Embedding provider name")
    embedding_model: str = Field(..., min_length=1, description="Embedding model identifier")
    embedding_dimension: int = Field(..., ge=1, description="Embedding vector dimensionality")
    indexed_at: str = Field(..., min_length=1, description="ISO-8601 UTC timestamp")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_values(cls, v: List[float]) -> List[float]:
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        for idx, val in enumerate(v):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Embedding value at index {idx} is non-numeric: {type(val)}")
            if math.isnan(val):
                raise ValueError(f"Embedding value at index {idx} is NaN")
            if math.isinf(val):
                raise ValueError(f"Embedding value at index {idx} is Infinite")
        return v
