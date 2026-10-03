"""
agent_schema.py — Pydantic schemas for Controlled AI Agent requests and responses.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.governance_retrieval_schema import AccessContextSchema


class AgentExecuteRequestSchema(BaseModel):
    """Schema validating an incoming agent execution request."""
    request: str = Field(
        ...,
        min_length=2,
        max_length=4000,
        description="Natural language request or task for the controlled AI agent",
        examples=["What is the policy for accessing confidential AI systems?"],
    )
    access_context: AccessContextSchema = Field(
        ...,
        description="Identity and access context of the requesting user",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier for the request",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation identifier (no long-term memory retained)",
    )

    @field_validator("request")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Agent request cannot be empty or whitespace only")
        return cleaned


class AgentExecuteResponseSchema(BaseModel):
    """Schema validating the structured agent response."""
    request_id: str = Field(..., description="Unique request identifier")
    status: str = Field(
        ...,
        description="Execution status: SUCCESS, DENIED, REVIEW_REQUIRED, COMPLETED, allowed, denied, review, or ERROR",
    )
    response: Optional[str] = Field(
        default=None,
        description="Clean structured textual response or refusal message",
    )
    sources: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of authorized citation sources retrieved during execution",
    )
    audit_id: Optional[str] = Field(
        default=None,
        description="Unique audit event correlation identifier",
    )
    capability: Optional[str] = Field(
        default="GOVERNANCE_GRAPH",
        description="Selected capability: RAG_QUESTION, RETRIEVAL_SEARCH, or GOVERNANCE_EVALUATION",
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured tool result when execution succeeds",
    )
    message: Optional[str] = Field(
        default=None,
        description="User-facing explanation message, particularly when denied or reviewing",
    )
    audit_reference: Optional[str] = Field(
        default=None,
        description="Immutable audit event reference identifier",
    )
    execution_time_ms: Optional[float] = Field(
        default=0.0,
        description="Execution time in milliseconds",
    )
