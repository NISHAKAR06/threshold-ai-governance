"""
metrics.py — Centralized Prometheus metrics collection for THRESHOLD AI Governance.
Provides robust, thread-safe, non-blocking metrics for:
- Application HTTP requests and latency
- Semantic & hybrid retrieval candidates and latencies
- Grounded RAG generations and context usage
- Controlled AI Agent routing, tool authorizations, and execution
- Enterprise governance policy decisions and access enforcements
- Responsible AI guardrails and prompt injection detections
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

from app.core.logger import get_logger

logger = get_logger("threshold.observability.metrics")

# Use a dedicated or standard Prometheus registry
METRICS_REGISTRY: CollectorRegistry = REGISTRY

# ── Application Metrics ───────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "threshold_http_requests_total",
    "Total HTTP requests received by the application.",
    ["method", "endpoint", "status_code"],
    registry=METRICS_REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "threshold_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=METRICS_REGISTRY,
)

# ── Retrieval Metrics ─────────────────────────────────────────
RETRIEVAL_REQUESTS_TOTAL = Counter(
    "threshold_retrieval_requests_total",
    "Total retrieval requests executed.",
    ["mode"],  # e.g., 'semantic', 'hybrid'
    registry=METRICS_REGISTRY,
)

RETRIEVAL_CANDIDATES_TOTAL = Counter(
    "threshold_retrieval_candidates_total",
    "Count of candidate chunks processed at each stage of retrieval.",
    ["stage"],  # 'semantic', 'keyword', 'fused', 'authorized', 'denied'
    registry=METRICS_REGISTRY,
)

RETRIEVAL_LATENCY_SECONDS = Histogram(
    "threshold_retrieval_latency_seconds",
    "Retrieval duration in seconds.",
    ["mode"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
    registry=METRICS_REGISTRY,
)

# ── RAG Metrics ───────────────────────────────────────────────
RAG_REQUESTS_TOTAL = Counter(
    "threshold_rag_requests_total",
    "Total RAG answer generation requests initiated.",
    ["status"],  # 'success', 'failure', 'insufficient_context'
    registry=METRICS_REGISTRY,
)

RAG_CONTEXT_CHUNKS_USED = Histogram(
    "threshold_rag_context_chunks_used",
    "Number of authorized context chunks provided to RAG prompts.",
    buckets=(0, 1, 2, 3, 5, 8, 12, 16, 20),
    registry=METRICS_REGISTRY,
)

RAG_LATENCY_SECONDS = Histogram(
    "threshold_rag_latency_seconds",
    "RAG answer generation latency in seconds.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0),
    registry=METRICS_REGISTRY,
)

# ── Agent Metrics ─────────────────────────────────────────────
AGENT_REQUESTS_TOTAL = Counter(
    "threshold_agent_requests_total",
    "Total Controlled AI Agent execution requests.",
    ["status"],  # 'SUCCESS', 'DENIED', 'REVIEW_REQUIRED', 'ERROR'
    registry=METRICS_REGISTRY,
)

AGENT_CAPABILITIES_TOTAL = Counter(
    "threshold_agent_capabilities_total",
    "Count of requests mapped to capabilities.",
    ["capability"],
    registry=METRICS_REGISTRY,
)

AGENT_TOOLS_TOTAL = Counter(
    "threshold_agent_tools_total",
    "Count of tool invocations by outcome.",
    ["tool_name", "outcome"],  # outcome: 'allowed', 'denied', 'failure', 'success'
    registry=METRICS_REGISTRY,
)

AGENT_LATENCY_SECONDS = Histogram(
    "threshold_agent_latency_seconds",
    "Total agent workflow execution duration in seconds.",
    ["capability"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
    registry=METRICS_REGISTRY,
)

# ── Governance Metrics ────────────────────────────────────────
GOVERNANCE_EVENTS_TOTAL = Counter(
    "threshold_governance_events_total",
    "Governance enforcement events.",
    ["event_type"],  # 'access_denied', 'policy_denied', 'review_required', 'output_validation_failure'
    registry=METRICS_REGISTRY,
)

# ── Responsible AI Metrics ────────────────────────────────────
RAI_INPUT_DECISIONS_TOTAL = Counter(
    "threshold_rai_input_decisions_total",
    "Responsible AI input guard decisions.",
    ["decision"],  # 'ALLOW', 'BLOCK', 'REVIEW'
    registry=METRICS_REGISTRY,
)

RAI_INJECTIONS_DETECTED_TOTAL = Counter(
    "threshold_rai_injections_detected_total",
    "Prompt injection detections by category.",
    ["category"],
    registry=METRICS_REGISTRY,
)

RAI_OUTPUT_DECISIONS_TOTAL = Counter(
    "threshold_rai_output_decisions_total",
    "Responsible AI output guard outcomes.",
    ["status"],  # 'PASS', 'FAIL'
    registry=METRICS_REGISTRY,
)


# ── Metric Recording Helper Functions ─────────────────────────

def record_http_request(method: str, endpoint: str, status_code: int, duration_seconds: float) -> None:
    """Record HTTP request metrics safely."""
    try:
        norm_endpoint = endpoint.split("?")[0]
        # Normalize dynamic path segments if any to avoid high cardinality
        HTTP_REQUESTS_TOTAL.labels(
            method=method.upper(),
            endpoint=norm_endpoint,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method.upper(),
            endpoint=norm_endpoint,
        ).observe(max(0.0, float(duration_seconds)))
    except Exception as exc:
        logger.debug("Failed to record HTTP metrics: %s", exc)


def record_retrieval_metrics(
    mode: str,
    semantic_count: int = 0,
    keyword_count: int = 0,
    fused_count: int = 0,
    authorized_count: int = 0,
    denied_count: int = 0,
    duration_seconds: float = 0.0,
) -> None:
    """Record candidate counts and latency for retrieval operations."""
    try:
        RETRIEVAL_REQUESTS_TOTAL.labels(mode=mode).inc()
        if semantic_count > 0:
            RETRIEVAL_CANDIDATES_TOTAL.labels(stage="semantic").inc(semantic_count)
        if keyword_count > 0:
            RETRIEVAL_CANDIDATES_TOTAL.labels(stage="keyword").inc(keyword_count)
        if fused_count > 0:
            RETRIEVAL_CANDIDATES_TOTAL.labels(stage="fused").inc(fused_count)
        if authorized_count > 0:
            RETRIEVAL_CANDIDATES_TOTAL.labels(stage="authorized").inc(authorized_count)
        if denied_count > 0:
            RETRIEVAL_CANDIDATES_TOTAL.labels(stage="denied").inc(denied_count)
        RETRIEVAL_LATENCY_SECONDS.labels(mode=mode).observe(max(0.0, float(duration_seconds)))
    except Exception as exc:
        logger.debug("Failed to record retrieval metrics: %s", exc)


def record_rag_metrics(
    status: str,
    chunks_used: int = 0,
    duration_seconds: float = 0.0,
) -> None:
    """Record RAG generation outcome, context size, and duration."""
    try:
        norm_status = status.lower()
        if norm_status not in ("success", "failure", "insufficient_context"):
            norm_status = "failure" if "fail" in norm_status or "error" in norm_status else "success"
        RAG_REQUESTS_TOTAL.labels(status=norm_status).inc()
        RAG_CONTEXT_CHUNKS_USED.observe(max(0, int(chunks_used)))
        RAG_LATENCY_SECONDS.observe(max(0.0, float(duration_seconds)))
    except Exception as exc:
        logger.debug("Failed to record RAG metrics: %s", exc)


def record_agent_metrics(
    status: str,
    capability: str,
    tool_name: Optional[str] = None,
    tool_authorized: Optional[bool] = None,
    duration_seconds: float = 0.0,
) -> None:
    """Record agent capability selection, tool authorizations, and execution time."""
    try:
        AGENT_REQUESTS_TOTAL.labels(status=status.upper()).inc()
        AGENT_CAPABILITIES_TOTAL.labels(capability=capability).inc()
        if tool_name:
            if tool_authorized is False:
                AGENT_TOOLS_TOTAL.labels(tool_name=tool_name, outcome="denied").inc()
            elif tool_authorized is True:
                AGENT_TOOLS_TOTAL.labels(tool_name=tool_name, outcome="allowed").inc()
        AGENT_LATENCY_SECONDS.labels(capability=capability).observe(max(0.0, float(duration_seconds)))
    except Exception as exc:
        logger.debug("Failed to record agent metrics: %s", exc)


def record_governance_event(event_type: str) -> None:
    """Record governance enforcement events."""
    try:
        GOVERNANCE_EVENTS_TOTAL.labels(event_type=event_type).inc()
    except Exception as exc:
        logger.debug("Failed to record governance event: %s", exc)


def record_rai_decision(decision: str) -> None:
    """Record Responsible AI input guard decision."""
    try:
        RAI_INPUT_DECISIONS_TOTAL.labels(decision=decision.upper()).inc()
    except Exception as exc:
        logger.debug("Failed to record RAI input decision: %s", exc)


def record_prompt_injection_detected(category: str) -> None:
    """Record detected prompt injection attempts."""
    try:
        RAI_INJECTIONS_DETECTED_TOTAL.labels(category=category).inc()
    except Exception as exc:
        logger.debug("Failed to record prompt injection detection: %s", exc)


def record_rai_output(status: str) -> None:
    """Record Responsible AI output guard validation status."""
    try:
        RAI_OUTPUT_DECISIONS_TOTAL.labels(status=status.upper()).inc()
    except Exception as exc:
        logger.debug("Failed to record RAI output decision: %s", exc)


def get_metrics_exposition() -> bytes:
    """Return Prometheus text exposition bytes."""
    return generate_latest(METRICS_REGISTRY)


def get_metrics_summary() -> Dict[str, Any]:
    """Return high-level summary of active metrics."""
    return {
        "registry": "prometheus",
        "content_type": CONTENT_TYPE_LATEST,
        "timestamp": time.time(),
    }
