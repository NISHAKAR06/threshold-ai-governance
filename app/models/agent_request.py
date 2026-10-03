"""
agent_request.py — Domain model representing an agent request with security access context.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union

from app.models.access_context import AccessContext


@dataclass
class AgentRequest:
    """
    Domain request model for controlled AI agent execution.
    Contains user instruction and validated access context.
    """
    request: str
    access_context: AccessContext
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.request:
            self.request = self.request.strip()
        if not self.request_id:
            self.request_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request": self.request,
            "conversation_id": self.conversation_id,
            "access_context": self.access_context.to_dict() if hasattr(self.access_context, "to_dict") else vars(self.access_context),
            "metadata": self.metadata,
        }
