"""
agent_controller.py — Central workflow orchestrator for controlled agent execution.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from app.models.agent_request import AgentRequest
from app.models.agent_decision import AgentPolicyDecision, ToolAuthDecision
from app.models.agent_tool_result import AgentToolResult
from app.agents.agent_validator import AgentValidator
from app.agents.agent_router import AgentRouter
from app.agents.tool_registry import ToolRegistry, create_default_tool_registry
from app.engines.agent_governance.policy_decision_engine import PolicyDecisionEngine
from app.engines.agent_governance.tool_authorization_engine import ToolAuthorizationEngine
from app.engines.agent_governance.tool_output_validator import ToolOutputValidator
from app.core.exceptions import (
    AgentValidationError,
    AgentRoutingError,
    ToolNotRegisteredError,
    ToolAuthorizationError,
    ToolExecutionError,
    ToolOutputValidationError,
)
from app.core.logger import agent_logger


@dataclass
class ControllerExecutionResult:
    """Internal result payload returned by the AgentController."""
    status: str                         # SUCCESS, DENIED, REQUIRES_REVIEW, ERROR
    capability: str
    tool_name: Optional[str] = None
    tool_result: Optional[AgentToolResult] = None
    policy_decision: Optional[AgentPolicyDecision] = None
    tool_auth_decision: Optional[ToolAuthDecision] = None
    message: Optional[str] = None
    execution_time_ms: float = 0.0


class AgentController:
    """
    Coordinates the controlled agent workflow:
    1. Validate Request
    2. Route Capability
    3. Resolve Tool
    4. Policy Decision
    5. Tool Authorization (prevents denied tools from executing)
    6. Execute Tool
    7. Validate Output
    8. Return Result
    """

    def __init__(
        self,
        validator: Optional[AgentValidator] = None,
        router: Optional[AgentRouter] = None,
        registry: Optional[ToolRegistry] = None,
        policy_engine: Optional[PolicyDecisionEngine] = None,
        auth_engine: Optional[ToolAuthorizationEngine] = None,
        output_validator: Optional[ToolOutputValidator] = None,
    ) -> None:
        self.validator = validator or AgentValidator()
        self.router = router or AgentRouter()
        self.registry = registry or create_default_tool_registry()
        self.policy_engine = policy_engine or PolicyDecisionEngine()
        self.auth_engine = auth_engine or ToolAuthorizationEngine()
        self.output_validator = output_validator or ToolOutputValidator()

    def execute_workflow(self, request: AgentRequest) -> ControllerExecutionResult:
        """
        Execute the complete controlled AI agent pipeline.

        Args:
            request: AgentRequest containing user prompt and AccessContext.

        Returns:
            ControllerExecutionResult containing status, capability, tool result, and decisions.
        """
        start_time = time.perf_counter()
        agent_logger.info(f"AgentController: Workflow started for request_id='{request.request_id}'")

        # 1. Validate Request
        validated_request = self.validator.validate(request)

        # 2. Route Capability
        routing_decision = self.router.route(validated_request.request)
        capability = routing_decision.capability
        agent_logger.info(
            f"AgentController: Request routed to capability='{capability}' (conf={routing_decision.confidence})"
        )

        # 3. Resolve Tool from Registry
        tool = self.registry.get(capability)
        tool_name = tool.name
        agent_logger.info(f"AgentController: Resolved tool '{tool_name}' for capability='{capability}'")

        # 4. Evaluate Policy Decision
        policy_decision = self.policy_engine.evaluate_request(
            request=validated_request,
            capability=capability,
        )
        agent_logger.info(
            f"AgentController: Policy verdict='{policy_decision.decision}' reason='{policy_decision.reason}'"
        )

        # 5. Check Tool Authorization
        auth_decision = self.auth_engine.authorize_tool(
            tool_name=tool_name,
            access_context=validated_request.access_context,
            policy_decision=policy_decision,
            capability=capability,
        )
        agent_logger.info(
            f"AgentController: Tool authorization status='{auth_decision.status}' authorized={auth_decision.is_authorized}"
        )

        # Enforce Authorization: If not authorized, tool MUST NOT execute!
        if not auth_decision.is_authorized:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            agent_logger.warning(
                f"AgentController: Execution HALTED. Tool '{tool_name}' was not authorized ({auth_decision.status})"
            )
            return ControllerExecutionResult(
                status=auth_decision.status,
                capability=capability,
                tool_name=tool_name,
                policy_decision=policy_decision,
                tool_auth_decision=auth_decision,
                message=auth_decision.reason or "The requested operation is not permitted.",
                execution_time_ms=elapsed_ms,
            )

        # 6. Execute Approved Tool
        agent_logger.info(f"AgentController: Executing approved tool '{tool_name}'...")
        tool_input = {
            "request": validated_request.request,
            "question": validated_request.request,
            "query": validated_request.request,
            **validated_request.metadata,
        }

        tool_result = tool.execute(
            input_data=tool_input,
            access_context=validated_request.access_context,
        )

        # 7. Validate Tool Output
        agent_logger.info(f"AgentController: Validating output for tool '{tool_name}'...")
        val_result = self.output_validator.validate_output(tool_result)

        if not val_result.is_valid:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            agent_logger.error(
                f"AgentController: Output validation failed: {val_result.reason}"
            )
            return ControllerExecutionResult(
                status="ERROR",
                capability=capability,
                tool_name=tool_name,
                policy_decision=policy_decision,
                tool_auth_decision=auth_decision,
                tool_result=tool_result,
                message=f"Output safety validation failed: {val_result.reason}",
                execution_time_ms=elapsed_ms,
            )

        if not tool_result.success:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            agent_logger.warning(
                f"AgentController: Tool execution returned failure: {tool_result.error}"
            )
            return ControllerExecutionResult(
                status="ERROR",
                capability=capability,
                tool_name=tool_name,
                policy_decision=policy_decision,
                tool_auth_decision=auth_decision,
                tool_result=tool_result,
                message=tool_result.error or "Tool execution failed.",
                execution_time_ms=elapsed_ms,
            )

        # 8. Return Result
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        agent_logger.info(
            f"AgentController: Workflow completed successfully in {elapsed_ms:.2f}ms"
        )
        return ControllerExecutionResult(
            status="SUCCESS",
            capability=capability,
            tool_name=tool_name,
            tool_result=tool_result,
            policy_decision=policy_decision,
            tool_auth_decision=auth_decision,
            execution_time_ms=elapsed_ms,
        )
