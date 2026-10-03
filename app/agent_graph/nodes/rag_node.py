"""
rag_node.py — Governance-Aware RAG Execution Node for LangGraph.

Executes hybrid semantic+keyword retrieval and source-grounded answer generation
via the existing RAGService. Strictly ensures unauthorized documents never enter the context.
"""
from __future__ import annotations

import time
from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.services.rag_service import RAGService
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.rag_node")


def rag_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Executes grounded RAG generation using authorized candidate chunks.
    Ensures unauthorized requests or chunks never reach generation.
    """
    start_time = time.monotonic()
    request_id = state.get("request_id", "unknown")
    question = state.get("user_query") or state.get("user_request", "")
    access_context = state.get("access_context") or {}
    params = state.get("tool_parameters") or {}
    gov_decision = state.get("governance_decision", "DENY")
    top_k = params.get("top_k", 5)

    if gov_decision != "ALLOW":
        logger.error(
            "RAGNode: Blocked unauthorized execution attempt",
            extra={"request_id": request_id, "decision": gov_decision},
        )
        return {
            "result": None,
            "tool_result": None,
            "error": "Governance clearance denied for RAG execution.",
            "status": "DENIED",
            "message": "Governance Refusal: Unauthorized document retrieval.",
            "final_response": "Governance Refusal: Unauthorized document retrieval.",
            "execution_time_ms": (time.monotonic() - start_time) * 1000.0,
        }

    logger.info("RAGNode: Generating grounded answer", extra={"request_id": request_id, "top_k": top_k})

    service = RAGService()
    rag_response = service.generate_answer(
        question=question,
        access_context=access_context,
        top_k=top_k,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000.0

    sources = [
        {
            "source_id": s.source_id,
            "document_id": s.document_id,
            "chunk_id": s.chunk_id,
            "classification": s.classification,
            "department": s.department,
            "fused_score": s.fused_score,
            "is_cited": s.is_cited,
        }
        for s in rag_response.sources
    ]

    result_payload = {
        "answer": rag_response.answer,
        "status": rag_response.status,
        "sources": sources,
        "retrieval_metadata": rag_response.retrieval_metadata,
        "model_used": rag_response.model_used,
        "provider_used": rag_response.provider_used,
    }

    if rag_response.status == "INSUFFICIENT_CONTEXT":
        exec_status = "INSUFFICIENT_CONTEXT"
    elif rag_response.status == "ERROR":
        exec_status = "ERROR"
    else:
        exec_status = "COMPLETED"

    return {
        "result": result_payload,
        "tool_result": result_payload,
        "message": rag_response.answer,
        "final_response": rag_response.answer,
        "retrieval_context": sources,
        "status": exec_status,
        "execution_time_ms": elapsed_ms,
    }
