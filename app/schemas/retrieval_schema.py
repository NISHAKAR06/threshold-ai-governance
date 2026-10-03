"""
retrieval_schema.py — Pydantic schemas validating semantic retrieval API requests and responses.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class RetrievalQueryRequestSchema(BaseModel):
    """Schema validating incoming semantic search query payload."""
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User search query string",
        examples=["What are the requirements for accessing sensitive AI systems?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top relevant chunks to retrieve (1-20)",
    )

    @field_validator("query")
    @classmethod
    def validate_query_not_whitespace(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Search query cannot be empty or whitespace only")
        return cleaned


class RetrievalResultItemSchema(BaseModel):
    """Schema representing a single retrieved, similarity-ranked chunk."""
    rank: int = Field(..., ge=1, description="1-based relevance rank")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    chunk_id: str = Field(..., min_length=1, description="Retrieved chunk identifier")
    document_id: str = Field(..., min_length=1, description="Parent document identifier")
    text: str = Field(..., min_length=1, description="Chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Preserved governance metadata")
    source: Dict[str, Any] = Field(..., description="Source file provenance metadata")
    distance: Optional[float] = Field(default=None, description="Raw vector distance if available")


class RetrievalResponseSchema(BaseModel):
    """Schema validating the complete semantic retrieval response payload."""
    query: str = Field(..., description="The processed search query")
    result_count: int = Field(..., ge=0, description="Total number of retrieved candidates")
    results: List[RetrievalResultItemSchema] = Field(..., description="Ranked list of retrieved chunks")
    execution_time_ms: float = Field(..., ge=0.0, description="End-to-end retrieval latency in milliseconds")
    embedding_provider: Optional[str] = Field(default=None, description="Provider used for query embedding")
    embedding_model: Optional[str] = Field(default=None, description="Model used for query embedding")
