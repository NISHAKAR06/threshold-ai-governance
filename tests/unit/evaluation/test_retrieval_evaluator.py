"""
test_retrieval_evaluator.py — Unit tests for deterministic retrieval evaluation.
"""
import pytest
from app.evaluation.retrieval_evaluator import RetrievalEvaluator


def test_perfect_retrieval():
    """Verify metrics when top-K retrieved matches all expected chunks in order."""
    evaluator = RetrievalEvaluator()
    retrieved = ["chunk-1", "chunk-2", "chunk-3"]
    expected = ["chunk-1", "chunk-2", "chunk-3"]

    res = evaluator.evaluate(retrieved, expected, k=3)
    assert res.precision_at_k == 1.0
    assert res.recall_at_k == 1.0
    assert res.mrr == 1.0
    assert res.authorized_retrieval_accuracy == 1.0
    assert res.unauthorized_retrieval_rate == 0.0


def test_partial_retrieval():
    """Verify precision and recall when some chunks match."""
    evaluator = RetrievalEvaluator()
    retrieved = ["chunk-unrelated", "chunk-1", "chunk-other"]
    expected = ["chunk-1", "chunk-2"]

    res = evaluator.evaluate(retrieved, expected, k=3)
    # Retrieved: 3 items, 1 match -> precision = 1/3
    assert round(res.precision_at_k, 2) == 0.33
    # Expected: 2 items, 1 match -> recall = 1/2 = 0.5
    assert res.recall_at_k == 0.5
    # First match at rank 2 -> MRR = 1/2 = 0.5
    assert res.mrr == 0.5


def test_zero_results_and_empty_handling():
    """Verify edge cases when retrieved or expected lists are empty."""
    evaluator = RetrievalEvaluator()

    # Empty retrieved
    res_empty = evaluator.evaluate([], ["chunk-1", "chunk-2"], k=5)
    assert res_empty.precision_at_k == 0.0
    assert res_empty.recall_at_k == 0.0
    assert res_empty.mrr == 0.0

    # No matches found
    res_no_match = evaluator.evaluate(["chunk-a", "chunk-b"], ["chunk-1"], k=5)
    assert res_no_match.precision_at_k == 0.0
    assert res_no_match.recall_at_k == 0.0
    assert res_no_match.mrr == 0.0


def test_authorization_accuracy_calculation():
    """Verify calculation of authorized vs unauthorized chunk retrieval rates."""
    evaluator = RetrievalEvaluator()
    retrieved = ["chunk-auth-1", "chunk-auth-2", "chunk-unauth-3", "chunk-auth-4"]
    authorized_set = {"chunk-auth-1", "chunk-auth-2", "chunk-auth-4"}

    res = evaluator.evaluate(
        retrieved_chunk_ids=retrieved,
        expected_chunk_ids=["chunk-auth-1"],
        authorized_chunk_ids=authorized_set,
        k=4,
    )
    # 3 out of 4 authorized
    assert res.authorized_retrieval_accuracy == 0.75
    assert res.unauthorized_retrieval_rate == 0.25
