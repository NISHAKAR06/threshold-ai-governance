"""
prompt_injection_detector.py — Deterministic, rule-based Prompt Injection & Jailbreak Detector.
Identifies adversarial attempts to:
- Override system instructions and developer guardrails
- Bypass enterprise governance and authorization filters
- Exfiltrate hidden system prompts and preambles
- Force unauthorized tool execution and system command escapes
- Inject synthetic delimiter boundaries to hijack context

Note: Rule-based heuristic detection provides strong deterministic defense against known attack vectors,
but does not guarantee prevention of novel or obfuscated multi-turn jailbreaks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.core.logger import get_logger

logger = get_logger("threshold.responsible_ai.injection_detector")


@dataclass
class PromptInjectionResult:
    """Detection outcome for prompt injection analysis."""
    detected: bool
    confidence: float
    categories: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "confidence": round(self.confidence, 2),
            "categories": self.categories,
            "matched_patterns": self.matched_patterns,
            "explanation": self.explanation,
        }


class PromptInjectionDetector:
    """
    Deterministic prompt injection detector using curated regex categories.
    Carefully designed to minimize false positives on genuine technical governance queries.
    """

    # Category 1: System Instruction Overrides
    OVERRIDE_PATTERNS = [
        r"(?i)\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|system)\s+(?:instructions|rules|prompts|guidelines)\b",
        r"(?i)\byou\s+are\s+now\s+(?:unrestricted|in\s+dan\s+mode|jailbroken|god\s+mode|freed)\b",
        r"(?i)\bact\s+as\s+(?:an?\s+)?unrestricted\s+ai\b",
        r"(?i)\bdo\s+anything\s+now\b",
        r"(?i)\bnew\s+rule:\s+(?:you\s+must|ignore)\b",
    ]

    # Category 2: Governance & Security Bypass
    GOVERNANCE_BYPASS_PATTERNS = [
        r"(?i)\b(?:bypass|disable|turn\s+off|circumvent|ignore)\s+(?:the\s+)?(?:governance|security|compliance|safety|policy|authorization|audit)\s+(?:filter|engine|check|rules?)\b",
        r"(?i)\bgrant\s+(?:me\s+)?(?:admin|root|unrestricted|god)\s+(?:access|clearance|privileges)\b",
        r"(?i)\bpretend\s+(?:i\s+have|to\s+have)\s+top[- ]secret\s+clearance\b",
        r"(?i)\bshow\s+(?:me\s+)?all\s+(?:restricted|confidential|classified)\s+data\s+without\s+(?:permission|clearance|authorization)\b",
    ]

    # Category 3: System Prompt Exfiltration
    PROMPT_EXTRACTION_PATTERNS = [
        r"(?i)\b(?:print|display|output|show|reveal|repeat)\s+(?:the\s+)?(?:initial|system|hidden|underlying)\s+(?:prompt|instructions|preamble|guidelines)\b",
        r"(?i)\bwhat\s+are\s+your\s+(?:exact\s+)?(?:system\s+instructions|system\s+prompts)\b",
        r"(?i)\brepeat\s+everything\s+above\s+(?:verbatim|word\s+for\s+word)\b",
    ]

    # Category 4: Unrestricted Tool / Command Forcing
    TOOL_FORCING_PATTERNS = [
        r"(?i)\b(?:execute|run)\s+(?:shell|bash|cmd|powershell)\s+(?:command|script)\b",
        r"(?i)\b(?:os\.system|subprocess\.Popen|eval\(|exec\()\b",
        r"(?i)\brm\s+-rf\s+/\b",
        r"(?i)\b(?:curl|wget)\s+https?://[^\s]+\s*\|\s*(?:bash|sh)\b",
    ]

    # Category 5: Context Delimiter Hijacking
    DELIMITER_HIJACK_PATTERNS = [
        r"(?i)<\s*\|\s*im_start\s*\|>",
        r"(?i)<\s*\|\s*im_end\s*\|>",
        r"(?i)\[\s*system\s*\]\s*:\s*",
        r"(?i)---\s*BEGIN\s+SYSTEM\s+PROMPT\s*---",
        r"(?i)---\s*END\s+OF\s+SYSTEM\s+PROMPT\s*---",
    ]

    def __init__(self, enabled: bool = True, strict_mode: bool = False) -> None:
        self.enabled = enabled
        self.strict_mode = strict_mode

        # Compile rules
        self.rules: Dict[str, List[re.Pattern]] = {
            "SYSTEM_OVERRIDE": [re.compile(p) for p in self.OVERRIDE_PATTERNS],
            "GOVERNANCE_BYPASS": [re.compile(p) for p in self.GOVERNANCE_BYPASS_PATTERNS],
            "PROMPT_EXTRACTION": [re.compile(p) for p in self.PROMPT_EXTRACTION_PATTERNS],
            "TOOL_FORCING": [re.compile(p) for p in self.TOOL_FORCING_PATTERNS],
            "DELIMITER_HIJACK": [re.compile(p) for p in self.DELIMITER_HIJACK_PATTERNS],
        }

    def detect(self, text: str) -> PromptInjectionResult:
        """
        Analyze input text for prompt injection and governance evasion patterns.
        """
        if not self.enabled or not text or not text.strip():
            return PromptInjectionResult(detected=False, confidence=0.0)

        cleaned = text.strip()
        matched_categories: List[str] = []
        matched_snippets: List[str] = []

        for category, patterns in self.rules.items():
            for pattern in patterns:
                match = pattern.search(cleaned)
                if match:
                    matched_categories.append(category)
                    matched_snippets.append(match.group(0)[:60])
                    break  # one hit per category is sufficient

        if not matched_categories:
            return PromptInjectionResult(detected=False, confidence=0.0)

        # Calculate heuristic confidence
        confidence = min(1.0, 0.65 + (0.15 * len(matched_categories)))
        explanation = f"Detected potential adversarial injection pattern(s) across: {', '.join(matched_categories)}"

        logger.warning(
            "Prompt injection detected in input",
            extra={
                "categories": matched_categories,
                "confidence": round(confidence, 2),
                "snippets": matched_snippets,
            },
        )

        return PromptInjectionResult(
            detected=True,
            confidence=confidence,
            categories=matched_categories,
            matched_patterns=matched_snippets,
            explanation=explanation,
        )
