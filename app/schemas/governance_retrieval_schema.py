"""
governance_retrieval_schema.py — Pydantic schemas validating hybrid governance search API payloads.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class AccessContextSchema(BaseModel):
    """Schema validating requester access credentials and security context."""
    user_id: str = Field(..., min_length=1, description="Requester user identifier", examples=["USER-001"])
    role: str = Field(..., min_length=1, description="Requester role e.g. EMPLOYEE, SECURITY_ANALYST, ADMIN", examples=["SECURITY_ANALYST"])
    department: Optional[str] = Field(default=None, description="Requester department name", examples=["Information Security"])
    clearance_level: Optional[str] = Field(
        default="INTERNAL",
        description="Clearance level (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED)",
        examples=["CONFIDENTIAL"],
    )

    @field_validator("role", "clearance_level")
    @classmethod
    def normalize_uppercase(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class GovernanceRetrievalRequestSchema(BaseModel):
    """Schema validating incoming hybrid governance retrieval query."""
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User search query string",
        examples=["Who can access sensitive AI model weights and production systems?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Desired number of top authorized chunks to retrieve (1-20)",
    )
    access_context: AccessContextSchema = Field(
        ...,
        description="Identity and access context of the requesting user",
    )

    @field_validator("query")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty or whitespace only")
        return cleaned


class GovernanceRetrievalResultItemSchema(BaseModel):
    """Schema representing an individual authorized, similarity-ranked chunk."""
    rank: int = Field(..., ge=1, description="1-based relevance rank")
    fused_score: float = Field(..., ge=0.0, description="Reciprocal Rank Fusion or hybrid score")
    chunk_id: str = Field(..., min_length=1, description="Unique chunk identifier")
    document_id: str = Field(..., min_length=1, description="Parent document identifier")
    text: str = Field(..., min_length=1, description="Authorized chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Preserved governance metadata")
    source: Dict[str, Any] = Field(..., description="Source file provenance metadata")
    semantic_score: Optional[float] = Field(default=None, description="Score from dense vector retrieval branch")
    keyword_score: Optional[float] = Field(default=None, description="Score from BM25 lexical retrieval branch")


class GovernanceRetrievalResponseSchema(BaseModel):
    """Schema validating the complete hybrid governance retrieval response payload."""
    query: str = Field(..., description="The processed search query")
    requested_top_k: int = Field(..., ge=1, description="Requested top_k value")
    authorized_result_count: int = Field(..., ge=0, description="Number of authorized chunks returned")
    denied_count: int = Field(default=0, ge=0, description="Number of candidate chunks filtered out by governance")
    execution_time_ms: float = Field(..., ge=0.0, description="Total retrieval latency in milliseconds")
    results: List[GovernanceRetrievalResultItemSchema] = Field(..., description="Ranked authorized chunks")
    fusion_strategy: str = Field(default="RRF", description="Fusion algorithm used (e.g. RRF)")
