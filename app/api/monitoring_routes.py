"""
monitoring_routes.py — API endpoints for System Monitoring & Telemetry (Phase 16).
Provides structured JSON aggregations of health, readiness, and metrics for frontend monitoring.
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.observability.health import check_liveness, check_readiness
from app.observability.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    RAG_REQUESTS_TOTAL,
    AGENT_REQUESTS_TOTAL,
    GOVERNANCE_EVENTS_TOTAL,
    RAI_INPUT_DECISIONS_TOTAL,
    RAI_INJECTIONS_DETECTED_TOTAL,
    RAI_OUTPUT_DECISIONS_TOTAL,
)

router = APIRouter()


def _collect_counter_totals(metric) -> Dict[str, float]:
    """Helper to safely sum Prometheus counter samples."""
    totals: Dict[str, float] = {}
    try:
        for s in metric.collect():
            for sample in s.samples:
                if sample.name.endswith("_total"):
                    key = "_".join(f"{k}={v}" for k, v in sample.labels.items()) if sample.labels else "total"
                    totals[key] = totals.get(key, 0.0) + sample.value
    except Exception:
        pass
    return totals


@router.get("/summary", summary="Get system monitoring telemetry summary")
async def get_monitoring_summary(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns high-level system telemetry for frontend monitoring cards and dashboards.
    """
    # 1. Liveness
    liveness = check_liveness()

    # 2. Readiness
    readiness = await check_readiness(db)

    # 3. Counters summary
    http_totals = _collect_counter_totals(HTTP_REQUESTS_TOTAL)
    rag_totals = _collect_counter_totals(RAG_REQUESTS_TOTAL)
    agent_totals = _collect_counter_totals(AGENT_REQUESTS_TOTAL)
    gov_totals = _collect_counter_totals(GOVERNANCE_EVENTS_TOTAL)
    rai_input = _collect_counter_totals(RAI_INPUT_DECISIONS_TOTAL)
    rai_injections = _collect_counter_totals(RAI_INJECTIONS_DETECTED_TOTAL)
    rai_output = _collect_counter_totals(RAI_OUTPUT_DECISIONS_TOTAL)

    total_http_reqs = sum(http_totals.values())
    total_rag_reqs = sum(rag_totals.values())
    total_agent_reqs = sum(agent_totals.values())
    total_injections = sum(rai_injections.values())

    return {
        "timestamp": time.time(),
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "liveness": liveness,
        "readiness": readiness,
        "telemetry": {
            "total_http_requests": int(total_http_reqs),
            "total_rag_requests": int(total_rag_reqs),
            "total_agent_executions": int(total_agent_reqs),
            "total_prompt_injections_detected": int(total_injections),
            "http_breakdown": http_totals,
            "rag_breakdown": rag_totals,
            "agent_breakdown": agent_totals,
            "governance_events": gov_totals,
            "rai_input_decisions": rai_input,
            "rai_output_decisions": rai_output,
        },
    }
