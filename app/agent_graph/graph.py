"""
graph.py — StateGraph Assembly and Invocation for LangGraph Agentic Governance.

Compiles the end-to-end Enterprise AI Governance StateGraph:
- START -> request_router -> governance_check
- Conditional branching based on policy decisions:
    - ALLOW -> (rag_node | tool_execution) -> output_guard -> audit_node -> END
    - DENY  -> safe_denial -> audit_node -> END
    - REVIEW -> hitl_review -> audit_node -> END
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from app.agent_graph.state import AgentGraphState, create_initial_state
from app.agent_graph.nodes.request_router import request_router_node
from app.agent_graph.nodes.governance_check import governance_check_node
from app.agent_graph.nodes.rag_node import rag_node
from app.agent_graph.nodes.tool_execution import tool_execution_node
from app.agent_graph.nodes.safe_denial_node import safe_denial_node
from app.agent_graph.nodes.hitl_review_node import hitl_review_node
from app.agent_graph.nodes.output_guard_node import output_guard_node
from app.agent_graph.nodes.audit_node import audit_node
from app.agent_graph.routing import route_governance_decision
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph")

# Global singleton cached compiled graph
_COMPILED_GRAPH = None


def compile_governance_graph():
    """
    Assembles and compiles the LangGraph StateGraph for enterprise AI governance.
    """
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is not None:
        return _COMPILED_GRAPH

    logger.info("Assembling LangGraph Enterprise Governance StateGraph...")
    builder = StateGraph(AgentGraphState)

    # 1. Register Graph Nodes
    builder.add_node("request_router", request_router_node)
    builder.add_node("governance_check", governance_check_node)
    builder.add_node("rag_node", rag_node)
    builder.add_node("tool_execution", tool_execution_node)
    builder.add_node("safe_denial", safe_denial_node)
    builder.add_node("hitl_review", hitl_review_node)
    builder.add_node("output_guard", output_guard_node)
    builder.add_node("audit_node", audit_node)

    # 2. Add Fixed Edges
    builder.add_edge(START, "request_router")
    builder.add_edge("request_router", "governance_check")

    # 3. Add Conditional Routing from Governance Check
    builder.add_conditional_edges(
        "governance_check",
        route_governance_decision,
        {
            "safe_denial": "safe_denial",
            "hitl_review": "hitl_review",
            "rag_node": "rag_node",
            "tool_execution": "tool_execution",
        },
    )

    # 4. Capability Execution -> Output Safety Guard
    builder.add_edge("rag_node", "output_guard")
    builder.add_edge("tool_execution", "output_guard")

    # 5. Convergence to Immutable Audit Trail -> END
    builder.add_edge("output_guard", "audit_node")
    builder.add_edge("safe_denial", "audit_node")
    builder.add_edge("hitl_review", "audit_node")
    builder.add_edge("audit_node", END)

    compiled = builder.compile()
    _COMPILED_GRAPH = compiled
    logger.info("LangGraph Enterprise Governance StateGraph compiled successfully.")
    return compiled


def run_governance_graph(
    user_request: str,
    access_context: Dict[str, Any],
    request_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> AgentGraphState:
    """
    Executes a user request through the full LangGraph Agentic Governance StateGraph.

    Parameters:
    - user_request: Natural language prompt or task
    - access_context: Authenticated caller credentials (role, clearance_level, department)
    - request_id: Unique request correlation ID

    Returns:
    - Final AgentGraphState containing results, sources, audit reference, and decision status.
    """
    initial_state = create_initial_state(
        user_request=user_request,
        access_context=access_context,
        request_id=request_id,
        conversation_id=conversation_id,
    )

    graph = compile_governance_graph()
    final_state = graph.invoke(initial_state)

    logger.info(
        "LangGraph execution completed",
        extra={
            "request_id": final_state.get("request_id"),
            "decision": final_state.get("governance_decision"),
            "status": final_state.get("status"),
            "audit_ref": final_state.get("audit_reference"),
        },
    )
    return final_state
