"""
test_governance_evaluator.py — Unit tests for enterprise governance policy and exposure evaluation.
"""
import pytest
from app.evaluation.governance_evaluator import GovernanceEvaluator


def test_authorized_access_clean():
    """Verify clean authorized case with zero leakage."""
    evaluator = GovernanceEvaluator()
    res = evaluator.evaluate_case(
        actual_decision="ALLOW",
        expected_decision="ALLOW",
        denied_chunk_ids=[],
        context_chunk_ids=["chunk-pub-1", "chunk-pub-2"],
        final_answer_text="Here is the public policy overview [Source 1].",
    )
    assert res.decision_matches is True
    assert res.unauthorized_exposure is False
    assert res.leaked_chunks_count == 0


def test_unauthorized_access_properly_denied():
    """Verify unauthorized request correctly blocked with zero leaked content."""
    evaluator = GovernanceEvaluator()
    res = evaluator.evaluate_case(
        actual_decision="DENIED",
        expected_decision="DENY",
        denied_chunk_ids=["chunk-secret-99"],
        context_chunk_ids=[],  # Never added to context
        final_answer_text="Access Denied: You do not have permission to view this resource.",
    )
    assert res.decision_matches is True
    assert res.unauthorized_exposure is False
    assert res.leaked_chunks_count == 0


def test_unauthorized_exposure_detected_in_context():
    """Verify detector flags exposure if a denied chunk ID is in the prompt context."""
    evaluator = GovernanceEvaluator()
    res = evaluator.evaluate_case(
        actual_decision="ALLOW",
        expected_decision="ALLOW",
        denied_chunk_ids=["chunk-restricted-01"],
        context_chunk_ids=["chunk-restricted-01", "chunk-allowed-02"],
        final_answer_text="This answer inadvertently received protected context.",
    )
    assert res.unauthorized_exposure is True
    assert res.leaked_chunks_count == 1


def test_unauthorized_exposure_detected_in_answer_text():
    """Verify detector flags exposure if denied chunk identifier appears in the answer."""
    evaluator = GovernanceEvaluator()
    res = evaluator.evaluate_case(
        actual_decision="ALLOW",
        expected_decision="ALLOW",
        denied_chunk_ids=["chunk-restricted-01"],
        context_chunk_ids=["chunk-allowed-02"],
        final_answer_text="Confidential data from chunk-restricted-01 was revealed.",
    )
    assert res.unauthorized_exposure is True
    assert res.leaked_chunks_count == 1


def test_aggregate_metrics_zero_exposure():
    """Verify aggregate calculation returns 0.00 exposure rate for compliant runs."""
    evaluator = GovernanceEvaluator()
    case1 = evaluator.evaluate_case("ALLOW", "ALLOW", [], ["c1"], "Clean answer")
    case2 = evaluator.evaluate_case("DENY", "DENY", ["c2"], [], "Blocked request")

    aggregates = evaluator.calculate_aggregate_metrics([case1, case2])
    assert aggregates["authorization_accuracy"] == 1.0
    assert aggregates["governance_enforcement_rate"] == 1.0
    assert aggregates["unauthorized_exposure_rate"] == 0.0


def test_aggregate_metrics_with_exposure_violation():
    """Verify aggregate calculation reflects exposure violations when leaks occur."""
    evaluator = GovernanceEvaluator()
    case1 = evaluator.evaluate_case("ALLOW", "ALLOW", [], ["c1"], "Clean answer")
    case2 = evaluator.evaluate_case("ALLOW", "DENY", ["c2"], ["c2"], "Leaked text with c2")

    aggregates = evaluator.calculate_aggregate_metrics([case1, case2])
    assert aggregates["authorization_accuracy"] == 0.5
    assert aggregates["unauthorized_exposure_rate"] == 0.5
    assert aggregates["governance_enforcement_rate"] == 0.5
