"""
tracing.py — Request context and distributed trace identification.
Provides ContextVar-backed request ID propagation across async tasks, coroutines,
and logging contexts without modifying function signatures.
"""
from __future__ import annotations

import uuid
import time
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator

_REQUEST_ID_CTX: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_TRACE_ID_CTX: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def generate_request_id() -> str:
    """Generate a clean, standard UUID4-based request identifier."""
    return f"req_{uuid.uuid4().hex[:16]}"


def get_request_id() -> Optional[str]:
    """Retrieve the current request ID from context, or None if outside a request."""
    return _REQUEST_ID_CTX.get()


def set_request_id(request_id: str) -> None:
    """Set the current request ID in context."""
    _REQUEST_ID_CTX.set(request_id)


def clear_request_id() -> None:
    """Clear request context."""
    _REQUEST_ID_CTX.set(None)


def get_trace_id() -> Optional[str]:
    """Retrieve trace ID if separate from request ID."""
    return _TRACE_ID_CTX.get() or _REQUEST_ID_CTX.get()


def set_trace_id(trace_id: str) -> None:
    """Set the current trace ID in context."""
    _TRACE_ID_CTX.set(trace_id)


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager for measuring execution spans with request context.
    Yields a mutable dictionary for span metadata and records execution duration.
    """
    span_data: Dict[str, Any] = {
        "span_name": name,
        "request_id": get_request_id(),
        "start_time": time.monotonic(),
        "attributes": dict(attributes or {}),
        "status": "IN_PROGRESS",
    }
    start = time.monotonic()
    try:
        yield span_data
        span_data["status"] = "SUCCESS"
    except Exception as exc:
        span_data["status"] = "ERROR"
        span_data["error"] = str(exc)
        span_data["error_type"] = type(exc).__name__
        raise
    finally:
        duration_ms = (time.monotonic() - start) * 1000.0
        span_data["duration_ms"] = round(duration_ms, 2)
