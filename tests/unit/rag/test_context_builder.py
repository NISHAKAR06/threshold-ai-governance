"""
test_context_builder.py — Unit tests for ContextBuilder.
"""
import pytest

from app.models.governance_retrieval_result import GovernanceRetrievalResultItem
from app.engines.rag.context_builder import ContextBuilder


@pytest.fixture
def sample_authorized_chunks():
    return [
        GovernanceRetrievalResultItem(
            rank=1,
            fused_score=0.032,
            chunk_id="SEC-001_CHUNK_0001",
            document_id="SEC-001",
            text="Access control protocol for high-risk autonomous AI systems.",
            metadata={
                "department": "Information Security",
                "classification": "RESTRICTED",
                "allowed_roles": ["SECURITY_ENGINEER", "ADMIN"],
                "document_type": "POLICY",
                "title": "Information Security Policy",
            },
            source={"file_path": "policies/sec_001.pdf"},
            semantic_score=0.92,
            keyword_score=4.5,
        ),
        GovernanceRetrievalResultItem(
            rank=2,
            fused_score=0.028,
            chunk_id="HR-001_CHUNK_0002",
            document_id="HR-001",
            text="Remote work core hours are 10:00 AM to 4:00 PM local time.",
            metadata={
                "department": "Human Resources",
                "classification": "INTERNAL",
                "allowed_roles": ["EMPLOYEE", "ADMIN"],
                "document_type": "HANDBOOK",
                "title": "Employee Handbook",
            },
            source={"file_path": "hr/handbook.pdf"},
            semantic_score=0.88,
            keyword_score=3.8,
        ),
        GovernanceRetrievalResultItem(
            rank=3,
            fused_score=0.020,
            chunk_id="ENG-001_CHUNK_0005",
            document_id="ENG-001",
            text="Production database deployment pipelines require multi-person review.",
            metadata={
                "department": "Engineering",
                "classification": "INTERNAL",
                "allowed_roles": ["ENGINEER", "ADMIN"],
                "document_type": "GUIDELINE",
                "title": "Deployment Guidelines",
            },
            source={"file_path": "engineering/guidelines.pdf"},
            semantic_score=0.75,
            keyword_score=2.1,
        ),
    ]


def test_context_builder_ranked_construction(sample_authorized_chunks):
    builder = ContextBuilder(max_chunks=5)
    result = builder.build_context(sample_authorized_chunks)

    assert result.chunks_used == 3
    assert "[SOURCE_1]" in result.formatted_context
    assert "[SOURCE_2]" in result.formatted_context
    assert "[SOURCE_3]" in result.formatted_context

    # Verify ranking order is preserved
    pos_s1 = result.formatted_context.find("[SOURCE_1]")
    pos_s2 = result.formatted_context.find("[SOURCE_2]")
    pos_s3 = result.formatted_context.find("[SOURCE_3]")
    assert pos_s1 < pos_s2 < pos_s3

    # Check source object mapping
    assert len(result.sources) == 3
    assert result.sources[0].source_id == "SOURCE_1"
    assert result.sources[0].document_id == "SEC-001"
    assert result.sources[0].chunk_id == "SEC-001_CHUNK_0001"
    assert result.sources[0].source_reference == "policies/sec_001.pdf"


def test_context_builder_max_chunks_limit(sample_authorized_chunks):
    builder = ContextBuilder(max_chunks=2)
    result = builder.build_context(sample_authorized_chunks)

    assert result.chunks_used == 2
    assert len(result.sources) == 2
    assert "[SOURCE_1]" in result.formatted_context
    assert "[SOURCE_2]" in result.formatted_context
    assert "[SOURCE_3]" not in result.formatted_context


def test_context_builder_max_context_length_limit(sample_authorized_chunks):
    # Set a tiny max length that accommodates only the first chunk
    builder = ContextBuilder(max_chunks=5, max_context_length=300)
    result = builder.build_context(sample_authorized_chunks)

    assert result.chunks_used == 1
    assert "[SOURCE_1]" in result.formatted_context
    assert "[SOURCE_2]" not in result.formatted_context


def test_context_builder_empty_chunks():
    builder = ContextBuilder()
    result = builder.build_context([])

    assert result.chunks_used == 0
    assert result.formatted_context == ""
    assert result.sources == []
    assert result.source_map == {}


def test_context_builder_metadata_traceability(sample_authorized_chunks):
    builder = ContextBuilder()
    result = builder.build_context(sample_authorized_chunks)

    src1 = result.sources[0]
    assert src1.classification == "RESTRICTED"
    assert src1.department == "Information Security"
    assert src1.document_type == "POLICY"
    assert src1.fused_score == 0.032
