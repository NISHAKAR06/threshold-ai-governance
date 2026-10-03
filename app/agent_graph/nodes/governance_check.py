"""
governance_check.py — Governance Evaluation Node for LangGraph Agentic Platform.

Reuses Threshold's deterministic policy rules (AG-01..AG-04), ToolRegistry permissions,
and Risk/Decision engines to decide:
- ALLOW  -> Execute requested RAG or tool capability
- DENY   -> Safe refusal via safe_denial_node
- REVIEW -> Escalation to Human-In-The-Loop review workflow
"""
from __future__ import annotations

from typing import Dict, Any, List
from app.agent_graph.state import AgentGraphState
from app.agents.tool_registry import ToolRegistry
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.governance")

# Clearance hierarchy index
CLEARANCE_RANKS = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "RESTRICTED": 3,
}


def governance_check_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Evaluates requested capability and access credentials against deterministic governance policies.
    """
    if state.get("governance_decision") == "DENY":
        # Already denied by previous node (e.g. RAI input guard)
        return {
            "status": "DENIED",
        }

    request_id = state.get("request_id", "unknown")
    user_req = state.get("user_query") or state.get("user_request", "")
    capability = state.get("capability", "UNKNOWN")
    tool_name = state.get("selected_action")
    access_context = state.get("access_context") or {}

    role = str(access_context.get("role", "GUEST")).upper()
    clearance = str(access_context.get("clearance_level", "PUBLIC")).upper()
    dept = str(access_context.get("department", "GENERAL"))
    is_admin = bool(access_context.get("is_admin", role in ("ADMIN", "SUPERADMIN")))

    from app.models.agent_request import AgentRequest
    from app.models.access_context import AccessContext
    from app.engines.agent_governance.policy_decision_engine import PolicyDecisionEngine
    from app.engines.agent_governance.tool_authorization_engine import ToolAuthorizationEngine
    from app.agents.tool_registry import create_default_tool_registry

    # 1. Instantiate domain access context
    ctx_obj = AccessContext(
        user_id=str(access_context.get("user_id", "ANONYMOUS")),
        role=role,
        department=dept,
        clearance_level=clearance,
        is_admin=is_admin,
    )

    agent_req = AgentRequest(
        request=user_req,
        access_context=ctx_obj,
        request_id=request_id,
    )

    # 2. Evaluate against deterministic PolicyDecisionEngine (AG-01..AG-04)
    policy_engine = PolicyDecisionEngine()
    policy_verdict = policy_engine.evaluate_request(request=agent_req, capability=capability)

    reasons: List[str] = []
    decision = policy_verdict.decision
    risk_score = 15.0
    risk_level = "LOW"

    if policy_verdict.reason:
        reasons.append(policy_verdict.reason)

    if policy_verdict.decision == "DENY":
        risk_score = 90.0
        risk_level = "HIGH"
    elif policy_verdict.decision == "REQUIRES_REVIEW":
        decision = "REVIEW"
        risk_score = 65.0
        risk_level = "MEDIUM"

    # 3. Check for administrative / destructive operations requiring HITL Review
    user_req_lower = user_req.lower()
    destructive_keywords = ["delete", "drop", "terminate", "purge", "revoke", "destroy", "truncate"]
    is_destructive = any(kw in user_req_lower for kw in destructive_keywords)

    if is_destructive:
        risk_score = 85.0
        risk_level = "HIGH"
        if not is_admin:
            decision = "DENY"
            reasons = ["Destructive or high-impact operational changes strictly prohibited for non-admin roles."]
        else:
            decision = "REVIEW"
            reasons = ["High-impact infrastructure modification exceeds automated autonomy threshold (mandates HITL confirmation)."]

    # 4. Tool Authorization via ToolAuthorizationEngine & ToolRegistry
    tool_reg = create_default_tool_registry()
    try:
        tool = tool_reg.get(tool_name) if tool_name else None
    except Exception:
        tool = None

    if decision != "DENY" and tool_name:
        if decision == "REVIEW" and is_destructive and is_admin:
            # High-impact admin operation explicitly slated for human-in-the-loop review
            pass
        else:
            tool_auth_engine = ToolAuthorizationEngine()
            auth_decision = tool_auth_engine.authorize_tool(
                tool_name=tool_name,
                access_context=ctx_obj,
                policy_decision=policy_verdict,
                capability=capability,
            )
            if not auth_decision.is_authorized:
                if auth_decision.status == "REQUIRES_REVIEW":
                    decision = "REVIEW"
                    risk_score = max(risk_score, 65.0)
                    risk_level = "MEDIUM"
                    reasons.append(auth_decision.reason)
                else:
                    decision = "DENY"
                    risk_score = max(risk_score, 75.0)
                    risk_level = "HIGH"
                    reasons.append(auth_decision.reason)

    # 5. Clearance hierarchy checks on registered tool
    if decision != "DENY" and tool:
        req_clearance = getattr(tool, "required_clearance", "INTERNAL").upper()
        user_rank = CLEARANCE_RANKS.get(clearance, 0)
        req_rank = CLEARANCE_RANKS.get(req_clearance, 1)

        if user_rank < req_rank and not is_admin:
            decision = "DENY"
            risk_score = max(risk_score, 70.0)
            risk_level = "HIGH"
            reasons.append(
                f"Clearance level '{clearance}' does not meet required '{req_clearance}' for tool '{tool.name}'."
            )
        elif getattr(tool, "requires_approval", False):
            decision = "REVIEW"
            risk_score = max(risk_score, 65.0)
            risk_level = "MEDIUM"
            reasons.append(f"Tool '{tool.name}' is flagged as requiring Human-in-the-Loop review.")

    # 6. Fallback for unrecognized capabilities
    if decision == "ALLOW" and capability not in ("RAG_QUESTION", "RAG_QUERY", "RETRIEVAL_SEARCH") and not tool:
        decision = "REVIEW"
        risk_score = 60.0
        risk_level = "MEDIUM"
        reasons.append("Unrecognized or generic capability routed to human review.")

    review_required = (decision == "REVIEW")
    status = "GOVERNED" if decision == "ALLOW" else ("PENDING_REVIEW" if review_required else "DENIED")

    gov_result = {
        "decision": decision,
        "reasons": reasons,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "review_required": review_required,
        "policy_decision": policy_verdict.decision,
        "evaluated_rules": getattr(policy_verdict, "evaluated_rules", []),
    }

    logger.info(
        "GovernanceCheck: Decision rendered",
        extra={
            "request_id": request_id,
            "decision": decision,
            "risk_score": risk_score,
            "reasons": reasons,
        },
    )

    return {
        "governance_decision": decision,
        "governance_result": gov_result,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "decision_reasons": reasons,
        "review_required": review_required,
        "status": status,
    }
