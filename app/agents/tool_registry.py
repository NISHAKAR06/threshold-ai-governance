"""
tool_registry.py — Strict registry of approved, non-dynamic agent tools for Phase 14.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List

from app.agents.tools.base_tool import BaseAgentTool
from app.agents.tools.governance_rag_tool import GovernanceRAGTool
from app.agents.tools.governance_retrieval_tool import GovernanceRetrievalTool
from app.agents.tools.governance_evaluation_tool import GovernanceEvaluationTool
from app.core.exceptions import ToolNotRegisteredError
from app.core.logger import agent_logger


class ToolRegistry:
    """
    Explicit tool registry managing approved tools for the Controlled AI Agent.
    Strictly forbids dynamic code execution or arbitrary tool registration.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseAgentTool] = {}

    def register(
        self,
        identifier: str,
        tool: BaseAgentTool,
        overwrite: bool = False,
    ) -> None:
        """
        Register a tool under a capability or tool identifier.

        Args:
            identifier: Capability name (e.g. RAG_QUESTION) or tool name.
            tool: BaseAgentTool implementation.
            overwrite: If False and identifier is already registered, raises ValueError.
        """
        if not isinstance(tool, BaseAgentTool):
            raise TypeError(f"Registered tool must inherit from BaseAgentTool, got {type(tool).__name__}")

        key = identifier.strip().upper()
        if not key:
            raise ValueError("Tool identifier cannot be empty.")

        if key in self._tools and not overwrite:
            raise ValueError(f"Tool identifier '{key}' is already registered in registry.")

        self._tools[key] = tool
        agent_logger.info(f"ToolRegistry: Registered tool '{tool.name}' under key '{key}'")

    def get(self, identifier: str) -> BaseAgentTool:
        """
        Retrieve a registered tool by capability or name.

        Args:
            identifier: Capability or tool name.

        Returns:
            The registered BaseAgentTool instance.

        Raises:
            ToolNotRegisteredError: If the tool is not registered.
        """
        key = (identifier or "").strip().upper()
        if key not in self._tools:
            agent_logger.error(f"ToolRegistry: Unknown tool lookup requested for '{key}'")
            raise ToolNotRegisteredError(
                f"No approved tool is registered for identifier '{identifier}'. "
                f"Available tools: {list(self._tools.keys())}"
            )
        return self._tools[key]

    def has_tool(self, identifier: str) -> bool:
        """Check if an identifier is registered."""
        return (identifier or "").strip().upper() in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return rich metadata for all registered tools including schemas and permissions."""
        seen_names = set()
        items = []
        for key, tool in self._tools.items():
            if tool.name not in seen_names:
                seen_names.add(tool.name)
                items.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": getattr(tool, "input_schema", {}),
                    "required_permission": getattr(tool, "required_permission", "READ"),
                    "required_clearance": getattr(tool, "required_clearance", "PUBLIC"),
                    "risk_level": getattr(tool, "risk_level", "LOW"),
                    "requires_approval": getattr(tool, "requires_approval", False),
                    "registered_key": key,
                })
        return items


def create_default_tool_registry(
    rag_tool: Optional[GovernanceRAGTool] = None,
    retrieval_tool: Optional[GovernanceRetrievalTool] = None,
    eval_tool: Optional[GovernanceEvaluationTool] = None,
) -> ToolRegistry:
    """
    Construct and return the default standard tool registry for Phase 14.
    """
    registry = ToolRegistry()

    r_tool = rag_tool or GovernanceRAGTool()
    ret_tool = retrieval_tool or GovernanceRetrievalTool()
    e_tool = eval_tool or GovernanceEvaluationTool()

    # Register by capability identifiers
    registry.register("RAG_QUESTION", r_tool)
    registry.register("RETRIEVAL_SEARCH", ret_tool)
    registry.register("GOVERNANCE_EVALUATION", e_tool)

    # Also register by canonical tool names
    registry.register("GOVERNANCERAGTOOL", r_tool)
    registry.register("GOVERNANCERETRIEVALTOOL", ret_tool)
    registry.register("GOVERNANCEEVALUATIONTOOL", e_tool)

    return registry
