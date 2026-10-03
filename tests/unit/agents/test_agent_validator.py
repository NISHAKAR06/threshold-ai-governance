"""
test_agent_validator.py — Unit tests for AgentValidator component in Phase 14.
"""
import pytest

from app.models.agent_request import AgentRequest
from app.models.access_context import AccessContext
from app.agents.agent_validator import AgentValidator
from app.core.exceptions import AgentValidationError


@pytest.fixture
def validator():
    return AgentValidator(max_request_length=1000)


@pytest.fixture
def valid_context():
    return AccessContext(
        user_id="USER-001",
        role="SECURITY_ENGINEER",
        department="Security",
        clearance_level="RESTRICTED",
    )


def test_valid_agent_request(validator, valid_context):
    """Test validating a well-formed agent request."""
    req = AgentRequest(
        request="What is the policy for accessing confidential systems?",
        access_context=valid_context,
    )
    validated = validator.validate(req)
    assert validated.request == "What is the policy for accessing confidential systems?"
    assert validated.access_context.user_id == "USER-001"
    assert validated.access_context.role == "SECURITY_ENGINEER"


def test_empty_agent_request(validator, valid_context):
    """Test rejection of empty or whitespace-only requests."""
    req_empty = AgentRequest(request="", access_context=valid_context)
    with pytest.raises(AgentValidationError, match="cannot be empty"):
        validator.validate(req_empty)

    req_spaces = AgentRequest(request="   \n\t  ", access_context=valid_context)
    with pytest.raises(AgentValidationError, match="cannot be empty|whitespace only"):
        validator.validate(req_spaces)


def test_request_too_short(validator, valid_context):
    """Test rejection of single-character request text."""
    req = AgentRequest(request="?", access_context=valid_context)
    with pytest.raises(AgentValidationError, match="too short"):
        validator.validate(req)


def test_request_exceeds_max_length(validator, valid_context):
    """Test rejection of requests exceeding length limit."""
    long_text = "a" * 1001
    req = AgentRequest(request=long_text, access_context=valid_context)
    with pytest.raises(AgentValidationError, match="exceeds maximum length"):
        validator.validate(req)


def test_missing_access_context(validator):
    """Test rejection when access context is missing."""
    req = AgentRequest(request="Valid question text", access_context=None)
    with pytest.raises(AgentValidationError, match="missing access_context"):
        validator.validate(req)


def test_dict_access_context_conversion(validator):
    """Test automatic conversion of dictionary access context."""
    req = AgentRequest(
        request="Valid question text",
        access_context={
            "user_id": "USER-002",
            "role": "DEVELOPER",
            "clearance_level": "INTERNAL",
            "is_admin": False,
        },
    )
    validated = validator.validate(req)
    assert isinstance(validated.access_context, AccessContext)
    assert validated.access_context.user_id == "USER-002"
    assert validated.access_context.role == "DEVELOPER"


def test_invalid_dict_access_context(validator):
    """Test rejection when dictionary lacks user_id or role."""
    req = AgentRequest(
        request="Valid question text",
        access_context={"user_id": "USER-002"},  # missing role
    )
    with pytest.raises(AgentValidationError, match="must contain 'user_id' and 'role'"):
        validator.validate(req)


def test_invalid_context_type(validator):
    """Test rejection of unsupported access context type."""
    req = AgentRequest(
        request="Valid question text",
        access_context=["invalid", "list"],
    )
    with pytest.raises(AgentValidationError, match="Unsupported access_context type"):
        validator.validate(req)
