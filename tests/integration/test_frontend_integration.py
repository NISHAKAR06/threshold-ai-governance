"""
test_frontend_integration.py — Integration test suite for Phase 16:
Frontend Integration and Enterprise AI Governance Dashboard.

Verifies:
1. Template rendering for all governance routes (/dashboard, /assistant, /search, /agent, /governance, /audit, /evaluation, /monitoring).
2. Backend API integration endpoints supporting the frontend (/api/v1/evaluation/*, /api/v1/monitoring/summary, /api/v1/agent/audit).
3. Delivery of core frontend JavaScript and CSS modules.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client for HTTP route validation."""
    return TestClient(app)


# ── 1. HTML Route Rendering ───────────────────────────────────────────────

def test_dashboard_route_rendering(client: TestClient):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Enterprise AI Governance Dashboard" in response.text
    assert "RAG Assistant" in response.text
    assert "Hybrid Search" in response.text
    assert "AI Agent Workspace" in response.text


def test_assistant_route_rendering(client: TestClient):
    response = client.get("/assistant")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Governance AI Assistant" in response.text
    assert "Retrieved Sources &amp; Evidence" in response.text or "Retrieved Sources & Evidence" in response.text
    assert "rag-clearance" in response.text
    assert "rag-role" in response.text


def test_search_route_rendering(client: TestClient):
    response = client.get("/search")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hybrid Document Search" in response.text
    assert "search-query-input" in response.text
    assert "filter-clearance" in response.text
    assert "filter-role" in response.text


def test_agent_route_rendering(client: TestClient):
    response = client.get("/agent")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Controlled AI Agent Workspace" in response.text
    assert "agent-request-input" in response.text
    assert "agent-clearance" in response.text
    assert "step-validation" in response.text
    assert "agent-audit-list" in response.text
    assert "Agent Audit Feed" in response.text


def test_evaluation_route_rendering(client: TestClient):
    response = client.get("/evaluation")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RAG &amp; Governance Evaluation" in response.text or "RAG & Governance Evaluation" in response.text
    assert "eval-run-btn" in response.text
    assert "metric-exposure" in response.text


def test_monitoring_route_rendering(client: TestClient):
    response = client.get("/monitoring")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "System Monitoring &amp; Observability" in response.text or "System Monitoring & Observability" in response.text
    assert "card-probe-liveness" in response.text
    assert "prom-metrics-preview" in response.text


def test_governance_and_audit_route_rendering(client: TestClient):
    gov_resp = client.get("/governance")
    assert gov_resp.status_code == 200
    assert "text/html" in gov_resp.headers["content-type"]

    audit_resp = client.get("/audit")
    assert audit_resp.status_code == 200
    assert "text/html" in audit_resp.headers["content-type"]


# ── 2. Backend API Integration Endpoints ──────────────────────────────────

def test_api_evaluation_latest(client: TestClient):
    response = client.get("/api/v1/evaluation/latest")
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "unauthorized_exposure_rate" in data
    assert "retrieval_metrics" in data
    assert "rag_metrics" in data
    assert data["unauthorized_exposure_rate"] == 0.0


def test_api_evaluation_runs_list(client: TestClient):
    response = client.get("/api/v1/evaluation/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert isinstance(data["runs"], list)
    assert len(data["runs"]) >= 1


def test_api_monitoring_summary(client: TestClient):
    response = client.get("/api/v1/monitoring/summary")
    assert response.status_code == 200
    data = response.json()
    assert "liveness" in data
    assert "readiness" in data
    assert "telemetry" in data
    assert "total_http_requests" in data["telemetry"]
    assert "total_rag_requests" in data["telemetry"]
    assert "total_agent_executions" in data["telemetry"]


def test_api_agent_audit_feed(client: TestClient):
    response = client.get("/api/v1/agent/audit")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "audit_records" in data
    assert isinstance(data["audit_records"], list)


# ── 3. Frontend Static Assets Delivery ────────────────────────────────────

@pytest.mark.parametrize("asset_path", [
    "/static/js/api.js",
    "/static/js/app.js",
    "/static/js/assistant.js",
    "/static/js/search.js",
    "/static/js/agent.js",
    "/static/js/evaluation.js",
    "/static/js/monitoring.js",
    "/static/css/search.css",
    "/static/css/agent.css",
    "/static/css/evaluation.css",
    "/static/css/monitoring.css",
])
def test_static_assets_exist(client: TestClient, asset_path: str):
    response = client.get(asset_path)
    assert response.status_code == 200
    assert len(response.content) > 50


def test_api_js_contains_phase16_methods(client: TestClient):
    response = client.get("/static/js/api.js")
    assert response.status_code == 200
    text = response.text
    assert "const rag = {" in text or "rag = {" in text
    assert "governanceSearch" in text
    assert "const agent = {" in text or "agent = {" in text
    assert "const evaluation = {" in text or "evaluation = {" in text
    assert "const monitoring = {" in text or "monitoring = {" in text
    assert "rag, retrieval, agent, evaluation, monitoring" in text
