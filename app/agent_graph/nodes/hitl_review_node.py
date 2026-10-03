"""
hitl_review_node.py — Human-in-the-Loop (HITL) Escalation Node for LangGraph.

Routes high-risk or ambiguous requests to the existing Human-in-the-Loop review system.
Guarantees that actions flagged for review are NEVER executed autonomously.
"""
from __future__ import annotations

import uuid
from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.hitl")


def hitl_review_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Escalates operational request to human reviewers and halts automated execution.
    """
    request_id = state.get("request_id", "unknown")
    tool_name = state.get("selected_action") or "OPERATIONAL_ACTION"
    reasons = state.get("decision_reasons") or ["Action exceeds automated autonomy threshold."]
    risk_score = state.get("risk_score", 65.0)

    review_id = f"REV-GRAPH-{uuid.uuid4().hex[:8].upper()}"

    logger.warning(
        "HITLReview: Request escalated to human review",
        extra={
            "request_id": request_id,
            "review_id": review_id,
            "action": tool_name,
            "risk_score": risk_score,
        },
    )

    reason_text = reasons[0] if reasons else "Mandatory human review threshold triggered."
    message = (
        f"Governance Escalation: This action ({tool_name}) requires Human-in-the-Loop approval. "
        f"Review Ticket '{review_id}' has been dispatched to administrators."
    )

    return {
        "status": "PENDING_REVIEW",
        "governance_decision": "REVIEW",
        "review_required": True,
        "message": message,
        "final_response": message,
        "tool_result": None,
        "result": {
            "review_required": True,
            "review_id": review_id,
            "action": tool_name,
            "risk_score": risk_score,
            "reasons": reasons,
            "status": "PENDING_APPROVAL",
        },
    }
