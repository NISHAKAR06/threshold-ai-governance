"""
test_engines.py — Unit tests for Threshold AI Governance engines.
"""
import pytest
from app.engines.risk_engine import risk_engine
from app.engines.policy_engine import policy_engine
from app.engines.decision_engine import decision_engine
from app.core.enums import RiskLevel, DecisionType, PolicyResult

def test_risk_engine_calculation():
    # Low risk scenario
    result = risk_engine.calculate(
        operation_type="READ",
        reversibility="reversible",
        data_scope="single_record",
        regulatory_category="none",
        llm_confidence=0.9,
        learning_adjustment=0.0
    )
    assert result.level == RiskLevel.LOW
    assert result.score < 30.0

    # High risk scenario
    result_high = risk_engine.calculate(
        operation_type="DELETE",
        reversibility="irreversible",
        data_scope="all_records",
        regulatory_category="GDPR",
        llm_confidence=0.9,
        learning_adjustment=0.0
    )
    assert result_high.level == RiskLevel.HIGH
    assert result_high.score >= 60.0

def test_policy_engine_evaluation():
    # Regular read should pass
    res = policy_engine.evaluate(
        operation_type="READ",
        target_table="knowledge_base",
        target_resource="article_1",
        affected_records=1,
        regulatory_category="none",
        risk_score=10.0,
        requestor_role="analyst"
    )
    assert res.overall == PolicyResult.PASS

    # DELETE on protected table should fail (raise PolicyResult.BLOCK)
    res_fail = policy_engine.evaluate(
        operation_type="DELETE",
        target_table="employees",
        target_resource="employee_1",
        affected_records=1,
        regulatory_category="GDPR",
        risk_score=90.0,
        requestor_role="analyst"
    )
    assert res_fail.overall == PolicyResult.BLOCK

def test_decision_engine_resolution():
    # Low risk, passing policy -> AUTO
    decision_auto = decision_engine.decide(
        risk_score=15.0,
        policy_result=PolicyResult.PASS,
        risk_level=RiskLevel.LOW
    )
    assert decision_auto.decision == DecisionType.AUTO

    # Medium/High risk (> confirm_threshold=60), passing policy -> CONFIRM
    decision_confirm = decision_engine.decide(
        risk_score=65.0,
        policy_result=PolicyResult.PASS,
        risk_level=RiskLevel.HIGH
    )
    assert decision_confirm.decision == DecisionType.CONFIRM

    # Policy fail -> REVIEW
    decision_review = decision_engine.decide(
        risk_score=15.0,
        policy_result=PolicyResult.BLOCK,
        risk_level=RiskLevel.LOW
    )
    assert decision_review.decision == DecisionType.REVIEW
