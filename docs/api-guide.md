# API Reference Guide — Threshold AI Governance

All API endpoints are versioned under `/api/v1` and documented interactively at `/docs` (Swagger UI) and `/redoc`.

## 1. Authentication Endpoints
- `POST /api/v1/auth/login`: Authenticate with username or email + password. Returns JWT token.
- `POST /api/v1/auth/signup`: Create a new user account with employee profile.
- `POST /api/v1/auth/reset-password`: Self-service password reset for locked or existing users.
- `GET /api/v1/auth/me`: Retrieve current caller's profile and security clearance.

## 2. RAG & Retrieval Endpoints
- `POST /api/v1/rag/ask`: Grounded policy Q&A with source citations.
- `POST /api/v1/retrieval/search`: Hybrid lexical + semantic document search.
- `POST /api/v1/retrieval/governance-search`: Search with explicit governance filtering simulation.

## 3. Agent & Orchestration Endpoints
- `POST /api/v1/agent/execute`: Execute task using the procedural Controlled Agent Controller.
- `POST /api/v1/agent/graph/execute`: Execute task using the LangGraph StateGraph engine.
- `GET /api/v1/agent/audit`: Retrieve immutable audit logs of agent workflows.

## 4. Evaluation & Monitoring Endpoints
- `GET /api/v1/evaluation/latest`: Fetch latest evaluation benchmark results.
- `POST /api/v1/evaluation/run`: Trigger automated evaluation run across synthetic test dataset.
- `GET /api/v1/monitoring/summary`: Safe aggregated telemetry summary for dashboard display.
- `GET /health`: Liveness probe.
- `GET /ready`: Readiness probe.
- `GET /metrics`: Prometheus metric scrapable endpoint.
