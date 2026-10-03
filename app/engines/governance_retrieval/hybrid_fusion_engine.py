"""
hybrid_fusion_engine.py — Merges candidate chunks from semantic and lexical search branches using Reciprocal Rank Fusion (RRF).
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Union
from app.config import settings
from app.models.retrieval_result import RetrievalResultItem
from app.core.logger import engine_logger


class HybridFusionEngine:
    """
    Fuses semantic similarity search results and BM25 keyword search results.
    Default algorithm: Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        strategy: Optional[str] = None,
        rrf_k: Optional[int] = None,
        semantic_weight: float = 1.0,
        keyword_weight: float = 1.0,
    ):
        self.strategy = (strategy or settings.HYBRID_FUSION_STRATEGY).upper()
        self.rrf_k = rrf_k if rrf_k is not None else settings.HYBRID_RRF_K
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def fuse(
        self,
        semantic_candidates: List[Union[RetrievalResultItem, Dict[str, Any]]],
        keyword_candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fuse two candidate result lists into a single ranked list.

        Args:
            semantic_candidates: Ranked results from vector retrieval.
            keyword_candidates: Ranked results from lexical search.
            top_k: Optional maximum number of fused results to return.

        Returns:
            List of merged candidate dicts sorted descending by fused_score.
        """
        if not semantic_candidates and not keyword_candidates:
            return []

        # Maps chunk_id -> dict with merged candidate info and RRF score accumulator
        merged_candidates: Dict[str, Dict[str, Any]] = {}

        # 1. Process Semantic Candidates
        for rank_idx, cand in enumerate(semantic_candidates, start=1):
            chunk_dict = self._to_dict(cand)
            chunk_id = chunk_dict.get("chunk_id")
            if not chunk_id:
                continue

            sem_score = chunk_dict.get("score")

            if chunk_id not in merged_candidates:
                merged_candidates[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": chunk_dict.get("document_id", ""),
                    "text": chunk_dict.get("text", ""),
                    "metadata": chunk_dict.get("metadata", {}),
                    "source": chunk_dict.get("source", {}),
                    "semantic_score": sem_score,
                    "keyword_score": None,
                    "fused_score": 0.0,
                }
            else:
                merged_candidates[chunk_id]["semantic_score"] = sem_score

            rrf_contribution = self.semantic_weight / (self.rrf_k + rank_idx)
            merged_candidates[chunk_id]["fused_score"] += rrf_contribution

        # 2. Process Keyword Candidates
        for rank_idx, cand in enumerate(keyword_candidates, start=1):
            chunk_dict = self._to_dict(cand)
            chunk_id = chunk_dict.get("chunk_id")
            if not chunk_id:
                continue

            kw_score = chunk_dict.get("lexical_score", chunk_dict.get("score"))

            if chunk_id not in merged_candidates:
                merged_candidates[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": chunk_dict.get("document_id", ""),
                    "text": chunk_dict.get("text", ""),
                    "metadata": chunk_dict.get("metadata", {}),
                    "source": chunk_dict.get("source", {}),
                    "semantic_score": None,
                    "keyword_score": kw_score,
                    "fused_score": 0.0,
                }
            else:
                merged_candidates[chunk_id]["keyword_score"] = kw_score
                # Fill missing fields if semantic candidate lacked text/meta
                if not merged_candidates[chunk_id].get("text"):
                    merged_candidates[chunk_id]["text"] = chunk_dict.get("text", "")
                if not merged_candidates[chunk_id].get("metadata"):
                    merged_candidates[chunk_id]["metadata"] = chunk_dict.get("metadata", {})

            rrf_contribution = self.keyword_weight / (self.rrf_k + rank_idx)
            merged_candidates[chunk_id]["fused_score"] += rrf_contribution

        # 3. Sort descending by fused_score; break ties deterministically by chunk_id
        fused_list = list(merged_candidates.values())
        fused_list.sort(key=lambda item: (-item["fused_score"], item["chunk_id"]))

        # Round fused scores
        for item in fused_list:
            item["fused_score"] = round(item["fused_score"], 6)

        engine_logger.info(
            f"HybridFusionEngine: Fused {len(semantic_candidates)} semantic and "
            f"{len(keyword_candidates)} keyword candidates into {len(fused_list)} unique candidates"
        )

        if top_k is not None and top_k > 0:
            return fused_list[:top_k]
        return fused_list

    @staticmethod
    def _to_dict(cand: Union[RetrievalResultItem, Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize candidate representation to dictionary."""
        if isinstance(cand, dict):
            return cand
        elif hasattr(cand, "to_dict"):
            return cand.to_dict()
        else:
            return {
                "chunk_id": getattr(cand, "chunk_id", ""),
                "document_id": getattr(cand, "document_id", ""),
                "text": getattr(cand, "text", ""),
                "score": getattr(cand, "score", 0.0),
                "metadata": getattr(cand, "metadata", {}),
                "source": getattr(cand, "source", {}),
            }
