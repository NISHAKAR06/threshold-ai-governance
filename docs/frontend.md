# Frontend Architecture — Threshold AI Governance

## 1. Design & Technology Stack
- **Architecture:** Server-rendered Jinja2 templates paired with a lightweight, reactive Vanilla JavaScript SPA Router (`SPARouter` in `app/static/js/router.js`).
- **Styling:** Modular Vanilla CSS utilizing CSS custom properties (variables) for consistent themes, dark mode support, and typography.
- **API Client:** Singleton `THRESHOLDAPI` client in `app/static/js/api.js` providing centralized token management, automatic retries, and unified error handling.

## 2. Interface Modules
1. **Executive Dashboard (`/dashboard`):** Real-time metric widgets, activity streams, and operational health status.
2. **RAG Assistant (`/rag`):** Interactive compliance Q&A chat interface with streaming indicators, source drawer, and confidence badges.
3. **Hybrid Search Explorer (`/retrieval`):** Interactive dual-mode document finder comparing semantic vs keyword retrieval rankings with clearance badges.
4. **Controlled Agent Workspace (`/agent`):** Dual-engine task runner supporting both procedural Agent Controller and LangGraph StateGraph orchestration.
5. **Governance & HITL Review (`/review`):** Human-in-the-Loop review portal for approving, rejecting, or amending high-risk operational tickets.
6. **Audit & Traceability Explorer (`/audit`):** Filterable, paginated audit trail with CSV/JSON export capabilities.
7. **Evaluation Benchmark Suite (`/evaluation`):** Visual scorecards displaying Precision@K, Recall@K, MRR, and grounding rates.
8. **Observability & Health Monitor (`/monitoring`):** Live telemetry dashboards showing latencies, request throughputs, and system readiness.
