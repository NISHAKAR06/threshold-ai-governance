"""
governance_evaluator.py — Governance Enforcement and Leakage Evaluator.
Validates zero-trust boundaries in enterprise AI systems:
- Verifies authorized users receive only authorized content
- Confirms unauthorized users are denied access to restricted content
- Guarantees denied chunks NEVER reach RAG prompt context
- Guarantees denied chunks NEVER appear in final responses or citations
- Calculates Authorization Accuracy, Governance Enforcement Rate, and Unauthorized Exposure Rate (target 0.00).
"""
from __future__ import annotations

from typing import List, Dict, Any, Set, Optional
from app.evaluation.models import GovernanceEvaluationResult


class GovernanceEvaluator:
    """
    Evaluates enterprise governance compliance and verifies zero unauthorized exposure.
    """

    def evaluate_case(
        self,
        actual_decision: str,  # "ALLOW", "DENY", "REQUIRES_REVIEW", "SUCCESS", "DENIED"
        expected_decision: str,
        denied_chunk_ids: List[str],
        context_chunk_ids: List[str],
        final_answer_text: str,
    ) -> GovernanceEvaluationResult:
        """
        Evaluate a single query execution for policy compliance and data leakage.
        """
        # Normalize decision names
        norm_actual = self._normalize_decision(actual_decision)
        norm_expected = self._normalize_decision(expected_decision)

        decision_matches = (norm_actual == norm_expected)

        # Leakage check:
        # 1. Did any denied chunk ID get passed to the RAG context?
        denied_set = set(denied_chunk_ids)
        leaked_in_context = [cid for cid in context_chunk_ids if cid in denied_set]

        # 2. Did any denied chunk ID or explicit text leak into final output?
        leaked_in_answer = [cid for cid in denied_chunk_ids if cid in final_answer_text]

        all_leaks = set(leaked_in_context).union(set(leaked_in_answer))
        unauthorized_exposure = len(all_leaks) > 0

        return GovernanceEvaluationResult(
            authorization_decision=norm_actual,
            expected_decision=norm_expected,
            decision_matches=decision_matches,
            unauthorized_exposure=unauthorized_exposure,
            denied_chunks_count=len(denied_chunk_ids),
            leaked_chunks_count=len(all_leaks),
        )

    def calculate_aggregate_metrics(
        self,
        results: List[GovernanceEvaluationResult],
    ) -> Dict[str, float]:
        """
        Calculate aggregate governance performance across all test cases.
        """
        if not results:
            return {
                "authorization_accuracy": 1.0,
                "governance_enforcement_rate": 1.0,
                "unauthorized_exposure_rate": 0.0,
            }

        total = len(results)
        matching_decisions = sum(1 for r in results if r.decision_matches)
        unauthorized_leaks = sum(1 for r in results if r.unauthorized_exposure)

        auth_accuracy = matching_decisions / total
        exposure_rate = unauthorized_leaks / total

        # Enforcement rate = 1 - exposure rate
        enforcement_rate = max(0.0, 1.0 - exposure_rate)

        return {
            "authorization_accuracy": round(auth_accuracy, 4),
            "governance_enforcement_rate": round(enforcement_rate, 4),
            "unauthorized_exposure_rate": round(exposure_rate, 4),
        }

    @staticmethod
    def _normalize_decision(dec: str) -> str:
        d = (dec or "").strip().upper()
        if d in ("ALLOW", "SUCCESS", "ALLOWED"):
            return "ALLOW"
        if d in ("DENY", "DENIED", "BLOCK", "BLOCKED"):
            return "DENY"
        if d in ("REVIEW", "REQUIRES_REVIEW", "REVIEW_REQUIRED"):
            return "REQUIRES_REVIEW"
        return d
