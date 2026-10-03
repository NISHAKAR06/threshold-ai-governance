"""
routing.py — Conditional Edge Routing Functions for LangGraph Agentic Platform.

Determines the deterministic execution path based on:
1. Responsible AI input guard results
2. Policy evaluation decisions (ALLOW, DENY, REVIEW)
3. Requested enterprise capabilities (RAG_QUERY vs APPROVED_TOOL_ACTION)
"""
from __future__ import annotations

from typing import Literal
from app.agent_graph.state import AgentGraphState
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.routing")


def route_governance_decision(
    state: AgentGraphState,
) -> Literal["safe_denial", "hitl_review", "rag_node", "tool_execution"]:
    """
    Evaluates governance check outcomes and directs the state to:
    - 'safe_denial': If decision is DENY or security policies were violated.
    - 'hitl_review': If high risk or ambiguous action mandates human review.
    - 'rag_node': If decision is ALLOW and capability is RAG / document retrieval.
    - 'tool_execution': If decision is ALLOW and capability is an approved tool.
    """
    decision = state.get("governance_decision", "DENY")
    capability = state.get("capability") or "RAG_QUERY"
    selected_action = state.get("selected_action")

    logger.info(
        "Routing: Evaluating conditional branch",
        extra={
            "request_id": state.get("request_id"),
            "decision": decision,
            "capability": capability,
            "action": selected_action,
        },
    )

    if decision == "DENY":
        return "safe_denial"

    if decision == "REVIEW":
        return "hitl_review"

    # Decision is ALLOW: route to capability execution node
    if capability in ("APPROVED_TOOL_ACTION", "TOOL_EXECUTION") or (
        selected_action and capability not in ("RAG_QUERY", "RAG_QUESTION")
    ):
        return "tool_execution"

    return "rag_node"


def route_capability(state: AgentGraphState) -> Literal["rag_node", "tool_execution", "safe_denial"]:
    """
    Routes directly based on capability classification when governance clearance has been established.
    """
    capability = state.get("capability")
    if capability in ("RAG_QUERY", "RETRIEVAL_SEARCH"):
        return "rag_node"
    elif capability in ("APPROVED_TOOL_ACTION", "TOOL_EXECUTION"):
        return "tool_execution"
    return "safe_denial"
