"""
test_rag_evaluator.py — Unit tests for RAG generation and grounding evaluation.
"""
import pytest
from app.evaluation.rag_evaluator import RAGEvaluator


def test_valid_grounded_answer():
    """Verify evaluator scores properly cited and grounded answers."""
    evaluator = RAGEvaluator()
    answer = (
        "Enterprise deployments require automated testing pipelines [Source 1]. "
        "All code modifications must be reviewed and signed off prior to merge [Source 2]."
    )
    sources = [
        {"content": "Automated testing pipelines must run on every commit."},
        {"content": "All code modifications require peer review before merging."},
    ]

    res = evaluator.evaluate(
        generated_answer=answer,
        authorized_sources=sources,
        expected_answer="Testing pipelines and peer review are required.",
    )

    assert res.answer_generated is True
    assert res.source_citations_present is True
    assert res.citations_valid is True
    assert res.grounding_score > 0.0
    assert res.similarity_score is not None
    assert res.similarity_score > 0.0


def test_invalid_citations_out_of_range():
    """Verify detection of citations referencing non-existent source indices."""
    evaluator = RAGEvaluator()
    answer = "The security protocol requires strict multi-factor authentication [Source 5]."
    sources = [
        {"content": "Multi-factor authentication is required."},  # Only 1 source present
    ]

    res = evaluator.evaluate(answer, sources)
    assert res.source_citations_present is True
    assert res.citations_valid is False  # Index 5 > valid_count 1


def test_empty_or_missing_answer():
    """Verify evaluator handles empty or None answers safely."""
    evaluator = RAGEvaluator()
    res_none = evaluator.evaluate(None, [])
    assert res_none.answer_generated is False
    assert res_none.source_citations_present is False
    assert res_none.grounding_score == 0.0

    res_empty = evaluator.evaluate("   ", [])
    assert res_empty.answer_generated is False
