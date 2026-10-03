"""
policy_validator.py — Responsible AI Policy Validation.
Integrates User Request + Access Context + Requested Capability with the
enterprise governance policy decision engine (Phase 14).
"""
from __future__ import annotations

from typing import Dict, Any, Optional, Union
from app.models.access_context import AccessContext
from app.models.agent_request import AgentRequest
from app.models.agent_decision import AgentPolicyDecision
from app.engines.agent_governance.policy_decision_engine import PolicyDecisionEngine
from app.core.logger import get_logger

logger = get_logger("threshold.responsible_ai.policy_validator")


class PolicyValidator:
    """
    Validates that a request, access context, and capability comply with enterprise policies
    before expensive pipeline operations (retrieval or LLM generation) begin.
    """

    def __init__(self, engine: Optional[PolicyDecisionEngine] = None) -> None:
        self.engine = engine or PolicyDecisionEngine()

    def validate(
        self,
        request_text: str,
        access_context: Union[AccessContext, Dict[str, Any]],
        capability: str = "RAG_QUESTION",
        request_id: Optional[str] = None,
    ) -> AgentPolicyDecision:
        """
        Validate request against deterministic enterprise policies.
        """
        ctx = (
            access_context
            if isinstance(access_context, AccessContext)
            else AccessContext.from_dict(access_context)
        )

        agent_req = AgentRequest(
            request=request_text,
            access_context=ctx,
            request_id=request_id or "val-req",
        )

        decision = self.engine.evaluate_request(agent_req, capability)
        logger.debug(
            "PolicyValidator outcome for user '%s', cap '%s': %s",
            ctx.user_id,
            capability,
            decision.decision,
        )
        return decision
