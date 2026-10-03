"""
hybrid_retrieval_service.py — Orchestrates hybrid semantic + keyword retrieval, fusion, and governance filtering.
"""
from __future__ import annotations

import time
from typing import Optional, Union, Dict, Any, List

from app.config import settings
from app.models.access_context import AccessContext
from app.models.hybrid_retrieval_response import HybridRetrievalResponse
from app.engines.retrieval.query_validator import QueryValidator
from app.services.retrieval_service import RetrievalService
from app.engines.governance_retrieval.keyword_search_engine import KeywordSearchEngine
from app.engines.governance_retrieval.hybrid_fusion_engine import HybridFusionEngine
from app.engines.governance_retrieval.governance_filter_engine import GovernanceFilterEngine
from app.engines.governance_retrieval.ranking_engine import RankingEngine
from app.core.exceptions import (
    AccessContextValidationError,
    InvalidRetrievalQueryError,
    QueryValidationError,
    HybridRetrievalError,
)
from app.core.logger import service_logger


class HybridRetrievalService:
    """
    Orchestration layer coordinating Phase 12 Hybrid Search and Governance-Aware Retrieval:
    1. Validates query and requester AccessContext.
    2. Retrieves candidate pools in parallel from Semantic (Dense) and Lexical (BM25) branches.
    3. Fuses candidates using Reciprocal Rank Fusion (RRF).
    4. Evaluates governance policies (Role, Clearance, Department, Lifecycle status).
    5. Produces final ranked and authorized HybridRetrievalResponse.
    """

    def __init__(
        self,
        semantic_service: Optional[RetrievalService] = None,
        keyword_engine: Optional[KeywordSearchEngine] = None,
        query_validator: Optional[QueryValidator] = None,
        fusion_engine: Optional[HybridFusionEngine] = None,
        governance_filter: Optional[GovernanceFilterEngine] = None,
        ranking_engine: Optional[RankingEngine] = None,
        candidate_multiplier: Optional[int] = None,
    ):
        self.semantic_service = semantic_service or RetrievalService()
        self.keyword_engine = keyword_engine or KeywordSearchEngine()
        self.query_validator = query_validator or QueryValidator()
        self.fusion_engine = fusion_engine or HybridFusionEngine()
        self.governance_filter = governance_filter or GovernanceFilterEngine()
        self.ranking_engine = ranking_engine or RankingEngine()
        self.candidate_multiplier = (
            candidate_multiplier
            if candidate_multiplier is not None
            else settings.HYBRID_CANDIDATE_MULTIPLIER
        )

    def retrieve(
        self,
        query: str,
        access_context: Union[AccessContext, Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> HybridRetrievalResponse:
        """
        Execute hybrid search and governance-filtered retrieval.

        Args:
            query: User search query string.
            access_context: User identity, role, department, and clearance level.
            top_k: Number of authorized chunks to return.

        Returns:
            HybridRetrievalResponse containing authorized, ranked chunks.
        """
        start_time = time.perf_counter()

        # 1. Validate AccessContext
        ctx = self._resolve_access_context(access_context)

        # 2. Validate Query
        val_result = self.query_validator.validate(query, top_k=top_k, raise_exception=True)
        cleaned_query = val_result.cleaned_query
        effective_top_k = val_result.cleaned_top_k

        service_logger.info(
            f"HybridRetrievalService: Request from user='{ctx.user_id}' role='{ctx.role}' "
            f"clearance='{ctx.clearance_level}' (query_len={len(cleaned_query)}, top_k={effective_top_k})"
        )

        # Candidate pool size to retrieve from each branch before filtering
        branch_k = min(
            settings.RETRIEVAL_MAX_TOP_K * self.candidate_multiplier,
            effective_top_k * self.candidate_multiplier,
        )

        # 3. Retrieve Semantic Candidates
        semantic_candidates = []
        try:
            sem_response = self.semantic_service.retrieve(query=cleaned_query, top_k=branch_k)
            semantic_candidates = sem_response.results
        except Exception as exc:
            service_logger.warning(
                f"HybridRetrievalService: Semantic retrieval branch encountered error: {exc}"
            )

        # 4. Retrieve Lexical / Keyword Candidates
        keyword_candidates = []
        if settings.KEYWORD_SEARCH_ENABLED:
            try:
                keyword_candidates = self.keyword_engine.search(query=cleaned_query, top_k=branch_k)
            except Exception as exc:
                service_logger.warning(
                    f"HybridRetrievalService: Keyword search branch encountered error: {exc}"
                )

        # 5. Hybrid Fusion (RRF)
        fused_candidates = self.fusion_engine.fuse(
            semantic_candidates=semantic_candidates,
            keyword_candidates=keyword_candidates,
        )

        # 6. Governance-Aware Filtering (Role, Clearance, Department)
        authorized_candidates, denied_count = self.governance_filter.filter_candidates(
            candidates=fused_candidates,
            access_context=ctx,
        )

        # 7. Final Ranking & Truncation to effective_top_k
        final_results = self.ranking_engine.rank(
            authorized_candidates=authorized_candidates,
            top_k=effective_top_k,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        service_logger.info(
            f"HybridRetrievalService: Completed in {elapsed_ms:.1f}ms -> "
            f"{len(semantic_candidates)} sem, {len(keyword_candidates)} kw -> "
            f"{len(fused_candidates)} fused -> {len(final_results)} authorized returned "
            f"({denied_count} denied)"
        )

        return HybridRetrievalResponse(
            query=cleaned_query,
            requested_top_k=effective_top_k,
            authorized_result_count=len(final_results),
            denied_count=denied_count,
            execution_time_ms=elapsed_ms,
            results=final_results,
            fusion_strategy=self.fusion_engine.strategy,
            semantic_candidate_count=len(semantic_candidates),
            keyword_candidate_count=len(keyword_candidates),
        )

    @staticmethod
    def _resolve_access_context(
        access_context: Union[AccessContext, Dict[str, Any]],
    ) -> AccessContext:
        """Validate and construct an AccessContext domain object."""
        if access_context is None:
            raise AccessContextValidationError("Access context is required for governance-aware retrieval")

        if isinstance(access_context, AccessContext):
            ctx = access_context
        elif isinstance(access_context, dict):
            ctx = AccessContext.from_dict(access_context)
        else:
            raise AccessContextValidationError(
                f"Unsupported access context format: {type(access_context).__name__}"
            )

        if not ctx.user_id or not ctx.user_id.strip():
            raise AccessContextValidationError("AccessContext user_id is missing or empty")
        if not ctx.role or not ctx.role.strip():
            raise AccessContextValidationError("AccessContext role is missing or empty")

        return ctx
