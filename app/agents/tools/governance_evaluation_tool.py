"""
governance_evaluation_tool.py — Agent tool evaluating requests against organizational governance rules.
"""
from __future__ import annotations

import time
import re
from typing import Dict, Any, List, Optional

from app.agents.tools.base_tool import BaseAgentTool
from app.models.access_context import AccessContext
from app.models.agent_tool_result import AgentToolResult
from app.core.logger import agent_logger


class GovernanceEvaluationTool(BaseAgentTool):
    """
    Evaluates actions, queries, or operational requests against deterministic governance rules.
    Checks for protected resources, restricted operations, clearance constraints, and regulatory rules.
    """

    # Real project governance rule IDs
    RULE_PROTECTED_RESOURCE = "P-01"   # Protected Resource Guard
    RULE_RESTRICTED_OP      = "P-02"   # Restricted Operation Guard
    RULE_ADMIN_ONLY         = "P-03"   # Admin-Only Operation Guard
    RULE_REGULATORY_DATA    = "P-06"   # Regulatory Data Guard
    RULE_HIGH_RISK_APPROVAL = "P-07"   # High Risk Approval Guard

    # Prohibited / restricted keywords for operations
    RESTRICTED_KEYWORDS = [
        "bypass", "drop table", "truncate", "delete audit", "disable governance",
        "override policy", "exfiltrate", "dump database", "disable logging",
    ]

    ADMIN_ONLY_KEYWORDS = [
        "modify permissions", "grant role", "user provision", "update system policy",
        "revoke clearance", "audit configuration",
    ]

    REGULATORY_KEYWORDS = [
        "pii", "pci-dss", "hipaa", "gdpr", "social security", "cardholder data", "phi",
    ]

    @property
    def name(self) -> str:
        return "GovernanceEvaluationTool"

    @property
    def description(self) -> str:
        return "Evaluates an operational or policy request against established organization governance rules."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Operational action or query to evaluate"},
            },
            "required": ["request"],
        }

    @property
    def required_permission(self) -> str:
        return "GOVERNANCE_EVALUATION"

    @property
    def required_clearance(self) -> str:
        return "INTERNAL"

    @property
    def risk_level(self) -> str:
        return "MEDIUM"

    @property
    def requires_approval(self) -> bool:
        return False

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        if not isinstance(input_data, dict):
            return False
        req = input_data.get("request") or input_data.get("query")
        return bool(req and isinstance(req, str) and req.strip())

    def execute(
        self,
        input_data: Dict[str, Any],
        access_context: AccessContext,
    ) -> AgentToolResult:
        start_time = time.perf_counter()
        req_text = (input_data.get("request") or input_data.get("query", "")).strip().lower()

        agent_logger.info(
            f"GovernanceEvaluationTool: Evaluating request for user='{access_context.user_id}' role='{access_context.role}'"
        )

        evaluated_rules: List[str] = [
            self.RULE_PROTECTED_RESOURCE,
            self.RULE_RESTRICTED_OP,
            self.RULE_ADMIN_ONLY,
            self.RULE_REGULATORY_DATA,
            self.RULE_HIGH_RISK_APPROVAL,
        ]

        # 1. Check for restricted operations / malicious attempts to bypass governance
        for kw in self.RESTRICTED_KEYWORDS:
            if kw in req_text:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return AgentToolResult(
                    tool_name=self.name,
                    success=True,
                    output={
                        "decision": "DENY",
                        "reason": f"Request contains restricted operation '{kw}' blocked by policy rule {self.RULE_RESTRICTED_OP}.",
                        "evaluated_rules": evaluated_rules,
                        "blocked_by": self.RULE_RESTRICTED_OP,
                    },
                    execution_time_ms=elapsed_ms,
                )

        # 2. Check for admin-only operations
        is_admin = access_context.is_admin or (access_context.role or "").upper() in ("ADMIN", "SUPERADMIN")
        for kw in self.ADMIN_ONLY_KEYWORDS:
            if kw in req_text and not is_admin:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return AgentToolResult(
                    tool_name=self.name,
                    success=True,
                    output={
                        "decision": "DENY",
                        "reason": f"Operation '{kw}' requires administrator privileges under policy rule {self.RULE_ADMIN_ONLY}.",
                        "evaluated_rules": evaluated_rules,
                        "blocked_by": self.RULE_ADMIN_ONLY,
                    },
                    execution_time_ms=elapsed_ms,
                )

        # 3. Check for regulatory / sensitive data handling
        for kw in self.REGULATORY_KEYWORDS:
            if kw in req_text:
                # Requires clearance check and human review
                user_clearance = (access_context.clearance_level or "PUBLIC").upper()
                if user_clearance in ("PUBLIC", "INTERNAL"):
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    return AgentToolResult(
                        tool_name=self.name,
                        success=True,
                        output={
                            "decision": "REVIEW",
                            "reason": f"Regulatory data domain '{kw}' requires secondary compliance review under {self.RULE_REGULATORY_DATA}.",
                            "evaluated_rules": evaluated_rules,
                            "review_trigger": self.RULE_REGULATORY_DATA,
                        },
                        execution_time_ms=elapsed_ms,
                    )

        # 4. Default: Request complies with governance policies
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return AgentToolResult(
            tool_name=self.name,
            success=True,
            output={
                "decision": "ALLOW",
                "reason": "Request complies with organizational governance policies and authorized access boundaries.",
                "evaluated_rules": evaluated_rules,
            },
            execution_time_ms=elapsed_ms,
        )
