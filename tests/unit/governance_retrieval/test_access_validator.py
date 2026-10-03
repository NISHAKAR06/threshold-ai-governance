"""
test_access_validator.py — Unit tests for AccessValidator.
"""
import pytest

from app.models.access_context import AccessContext
from app.engines.governance_retrieval.access_validator import AccessValidator, AccessDecision


def test_access_validator_valid_access():
    validator = AccessValidator()
    ctx = AccessContext(
        user_id="U1",
        role="SECURITY_ENGINEER",
        department="Information Security",
        clearance_level="CONFIDENTIAL",
    )
    meta = {
        "department": "Information Security",
        "classification": "CONFIDENTIAL",
        "allowed_roles": ["SECURITY_ENGINEER", "ADMIN"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is True
    assert decision.reason == "Authorized"


def test_access_validator_denied_role():
    validator = AccessValidator()
    ctx = AccessContext(
        user_id="U2",
        role="EMPLOYEE",
        department="Finance",
        clearance_level="CONFIDENTIAL",
    )
    meta = {
        "department": "Information Security",
        "classification": "CONFIDENTIAL",
        "allowed_roles": ["SECURITY_ENGINEER", "ADMIN"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is False
    assert "not permitted in chunk allowed_roles" in decision.reason


def test_access_validator_missing_context():
    validator = AccessValidator()
    meta = {
        "department": "IT",
        "classification": "INTERNAL",
        "allowed_roles": ["EMPLOYEE"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(None, meta)
    assert decision.is_allowed is False
    assert "Missing AccessContext" in decision.reason


def test_access_validator_malformed_role():
    validator = AccessValidator()
    ctx = AccessContext(user_id="U3", role="")
    meta = {
        "department": "IT",
        "classification": "INTERNAL",
        "allowed_roles": ["EMPLOYEE"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is False
    assert "User role is missing or empty" in decision.reason


def test_access_validator_clearance_levels():
    validator = AccessValidator()
    # User has INTERNAL (level 2), chunk requires RESTRICTED (level 4)
    ctx = AccessContext(
        user_id="U4",
        role="ENGINEER",
        department="Engineering",
        clearance_level="INTERNAL",
    )
    meta = {
        "department": "Engineering",
        "classification": "RESTRICTED",
        "allowed_roles": ["ENGINEER"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is False
    assert "is below chunk classification" in decision.reason

    # User upgraded to RESTRICTED clearance
    ctx_upgraded = AccessContext(
        user_id="U4",
        role="ENGINEER",
        department="Engineering",
        clearance_level="RESTRICTED",
    )
    decision_upgraded = validator.validate_access(ctx_upgraded, meta)
    assert decision_upgraded.is_allowed is True


def test_access_validator_universal_role():
    validator = AccessValidator()
    ctx = AccessContext(
        user_id="U5",
        role="MARKETING_ANALYST",
        department="Marketing",
        clearance_level="INTERNAL",
    )
    meta = {
        "department": "HR",
        "classification": "INTERNAL",
        "allowed_roles": ["ALL_EMPLOYEES"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is True


def test_access_validator_admin_bypass():
    validator = AccessValidator()
    # Admin accesses chunk even if allowed_roles only lists AI_ENGINEER
    ctx = AccessContext(
        user_id="U-ADMIN",
        role="ADMIN",
        department="Executive",
        clearance_level="RESTRICTED",
    )
    meta = {
        "department": "Research",
        "classification": "RESTRICTED",
        "allowed_roles": ["AI_ENGINEER"],
        "status": "ACTIVE",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is True


def test_access_validator_strict_department_check():
    validator_strict = AccessValidator(strict_department_check=True)
    ctx = AccessContext(
        user_id="U6",
        role="ENGINEER",
        department="Engineering",
        clearance_level="INTERNAL",
    )
    # Different department, not cross-cutting, specific role
    meta = {
        "department": "Finance",
        "classification": "INTERNAL",
        "allowed_roles": ["ENGINEER"],
        "status": "ACTIVE",
    }
    decision = validator_strict.validate_access(ctx, meta)
    assert decision.is_allowed is False
    assert "does not match chunk department" in decision.reason

    # Cross-cutting department (Enterprise Governance) passes even with strict department check
    meta_cross = {
        "department": "Enterprise Governance",
        "classification": "INTERNAL",
        "allowed_roles": ["ENGINEER"],
        "status": "ACTIVE",
    }
    decision_cross = validator_strict.validate_access(ctx, meta_cross)
    assert decision_cross.is_allowed is True


def test_access_validator_archived_document():
    validator = AccessValidator()
    ctx = AccessContext(
        user_id="U7",
        role="EMPLOYEE",
        department="Operations",
        clearance_level="INTERNAL",
    )
    meta = {
        "department": "Operations",
        "classification": "INTERNAL",
        "allowed_roles": ["EMPLOYEE"],
        "status": "ARCHIVED",
    }
    decision = validator.validate_access(ctx, meta)
    assert decision.is_allowed is False
    assert "not active" in decision.reason
