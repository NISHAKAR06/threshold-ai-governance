"""
governance_retrieval_tool.py — Agent tool integrating Phase 12 Hybrid Search + Governance-Aware Retrieval.
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional

from app.agents.tools.base_tool import BaseAgentTool
from app.models.access_context import AccessContext
from app.models.agent_tool_result import AgentToolResult
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.core.logger import agent_logger


class GovernanceRetrievalTool(BaseAgentTool):
    """
    Executes hybrid semantic and keyword retrieval over indexed policy documents.
    Reuses Phase 12 HybridRetrievalService directly with role, clearance, and department checks.
    """

    def __init__(self, retrieval_service: Optional[HybridRetrievalService] = None) -> None:
        self._retrieval_service = retrieval_service or HybridRetrievalService()

    @property
    def name(self) -> str:
        return "GovernanceRetrievalTool"

    @property
    def description(self) -> str:
        return "Searches and retrieves authorized policy chunks using hybrid semantic and keyword search."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for policy chunks"},
                "top_k": {"type": "integer", "description": "Candidate retrieval count", "default": 5},
            },
            "required": ["query"],
        }

    @property
    def required_permission(self) -> str:
        return "RETRIEVAL_SEARCH"

    @property
    def required_clearance(self) -> str:
        return "INTERNAL"

    @property
    def risk_level(self) -> str:
        return "LOW"

    @property
    def requires_approval(self) -> bool:
        return False

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        if not isinstance(input_data, dict):
            return False
        query = input_data.get("query") or input_data.get("request")
        return bool(query and isinstance(query, str) and query.strip())

    def execute(
        self,
        input_data: Dict[str, Any],
        access_context: AccessContext,
    ) -> AgentToolResult:
        start_time = time.perf_counter()
        query = (input_data.get("query") or input_data.get("request", "")).strip()
        top_k = input_data.get("top_k")

        agent_logger.info(
            f"GovernanceRetrievalTool: Executing retrieval (query_len={len(query)}) for user='{access_context.user_id}'"
        )

        try:
            retrieval_response = self._retrieval_service.retrieve(
                query=query,
                access_context=access_context,
                top_k=top_k,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return AgentToolResult(
                tool_name=self.name,
                success=True,
                output=retrieval_response.to_dict(),
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            agent_logger.error(f"GovernanceRetrievalTool: Execution failed: {exc}", exc_info=True)
            return AgentToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )
