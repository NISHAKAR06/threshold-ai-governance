"""
governance_rag_tool.py — Agent tool integrating Phase 13 Governance-Aware RAG Answer Generation.
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional

from app.agents.tools.base_tool import BaseAgentTool
from app.models.access_context import AccessContext
from app.models.agent_tool_result import AgentToolResult
from app.services.rag_service import RAGService
from app.core.logger import agent_logger


class GovernanceRAGTool(BaseAgentTool):
    """
    Executes grounded RAG answer generation over authorized governance documents.
    Reuses Phase 13 RAGService directly without duplicating retrieval or LLM logic.
    """

    def __init__(self, rag_service: Optional[RAGService] = None) -> None:
        self._rag_service = rag_service or RAGService()

    @property
    def name(self) -> str:
        return "GovernanceRAGTool"

    @property
    def description(self) -> str:
        return "Answers questions regarding enterprise policies, compliance, and guidelines using grounded RAG."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "User question or inquiry"},
                "top_k": {"type": "integer", "description": "Candidate retrieval count", "default": 5},
            },
            "required": ["question"],
        }

    @property
    def required_permission(self) -> str:
        return "RAG_QUESTION"

    @property
    def required_clearance(self) -> str:
        return "PUBLIC"

    @property
    def risk_level(self) -> str:
        return "LOW"

    @property
    def requires_approval(self) -> bool:
        return False

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        if not isinstance(input_data, dict):
            return False
        question = input_data.get("question") or input_data.get("request")
        return bool(question and isinstance(question, str) and question.strip())

    def execute(
        self,
        input_data: Dict[str, Any],
        access_context: AccessContext,
    ) -> AgentToolResult:
        start_time = time.perf_counter()
        question = (input_data.get("question") or input_data.get("request", "")).strip()
        top_k = input_data.get("top_k")

        agent_logger.info(
            f"GovernanceRAGTool: Executing question (len={len(question)}) for user='{access_context.user_id}'"
        )

        try:
            rag_response = self._rag_service.generate_answer(
                question=question,
                access_context=access_context,
                top_k=top_k,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return AgentToolResult(
                tool_name=self.name,
                success=True,
                output=rag_response.to_dict(),
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            agent_logger.error(f"GovernanceRAGTool: Execution failed: {exc}", exc_info=True)
            return AgentToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )
