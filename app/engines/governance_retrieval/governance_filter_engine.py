"""
governance_filter_engine.py — Filters fused candidate chunks according to requester AccessContext.
Prevents unauthorized chunk contents from leaking into retrieval results.
"""
from __future__ import annotations

from typing import List, Dict, Any, Tuple, Optional

from app.models.access_context import AccessContext
from app.engines.governance_retrieval.access_validator import AccessValidator
from app.core.logger import engine_logger
from app.core.exceptions import GovernanceFilteringError


class GovernanceFilterEngine:
    """
    Applies security policies and access controls across fused candidate chunks.
    Filters out any chunks failing role, classification, department, or lifecycle checks.
    """

    def __init__(self, validator: Optional[AccessValidator] = None):
        self.validator = validator or AccessValidator()

    def filter_candidates(
        self,
        candidates: List[Dict[str, Any]],
        access_context: AccessContext,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Filter candidate chunks against requester access context.

        Args:
            candidates: List of fused candidate dictionaries.
            access_context: Requester's verified AccessContext.

        Returns:
            Tuple of (authorized_candidates, denied_count).
        """
        if not candidates:
            return [], 0

        if not access_context:
            engine_logger.warning("GovernanceFilterEngine: Missing access_context; denying all candidates")
            return [], len(candidates)

        authorized: List[Dict[str, Any]] = []
        denied_count: int = 0

        for cand in candidates:
            chunk_id = cand.get("chunk_id", "UNKNOWN")
            meta = cand.get("metadata", {})

            try:
                decision = self.validator.validate_access(access_context, meta)
                if decision.is_allowed:
                    authorized.append(cand)
                else:
                    denied_count += 1
                    engine_logger.debug(
                        f"GovernanceFilterEngine: Denied chunk '{chunk_id}' for user "
                        f"'{access_context.user_id}' ({access_context.role}): {decision.reason}"
                    )
            except Exception as exc:
                denied_count += 1
                engine_logger.error(
                    f"GovernanceFilterEngine: Error validating chunk '{chunk_id}': {exc}"
                )

        engine_logger.info(
            f"GovernanceFilterEngine: Evaluated {len(candidates)} candidates -> "
            f"{len(authorized)} authorized, {denied_count} denied"
        )
        return authorized, denied_count
