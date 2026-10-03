"""
tool_execution.py — Controlled Tool Execution Node for LangGraph Agentic Platform.

Executes only verified, approved tools registered in ToolRegistry.
Prohibits arbitrary code execution or unsanitized shell commands.
"""
from __future__ import annotations

import time
from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.agents.tool_registry import ToolRegistry
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.tool_execution")


def tool_execution_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Executes approved operational tools and captures structured output.
    Enforces authorization check, strict input validation, and post-execution output validation.
    """
    start_time = time.monotonic()
    request_id = state.get("request_id", "unknown")
    tool_name = state.get("selected_action")
    params = state.get("tool_parameters") or {}
    access_context = state.get("access_context") or {}
    gov_decision = state.get("governance_decision", "DENY")
    review_req = state.get("review_required", False)

    logger.info("ToolExecution: Executing approved tool", extra={"request_id": request_id, "tool": tool_name})

    # 1. Governance Authorization Assertion Guard
    if gov_decision != "ALLOW" or review_req:
        logger.error(
            "ToolExecution: Attempted tool execution without governance ALLOW clearance",
            extra={"request_id": request_id, "decision": gov_decision, "review_required": review_req},
        )
        return {
            "result": None,
            "tool_result": None,
            "error": "Security Block: Tool execution attempted without governance authorization.",
            "status": "DENIED",
            "final_response": "Governance Refusal: Unauthorized tool execution blocked.",
            "message": "Governance Refusal: Unauthorized tool execution blocked.",
            "execution_time_ms": (time.monotonic() - start_time) * 1000.0,
        }

    from app.agents.tool_registry import create_default_tool_registry
    from app.models.access_context import AccessContext
    from app.engines.agent_governance.tool_output_validator import ToolOutputValidator

    tool_reg = create_default_tool_registry()
    try:
        tool = tool_reg.get(tool_name) if tool_name else None
    except Exception:
        tool = None

    if not tool:
        return {
            "result": None,
            "tool_result": None,
            "error": f"Tool '{tool_name}' not found in approved ToolRegistry.",
            "status": "ERROR",
            "final_response": f"Execution halted: unrecognized tool '{tool_name}'.",
            "message": f"Execution halted: unrecognized tool '{tool_name}'.",
            "execution_time_ms": (time.monotonic() - start_time) * 1000.0,
        }

    try:
        # Prepare tool input parameters
        input_data = dict(params)
        user_req = state.get("user_query") or state.get("user_request", "")
        input_data.setdefault("question", user_req)
        input_data.setdefault("request", user_req)
        input_data.setdefault("query", user_req)

        # 2. Strict Input Validation
        if not tool.validate_input(input_data):
            logger.warning("ToolExecution: Input validation failed", extra={"request_id": request_id, "tool": tool_name})
            return {
                "result": None,
                "tool_result": None,
                "error": f"Tool '{tool_name}' rejected input: invalid parameters.",
                "status": "ERROR",
                "final_response": f"Tool '{tool_name}' rejected execution due to invalid input payload.",
                "message": f"Tool '{tool_name}' rejected execution due to invalid input payload.",
                "execution_time_ms": (time.monotonic() - start_time) * 1000.0,
            }

        # Ensure AccessContext instance
        if isinstance(access_context, dict):
            ctx_obj = AccessContext(
                user_id=str(access_context.get("user_id", "ANONYMOUS")),
                role=str(access_context.get("role", "GUEST")),
                department=str(access_context.get("department", "GENERAL")),
                clearance_level=str(access_context.get("clearance_level", "PUBLIC")),
                is_admin=bool(access_context.get("is_admin", False)),
            )
        else:
            ctx_obj = access_context

        # 3. Execute approved tool
        tool_result = tool.execute(input_data, ctx_obj)
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        # 4. Tool Output Validation via ToolOutputValidator
        output_validator = ToolOutputValidator()
        validation_res = output_validator.validate_output(tool_result)
        if not validation_res.is_valid:
            logger.error(
                "ToolExecution: Output validation failed",
                extra={"request_id": request_id, "reason": validation_res.reason},
            )
            return {
                "result": None,
                "tool_result": None,
                "error": f"Tool output validation failed: {validation_res.reason}",
                "status": "ERROR",
                "final_response": f"Tool output security violation: {validation_res.reason}",
                "message": f"Tool output security violation: {validation_res.reason}",
                "execution_time_ms": elapsed_ms,
            }

        if not tool_result.success:
            return {
                "result": None,
                "tool_result": None,
                "error": tool_result.error or "Tool reported execution failure",
                "status": "ERROR",
                "final_response": tool_result.error or "Tool reported execution failure",
                "message": tool_result.error or "Tool reported execution failure",
                "execution_time_ms": elapsed_ms,
            }

        output_data = (
            tool_result.output
            if hasattr(tool_result, "output")
            else (tool_result.data if hasattr(tool_result, "data") else tool_result)
        )
        output_msg = getattr(tool_result, "message", "Tool execution completed successfully.")
        if isinstance(output_data, dict) and "message" in output_data and not output_msg:
            output_msg = output_data["message"]

        return {
            "result": output_data,
            "tool_result": output_data,
            "message": output_msg,
            "final_response": output_msg,
            "status": "COMPLETED",
            "execution_time_ms": elapsed_ms,
        }
    except Exception as exc:
        logger.error("ToolExecution: Tool invocation failed", extra={"request_id": request_id, "error": str(exc)})
        return {
            "result": None,
            "tool_result": None,
            "error": str(exc),
            "status": "ERROR",
            "message": f"Tool execution failed: {str(exc)}",
            "final_response": f"Tool execution failed: {str(exc)}",
            "execution_time_ms": (time.monotonic() - start_time) * 1000.0,
        }
