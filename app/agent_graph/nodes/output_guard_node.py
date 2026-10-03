"""
output_guard_node.py — Responsible AI Output Safety Node for LangGraph.

Validates all graph outputs using ResponsibleAIOutputGuard to prevent:
- Disclosure of system prompt templates or chain-of-thought
- Unredacted credentials, tokens, or PII
- Metadata leakage from unauthorized documents
"""
from __future__ import annotations

from typing import Dict, Any
from app.agent_graph.state import AgentGraphState
from app.responsible_ai.output_guard import ResponsibleAIOutputGuard
from app.core.logger import get_logger

logger = get_logger("threshold.agent_graph.output_guard")


def output_guard_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Validates agent outputs against Responsible AI safety rules.
    """
    request_id = state.get("request_id", "unknown")
    result = state.get("result")
    message = state.get("message") or ""
    retrieval_context = state.get("retrieval_context") or []

    guard = ResponsibleAIOutputGuard()

    violations = []
    # 1. Validate textual message
    if message:
        out_res = guard.validate_agent_output(message)
        if not out_res.is_valid:
            violations.extend(out_res.violations)

    # 2. If RAG result is present, check grounding against authorized sources
    if isinstance(result, dict) and "answer" in result:
        rag_res = guard.validate_rag_output(
            answer=result["answer"],
            authorized_sources=retrieval_context,
        )
        if not rag_res.is_valid:
            violations.extend(rag_res.violations)

    # 3. Check for chain-of-thought or internal reasoning leakage
    import re
    cot_patterns = [
        r"(?i)\bthought:\s*",
        r"(?i)\binternal reasoning:\s*",
        r"(?i)\bchain[- ]of[- ]thought\b",
        r"(?i)\bsystem prompt\b",
    ]
    target_text = str(message) + " " + str(result.get("answer", "") if isinstance(result, dict) else "")
    for pattern in cot_patterns:
        if re.search(pattern, target_text):
            violations.append("CHAIN_OF_THOUGHT_LEAK_DETECTED")
            break

    if violations:
        logger.warning(
            "OutputGuard: Policy violations detected in output",
            extra={"request_id": request_id, "violations": violations},
        )
        sanitized_msg = "[Response sanitized by Responsible AI Output Guard due to security policy violations.]"
        return {
            "output_violations": violations,
            "error": f"Output policy violations detected: {', '.join(violations)}",
            "message": sanitized_msg,
            "final_response": sanitized_msg,
        }

    return {
        "output_violations": [],
        "final_response": message,
    }
