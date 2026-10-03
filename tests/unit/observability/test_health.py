"""
test_health.py — Unit tests for Liveness, Readiness, and Metrics endpoints.
"""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.observability.health import check_liveness, check_readiness


client = TestClient(app)


def test_liveness_check_direct():
    """Verify direct call to check_liveness returns healthy status."""
    res = check_liveness()
    assert res["status"] == "healthy"
    assert "app" in res
    assert "version" in res
    assert "timestamp" in res


@pytest.mark.asyncio
async def test_readiness_check_success():
    """Verify readiness returns ready when DB execute succeeds."""
    mock_db = AsyncMock()
    res = await check_readiness(mock_db)
    assert res["status"] == "ready"
    assert res["components"]["database"]["status"] == "up"
    assert res["components"]["configuration"]["status"] == "valid"


@pytest.mark.asyncio
async def test_readiness_check_db_failure():
    """Verify readiness returns not_ready when DB query fails."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = ConnectionError("Database connection lost")

    res = await check_readiness(mock_db)
    assert res["status"] == "not_ready"
    assert res["components"]["database"]["status"] == "down"


def test_health_endpoint_http():
    """Verify GET /health returns 200 and healthy JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "THRESHOLD" in data["app"]


def test_metrics_endpoint_http():
    """Verify GET /metrics returns 200 and prometheus text exposition."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "threshold_http_requests_total" in response.text
