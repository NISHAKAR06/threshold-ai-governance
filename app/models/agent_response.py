"""
agent_response.py — Structured response model returned by the Controlled AI Agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class AgentResponse:
    """Structured response object produced by AgentService."""
    request_id: str
    status: str                                  # SUCCESS, DENIED, REVIEW_REQUIRED, ERROR
    capability: str                              # RAG_QUESTION, RETRIEVAL_SEARCH, GOVERNANCE_EVALUATION
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    audit_reference: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "request_id": self.request_id,
            "status": self.status,
            "capability": self.capability,
            "audit_reference": self.audit_reference,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }
        if self.result is not None:
            data["result"] = self.result
        if self.message is not None:
            data["message"] = self.message
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        return cls(
            request_id=data["request_id"],
            status=data["status"],
            capability=data.get("capability", "UNKNOWN"),
            result=data.get("result"),
            message=data.get("message"),
            audit_reference=data.get("audit_reference"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
        )
