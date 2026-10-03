"""
test_tool_registry.py — Unit tests for ToolRegistry component in Phase 14.
"""
import pytest
from typing import Dict, Any

from app.agents.tool_registry import ToolRegistry, create_default_tool_registry
from app.agents.tools.base_tool import BaseAgentTool
from app.models.access_context import AccessContext
from app.models.agent_tool_result import AgentToolResult
from app.core.exceptions import ToolNotRegisteredError


class DummyTool(BaseAgentTool):
    @property
    def name(self) -> str:
        return "DummyTool"

    @property
    def description(self) -> str:
        return "A dummy test tool"

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True

    def execute(self, input_data: Dict[str, Any], access_context: AccessContext) -> AgentToolResult:
        return AgentToolResult(tool_name=self.name, success=True, output={"status": "ok"})


def test_tool_registration_and_lookup():
    """Test registering a tool and looking it up."""
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register("TEST_CAPABILITY", tool)

    assert registry.has_tool("TEST_CAPABILITY")
    retrieved = registry.get("TEST_CAPABILITY")
    assert retrieved is tool
    assert retrieved.name == "DummyTool"


def test_unknown_tool_lookup():
    """Test that requesting an unregistered tool raises ToolNotRegisteredError."""
    registry = ToolRegistry()
    assert not registry.has_tool("NON_EXISTENT_TOOL")
    with pytest.raises(ToolNotRegisteredError, match="No approved tool is registered"):
        registry.get("NON_EXISTENT_TOOL")


def test_duplicate_registration_handling():
    """Test that registering duplicate tool without overwrite flag raises ValueError."""
    registry = ToolRegistry()
    tool1 = DummyTool()
    tool2 = DummyTool()

    registry.register("TEST_TOOL", tool1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("TEST_TOOL", tool2, overwrite=False)

    # Overwrite works when enabled
    registry.register("TEST_TOOL", tool2, overwrite=True)
    assert registry.get("TEST_TOOL") is tool2


def test_invalid_tool_type():
    """Test that registering an object not inheriting BaseAgentTool raises TypeError."""
    registry = ToolRegistry()
    with pytest.raises(TypeError, match="must inherit from BaseAgentTool"):
        registry.register("INVALID", "not_a_tool")  # type: ignore


def test_default_tool_registry_creation():
    """Verify create_default_tool_registry registers standard Phase 14 tools."""
    reg = create_default_tool_registry()
    assert reg.has_tool("RAG_QUESTION")
    assert reg.has_tool("RETRIEVAL_SEARCH")
    assert reg.has_tool("GOVERNANCE_EVALUATION")

    rag_tool = reg.get("RAG_QUESTION")
    ret_tool = reg.get("RETRIEVAL_SEARCH")
    eval_tool = reg.get("GOVERNANCE_EVALUATION")

    assert rag_tool.name == "GovernanceRAGTool"
    assert ret_tool.name == "GovernanceRetrievalTool"
    assert eval_tool.name == "GovernanceEvaluationTool"


def test_list_tools_metadata():
    """Test listing metadata of registered tools."""
    reg = create_default_tool_registry()
    tools = reg.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "GovernanceRAGTool" in tool_names
    assert "GovernanceRetrievalTool" in tool_names
    assert "GovernanceEvaluationTool" in tool_names
