"""
request_metrics.py — HTTP Request Metrics Middleware.
Observes HTTP request counts, durations, and HTTP status codes using Prometheus metrics.
"""
from __future__ import annotations

import time
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.metrics import record_http_request


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that instruments every incoming HTTP request with duration histograms
    and request counters.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Exclude prometheus scrape itself to avoid skewing metrics
        path = request.url.path
        if path == "/metrics" or path.startswith("/static/"):
            return await call_next(request)

        start_time = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_seconds = time.monotonic() - start_time
            record_http_request(
                method=request.method,
                endpoint=path,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
