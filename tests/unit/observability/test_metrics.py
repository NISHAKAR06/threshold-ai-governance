"""
test_metrics.py — Unit tests for centralized Prometheus metrics collection.
"""
import pytest
from app.observability.metrics import (
    record_http_request,
    record_retrieval_metrics,
    record_rag_metrics,
    record_agent_metrics,
    record_governance_event,
    record_rai_decision,
    record_prompt_injection_detected,
    record_rai_output,
    get_metrics_exposition,
    get_metrics_summary,
)


def test_record_http_request():
    """Verify HTTP request metrics can be observed without errors."""
    record_http_request("GET", "/api/v1/health", 200, 0.015)
    record_http_request("POST", "/api/v1/rag/ask", 200, 0.350)
    record_http_request("POST", "/api/v1/rag/ask", 400, 0.050)

    exposition = get_metrics_exposition().decode("utf-8")
    assert "threshold_http_requests_total" in exposition
    assert "threshold_http_request_duration_seconds" in exposition


def test_record_retrieval_metrics():
    """Verify retrieval candidate and latency counters."""
    record_retrieval_metrics(
        mode="hybrid",
        semantic_count=10,
        keyword_count=8,
        fused_count=12,
        authorized_count=5,
        denied_count=7,
        duration_seconds=0.045,
    )
    exposition = get_metrics_exposition().decode("utf-8")
    assert "threshold_retrieval_requests_total" in exposition
    assert "threshold_retrieval_candidates_total" in exposition


def test_record_rag_metrics():
    """Verify RAG request and context metrics."""
    record_rag_metrics(status="success", chunks_used=4, duration_seconds=0.85)
    record_rag_metrics(status="failure", chunks_used=0, duration_seconds=0.12)
    record_rag_metrics(status="insufficient_context", chunks_used=0, duration_seconds=0.05)

    exposition = get_metrics_exposition().decode("utf-8")
    assert "threshold_rag_requests_total" in exposition
    assert "threshold_rag_context_chunks_used" in exposition


def test_record_agent_metrics():
    """Verify agent capability, tool authorization, and latency metrics."""
    record_agent_metrics(
        status="SUCCESS",
        capability="RAG_QUESTION",
        tool_name="GovernanceRAGTool",
        tool_authorized=True,
        duration_seconds=0.65,
    )
    record_agent_metrics(
        status="DENIED",
        capability="GOVERNANCE_EVALUATION",
        tool_name="RestrictedTool",
        tool_authorized=False,
        duration_seconds=0.02,
    )
    exposition = get_metrics_exposition().decode("utf-8")
    assert "threshold_agent_requests_total" in exposition
    assert "threshold_agent_capabilities_total" in exposition
    assert "threshold_agent_tools_total" in exposition


def test_record_governance_and_rai_metrics():
    """Verify governance enforcement and Responsible AI metrics."""
    record_governance_event("access_denied")
    record_rai_decision("BLOCK")
    record_prompt_injection_detected("SYSTEM_OVERRIDE")
    record_rai_output("PASS")

    exposition = get_metrics_exposition().decode("utf-8")
    assert "threshold_governance_events_total" in exposition
    assert "threshold_rai_input_decisions_total" in exposition
    assert "threshold_rai_injections_detected_total" in exposition
    assert "threshold_rai_output_decisions_total" in exposition


def test_metric_failure_safety():
    """Verify metric recording helper never throws even on invalid inputs."""
    # Passing invalid types or None should be caught and logged safely
    record_http_request("INVALID", "/test", "not_an_int", "not_a_float")  # type: ignore
    record_retrieval_metrics(mode=None, duration_seconds="invalid")  # type: ignore
    record_rag_metrics(status=None, duration_seconds=None)  # type: ignore


def test_get_metrics_summary():
    """Verify high level metrics summary dictionary."""
    summary = get_metrics_summary()
    assert summary["registry"] == "prometheus"
    assert "timestamp" in summary
