"""
input_guard.py — Responsible AI Input Guardrail.
Validates user input before allowing requests into RAG, Retrieval, or Agent pipelines:
- Size bounds checking (preventing context stuffing and buffer flooding)
- Malformed / binary input sanitization (null bytes, non-printable control sequences)
- Prompt injection and jailbreak pattern detection
- Deterministic structured decision: ALLOW, BLOCK, REVIEW
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

from app.config import settings
from app.responsible_ai.prompt_injection_detector import (
    PromptInjectionDetector,
    PromptInjectionResult,
)
from app.observability.metrics import (
    record_rai_decision,
    record_prompt_injection_detected,
)
from app.core.logger import get_logger

logger = get_logger("threshold.responsible_ai.input_guard")


class GuardDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


@dataclass
class InputGuardResult:
    """Structured decision returned by Responsible AI Input Guard."""
    decision: GuardDecision
    reason: str
    risk_score: float
    violations: List[str] = field(default_factory=list)
    sanitized_text: str = ""
    injection_details: Optional[PromptInjectionResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "risk_score": round(self.risk_score, 2),
            "violations": self.violations,
            "sanitized_text": self.sanitized_text,
            "injection_details": self.injection_details.to_dict() if self.injection_details else None,
        }


class ResponsibleAIInputGuard:
    """
    Production input guardrail for AI workflows.
    Ensures input text is safe, bounded, well-formed, and free of adversarial bypass vectors.
    """

    def __init__(
        self,
        max_length: Optional[int] = None,
        injection_detector: Optional[PromptInjectionDetector] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.enabled = settings.RAI_ENABLED if enabled is None else enabled
        self.max_length = max_length or settings.RAI_MAX_INPUT_LENGTH
        self.detector = injection_detector or PromptInjectionDetector(
            enabled=settings.RAI_INJECTION_DETECTION_ENABLED,
            strict_mode=settings.RAI_STRICT_MODE,
        )

    def validate_input(self, text: Any) -> InputGuardResult:
        """
        Validate incoming request text against Responsible AI guardrails.
        """
        if not self.enabled:
            return InputGuardResult(
                decision=GuardDecision.ALLOW,
                reason="Input guardrail disabled by configuration.",
                risk_score=0.0,
                sanitized_text=str(text or ""),
            )

        # 1. Type validation
        if not isinstance(text, str):
            record_rai_decision(GuardDecision.BLOCK.value)
            return InputGuardResult(
                decision=GuardDecision.BLOCK,
                reason="Input must be a valid string.",
                risk_score=1.0,
                violations=["INVALID_DATA_TYPE"],
            )

        # 2. Empty / whitespace check
        trimmed = text.strip()
        if not trimmed:
            record_rai_decision(GuardDecision.BLOCK.value)
            return InputGuardResult(
                decision=GuardDecision.BLOCK,
                reason="Input text cannot be empty or solely whitespace.",
                risk_score=0.5,
                violations=["EMPTY_INPUT"],
            )

        # 3. Size validation
        if len(text) > self.max_length:
            record_rai_decision(GuardDecision.BLOCK.value)
            logger.warning("Input rejected: length %d exceeds max %d", len(text), self.max_length)
            return InputGuardResult(
                decision=GuardDecision.BLOCK,
                reason=f"Input length ({len(text)}) exceeds maximum allowed limit of {self.max_length} characters.",
                risk_score=0.9,
                violations=["EXCESSIVE_LENGTH"],
            )

        # 4. Malformed content detection: Null bytes, dangerous non-printable chars
        if "\x00" in text:
            record_rai_decision(GuardDecision.BLOCK.value)
            return InputGuardResult(
                decision=GuardDecision.BLOCK,
                reason="Malformed input: null byte characters detected.",
                risk_score=1.0,
                violations=["MALFORMED_NULL_BYTES"],
            )

        # Filter unprintable control codes (except standard newlines/tabs)
        sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # 5. Prompt injection analysis
        injection_result = self.detector.detect(sanitized)
        if injection_result.detected:
            for cat in injection_result.categories:
                record_prompt_injection_detected(cat)

            # In strict mode or multi-category hits, block immediately
            # If low confidence or single suspicious word, route to REVIEW
            if injection_result.confidence >= 0.7 or "GOVERNANCE_BYPASS" in injection_result.categories:
                decision = GuardDecision.BLOCK
                reason = f"Security Violation: {injection_result.explanation}"
            else:
                decision = GuardDecision.REVIEW
                reason = f"Compliance Review Required: {injection_result.explanation}"

            record_rai_decision(decision.value)
            return InputGuardResult(
                decision=decision,
                reason=reason,
                risk_score=injection_result.confidence,
                violations=injection_result.categories,
                sanitized_text=sanitized,
                injection_details=injection_result,
            )

        # 6. Pass all checks
        record_rai_decision(GuardDecision.ALLOW.value)
        return InputGuardResult(
            decision=GuardDecision.ALLOW,
            reason="Input validation passed all Responsible AI checks.",
            risk_score=0.0,
            sanitized_text=sanitized,
        )
