"""
output_guard.py — Responsible AI Output Guardrail.
Validates generated answers and agent responses prior to client delivery:
- Enforces valid response data structures
- Citation verification: verifies cited sources correspond to authorized context items
- Unauthorized source leak prevention: blocks responses referencing unauthorized document/chunk identifiers
- Secret & credential leakage protection: checks for accidental leaks of API keys, tokens, or DB URIs
- Returns structured validation decision without fabricating or hallucinative rewriting
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Union

from app.config import settings
from app.observability.metrics import record_rai_output, record_governance_event
from app.core.logger import get_logger

logger = get_logger("threshold.responsible_ai.output_guard")


@dataclass
class OutputGuardResult:
    """Structured decision returned by Responsible AI Output Guard."""
    is_valid: bool
    status: str  # "PASS" or "FAIL"
    violations: List[str] = field(default_factory=list)
    sanitized_output: Optional[Any] = None
    audit_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "violations": self.violations,
            "audit_details": self.audit_details,
        }


class ResponsibleAIOutputGuard:
    """
    Validates final pipeline answers and responses to guarantee security,
    privacy, and citation integrity.
    """

    # Secret scanning patterns
    SECRET_PATTERNS = [
        (r"(?i)AIza[0-9A-Za-z-_]{35}", "GOOGLE_API_KEY_LEAK"),
        (r"(?i)sk-[A-Za-z0-9]{32,}", "OPENAI_API_KEY_LEAK"),
        (r"(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "PRIVATE_KEY_LEAK"),
        (r"(?i)(?:postgres|mysql|sqlite|mongodb)\+?[a-z]*://[^\s:]+:[^\s@]+@[^\s]+", "DATABASE_URI_LEAK"),
        (r"(?i)bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "JWT_TOKEN_LEAK"),
        # AWS access keys: AKIA followed by 16 uppercase alphanumeric characters
        (r"(?i)\bAKIA[0-9A-Z]{16}\b", "AWS_ACCESS_KEY_LEAK"),
        # GitHub personal access tokens (classic format)
        (r"(?i)\bghp_[A-Za-z0-9]{36,}\b", "GITHUB_TOKEN_LEAK"),
        # Generic high-entropy API key label patterns
        (r"(?i)(?:api_key|access_token|secret_key)\s*[=:]\s*[A-Za-z0-9-_]{32,}", "GENERIC_API_KEY_LEAK"),
    ]

    CITATION_PATTERN = re.compile(r"\[(?:Source|Doc|Chunk)\s*(\d+)\]", re.IGNORECASE)

    def __init__(self, enabled: Optional[bool] = None) -> None:
        self.enabled = (
            settings.RAI_OUTPUT_VALIDATION_ENABLED
            if enabled is None
            else enabled
        )
        self.compiled_secrets = [
            (re.compile(pattern), code) for pattern, code in self.SECRET_PATTERNS
        ]

    def validate_rag_output(
        self,
        answer: str,
        authorized_sources: List[Any],
        unauthorized_source_ids: Optional[Set[str]] = None,
    ) -> OutputGuardResult:
        """
        Validate RAG answer text against citations, secrets, and unauthorized source leaks.
        """
        if not self.enabled:
            return OutputGuardResult(is_valid=True, status="PASS", sanitized_output=answer)

        violations: List[str] = []
        unauth_ids = unauthorized_source_ids or set()

        # 1. Structural check
        if not isinstance(answer, str) or not answer.strip():
            violations.append("EMPTY_OR_INVALID_ANSWER_STRUCTURE")

        # 2. Secret & Credential Scanning
        for regex, code in self.compiled_secrets:
            if regex.search(answer):
                violations.append(code)
                record_governance_event("output_secret_leak_detected")
                logger.error("Output guard detected confidential credential leak: %s", code)

        # 3. Citation Validity
        # Extract cited indices e.g. [Source 1], [Source 2]
        cited_indices = set()
        for match in self.CITATION_PATTERN.finditer(answer):
            try:
                idx = int(match.group(1))
                cited_indices.add(idx)
            except ValueError:
                pass

        valid_source_count = len(authorized_sources)
        invalid_citations = [idx for idx in cited_indices if idx < 1 or idx > valid_source_count]
        if invalid_citations:
            violations.append(f"INVALID_CITATION_INDICES_{invalid_citations}")
            logger.warning("Output contains citations outside authorized source range: %s", invalid_citations)

        # 4. Unauthorized Source IDs Leaked into Output
        for unauth_id in unauth_ids:
            if unauth_id in answer:
                violations.append(f"UNAUTHORIZED_SOURCE_LEAK_{unauth_id}")
                record_governance_event("output_unauthorized_source_leak")
                logger.error("CRITICAL: Unauthorized source identifier leaked in output: %s", unauth_id)

        # 5. Determine Result
        if violations:
            record_rai_output("FAIL")
            record_governance_event("output_validation_failure")
            return OutputGuardResult(
                is_valid=False,
                status="FAIL",
                violations=violations,
                sanitized_output=None,
                audit_details={"citation_count": len(cited_indices), "violations": violations},
            )

        record_rai_output("PASS")
        return OutputGuardResult(
            is_valid=True,
            status="PASS",
            violations=[],
            sanitized_output=answer,
            audit_details={"citation_count": len(cited_indices)},
        )

    def validate_agent_output(self, output: Dict[str, Any]) -> OutputGuardResult:
        """
        Validate Controlled Agent dictionary output for sensitive secret leaks or invalid structures.
        """
        if not self.enabled:
            return OutputGuardResult(is_valid=True, status="PASS", sanitized_output=output)

        violations: List[str] = []
        output_str = str(output)

        for regex, code in self.compiled_secrets:
            if regex.search(output_str):
                violations.append(code)
                record_governance_event("agent_output_secret_leak")

        if violations:
            record_rai_output("FAIL")
            return OutputGuardResult(
                is_valid=False,
                status="FAIL",
                violations=violations,
                sanitized_output=None,
                audit_details={"violations": violations},
            )

        record_rai_output("PASS")
        return OutputGuardResult(
            is_valid=True,
            status="PASS",
            violations=[],
            sanitized_output=output,
        )
