"""
agent_validator.py — Input validation component for incoming agent requests and security contexts.
"""
from __future__ import annotations

from typing import Union, Dict, Any, Optional

from app.config import settings
from app.models.agent_request import AgentRequest
from app.models.access_context import AccessContext
from app.core.exceptions import AgentValidationError


class AgentValidator:
    """
    Validates agent requests for structure, content length, and valid security access contexts.
    """

    def __init__(self, max_request_length: Optional[int] = None) -> None:
        self.max_request_length = max_request_length or settings.AGENT_MAX_REQUEST_LENGTH

    def validate(self, request: AgentRequest) -> AgentRequest:
        """
        Validate an incoming AgentRequest.

        Args:
            request: AgentRequest instance.

        Returns:
            Sanitized AgentRequest instance.

        Raises:
            AgentValidationError: If request text or access context is invalid.
        """
        if not isinstance(request, AgentRequest):
            raise AgentValidationError(
                f"Expected AgentRequest instance, got {type(request).__name__}"
            )

        raw_text = request.request
        if not raw_text or not isinstance(raw_text, str):
            raise AgentValidationError("Agent request text cannot be empty.")

        clean_text = raw_text.strip()
        if not clean_text:
            raise AgentValidationError("Agent request text cannot be whitespace only.")

        if len(clean_text) < 2:
            raise AgentValidationError("Agent request text is too short (minimum 2 characters).")

        if len(clean_text) > self.max_request_length:
            raise AgentValidationError(
                f"Agent request text exceeds maximum length of {self.max_request_length} characters."
            )

        # Validate AccessContext
        ctx = request.access_context
        if ctx is None:
            raise AgentValidationError("Agent request is missing access_context.")

        if isinstance(ctx, dict):
            user_id = ctx.get("user_id")
            role = ctx.get("role")
            if not user_id or not role:
                raise AgentValidationError("Access context dictionary must contain 'user_id' and 'role'.")
            # Convert to AccessContext object
            ctx = AccessContext(
                user_id=str(user_id),
                role=str(role),
                department=ctx.get("department"),
                clearance_level=ctx.get("clearance_level", "PUBLIC"),
                is_admin=bool(ctx.get("is_admin", False)),
            )
            request.access_context = ctx
        elif isinstance(ctx, AccessContext):
            if not ctx.user_id or not str(ctx.user_id).strip():
                raise AgentValidationError("Access context user_id cannot be empty.")
            if not ctx.role or not str(ctx.role).strip():
                raise AgentValidationError("Access context role cannot be empty.")
        else:
            raise AgentValidationError(
                f"Unsupported access_context type: {type(ctx).__name__}. Must be AccessContext or dict."
            )

        request.request = clean_text
        return request
