"""
test_agent_router.py — Unit tests for AgentRouter component in Phase 14.
"""
import pytest

from app.agents.agent_router import AgentRouter, RoutingDecision
from app.core.exceptions import AgentRoutingError


@pytest.fixture
def router():
    return AgentRouter()


def test_route_rag_question(router):
    """Test routing question-style prompts to RAG_QUESTION."""
    queries = [
        "What is the policy for accessing confidential AI systems?",
        "How do employees submit remote work requests?",
        "Explain the incident response containment protocol",
        "Who is authorized to approve model deployment?",
        "Why is dual-key authorization required?",
    ]
    for q in queries:
        decision = router.route(q)
        assert isinstance(decision, RoutingDecision)
        assert decision.capability == "RAG_QUESTION"
        assert decision.confidence >= 0.7


def test_route_retrieval_search(router):
    """Test routing document lookup requests to RETRIEVAL_SEARCH."""
    queries = [
        "Show relevant policies for model access",
        "Find policies related to data retention",
        "Search for documents concerning encryption standards",
        "List all documents for security procedures",
        "Retrieve chunks about remote work core hours",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.capability == "RETRIEVAL_SEARCH"
        assert decision.confidence >= 0.8


def test_route_governance_evaluation(router):
    """Test routing policy checks and approval queries to GOVERNANCE_EVALUATION."""
    queries = [
        "Is this request compliant with governance rules?",
        "Verify compliance for bulk user data export",
        "Can I execute a database migration without review?",
        "Run policy check on user provisioning",
        "Is this operation permitted under company guidelines?",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.capability == "GOVERNANCE_EVALUATION"
        assert decision.confidence >= 0.9


def test_route_empty_request(router):
    """Test that empty or whitespace request text raises AgentRoutingError."""
    with pytest.raises(AgentRoutingError, match="Cannot route empty"):
        router.route("")

    with pytest.raises(AgentRoutingError, match="Cannot route empty"):
        router.route("   \t\n  ")


def test_supported_capabilities_contain_required_set(router):
    """Verify router restricts capabilities to supported set."""
    assert "RAG_QUESTION" in router.SUPPORTED_CAPABILITIES
    assert "RETRIEVAL_SEARCH" in router.SUPPORTED_CAPABILITIES
    assert "GOVERNANCE_EVALUATION" in router.SUPPORTED_CAPABILITIES
    assert len(router.SUPPORTED_CAPABILITIES) == 3
