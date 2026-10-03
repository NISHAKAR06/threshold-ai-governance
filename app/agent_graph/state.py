"""
state.py — Typed Graph State Definition for LangGraph Agentic Governance.

Defines the authoritative state dictionary passed through the StateGraph nodes.
Strictly prohibits storing API keys, secrets, raw prompt templates, or internal chain-of-thought.
"""
from __future__ import annotations

from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentGraphState(TypedDict, total=False):
    """
    Typed graph state passed between nodes in the LangGraph enterprise governance orchestrator.
    Contains strictly the execution context, governance evaluations, tool results, and audit trails.
    """
    # Core state parameters required by governance specification
    request_id: str
    user_id: str
    user_role: str
    user_query: str
    governance_result: Dict[str, Any]
    retrieval_context: List[Dict[str, Any]]
    selected_action: Optional[str]
    tool_result: Optional[Any]
    final_response: Optional[str]
    review_required: bool
    error: Optional[str]
    audit_metadata: Dict[str, Any]

    # Additional execution attributes for system integration and backward compatibility
    access_context: Dict[str, Any]
    user_request: str
    capability: Optional[str]
    risk_score: float
    risk_level: str
    governance_decision: str  # ALLOW, DENY, REVIEW
    decision_reasons: List[str]
    tool_parameters: Dict[str, Any]
    result: Optional[Any]
    message: Optional[str]
    output_violations: List[str]
    audit_reference: Optional[str]
    execution_time_ms: float
    status: str  # INITIALIZED, ROUTED, GOVERNED, COMPLETED, DENIED, PENDING_REVIEW, INSUFFICIENT_CONTEXT, ERROR


def create_initial_state(
    user_request: str,
    access_context: Dict[str, Any],
    request_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> AgentGraphState:
    """
    Factory function creating an initial, sanitized AgentGraphState.
    """
    import uuid
    req_id = request_id or f"req_graph_{uuid.uuid4().hex[:12]}"
    user_id = str(access_context.get("user_id", "ANONYMOUS"))
    user_role = str(access_context.get("role", "GUEST")).upper()
    query = user_request.strip()

    return {
        # Core specification fields
        "request_id": req_id,
        "user_id": user_id,
        "user_role": user_role,
        "user_query": query,
        "governance_result": {
            "decision": "PENDING",
            "reasons": [],
            "risk_score": 0.0,
            "risk_level": "LOW",
            "review_required": False,
        },
        "retrieval_context": [],
        "selected_action": None,
        "tool_result": None,
        "final_response": None,
        "review_required": False,
        "error": None,
        "audit_metadata": {},

        # Compatibility fields
        "user_request": query,
        "access_context": dict(access_context),
        "capability": None,
        "risk_score": 0.0,
        "risk_level": "LOW",
        "governance_decision": "PENDING",
        "decision_reasons": [],
        "tool_parameters": {},
        "result": None,
        "message": None,
        "output_violations": [],
        "audit_reference": None,
        "execution_time_ms": 0.0,
        "status": "INITIALIZED",
    }
