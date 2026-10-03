"""
agent_decision.py — Domain models representing governance policy decisions and tool authorization decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AgentPolicyDecision:
    """Outcome of governance policy evaluation for an agent request."""
    decision: str  # ALLOW, DENY, REQUIRES_REVIEW
    reason: str
    evaluated_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_allowed(self) -> bool:
        return self.decision == "ALLOW"

    @property
    def is_denied(self) -> bool:
        return self.decision == "DENY"

    @property
    def requires_review(self) -> bool:
        return self.decision == "REQUIRES_REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "evaluated_rules": self.evaluated_rules,
            "metadata": self.metadata,
        }


@dataclass
class ToolAuthDecision:
    """Outcome of tool authorization check prior to tool execution."""
    tool_name: str
    is_authorized: bool
    status: str  # ALLOW, DENY, REQUIRES_REVIEW
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "is_authorized": self.is_authorized,
            "status": self.status,
            "reason": self.reason,
            "metadata": self.metadata,
        }
