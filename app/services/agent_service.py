"""
agent_service.py — High-level service orchestrating Controlled AI Agent execution and audit trail logging.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

from app.models.agent_request import AgentRequest
from app.models.agent_response import AgentResponse
from app.models.access_context import AccessContext
from app.agents.agent_controller import AgentController, ControllerExecutionResult
from app.services.audit_service import AuditService
from app.core.exceptions import (
    AgentValidationError,
    AgentRoutingError,
    ToolNotRegisteredError,
    ToolAuthorizationError,
    ToolExecutionError,
    ToolOutputValidationError,
)
from app.core.logger import agent_logger, audit_logger


class AgentAuditRecord:
    """Immutable audit record representing a single agent execution event."""
    __slots__ = (
        "event_id",
        "request_id",
        "timestamp",
        "requested_capability",
        "selected_capability",
        "policy_decision",
        "tool_name",
        "tool_authorization",
        "execution_status",
        "user_id",
        "role",
        "execution_time_ms",
    )

    def __init__(
        self,
        event_id: str,
        request_id: str,
        timestamp: str,
        requested_capability: Optional[str],
        selected_capability: str,
        policy_decision: str,
        tool_name: Optional[str],
        tool_authorization: str,
        execution_status: str,
        user_id: str,
        role: str,
        execution_time_ms: float,
    ) -> None:
        self.event_id = event_id
        self.request_id = request_id
        self.timestamp = timestamp
        self.requested_capability = requested_capability
        self.selected_capability = selected_capability
        self.policy_decision = policy_decision
        self.tool_name = tool_name
        self.tool_authorization = tool_authorization
        self.execution_status = execution_status
        self.user_id = user_id
        self.role = role
        self.execution_time_ms = execution_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "requested_capability": self.requested_capability,
            "selected_capability": self.selected_capability,
            "policy_decision": self.policy_decision,
            "tool_name": self.tool_name,
            "tool_authorization": self.tool_authorization,
            "execution_status": self.execution_status,
            "user_id": self.user_id,
            "role": self.role,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


class AgentService:
    """
    Production-grade service managing governed agent execution:
    - Receives user request and AccessContext.
    - Orchestrates AgentController.
    - Generates and persists append-oriented audit events.
    - Returns structured AgentResponse.
    - Prevents arbitrary code execution or tool execution bypasses.
    """

    # In-memory append-only audit log buffer for fast lookup and offline verification
    _audit_log_store: List[AgentAuditRecord] = []

    def __init__(
        self,
        controller: Optional[AgentController] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        self.controller = controller or AgentController()
        self.audit_service = audit_service

    def execute(
        self,
        request: str,
        access_context: Union[AccessContext, Dict[str, Any]],
        request_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        requested_capability: Optional[str] = None,
    ) -> AgentResponse:
        """
        Execute controlled agent request pipeline.

        Args:
            request: Natural language user instruction or query.
            access_context: AccessContext model or dictionary.
            request_id: Optional unique request id.
            conversation_id: Optional conversation id.
            requested_capability: Optional explicit capability if requested.

        Returns:
            AgentResponse: Structured output or denial explanation.
        """
        req_id = request_id or str(uuid.uuid4())
        ctx = self._resolve_access_context(access_context)

        agent_req = AgentRequest(
            request=request,
            access_context=ctx,
            request_id=req_id,
            conversation_id=conversation_id,
        )

        agent_logger.info(
            f"AgentService: Received execution request for user='{ctx.user_id}' (req_id='{req_id}')"
        )

        try:
            # 1. Execute controlled workflow
            exec_result = self.controller.execute_workflow(agent_req)

            # 2. Extract decisions
            policy_decision_val = (
                exec_result.policy_decision.decision if exec_result.policy_decision else "UNKNOWN"
            )
            tool_auth_val = (
                exec_result.tool_auth_decision.status if exec_result.tool_auth_decision else "UNKNOWN"
            )
            selected_cap = exec_result.capability
            tool_name = exec_result.tool_name

            # 3. Create Audit Record
            audit_event_id = self._record_audit_event(
                request_id=req_id,
                requested_capability=requested_capability,
                selected_capability=selected_cap,
                policy_decision=policy_decision_val,
                tool_name=tool_name,
                tool_authorization=tool_auth_val,
                execution_status=exec_result.status,
                user_id=ctx.user_id,
                role=ctx.role,
                execution_time_ms=exec_result.execution_time_ms,
            )

            # 4. Construct Structured Response
            if exec_result.status == "SUCCESS":
                result_output = exec_result.tool_result.output if exec_result.tool_result else {}
                return AgentResponse(
                    request_id=req_id,
                    status="SUCCESS",
                    capability=selected_cap,
                    result=result_output,
                    audit_reference=audit_event_id,
                    execution_time_ms=exec_result.execution_time_ms,
                )
            elif exec_result.status in ("DENY", "DENIED"):
                return AgentResponse(
                    request_id=req_id,
                    status="DENIED",
                    capability=selected_cap,
                    message=exec_result.message or "The requested operation is not permitted.",
                    audit_reference=audit_event_id,
                    execution_time_ms=exec_result.execution_time_ms,
                )
            elif exec_result.status == "REQUIRES_REVIEW":
                return AgentResponse(
                    request_id=req_id,
                    status="REVIEW_REQUIRED",
                    capability=selected_cap,
                    message=exec_result.message or "The requested operation requires compliance review.",
                    audit_reference=audit_event_id,
                    execution_time_ms=exec_result.execution_time_ms,
                )
            else:
                return AgentResponse(
                    request_id=req_id,
                    status="ERROR",
                    capability=selected_cap,
                    message=exec_result.message or "Agent workflow encountered an execution error.",
                    audit_reference=audit_event_id,
                    execution_time_ms=exec_result.execution_time_ms,
                )

        except (AgentValidationError, AgentRoutingError, ToolNotRegisteredError) as known_err:
            agent_logger.warning(f"AgentService: Handled validation/routing error: {known_err}")
            audit_event_id = self._record_audit_event(
                request_id=req_id,
                requested_capability=requested_capability,
                selected_capability="UNKNOWN",
                policy_decision="DENY",
                tool_name=None,
                tool_authorization="DENY",
                execution_status="ERROR",
                user_id=ctx.user_id,
                role=ctx.role,
                execution_time_ms=0.0,
            )
            # Re-raise domain error so FastAPI exception handler returns proper HTTP code
            raise known_err

        except Exception as exc:
            agent_logger.error(f"AgentService: Unhandled exception: {exc}", exc_info=True)
            audit_event_id = self._record_audit_event(
                request_id=req_id,
                requested_capability=requested_capability,
                selected_capability="UNKNOWN",
                policy_decision="ERROR",
                tool_name=None,
                tool_authorization="ERROR",
                execution_status="ERROR",
                user_id=ctx.user_id,
                role=ctx.role,
                execution_time_ms=0.0,
            )
            return AgentResponse(
                request_id=req_id,
                status="ERROR",
                capability="UNKNOWN",
                message="An error occurred during agent execution.",
                audit_reference=audit_event_id,
            )

    def _record_audit_event(
        self,
        request_id: str,
        requested_capability: Optional[str],
        selected_capability: str,
        policy_decision: str,
        tool_name: Optional[str],
        tool_authorization: str,
        execution_status: str,
        user_id: str,
        role: str,
        execution_time_ms: float,
    ) -> str:
        """Create and append an immutable audit record."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        record = AgentAuditRecord(
            event_id=event_id,
            request_id=request_id,
            timestamp=timestamp,
            requested_capability=requested_capability,
            selected_capability=selected_capability,
            policy_decision=policy_decision,
            tool_name=tool_name,
            tool_authorization=tool_authorization,
            execution_status=execution_status,
            user_id=user_id,
            role=role,
            execution_time_ms=execution_time_ms,
        )
        self._audit_log_store.append(record)

        audit_logger.info(
            "Agent audit event recorded",
            extra={
                "event_id": event_id,
                "request_id": request_id,
                "selected_capability": selected_capability,
                "policy_decision": policy_decision,
                "tool_name": tool_name,
                "tool_authorization": tool_authorization,
                "execution_status": execution_status,
            },
        )
        return event_id

    @classmethod
    def get_audit_records(cls) -> List[Dict[str, Any]]:
        """Return read-only copy of appended audit records."""
        return [r.to_dict() for r in cls._audit_log_store]

    @classmethod
    def clear_audit_records(cls) -> None:
        """Clear audit buffer (used strictly for test suite teardown)."""
        cls._audit_log_store.clear()

    def _resolve_access_context(
        self,
        ctx: Union[AccessContext, Dict[str, Any]],
    ) -> AccessContext:
        """Convert input access context dictionary or instance into AccessContext."""
        if isinstance(ctx, AccessContext):
            return ctx
        if isinstance(ctx, dict):
            return AccessContext(
                user_id=str(ctx.get("user_id", "anonymous")),
                role=str(ctx.get("role", "EMPLOYEE")),
                department=ctx.get("department"),
                clearance_level=ctx.get("clearance_level", "PUBLIC"),
                is_admin=bool(ctx.get("is_admin", False)),
            )
        raise AgentValidationError(
            f"Unsupported access_context type: {type(ctx).__name__}. Must be AccessContext or dict."
        )
