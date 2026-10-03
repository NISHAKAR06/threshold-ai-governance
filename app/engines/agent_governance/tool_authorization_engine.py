"""
tool_authorization_engine.py — Pre-execution authorization engine for agent tools in Phase 14.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Set

from app.config import settings
from app.models.access_context import AccessContext
from app.models.agent_decision import AgentPolicyDecision, ToolAuthDecision
from app.core.logger import engine_logger


class ToolAuthorizationEngine:
    """
    Evaluates whether a requested tool is permitted to execute given the caller's AccessContext
    and the preceding PolicyDecisionEngine verdict.
    Guarantees that unauthorized or denied tools can NEVER execute.
    """

    # Tool capability mappings
    TOOL_CAPABILITY_MAP: Dict[str, str] = {
        "GovernanceRAGTool": "RAG_QUESTION",
        "GovernanceRetrievalTool": "RETRIEVAL_SEARCH",
        "GovernanceEvaluationTool": "GOVERNANCE_EVALUATION",
    }

    # Minimum clearance level mapping
    MIN_CLEARANCE: Dict[str, int] = {
        "PUBLIC": 1,
        "INTERNAL": 2,
        "CONFIDENTIAL": 3,
        "RESTRICTED": 4,
    }

    def __init__(self, enabled_tools: Optional[List[str]] = None) -> None:
        self.enabled_tools: Set[str] = set(
            enabled_tools if enabled_tools is not None else settings.AGENT_ENABLED_TOOLS
        )

    def authorize_tool(
        self,
        tool_name: str,
        access_context: AccessContext,
        policy_decision: AgentPolicyDecision,
        capability: Optional[str] = None,
    ) -> ToolAuthDecision:
        """
        Determine if the tool execution is authorized.

        Args:
            tool_name: Name of the registered tool to be executed.
            access_context: Security context of the requesting principal.
            policy_decision: Verdict produced by PolicyDecisionEngine.
            capability: Optional capability identifier (e.g. RAG_QUESTION).

        Returns:
            ToolAuthDecision: is_authorized=True only if all checks pass.
        """
        # 1. Enforce prior policy decision
        if policy_decision.is_denied:
            engine_logger.warning(
                f"ToolAuthorizationEngine: Tool '{tool_name}' DENIED due to policy block: {policy_decision.reason}"
            )
            return ToolAuthDecision(
                tool_name=tool_name,
                is_authorized=False,
                status="DENY",
                reason=f"Policy decision blocked tool execution: {policy_decision.reason}",
            )

        if policy_decision.requires_review:
            engine_logger.info(
                f"ToolAuthorizationEngine: Tool '{tool_name}' requires human review: {policy_decision.reason}"
            )
            return ToolAuthDecision(
                tool_name=tool_name,
                is_authorized=False,
                status="REQUIRES_REVIEW",
                reason=f"Tool execution halted pending human compliance review: {policy_decision.reason}",
            )

        # 2. Check if tool is enabled in system configuration
        resolved_cap = capability or self.TOOL_CAPABILITY_MAP.get(tool_name, tool_name)
        if (
            tool_name not in self.enabled_tools
            and resolved_cap not in self.enabled_tools
            and "*" not in self.enabled_tools
        ):
            engine_logger.warning(
                f"ToolAuthorizationEngine: Tool '{tool_name}' is not in configured AGENT_ENABLED_TOOLS"
            )
            return ToolAuthDecision(
                tool_name=tool_name,
                is_authorized=False,
                status="DENY",
                reason=f"Tool '{tool_name}' is currently disabled in system governance configuration.",
            )

        # 3. Access Context Validation
        if not access_context:
            return ToolAuthDecision(
                tool_name=tool_name,
                is_authorized=False,
                status="DENY",
                reason="Missing or invalid access credentials.",
            )

        role = (access_context.role or "").strip().upper()
        if not role:
            return ToolAuthDecision(
                tool_name=tool_name,
                is_authorized=False,
                status="DENY",
                reason="User role is unspecified.",
            )

        # 4. Tool-specific authorization checks
        user_clearance = (access_context.clearance_level or "PUBLIC").strip().upper()
        user_rank = self.MIN_CLEARANCE.get(user_clearance, 1)

        if tool_name == "GovernanceEvaluationTool":
            # Evaluation tool requires at least INTERNAL clearance
            if user_rank < self.MIN_CLEARANCE["INTERNAL"] and not access_context.is_admin:
                return ToolAuthDecision(
                    tool_name=tool_name,
                    is_authorized=False,
                    status="DENY",
                    reason="Governance evaluation tool requires clearance level INTERNAL or higher.",
                )

        engine_logger.debug(
            f"ToolAuthorizationEngine: Tool '{tool_name}' AUTHORIZED for user='{access_context.user_id}'"
        )
        return ToolAuthDecision(
            tool_name=tool_name,
            is_authorized=True,
            status="ALLOW",
            reason="Tool execution authorized.",
        )
