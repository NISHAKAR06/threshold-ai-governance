"""
test_tool_authorization.py — Unit tests for ToolAuthorizationEngine in Phase 14.
"""
import pytest

from app.models.access_context import AccessContext
from app.models.agent_decision import AgentPolicyDecision, ToolAuthDecision
from app.engines.agent_governance.tool_authorization_engine import ToolAuthorizationEngine


@pytest.fixture
def auth_engine():
    return ToolAuthorizationEngine(
        enabled_tools=["GovernanceRAGTool", "GovernanceRetrievalTool", "GovernanceEvaluationTool"]
    )


@pytest.fixture
def allowed_policy():
    return AgentPolicyDecision(
        decision="ALLOW",
        reason="Complies with governance policies",
    )


@pytest.fixture
def denied_policy():
    return AgentPolicyDecision(
        decision="DENY",
        reason="Violates security guardrails",
    )


@pytest.fixture
def review_policy():
    return AgentPolicyDecision(
        decision="REQUIRES_REVIEW",
        reason="Requires secondary approval",
    )


def test_allowed_tool_authorization(auth_engine, allowed_policy):
    """Test authorized tool execution under valid access context."""
    ctx = AccessContext(
        user_id="USER-101",
        role="SECURITY_ENGINEER",
        clearance_level="RESTRICTED",
    )
    decision = auth_engine.authorize_tool(
        tool_name="GovernanceRAGTool",
        access_context=ctx,
        policy_decision=allowed_policy,
    )
    assert isinstance(decision, ToolAuthDecision)
    assert decision.is_authorized is True
    assert decision.status == "ALLOW"


def test_denied_by_policy_verdict(auth_engine, denied_policy):
    """Test that a DENY policy decision halts tool execution before running."""
    ctx = AccessContext(
        user_id="USER-101",
        role="ADMIN",
        clearance_level="RESTRICTED",
        is_admin=True,
    )
    decision = auth_engine.authorize_tool(
        tool_name="GovernanceRAGTool",
        access_context=ctx,
        policy_decision=denied_policy,
    )
    assert decision.is_authorized is False
    assert decision.status == "DENY"
    assert "Policy decision blocked" in decision.reason


def test_review_required_halts_execution(auth_engine, review_policy):
    """Test that REQUIRES_REVIEW halts automatic execution."""
    ctx = AccessContext(
        user_id="USER-101",
        role="ANALYST",
        clearance_level="INTERNAL",
    )
    decision = auth_engine.authorize_tool(
        tool_name="GovernanceEvaluationTool",
        access_context=ctx,
        policy_decision=review_policy,
    )
    assert decision.is_authorized is False
    assert decision.status == "REQUIRES_REVIEW"
    assert "halted pending human" in decision.reason


def test_disabled_tool_authorization(allowed_policy):
    """Test that disabling a tool in enabled_tools results in denial."""
    strict_engine = ToolAuthorizationEngine(enabled_tools=["GovernanceRAGTool"])
    ctx = AccessContext(user_id="USER-101", role="ENGINEER", clearance_level="CONFIDENTIAL")

    decision = strict_engine.authorize_tool(
        tool_name="GovernanceEvaluationTool",
        access_context=ctx,
        policy_decision=allowed_policy,
    )
    assert decision.is_authorized is False
    assert decision.status == "DENY"
    assert "currently disabled" in decision.reason


def test_evaluation_tool_clearance_restriction(auth_engine, allowed_policy):
    """Test that low-clearance users cannot run GovernanceEvaluationTool."""
    ctx_public = AccessContext(user_id="USER-LOW", role="GUEST", clearance_level="PUBLIC")
    decision = auth_engine.authorize_tool(
        tool_name="GovernanceEvaluationTool",
        access_context=ctx_public,
        policy_decision=allowed_policy,
    )
    assert decision.is_authorized is False
    assert decision.status == "DENY"
    assert "INTERNAL or higher" in decision.reason
