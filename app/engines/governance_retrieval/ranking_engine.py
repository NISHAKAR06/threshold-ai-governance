"""
ranking_engine.py — Produces final ordered and truncated list of authorized retrieval results.
"""
from __future__ import annotations

from typing import List, Dict, Any
from app.models.governance_retrieval_result import GovernanceRetrievalResultItem
from app.core.logger import engine_logger


class RankingEngine:
    """
    Ranks authorized candidates by fused relevance score, enforces top_k limits,
    resolves score ties deterministically, and maps records into domain result models.
    """

    @staticmethod
    def rank(
        authorized_candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[GovernanceRetrievalResultItem]:
        """
        Rank authorized candidates, truncate to top_k, and construct result items.

        Args:
            authorized_candidates: Filtered list of candidate dictionaries.
            top_k: Number of top results to return.

        Returns:
            List of GovernanceRetrievalResultItem objects with 1-based ranks.
        """
        if not authorized_candidates or top_k <= 0:
            return []

        # Sort descending by fused_score; break ties deterministically by chunk_id
        sorted_candidates = sorted(
            authorized_candidates,
            key=lambda c: (-c.get("fused_score", 0.0), c.get("chunk_id", "")),
        )

        ranked_results: List[GovernanceRetrievalResultItem] = []
        for idx, cand in enumerate(sorted_candidates[:top_k], start=1):
            item = GovernanceRetrievalResultItem(
                rank=idx,
                fused_score=round(cand.get("fused_score", 0.0), 6),
                chunk_id=cand.get("chunk_id", ""),
                document_id=cand.get("document_id", ""),
                text=cand.get("text", ""),
                metadata=cand.get("metadata", {}),
                source=cand.get("source", {}),
                semantic_score=cand.get("semantic_score"),
                keyword_score=cand.get("keyword_score"),
            )
            ranked_results.append(item)

        engine_logger.debug(f"RankingEngine: Ranked {len(ranked_results)} final items (top_k={top_k})")
        return ranked_results
