"""
agent_router.py — Intent and capability routing component for Controlled AI Agent requests.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Set, Optional

from app.config import settings
from app.core.exceptions import AgentRoutingError
from app.core.logger import agent_logger


@dataclass
class RoutingDecision:
    """Structured decision returned by the AgentRouter."""
    capability: str
    confidence: float
    reason: str


class AgentRouter:
    """
    Analyzes request intent and maps it deterministically to an authorized capability:
    - RAG_QUESTION: Synthesis and grounded question-answering over governance documents.
    - RETRIEVAL_SEARCH: Document search, chunk retrieval, and relevance ranking.
    - GOVERNANCE_EVALUATION: Policy compliance checking, approval verification, and rule evaluation.
    """

    CAPABILITY_RAG_QUESTION = "RAG_QUESTION"
    CAPABILITY_RETRIEVAL_SEARCH = "RETRIEVAL_SEARCH"
    CAPABILITY_GOVERNANCE_EVALUATION = "GOVERNANCE_EVALUATION"

    SUPPORTED_CAPABILITIES: Set[str] = {
        CAPABILITY_RAG_QUESTION,
        CAPABILITY_RETRIEVAL_SEARCH,
        CAPABILITY_GOVERNANCE_EVALUATION,
    }

    # Deterministic pattern triggers
    EVALUATION_PATTERNS = [
        r"\bcompliant\b",
        r"\bcompliance\b",
        r"\bevaluate\b",
        r"\bis\s+this\s+(request|action|operation)?\s*(compliant|permitted|allowed|governed)\b",
        r"\bgovernance\s+check\b",
        r"\bverify\s+compliance\b",
        r"\bpolicy\s+check\b",
        r"\brule\s+evaluation\b",
        r"\bcan\s+i\s+(execute|perform|run|access)\b",
    ]

    RETRIEVAL_PATTERNS = [
        r"\bshow\s+(relevant\s+)?(policies|documents|chunks|records|guidelines)\b",
        r"\b(find|search|retrieve|lookup|list)\s+(all\s+)?(policies|documents|chunks|records|guidelines)\b",
        r"\bsearch\s+for\b",
        r"\bretrieve\s+chunks\b",
    ]

    QUESTION_PATTERNS = [
        r"^(what|how|why|who|when|where|explain|describe|clarify|detail)\b",
        r"\?$",
        r"\bwhat\s+is\s+the\s+policy\b",
        r"\bwhat\s+are\s+the\s+(rules|requirements|guidelines)\b",
    ]

    def __init__(self, strategy: Optional[str] = None) -> None:
        self.strategy = strategy or settings.AGENT_ROUTING_STRATEGY

    def route(self, request_text: str) -> RoutingDecision:
        """
        Route request text to an approved capability.

        Args:
            request_text: Natural language user prompt.

        Returns:
            RoutingDecision containing resolved capability, confidence, and explanation.

        Raises:
            AgentRoutingError: If request cannot be routed to a valid capability.
        """
        if not request_text or not isinstance(request_text, str) or not request_text.strip():
            raise AgentRoutingError("Cannot route empty or whitespace request text.")

        cleaned = request_text.strip().lower()

        # 1. Check Governance Evaluation Intent first
        for pattern in self.EVALUATION_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                agent_logger.info(f"AgentRouter: Routed to {self.CAPABILITY_GOVERNANCE_EVALUATION} via pattern '{pattern}'")
                return RoutingDecision(
                    capability=self.CAPABILITY_GOVERNANCE_EVALUATION,
                    confidence=0.95,
                    reason=f"Matched compliance evaluation intent: '{pattern}'",
                )

        # 2. Check Retrieval Search Intent
        for pattern in self.RETRIEVAL_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                agent_logger.info(f"AgentRouter: Routed to {self.CAPABILITY_RETRIEVAL_SEARCH} via pattern '{pattern}'")
                return RoutingDecision(
                    capability=self.CAPABILITY_RETRIEVAL_SEARCH,
                    confidence=0.92,
                    reason=f"Matched document retrieval search intent: '{pattern}'",
                )

        # 3. Check Q&A / RAG Question Intent
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                agent_logger.info(f"AgentRouter: Routed to {self.CAPABILITY_RAG_QUESTION} via pattern '{pattern}'")
                return RoutingDecision(
                    capability=self.CAPABILITY_RAG_QUESTION,
                    confidence=0.90,
                    reason=f"Matched question answering intent: '{pattern}'",
                )

        # 4. Default heuristic: If text contains question indicators or is general query, default safely to RAG
        agent_logger.info(f"AgentRouter: Defaulted to {self.CAPABILITY_RAG_QUESTION} for input: '{cleaned[:60]}...'")
        return RoutingDecision(
            capability=self.CAPABILITY_RAG_QUESTION,
            confidence=0.75,
            reason="Defaulted to knowledge Q&A for general inquiry.",
        )
