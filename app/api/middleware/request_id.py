"""
request_id.py — Request Identification Middleware.
Extracts existing incoming trace/request IDs (e.g., X-Request-ID, X-Trace-ID) or generates
a unique request ID, binds it to the current contextvar, and attaches it to the response header.
"""
from __future__ import annotations

from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.tracing import (
    generate_request_id,
    set_request_id,
    clear_request_id,
    set_trace_id,
)
from app.config import settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request has a unique identifier
    propagated through logs, metrics, audit records, and downstream responses.
    """

    def __init__(self, app, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # 1. Check for incoming request ID or trace ID
        incoming_id = (
            request.headers.get(self.header_name)
            or request.headers.get("x-request-id")
            or request.headers.get("X-Trace-ID")
            or request.headers.get("x-trace-id")
        )

        # 2. Reuse or generate
        request_id = incoming_id.strip() if incoming_id and incoming_id.strip() else generate_request_id()

        # 3. Attach to context and state
        set_request_id(request_id)
        set_trace_id(request_id)
        request.state.request_id = request_id

        try:
            # 4. Propagate request downstream
            response = await call_next(request)
            # 5. Attach request ID to response header
            response.headers[self.header_name] = request_id
            return response
        finally:
            clear_request_id()
