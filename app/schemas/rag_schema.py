"""
rag_schema.py — Pydantic schemas validating incoming RAG requests and structured responses.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.governance_retrieval_schema import AccessContextSchema


class RAGRequestSchema(BaseModel):
    """Schema validating an incoming governance-aware RAG question payload."""
    question: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User question regarding enterprise governance, policies, or operations",
        examples=["What are the requirements for accessing confidential AI systems?"],
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of candidate chunks to retrieve from the hybrid governance index",
    )
    access_context: AccessContextSchema = Field(
        ...,
        description="Identity and access context of the requesting user",
    )

    @field_validator("question")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or whitespace only")
        return cleaned


class RAGSourceSchema(BaseModel):
    """Schema representing an individual authorized source cited in the RAG answer."""
    source_id: str = Field(..., description="Deterministic source label, e.g. SOURCE_1")
    document_id: str = Field(..., description="Parent document identifier, e.g. SEC-001")
    chunk_id: str = Field(..., description="Unique chunk identifier, e.g. SEC-001_CHUNK_0001")
    document_type: str = Field(default="DOCUMENT", description="Governance document type")
    source_reference: str = Field(default="", description="Provenance reference e.g. file path or title")
    classification: Optional[str] = Field(default=None, description="Document data classification")
    department: Optional[str] = Field(default=None, description="Document owning department")
    fused_score: Optional[float] = Field(default=None, description="Hybrid retrieval fusion score")
    is_cited: bool = Field(default=False, description="Whether this source was cited in the generated answer text")


class RAGRetrievalMetadataSchema(BaseModel):
    """Schema describing retrieval execution statistics and context utilization."""
    authorized_result_count: int = Field(default=0, description="Total authorized chunks retrieved by Phase 12")
    context_chunks_used: int = Field(default=0, description="Authorized chunks fitting into the LLM context budget")
    denied_count: int = Field(default=0, description="Chunks filtered out by governance access checks")
    fusion_strategy: Optional[str] = Field(default="RRF", description="Hybrid fusion algorithm used")


class RAGResponseSchema(BaseModel):
    """Schema validating the complete structured RAG response payload."""
    question: str = Field(..., description="The original or normalized user question")
    answer: str = Field(..., description="Grounded, source-attributed answer text")
    status: str = Field(..., description="Response status: SUCCESS, INSUFFICIENT_CONTEXT, or ERROR")
    sources: List[RAGSourceSchema] = Field(default_factory=list, description="Authorized context sources")
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata on retrieval and context")
    execution_time_ms: float = Field(..., description="End-to-end processing latency in milliseconds")
    model_used: Optional[str] = Field(default=None, description="LLM model identifier used for generation")
    provider_used: Optional[str] = Field(default=None, description="LLM provider name (e.g. gemini, mock)")
