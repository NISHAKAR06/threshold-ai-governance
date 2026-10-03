"""
test_governance_filter_engine.py — Unit tests for GovernanceFilterEngine.
"""
import pytest

from app.models.access_context import AccessContext
from app.engines.governance_retrieval.governance_filter_engine import GovernanceFilterEngine
from app.engines.governance_retrieval.access_validator import AccessValidator


@pytest.fixture
def sample_candidates():
    return [
        {
            "chunk_id": "SEC-001_CHUNK_0001",
            "document_id": "SEC-001",
            "text": "Enterprise information security general hygiene for all staff.",
            "fused_score": 0.032,
            "metadata": {
                "department": "Information Security",
                "classification": "INTERNAL",
                "allowed_roles": ["EMPLOYEE", "MANAGER", "SECURITY_ENGINEER", "ADMIN"],
                "status": "ACTIVE",
            },
            "source": {"file_path": "sec_001.pdf"},
        },
        {
            "chunk_id": "SEC-004_CHUNK_0001",
            "document_id": "SEC-004",
            "text": "Cybersecurity incident response playbooks and CSIRT containment.",
            "fused_score": 0.028,
            "metadata": {
                "department": "Information Security",
                "classification": "CONFIDENTIAL",
                "allowed_roles": ["SECURITY_ENGINEER", "MANAGER", "ADMIN"],
                "status": "ACTIVE",
            },
            "source": {"file_path": "sec_004.pdf"},
        },
        {
            "chunk_id": "ENG-007_CHUNK_0001",
            "document_id": "ENG-007",
            "text": "Proprietary foundational neural network model weights and secret keys.",
            "fused_score": 0.025,
            "metadata": {
                "department": "Engineering",
                "classification": "RESTRICTED",
                "allowed_roles": ["AI_ENGINEER", "ADMIN"],
                "status": "ACTIVE",
            },
            "source": {"file_path": "eng_007.pdf"},
        },
        {
            "chunk_id": "CORRUPT_CHUNK",
            "document_id": "CORRUPT",
            "text": "Corrupted metadata chunk without allowed_roles.",
            "fused_score": 0.015,
            "metadata": {
                "department": "Engineering",
                "classification": "INTERNAL",
            },
            "source": {},
        },
    ]


def test_governance_filter_authorized_role(sample_candidates):
    filter_engine = GovernanceFilterEngine()
    ctx = AccessContext(
        user_id="USER-ENG-01",
        role="AI_ENGINEER",
        department="Engineering",
        clearance_level="RESTRICTED",
    )

    authorized, denied_count = filter_engine.filter_candidates(sample_candidates, ctx)

    chunk_ids = [c["chunk_id"] for c in authorized]
    # AI_ENGINEER with RESTRICTED clearance should access ENG-007 (role AI_ENGINEER, RESTRICTED)
    assert "ENG-007_CHUNK_0001" in chunk_ids
    # SEC-001 has allowed_roles including AI_ENGINEER or not? Wait, SEC-001 has EMPLOYEE, MANAGER, SECURITY_ENGINEER, ADMIN.
    # If role is AI_ENGINEER, does it have SEC-001?
    # In sample_candidates, SEC-001 allowed_roles doesn't list AI_ENGINEER, so denied.
    assert "SEC-004_CHUNK_0001" not in chunk_ids  # role is not in SEC-004
    assert "CORRUPT_CHUNK" not in chunk_ids        # missing allowed_roles
    assert denied_count == 3


def test_governance_filter_general_employee(sample_candidates):
    filter_engine = GovernanceFilterEngine()
    ctx = AccessContext(
        user_id="USER-EMP-01",
        role="EMPLOYEE",
        department="Operations",
        clearance_level="INTERNAL",
    )

    authorized, denied_count = filter_engine.filter_candidates(sample_candidates, ctx)
    chunk_ids = [c["chunk_id"] for c in authorized]

    assert "SEC-001_CHUNK_0001" in chunk_ids
    assert "SEC-004_CHUNK_0001" not in chunk_ids  # role & clearance mismatch
    assert "ENG-007_CHUNK_0001" not in chunk_ids  # role & clearance mismatch
    assert "CORRUPT_CHUNK" not in chunk_ids
    assert len(authorized) == 1
    assert denied_count == 3


def test_governance_filter_unauthorized_role(sample_candidates):
    filter_engine = GovernanceFilterEngine()
    ctx = AccessContext(
        user_id="USER-INTERN-01",
        role="CONTRACTOR",
        department="HR",
        clearance_level="PUBLIC",
    )

    authorized, denied_count = filter_engine.filter_candidates(sample_candidates, ctx)
    assert len(authorized) == 0
    assert denied_count == len(sample_candidates)


def test_governance_filter_missing_role_metadata(sample_candidates):
    filter_engine = GovernanceFilterEngine()
    ctx = AccessContext(
        user_id="USER-SEC-01",
        role="SECURITY_ENGINEER",
        department="Information Security",
        clearance_level="CONFIDENTIAL",
    )

    authorized, denied_count = filter_engine.filter_candidates(sample_candidates, ctx)
    chunk_ids = [c["chunk_id"] for c in authorized]

    # The chunk without allowed_roles must never be returned
    assert "CORRUPT_CHUNK" not in chunk_ids


def test_governance_filter_classification_restrictions(sample_candidates):
    filter_engine = GovernanceFilterEngine()
    # SECURITY_ENGINEER has the role for SEC-004, but only has INTERNAL clearance (SEC-004 requires CONFIDENTIAL)
    ctx = AccessContext(
        user_id="USER-SEC-JUNIOR",
        role="SECURITY_ENGINEER",
        department="Information Security",
        clearance_level="INTERNAL",
    )

    authorized, denied_count = filter_engine.filter_candidates(sample_candidates, ctx)
    chunk_ids = [c["chunk_id"] for c in authorized]

    assert "SEC-001_CHUNK_0001" in chunk_ids      # INTERNAL <= INTERNAL -> Allowed
    assert "SEC-004_CHUNK_0001" not in chunk_ids  # CONFIDENTIAL > INTERNAL -> Denied


def test_governance_filter_empty_and_none_context(sample_candidates):
    filter_engine = GovernanceFilterEngine()

    auth_empty, denied_empty = filter_engine.filter_candidates([], AccessContext(user_id="U1", role="ADMIN"))
    assert auth_empty == []
    assert denied_empty == 0

    auth_none, denied_none = filter_engine.filter_candidates(sample_candidates, None)
    assert auth_none == []
    assert denied_none == len(sample_candidates)
