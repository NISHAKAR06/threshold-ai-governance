"""
rag_routes.py — API endpoints for Governance-Aware RAG Answer Generation.

Phase 13: Grounded, source-attributed AI answer generation using authorized retrieval results.
Exposes POST /ask (mounted under /rag and /api/v1/rag).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.logger import get_logger
from app.schemas.rag_schema import (
    RAGRequestSchema,
    RAGResponseSchema,
    RAGSourceSchema,
)
from app.services.rag_service import RAGService
from app.dependencies import get_current_user, trusted_access_context

logger = get_logger("threshold.api.rag")

router = APIRouter()


def get_rag_service() -> RAGService:
    """Dependency provider for RAGService."""
    return RAGService()


@router.post(
    "/ask",
    response_model=RAGResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Governance-Aware RAG Answer Generation",
    description=(
        "Executes a grounded RAG generation pipeline: calls Phase 12 hybrid retrieval, "
        "enforces governance access policies, builds a bounded context with deterministic "
        "source identifiers, prompts the configured LLM, validates output grounding, and "
        "returns source-attributed results."
    ),
)
async def ask_question(
    payload: RAGRequestSchema,
    service: RAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user),
) -> RAGResponseSchema:
    """
    Generate an authorized, grounded answer to an enterprise governance question.
    """
    access_context = trusted_access_context(payload.access_context.model_dump(), current_user)
    logger.info(
        "API RAG ask invoked",
        extra={
            "question_len": len(payload.question or ""),
            "top_k": payload.top_k,
            "user_id": access_context["user_id"],
            "role": access_context["role"],
        },
    )

    # ── Phase 15: Responsible AI Input Guard ───────────────────
    from app.responsible_ai.input_guard import ResponsibleAIInputGuard, GuardDecision
    from app.responsible_ai.output_guard import ResponsibleAIOutputGuard
    from app.observability.metrics import record_rag_metrics, record_governance_event
    from app.core.exceptions import (
        PromptInjectionDetectedError,
        ResponsibleAIValidationError,
        OutputGuardValidationError,
    )

    input_guard = ResponsibleAIInputGuard()
    in_res = input_guard.validate_input(payload.question)
    if in_res.decision == GuardDecision.BLOCK:
        if in_res.injection_details and in_res.injection_details.detected:
            raise PromptInjectionDetectedError(in_res.reason)
        raise ResponsibleAIValidationError(in_res.reason)

    # ── Execute RAG generation ────────────────────────────────
    response = service.generate_answer(
        question=in_res.sanitized_text or payload.question,
        access_context=access_context,
        top_k=payload.top_k,
    )

    # ── Phase 15: Responsible AI Output Guard ──────────────────
    output_guard = ResponsibleAIOutputGuard()
    out_res = output_guard.validate_rag_output(
        answer=response.answer,
        authorized_sources=[s.__dict__ for s in response.sources],
    )
    if not out_res.is_valid:
        record_governance_event("output_validation_failure")
        raise OutputGuardValidationError(
            f"Response output validation failed: {', '.join(out_res.violations)}"
        )

    # ── Phase 15: Metrics recording ────────────────────────────
    record_rag_metrics(
        status=response.status,
        chunks_used=len(response.sources),
        duration_seconds=response.execution_time_ms / 1000.0,
    )

    return RAGResponseSchema(
        question=response.question,
        answer=response.answer,
        status=response.status,
        sources=[
            RAGSourceSchema(
                source_id=s.source_id,
                document_id=s.document_id,
                chunk_id=s.chunk_id,
                document_type=s.document_type,
                source_reference=s.source_reference,
                classification=s.classification,
                department=s.department,
                fused_score=s.fused_score,
                is_cited=s.is_cited,
            )
            for s in response.sources
        ],
        retrieval_metadata=response.retrieval_metadata,
        execution_time_ms=response.execution_time_ms,
        model_used=response.model_used,
        provider_used=response.provider_used,
    )
