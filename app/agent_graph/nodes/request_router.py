"""
request_router.py — Request Router Node for LangGraph Agentic Governance.

1. Runs early Responsible AI Input Guard check (prompt injection mitigation).
2. Maps natural language user requests to structured enterprise capabilities:
   - RAG_QUERY (Governance Q&A)
   - RETRIEVAL_SEARCH (Authorized Document Retrieval)
   - APPROVED_TOOL_ACTION (Controlled Operational Execution)
"""
from __future__ import annotations

from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.responsible_ai.input_guard import ResponsibleAIInputGuard, GuardDecision
from app.agents.agent_router import AgentRouter
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.router")


def request_router_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Evaluates incoming request through RAI Input Guard and determines targeted capability.
    """
    user_request = state.get("user_query") or state.get("user_request", "")
    request_id = state.get("request_id", "unknown")

    logger.info("RequestRouter: Evaluating request", extra={"request_id": request_id, "len": len(user_request)})

    # 1. Responsible AI Input Guard validation
    guard = ResponsibleAIInputGuard()
    guard_decision = guard.validate_input(user_request)

    if guard_decision.decision == GuardDecision.BLOCK:
        logger.warning(
            "RequestRouter: Intercepted adversarial or prohibited input",
            extra={"request_id": request_id, "reason": guard_decision.reason},
        )
        reason_msg = f"Responsible AI Block: {guard_decision.reason}"
        refusal_msg = f"Governance Refusal: {reason_msg}"
        return {
            "capability": "UNKNOWN",
            "governance_decision": "DENY",
            "decision_reasons": [reason_msg],
            "governance_result": {
                "decision": "DENY",
                "reasons": [reason_msg],
                "risk_score": 95.0,
                "risk_level": "HIGH",
                "review_required": False,
            },
            "status": "DENIED",
            "review_required": False,
            "error": guard_decision.reason,
            "message": refusal_msg,
            "final_response": refusal_msg,
        }

    sanitized_request = guard_decision.sanitized_text or user_request

    # 2. Capability Resolution via AgentRouter
    router = AgentRouter()
    routing_result = router.route(sanitized_request)
    capability = routing_result.capability

    # Resolve tool if present
    tool_name = None
    try:
        from app.agents.tool_registry import create_default_tool_registry
        registry = create_default_tool_registry()
        tool = registry.get(capability)
        tool_name = tool.name if tool else None
    except Exception:
        tool_name = None

    logger.info(
        "RequestRouter: Capability mapped",
        extra={
            "request_id": request_id,
            "capability": capability,
            "tool": tool_name,
        },
    )

    return {
        "user_query": sanitized_request,
        "user_request": sanitized_request,
        "capability": capability,
        "selected_action": tool_name,
        "tool_parameters": {},
        "status": "ROUTED",
    }
