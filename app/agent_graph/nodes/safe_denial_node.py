"""
safe_denial_node.py — Safe Refusal Node for LangGraph Agentic Governance.

Formats safe, non-leaking rejection messages for requests denied by policies or RAI guards.
Ensures zero disclosure of restricted document metadata or internal system prompts.
"""
from __future__ import annotations

from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.denial")


def safe_denial_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Constructs a safe denial response without exposing internal security policies or confidential resources.
    """
    request_id = state.get("request_id", "unknown")
    reasons = state.get("decision_reasons") or ["Access criteria not met."]
    error = state.get("error")

    logger.warning("SafeDenial: Formatting refusal", extra={"request_id": request_id, "reasons": reasons})

    primary_reason = reasons[0] if reasons else (error or "Action not authorized.")
    refusal_msg = (
        f"Governance Refusal: This operation cannot be completed. "
        f"Reason: {primary_reason}"
    )

    return {
        "status": "DENIED",
        "governance_decision": "DENY",
        "review_required": False,
        "message": refusal_msg,
        "final_response": refusal_msg,
        "error": primary_reason,
        "tool_result": None,
        "result": {
            "authorized": False,
            "decision": "DENY",
            "reason": primary_reason,
        },
    }
