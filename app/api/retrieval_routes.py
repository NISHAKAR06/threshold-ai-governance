"""
retrieval_routes.py — Semantic Retrieval API endpoints.

Phase 11: Pure semantic retrieval over enterprise chunks.
Exposes POST /search (and mounted under /api/v1/retrieval and /retrieval).
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status

from app.core.logger import get_logger
from app.schemas.retrieval_schema import RetrievalQueryRequestSchema, RetrievalResponseSchema
from app.services.retrieval_service import RetrievalService

logger = get_logger("threshold.api.retrieval")

router = APIRouter()


def get_retrieval_service() -> RetrievalService:
    """Dependency provider for RetrievalService."""
    return RetrievalService()


@router.post(
    "/search",
    response_model=RetrievalResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Semantic Retrieval Search",
    description=(
        "Executes a pure semantic similarity search over indexed document chunks. "
        "Returns ranked chunks with full governance metadata, source traceability, and similarity scores."
    ),
)
async def semantic_search(
    payload: RetrievalQueryRequestSchema,
    service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponseSchema:
    """
    Search indexed knowledge base chunks using semantic query embeddings.
    """
    logger.info(
        "API semantic search invoked",
        extra={"query_len": len(payload.query or ""), "top_k": payload.top_k},
    )

    response = service.retrieve(
        query=payload.query,
        top_k=payload.top_k,
    )

    # Convert dataclass to Pydantic schema model
    return RetrievalResponseSchema(
        query=response.query,
        result_count=response.result_count,
        results=[
            {
                "rank": r.rank,
                "score": r.score,
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "text": r.text,
                "metadata": r.metadata,
                "source": r.source,
                "embedding_model": r.embedding_model,
                "embedding_provider": r.embedding_provider,
            }
            for r in response.results
        ],
        execution_time_ms=response.execution_time_ms,
        embedding_model=response.embedding_model,
        embedding_provider=response.embedding_provider,
    )


# ── Phase 12: Hybrid Search & Governance-Aware Retrieval ───────
from app.schemas.governance_retrieval_schema import (
    GovernanceRetrievalRequestSchema,
    GovernanceRetrievalResponseSchema,
    GovernanceRetrievalResultItemSchema,
)
from app.services.hybrid_retrieval_service import HybridRetrievalService


def get_hybrid_retrieval_service() -> HybridRetrievalService:
    """Dependency provider for HybridRetrievalService."""
    return HybridRetrievalService()


@router.post(
    "/governance-search",
    response_model=GovernanceRetrievalResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Hybrid Search + Governance-Aware Retrieval",
    description=(
        "Executes parallel semantic + BM25 keyword retrieval, fuses candidate chunks via RRF, "
        "and authorizes results against the requester's role, clearance level, and department."
    ),
)
async def governance_search(
    payload: GovernanceRetrievalRequestSchema,
    service: HybridRetrievalService = Depends(get_hybrid_retrieval_service),
) -> GovernanceRetrievalResponseSchema:
    """
    Search indexed knowledge base chunks using hybrid retrieval and governance filtering.
    """
    logger.info(
        "API governance search invoked",
        extra={
            "query_len": len(payload.query or ""),
            "top_k": payload.top_k,
            "user_id": payload.access_context.user_id,
            "role": payload.access_context.role,
        },
    )

    response = service.retrieve(
        query=payload.query,
        access_context=payload.access_context.model_dump(),
        top_k=payload.top_k,
    )

    return GovernanceRetrievalResponseSchema(
        query=response.query,
        requested_top_k=response.requested_top_k,
        authorized_result_count=response.authorized_result_count,
        denied_count=response.denied_count,
        execution_time_ms=response.execution_time_ms,
        fusion_strategy=response.fusion_strategy,
        results=[
            GovernanceRetrievalResultItemSchema(
                rank=r.rank,
                fused_score=r.fused_score,
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                metadata=r.metadata,
                source=r.source,
                semantic_score=r.semantic_score,
                keyword_score=r.keyword_score,
            )
            for r in response.results
        ],
    )
