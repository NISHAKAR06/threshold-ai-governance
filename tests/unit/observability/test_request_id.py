"""
test_request_id.py — Unit tests for Request ID and tracing propagation.
"""
import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.applications import Starlette
from starlette.testclient import TestClient

from app.observability.tracing import (
    generate_request_id,
    get_request_id,
    set_request_id,
    clear_request_id,
    trace_span,
)
from app.api.middleware.request_id import RequestIdMiddleware


def test_generate_request_id():
    """Verify generated request IDs have the expected format and uniqueness."""
    rid1 = generate_request_id()
    rid2 = generate_request_id()
    assert rid1.startswith("req_")
    assert rid2.startswith("req_")
    assert rid1 != rid2


def test_contextvar_propagation():
    """Verify request ID is accessible via get_request_id within context."""
    clear_request_id()
    assert get_request_id() is None

    test_id = "req_custom_12345"
    set_request_id(test_id)
    assert get_request_id() == test_id

    clear_request_id()
    assert get_request_id() is None


def test_trace_span_lifecycle():
    """Verify trace_span context manager tracks execution time and status."""
    set_request_id("req_span_test")
    with trace_span("test_operation", attributes={"source": "unit_test"}) as span:
        assert span["span_name"] == "test_operation"
        assert span["request_id"] == "req_span_test"
        assert span["status"] == "IN_PROGRESS"

    assert span["status"] == "SUCCESS"
    assert "duration_ms" in span
    assert span["duration_ms"] >= 0.0


def test_trace_span_error_handling():
    """Verify trace_span captures error details when an exception is raised."""
    with pytest.raises(ValueError, match="Span failure"):
        with trace_span("failing_operation") as span:
            raise ValueError("Span failure")

    assert span["status"] == "ERROR"
    assert span["error_type"] == "ValueError"


def test_request_id_middleware_generates_new_id():
    """Verify middleware assigns a new request ID when none is provided in headers."""
    app = Starlette()
    app.add_middleware(RequestIdMiddleware)

    @app.route("/test-id")
    async def endpoint(request):
        return Response("ok", media_type="text/plain")

    client = TestClient(app)
    response = client.get("/test-id")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"].startswith("req_")


def test_request_id_middleware_reuses_existing_id():
    """Verify middleware preserves and propagates existing X-Request-ID header."""
    app = Starlette()
    app.add_middleware(RequestIdMiddleware)

    @app.route("/test-id")
    async def endpoint(request):
        return Response("ok", media_type="text/plain")

    client = TestClient(app)
    custom_id = "client-trace-abc-987"
    response = client.get("/test-id", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
