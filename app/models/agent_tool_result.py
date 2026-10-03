"""
agent_tool_result.py — Domain model representing the execution output of an approved agent tool.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class AgentToolResult:
    """Execution output and metadata produced by an authorized agent tool."""
    tool_name: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentToolResult":
        return cls(
            tool_name=data.get("tool_name", "unknown_tool"),
            success=data.get("success", False),
            output=data.get("output", {}),
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
        )
