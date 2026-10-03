"""
test_governance_rag_tool.py — Unit tests for GovernanceRAGTool in Phase 14.
"""
import pytest
from unittest.mock import MagicMock

from app.agents.tools.governance_rag_tool import GovernanceRAGTool
from app.models.access_context import AccessContext
from app.models.agent_tool_result import AgentToolResult
from app.models.rag_response import RAGResponse
from app.services.rag_service import RAGService
from app.core.exceptions import RAGError


@pytest.fixture
def mock_rag_service():
    return MagicMock(spec=RAGService)


@pytest.fixture
def rag_tool(mock_rag_service):
    return GovernanceRAGTool(rag_service=mock_rag_service)


@pytest.fixture
def access_context():
    return AccessContext(
        user_id="USER-001",
        role="SECURITY_ENGINEER",
        clearance_level="RESTRICTED",
    )


def test_rag_tool_metadata(rag_tool):
    """Test tool name and description properties."""
    assert rag_tool.name == "GovernanceRAGTool"
    assert "g" in rag_tool.description.lower()


def test_rag_tool_validate_input(rag_tool):
    """Test input validation logic."""
    assert rag_tool.validate_input({"question": "What is the policy?"}) is True
    assert rag_tool.validate_input({"request": "Explain access control"}) is True
    assert rag_tool.validate_input({"question": ""}) is False
    assert rag_tool.validate_input({}) is False
    assert rag_tool.validate_input("not_a_dict") is False


def test_rag_tool_successful_execution(rag_tool, mock_rag_service, access_context):
    """Test successful tool execution delegating to RAGService."""
    mock_rag_service.generate_answer.return_value = RAGResponse(
        question="What is the policy?",
        answer="Authorized security policies require dual authorization.",
        status="SUCCESS",
        sources=[],
        retrieval_metadata={"authorized_result_count": 2},
    )

    result = rag_tool.execute(
        input_data={"question": "What is the policy?", "top_k": 3},
        access_context=access_context,
    )

    assert isinstance(result, AgentToolResult)
    assert result.success is True
    assert result.tool_name == "GovernanceRAGTool"
    assert "Authorized security policies" in result.output["answer"]
    assert result.error is None
    assert result.execution_time_ms >= 0.0

    mock_rag_service.generate_answer.assert_called_once_with(
        question="What is the policy?",
        access_context=access_context,
        top_k=3,
    )


def test_rag_tool_handles_service_exception(rag_tool, mock_rag_service, access_context):
    """Test that tool gracefully captures exceptions without crashing."""
    mock_rag_service.generate_answer.side_effect = RAGError("Retrieval index corrupted")

    result = rag_tool.execute(
        input_data={"question": "What is the policy?"},
        access_context=access_context,
    )

    assert result.success is False
    assert "Retrieval index corrupted" in result.error
