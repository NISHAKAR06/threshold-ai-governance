"""
agent.py — API route endpoints for Controlled AI Agent execution in Phase 14.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.logger import get_logger
from app.schemas.agent_schema import AgentExecuteRequestSchema, AgentExecuteResponseSchema
from app.services.agent_service import AgentService
from app.dependencies import get_current_user, require_admin, trusted_access_context

logger = get_logger("threshold.api.agent")

router = APIRouter()


def get_agent_service() -> AgentService:
    """Dependency injection provider for AgentService."""
    return AgentService()


@router.post(
    "/execute",
    response_model=AgentExecuteResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Execute Controlled AI Agent Workflow",
    description=(
        "Executes a controlled, auditable AI agent workflow: validates user prompt and "
        "security context, maps intent to approved capabilities (RAG_QUESTION, RETRIEVAL_SEARCH, "
        "GOVERNANCE_EVALUATION), applies deterministic governance policies and tool authorizations, "
        "executes approved registered tools, validates outputs for safety, generates immutable audit trails, "
        "and returns structured responses."
    ),
)
async def execute_agent(
    payload: AgentExecuteRequestSchema,
    service: AgentService = Depends(get_agent_service),
    current_user: dict = Depends(get_current_user),
) -> AgentExecuteResponseSchema:
    """
    Controlled agent execution endpoint.
    """
    access_context = trusted_access_context(payload.access_context.model_dump(), current_user)
    logger.info(
        "API agent execute invoked",
        extra={
            "user_id": access_context["user_id"],
            "role": access_context["role"],
            "request_len": len(payload.request),
        },
    )

    # ── Phase 15: Responsible AI Input Guard ───────────────────
    from app.responsible_ai.input_guard import ResponsibleAIInputGuard, GuardDecision
    from app.responsible_ai.output_guard import ResponsibleAIOutputGuard
    from app.observability.metrics import record_agent_metrics, record_governance_event
    from app.core.exceptions import (
        PromptInjectionDetectedError,
        ResponsibleAIValidationError,
        OutputGuardValidationError,
    )

    input_guard = ResponsibleAIInputGuard()
    in_res = input_guard.validate_input(payload.request)
    if in_res.decision == GuardDecision.BLOCK:
        if in_res.injection_details and in_res.injection_details.detected:
            raise PromptInjectionDetectedError(in_res.reason)
        raise ResponsibleAIValidationError(in_res.reason)

    # ── Execute Agent Workflow ────────────────────────────────
    response = service.execute(
        request=in_res.sanitized_text or payload.request,
        access_context=access_context,
        request_id=payload.request_id,
        conversation_id=payload.conversation_id,
    )

    # ── Phase 15: Responsible AI Output Guard ──────────────────
    if response.result:
        output_guard = ResponsibleAIOutputGuard()
        out_res = output_guard.validate_agent_output(response.result)
        if not out_res.is_valid:
            record_governance_event("output_validation_failure")
            raise OutputGuardValidationError(
                f"Agent output validation failed: {', '.join(out_res.violations)}"
            )

    # ── Phase 15: Metrics recording ────────────────────────────
    record_agent_metrics(
        status=response.status,
        capability=response.capability or "UNKNOWN",
        duration_seconds=response.execution_time_ms / 1000.0,
    )

    return AgentExecuteResponseSchema(
        request_id=response.request_id,
        status=response.status,
        capability=response.capability,
        result=response.result,
        message=response.message,
        audit_reference=response.audit_reference,
        execution_time_ms=response.execution_time_ms,
    )


@router.get(
    "/audit",
    summary="List Agent Execution Audit Records",
    description="Returns read-only immutable audit records of all Controlled AI Agent workflow executions.",
)
async def list_agent_audit(limit: int = 50, _: dict = Depends(require_admin)):
    """
    Returns recorded agent execution audit trail events.
    """
    records = AgentService.get_audit_records()
    # Return newest first
    items = list(reversed(records))[:limit]
    return {
        "items": items,
        "audit_records": items,
        "total": len(records),
    }


@router.post(
    "/graph/execute",
    response_model=AgentExecuteResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Execute LangGraph Enterprise Governance StateGraph Workflow",
    description=(
        "Orchestrates natural language requests through the LangGraph StateGraph engine: "
        "RAI input guard -> deterministic governance check -> conditional routing "
        "-> (RAG node | Tool execution | Safe denial | HITL review) -> output safety guard -> immutable audit."
    ),
)
async def execute_agent_graph(
    payload: AgentExecuteRequestSchema,
    current_user: dict = Depends(get_current_user),
) -> AgentExecuteResponseSchema:
    """
    Executes a governed request through the LangGraph StateGraph workflow engine.
    """
    from app.agent_graph.graph import run_governance_graph

    access_ctx = trusted_access_context(payload.access_context.model_dump(), current_user)
    final_state = run_governance_graph(
        user_request=payload.request,
        access_context=access_ctx,
        request_id=payload.request_id,
        conversation_id=payload.conversation_id,
    )

    response_text = final_state.get("final_response") or final_state.get("message")
    sources = final_state.get("retrieval_context") or []
    audit_id = final_state.get("audit_reference")

    return AgentExecuteResponseSchema(
        request_id=final_state.get("request_id") or payload.request_id,
        status=final_state.get("status", "COMPLETED"),
        response=response_text,
        sources=sources,
        audit_id=audit_id,
        capability=final_state.get("capability") or "GOVERNANCE_GRAPH",
        result=final_state.get("result"),
        message=final_state.get("message"),
        audit_reference=audit_id,
        execution_time_ms=final_state.get("execution_time_ms", 0.0),
    )
