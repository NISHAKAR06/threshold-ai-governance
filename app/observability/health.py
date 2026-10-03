"""
health.py — Health and readiness probe implementations for THRESHOLD AI Governance.
Provides:
- GET /health: Fast, non-blocking liveness probe.
- GET /ready: Comprehensive dependency readiness check (DB, vector store, config).
- GET /metrics: Prometheus metrics exposition endpoint.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Response, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.observability.metrics import get_metrics_exposition, CONTENT_TYPE_LATEST
from app.core.logger import get_logger

logger = get_logger("threshold.observability.health")

router = APIRouter()


def check_liveness() -> Dict[str, Any]:
    """
    Fast liveness check indicating the process is alive and accepting connections.
    Does not perform external I/O or expensive checks.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
    }


async def check_readiness(db: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """
    Readiness check validating application dependencies:
    - Database connectivity
    - Vector store index presence
    - Configuration sanity
    Returns structured dictionary with overall status and component statuses.
    Never exposes credentials or internal file system secrets.
    """
    components: Dict[str, Any] = {}
    is_ready = True

    # 1. Database check
    if db is not None:
        try:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            components["database"] = {"status": "up"}
        except Exception as exc:
            components["database"] = {"status": "down", "error": "Database unreachable"}
            is_ready = False
    else:
        components["database"] = {"status": "skipped"}

    # 2. Vector store check
    try:
        vs_path = Path(settings.VECTOR_STORE_PATH)
        vs_exists = vs_path.exists()
        components["vector_store"] = {
            "status": "up" if vs_exists else "uninitialized",
            "provider": settings.VECTOR_STORE_PROVIDER,
        }
    except Exception:
        components["vector_store"] = {"status": "error", "error": "Path check failed"}
        is_ready = False

    # 3. Configuration check
    try:
        settings.validate_production_config(settings)
        components["configuration"] = {"status": "valid"}
    except Exception as exc:
        components["configuration"] = {"status": "invalid", "error": str(exc)}
        is_ready = False

    return {
        "status": "ready" if is_ready else "not_ready",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "components": components,
    }


@router.get("/health", tags=["Observability"], summary="Application Liveness Probe")
async def health_endpoint():
    """Liveness probe returning 200 OK if server process is running."""
    return check_liveness()


@router.get("/ready", tags=["Observability"], summary="Application Readiness Probe")
async def readiness_endpoint(db: AsyncSession = Depends(get_db)):
    """Readiness probe checking database, vector storage, and configuration."""
    res = await check_readiness(db)
    status_code = status.HTTP_200_OK if res["status"] == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=res)


@router.get("/metrics", tags=["Observability"], summary="Prometheus Metrics Exposition")
async def metrics_endpoint():
    """Exposes Prometheus text formatted metrics."""
    if not settings.METRICS_ENABLED:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Metrics disabled"})
    exposition = get_metrics_exposition()
    return Response(content=exposition, media_type=CONTENT_TYPE_LATEST)
