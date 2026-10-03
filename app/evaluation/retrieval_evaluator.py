"""
retrieval_evaluator.py — Deterministic Retrieval Metrics Evaluator.
Computes standard information retrieval metrics without requiring LLM calls:
- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR)
- Authorized Retrieval Accuracy
- Unauthorized Retrieval Rate
"""
from __future__ import annotations

from typing import List, Set, Any, Optional
from app.evaluation.models import RetrievalEvaluationResult


class RetrievalEvaluator:
    """
    Evaluates candidate retrieval quality against expected ground-truth chunks or documents.
    """

    def evaluate(
        self,
        retrieved_chunk_ids: List[str],
        expected_chunk_ids: List[str],
        authorized_chunk_ids: Optional[Set[str]] = None,
        k: int = 5,
    ) -> RetrievalEvaluationResult:
        """
        Compute retrieval performance metrics for a single query.

        Args:
            retrieved_chunk_ids: Ordered list of retrieved chunk identifiers.
            expected_chunk_ids: Ground truth relevant chunk identifiers.
            authorized_chunk_ids: Set of chunk IDs that the user was permitted to see.
            k: Top-K evaluation cutoff.

        Returns:
            RetrievalEvaluationResult with deterministic scores.
        """
        k = max(1, k)
        top_retrieved = retrieved_chunk_ids[:k]
        top_set = set(top_retrieved)
        expected_set = set(expected_chunk_ids)

        # 1. Precision@K
        # |retrieved ∩ expected| / min(k, len(retrieved)) or 0 if retrieved is empty
        if not top_retrieved:
            precision_at_k = 0.0
        else:
            intersection = top_set.intersection(expected_set)
            precision_at_k = len(intersection) / len(top_retrieved)

        # 2. Recall@K
        # |retrieved ∩ expected| / |expected|
        if not expected_set:
            recall_at_k = 1.0 if not top_retrieved else 0.0
        else:
            intersection = top_set.intersection(expected_set)
            recall_at_k = len(intersection) / len(expected_set)

        # 3. Reciprocal Rank (RR)
        # 1 / rank of first relevant chunk found
        rr = 0.0
        for rank, chunk_id in enumerate(top_retrieved, start=1):
            if chunk_id in expected_set:
                rr = 1.0 / rank
                break

        # 4. Authorized Retrieval Accuracy & Unauthorized Retrieval Rate
        if authorized_chunk_ids is not None and top_retrieved:
            authorized_count = sum(1 for cid in top_retrieved if cid in authorized_chunk_ids)
            unauthorized_count = len(top_retrieved) - authorized_count
            auth_accuracy = authorized_count / len(top_retrieved)
            unauth_rate = unauthorized_count / len(top_retrieved)
        else:
            auth_accuracy = 1.0
            unauth_rate = 0.0

        return RetrievalEvaluationResult(
            precision_at_k=precision_at_k,
            recall_at_k=recall_at_k,
            mrr=rr,
            authorized_retrieval_accuracy=auth_accuracy,
            unauthorized_retrieval_rate=unauth_rate,
            k=k,
            retrieved_chunk_ids=top_retrieved,
        )
