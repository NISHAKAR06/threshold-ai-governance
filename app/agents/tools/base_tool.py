"""
base_tool.py — Base interface for all controlled agent tools in Phase 14.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.models.access_context import AccessContext
from app.models.agent_tool_result import AgentToolResult


class BaseAgentTool(ABC):
    """
    Abstract interface for registered agent tools.
    Enforces strict input validation, isolated dependencies, and standardized results.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the tool capability."""
        pass

    @property
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema defining the accepted input payload."""
        return {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Operational prompt or query string"}
            },
            "required": ["request"],
        }

    @property
    def required_permission(self) -> str:
        """Specific permission string required to execute this tool."""
        return "READ"

    @property
    def required_clearance(self) -> str:
        """Minimum clearance level required: PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED."""
        return "PUBLIC"

    @property
    def risk_level(self) -> str:
        """Risk evaluation rating: LOW, MEDIUM, or HIGH."""
        return "LOW"

    @property
    def requires_approval(self) -> bool:
        """Whether this tool mandates explicit human review prior to execution."""
        return False

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input payload before tool execution.

        Args:
            input_data: Tool arguments and query parameters.

        Returns:
            True if input is valid; False otherwise.
        """
        pass

    @abstractmethod
    def execute(
        self,
        input_data: Dict[str, Any],
        access_context: AccessContext,
    ) -> AgentToolResult:
        """
        Execute tool logic under the caller's AccessContext.

        Args:
            input_data: Validated parameters for the tool.
            access_context: Verified security credentials of the caller.

        Returns:
            AgentToolResult containing execution status, output data, and error message if any.
        """
        pass
