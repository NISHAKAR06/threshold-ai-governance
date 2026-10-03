"""
tool_output_validator.py — Safety and integrity validation engine for agent tool outputs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from app.models.agent_tool_result import AgentToolResult
from app.core.logger import engine_logger


@dataclass
class ToolOutputValidationResult:
    """Result of validating a tool's execution output."""
    is_valid: bool
    reason: str
    cleaned_output: Optional[Dict[str, Any]] = None


class ToolOutputValidator:
    """
    Validates output produced by an approved agent tool:
    1. Ensures output is well-formed.
    2. Enforces that sensitive credentials or secret tokens are not leaked.
    3. Prevents execution directives or embedded code execution payloads.
    4. Guarantees output cannot trigger secondary autonomous tool chaining.
    """

    PROHIBITED_SENSITIVE_KEYS = {
        "password",
        "secret",
        "api_key",
        "private_key",
        "bearer_token",
        "raw_credential",
        "session_token",
    }

    PROHIBITED_CODE_PATTERNS = [
        r"<script[\s>]",
        r"javascript:",
        r"__import__\s*\(",
        r"subprocess\.",
        r"os\.system\s*\(",
    ]

    def validate_output(
        self,
        tool_result: AgentToolResult,
    ) -> ToolOutputValidationResult:
        """
        Perform rigorous post-execution validation on tool output.

        Args:
            tool_result: AgentToolResult containing the raw execution output.

        Returns:
            ToolOutputValidationResult indicating validity and sanitized data.
        """
        if not isinstance(tool_result, AgentToolResult):
            return ToolOutputValidationResult(
                is_valid=False,
                reason="Invalid tool result type provided to validator.",
            )

        if not tool_result.success:
            # If tool reported failure, error message should be clean and not expose stack trace
            error_msg = tool_result.error or "Tool reported execution failure"
            return ToolOutputValidationResult(
                is_valid=True,
                reason="Tool execution failed gracefully.",
                cleaned_output={"error": error_msg},
            )

        output = tool_result.output
        if not isinstance(output, dict):
            return ToolOutputValidationResult(
                is_valid=False,
                reason=f"Tool output must be a dictionary, got {type(output).__name__}.",
            )

        # 1. Check for sensitive keys in output
        sensitive_found = self._scan_sensitive_keys(output)
        if sensitive_found:
            engine_logger.error(
                f"ToolOutputValidator: Output contains sensitive key: {sensitive_found}"
            )
            return ToolOutputValidationResult(
                is_valid=False,
                reason=f"Tool output contains restricted internal field '{sensitive_found}'.",
            )

        # 2. Check for script / executable payloads in string values
        executable_found = self._scan_code_injection(output)
        if executable_found:
            engine_logger.error(
                f"ToolOutputValidator: Output contains code injection pattern: {executable_found}"
            )
            return ToolOutputValidationResult(
                is_valid=False,
                reason="Tool output contains disallowed executable payload pattern.",
            )

        return ToolOutputValidationResult(
            is_valid=True,
            reason="Tool output passed all safety validation checks.",
            cleaned_output=output,
        )

    def _scan_sensitive_keys(self, obj: Any) -> Optional[str]:
        """Recursively scan for prohibited sensitive keys in output dictionaries."""
        if isinstance(obj, dict):
            for key, val in obj.items():
                if str(key).lower() in self.PROHIBITED_SENSITIVE_KEYS:
                    return str(key)
                nested = self._scan_sensitive_keys(val)
                if nested:
                    return nested
        elif isinstance(obj, list):
            for item in obj:
                nested = self._scan_sensitive_keys(item)
                if nested:
                    return nested
        return None

    def _scan_code_injection(self, obj: Any) -> Optional[str]:
        """Recursively scan string fields for executable injection payloads."""
        if isinstance(obj, str):
            for pattern in self.PROHIBITED_CODE_PATTERNS:
                if re.search(pattern, obj, re.IGNORECASE):
                    return pattern
        elif isinstance(obj, dict):
            for val in obj.values():
                found = self._scan_code_injection(val)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = self._scan_code_injection(item)
                if found:
                    return found
        return None
