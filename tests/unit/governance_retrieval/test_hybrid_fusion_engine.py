"""
test_hybrid_fusion_engine.py — Unit tests for HybridFusionEngine (RRF).
"""
import pytest
from app.engines.governance_retrieval.hybrid_fusion_engine import HybridFusionEngine


def test_fusion_semantic_only():
    engine = HybridFusionEngine(rrf_k=60)
    semantic = [
        {"chunk_id": "C1", "document_id": "D1", "text": "Text 1", "score": 0.95},
        {"chunk_id": "C2", "document_id": "D2", "text": "Text 2", "score": 0.85},
    ]
    keyword = []

    fused = engine.fuse(semantic, keyword)
    assert len(fused) == 2
    assert fused[0]["chunk_id"] == "C1"
    assert fused[0]["fused_score"] == pytest.approx(1.0 / (60 + 1), rel=1e-3)
    assert fused[1]["chunk_id"] == "C2"
    assert fused[1]["fused_score"] == pytest.approx(1.0 / (60 + 2), rel=1e-3)


def test_fusion_keyword_only():
    engine = HybridFusionEngine(rrf_k=60)
    semantic = []
    keyword = [
        {"chunk_id": "C3", "document_id": "D3", "text": "Text 3", "score": 5.4},
    ]

    fused = engine.fuse(semantic, keyword)
    assert len(fused) == 1
    assert fused[0]["chunk_id"] == "C3"
    assert fused[0]["keyword_score"] == 5.4
    assert fused[0]["fused_score"] == pytest.approx(1.0 / (60 + 1), rel=1e-3)


def test_fusion_overlapping_results():
    engine = HybridFusionEngine(rrf_k=60)
    # C1 appears rank 1 in semantic and rank 2 in keyword
    # C2 appears rank 2 in semantic only
    # C3 appears rank 1 in keyword only
    semantic = [
        {"chunk_id": "C1", "document_id": "D1", "text": "Shared chunk", "score": 0.90},
        {"chunk_id": "C2", "document_id": "D2", "text": "Sem only", "score": 0.80},
    ]
    keyword = [
        {"chunk_id": "C3", "document_id": "D3", "text": "Kw only", "score": 4.0},
        {"chunk_id": "C1", "document_id": "D1", "text": "Shared chunk", "score": 3.0},
    ]

    fused = engine.fuse(semantic, keyword)
    assert len(fused) == 3

    # C1 gets 1/(60+1) + 1/(60+2) = ~0.01639 + 0.01613 = ~0.03252
    assert fused[0]["chunk_id"] == "C1"
    assert fused[0]["semantic_score"] == 0.90
    assert fused[0]["keyword_score"] == 3.0
    expected_c1_score = 1.0 / 61.0 + 1.0 / 62.0
    assert fused[0]["fused_score"] == pytest.approx(expected_c1_score, rel=1e-3)


def test_fusion_deterministic_ranking_tie_breaker():
    engine = HybridFusionEngine(rrf_k=60)
    # Two disjoint chunks with identical rank (both rank 1 in their respective single-item lists)
    semantic = [{"chunk_id": "B_CHUNK", "document_id": "B", "text": "b", "score": 0.9}]
    keyword = [{"chunk_id": "A_CHUNK", "document_id": "A", "text": "a", "score": 10.0}]

    fused = engine.fuse(semantic, keyword)
    assert len(fused) == 2
    # Equal score: secondary sort key chunk_id ascending ("A_CHUNK" before "B_CHUNK")
    assert fused[0]["chunk_id"] == "A_CHUNK"
    assert fused[1]["chunk_id"] == "B_CHUNK"


def test_fusion_empty_both():
    engine = HybridFusionEngine()
    assert engine.fuse([], []) == []
