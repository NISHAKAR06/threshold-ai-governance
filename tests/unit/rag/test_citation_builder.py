"""
test_citation_builder.py — Unit tests for CitationBuilder.
"""
from app.engines.rag.citation_builder import CitationBuilder
from app.models.rag_source import RAGSource


def test_citation_builder_mapping():
    builder = CitationBuilder()
    context_sources = [
        RAGSource(
            source_id="SOURCE_1",
            document_id="SEC-001",
            chunk_id="SEC-001_CHUNK_0001",
            document_type="POLICY",
            source_reference="policies/sec_001.pdf",
            classification="RESTRICTED",
            department="Information Security",
            fused_score=0.035,
        ),
        RAGSource(
            source_id="SOURCE_2",
            document_id="HR-001",
            chunk_id="HR-001_CHUNK_0001",
            document_type="HANDBOOK",
            source_reference="hr/handbook.pdf",
            classification="INTERNAL",
            department="Human Resources",
            fused_score=0.025,
        ),
    ]

    # Model cited only SOURCE_1
    cited_ids = ["SOURCE_1"]

    # When only_cited=False (default): all authorized context sources returned, is_cited marked
    all_sources = builder.build_citations(context_sources, cited_ids, only_cited=False)
    assert len(all_sources) == 2
    assert all_sources[0].source_id == "SOURCE_1"
    assert all_sources[0].is_cited is True
    assert all_sources[1].source_id == "SOURCE_2"
    assert all_sources[1].is_cited is False

    # When only_cited=True: only cited sources returned
    cited_only = builder.build_citations(context_sources, cited_ids, only_cited=True)
    assert len(cited_only) == 1
    assert cited_only[0].source_id == "SOURCE_1"
    assert cited_only[0].is_cited is True


def test_citation_builder_empty():
    builder = CitationBuilder()
    assert builder.build_citations([], ["SOURCE_1"]) == []
