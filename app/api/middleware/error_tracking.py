"""
error_tracking.py — Production Error Tracking Middleware.
Intercepts unhandled server exceptions, logs structured error context with request ID,
and returns safe, sanitised error responses that never leak secrets, file paths, or internal tracebacks.
"""
from __future__ import annotations

import traceback
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.observability.tracing import get_request_id
from app.core.logger import get_logger

logger = get_logger("threshold.api.error_tracking")


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Production-grade middleware ensuring no raw stack traces or internal secrets
    leak to clients in case of unexpected unhandled exceptions.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = get_request_id() or getattr(request.state, "request_id", "unknown")

            # Structured internal log with stack trace for operators
            logger.error(
                "Unhandled server exception during request processing",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )

            # Safe client response without leaking sensitive details
            return JSONResponse(
                status_code=500,
                content={
                    "detail": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred while processing your request.",
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id} if request_id != "unknown" else {},
            )
