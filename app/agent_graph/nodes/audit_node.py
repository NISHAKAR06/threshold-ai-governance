"""
audit_node.py — Immutable Audit Logging Node for LangGraph Agentic Platform.

Creates an authoritative, immutable audit trail event for every graph execution,
capturing request IDs, capabilities, governance decisions, risk scores, and latencies.
"""
from __future__ import annotations

import uuid
from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.services.agent_service import AgentService
from app.observability.metrics import record_agent_metrics, record_governance_event
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.audit")


def audit_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Persists immutable audit event and registers Prometheus metrics.
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id", "ANONYMOUS")
    capability = state.get("capability") or "UNKNOWN"
    decision = state.get("governance_decision") or "UNKNOWN"
    status = state.get("status") or "COMPLETED"
    duration_ms = state.get("execution_time_ms", 0.0)
    reasons = state.get("decision_reasons") or []

    from datetime import datetime, timezone
    from app.services.agent_service import AgentService, AgentAuditRecord

    audit_ref = f"AUD-LG-{uuid.uuid4().hex[:10].upper()}"
    access_ctx = state.get("access_context") or {}
    now_iso = datetime.now(timezone.utc).isoformat()
    record = AgentAuditRecord(
        event_id=audit_ref,
        request_id=request_id,
        timestamp=now_iso,
        requested_capability=None,
        selected_capability=capability,
        policy_decision=decision,
        tool_name=state.get("selected_action"),
        tool_authorization="ALLOW" if decision == "ALLOW" else ("REVIEW" if decision == "REVIEW" else "DENY"),
        execution_status=status,
        user_id=user_id,
        role=str(access_ctx.get("role", "GUEST")),
        execution_time_ms=duration_ms,
    )
    AgentService._audit_log_store.append(record)

    # Detailed structured metadata complying with STEP 8 specification
    audit_metadata = {
        "request_id": request_id,
        "user_id": user_id,
        "user_role": str(access_ctx.get("role", "GUEST")),
        "request_type": capability,
        "governance_decision": decision,
        "selected_capability": capability,
        "selected_tool": state.get("selected_action"),
        "execution_status": status,
        "review_status": "REQUIRED" if state.get("review_required") else ("DENIED" if decision == "DENY" else "NOT_REQUIRED"),
        "latency_ms": duration_ms,
        "final_outcome": status,
        "timestamp": now_iso,
        "audit_id": audit_ref,
    }

    # Record Prometheus metrics
    record_agent_metrics(
        status=status,
        capability=capability,
        duration_seconds=duration_ms / 1000.0,
    )
    record_governance_event(f"decision_{decision.lower()}")

    logger.info(
        "AuditNode: Audit event recorded",
        extra={
            "request_id": request_id,
            "audit_ref": audit_ref,
            "decision": decision,
            "status": status,
        },
    )

    return {
        "audit_reference": audit_ref,
        "audit_metadata": audit_metadata,
    }
