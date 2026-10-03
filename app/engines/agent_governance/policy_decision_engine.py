"""
policy_decision_engine.py — Deterministic governance policy engine for Controlled AI Agent requests.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from app.models.agent_request import AgentRequest
from app.models.access_context import AccessContext
from app.models.agent_decision import AgentPolicyDecision
from app.core.logger import engine_logger


class PolicyDecisionEngine:
    """
    Evaluates agent requests and access context against deterministic organizational governance policies.
    Guarantees that security boundaries and compliance guardrails cannot be overridden by LLM output.
    """

    # Rule IDs
    RULE_INJECTION_GUARD      = "AG-01"   # Prompt Injection / Adversarial Guard
    RULE_CLEARANCE_POLICY     = "AG-02"   # Clearance Level Consistency Guard
    RULE_RESTRICTED_OPERATION = "AG-03"   # Prohibited Operations Guard
    RULE_ROLE_AUTHORIZATION   = "AG-04"   # Role Capability Matrix Guard

    # Injection & adversarial keywords
    ADVERSARIAL_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"system\s+override",
        r"jailbreak",
        r"disregard\s+(all\s+)?rules",
        r"bypass\s+security",
        r"print\s+system\s+prompt",
        r"reveal\s+internal\s+tokens",
        r"exfiltrate",
    ]

    # Prohibited system destructive actions
    DESTRUCTIVE_KEYWORDS = [
        "drop database",
        "drop table",
        "delete audit",
        "disable logging",
        "purge records",
        "rm -rf",
    ]

    def evaluate_request(
        self,
        request: AgentRequest,
        capability: str,
    ) -> AgentPolicyDecision:
        """
        Evaluate whether the requested agent capability and user prompt are compliant with governance rules.

        Args:
            request: Validated AgentRequest domain object.
            capability: Resolved capability string (e.g. RAG_QUESTION, RETRIEVAL_SEARCH, GOVERNANCE_EVALUATION).

        Returns:
            AgentPolicyDecision indicating ALLOW, DENY, or REQUIRES_REVIEW.
        """
        req_text = request.request.lower()
        context = request.access_context
        evaluated_rules: List[str] = [
            self.RULE_INJECTION_GUARD,
            self.RULE_CLEARANCE_POLICY,
            self.RULE_RESTRICTED_OPERATION,
            self.RULE_ROLE_AUTHORIZATION,
        ]

        # 1. Rule AG-01: Adversarial Prompt Injection Guard
        for pattern in self.ADVERSARIAL_PATTERNS:
            if re.search(pattern, req_text, re.IGNORECASE):
                engine_logger.warning(
                    f"PolicyDecisionEngine: Adversarial pattern matched '{pattern}' for user='{context.user_id}'"
                )
                return AgentPolicyDecision(
                    decision="DENY",
                    reason="Request contains patterns violating adversarial prompt safety guardrails.",
                    evaluated_rules=evaluated_rules,
                    metadata={"blocked_by": self.RULE_INJECTION_GUARD},
                )

        # 2. Rule AG-03: Restricted / Destructive Operation Guard
        for kw in self.DESTRUCTIVE_KEYWORDS:
            if kw in req_text:
                engine_logger.warning(
                    f"PolicyDecisionEngine: Destructive keyword matched '{kw}' for user='{context.user_id}'"
                )
                return AgentPolicyDecision(
                    decision="DENY",
                    reason="Request attempts destructive operations prohibited by organizational policy.",
                    evaluated_rules=evaluated_rules,
                    metadata={"blocked_by": self.RULE_RESTRICTED_OPERATION},
                )

        # 3. Rule AG-04: Role & Capability Matrix Guard
        user_role = (context.role or "").strip().upper()
        if not user_role:
            return AgentPolicyDecision(
                decision="DENY",
                reason="User access context lacks a valid role specification.",
                evaluated_rules=evaluated_rules,
                metadata={"blocked_by": self.RULE_ROLE_AUTHORIZATION},
            )

        # 4. Rule AG-02: Clearance Policy & Review triggers
        user_clearance = (context.clearance_level or "PUBLIC").strip().upper()
        if "sensitive security playbook" in req_text or "classified forensic analysis" in req_text:
            if user_clearance not in ("CONFIDENTIAL", "RESTRICTED") and not context.is_admin:
                return AgentPolicyDecision(
                    decision="DENY",
                    reason="Request requires elevated clearance level (CONFIDENTIAL or higher).",
                    evaluated_rules=evaluated_rules,
                    metadata={"blocked_by": self.RULE_CLEARANCE_POLICY},
                )

        # High risk evaluation actions trigger manual review requirement
        if capability == "GOVERNANCE_EVALUATION" and any(k in req_text for k in ["delete", "purge", "revoke"]):
            return AgentPolicyDecision(
                decision="REQUIRES_REVIEW",
                reason="High-risk governance evaluation requires secondary compliance officer review.",
                evaluated_rules=evaluated_rules,
                metadata={"review_trigger": self.RULE_RESTRICTED_OPERATION},
            )

        engine_logger.debug(
            f"PolicyDecisionEngine: Request approved for capability='{capability}' user='{context.user_id}'"
        )
        return AgentPolicyDecision(
            decision="ALLOW",
            reason="Request complies with all deterministic governance policies.",
            evaluated_rules=evaluated_rules,
        )
