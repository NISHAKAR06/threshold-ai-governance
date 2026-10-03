# Observability & Metrics — Threshold AI Governance

> **Current Version: v2.0** — Prometheus metrics are now atomically recorded in the `audit_node` terminal graph step, guaranteeing 100% metric coverage for every LangGraph execution.

---

## 1. Request Correlation & Distributed Tracing

Every incoming request receives an authoritative `request_id` (client-supplied `X-Request-ID` header or UUID auto-generated):
- Propagates across: HTTP middleware → LangGraph `AgentGraphState` → Hybrid Retrieval → RAG LLM → `audit_node` → Audit Logs.
- Log format: Structured JSON including `timestamp`, `log_level`, `logger_name`, `module`, `function`, `request_id`.

### v1 vs v2 Tracing Comparison

| Aspect | v1 | v2 |
|:---|:---|:---|
| `request_id` propagation | Passed as function argument, could be lost | Stored in `AgentGraphState.request_id` — immutably propagated to all nodes |
| Metric recording | Manual calls in service methods | Atomic call in `audit_node` — always executes as terminal graph step |
| Audit record | Created if service call succeeded | `AUD-LG-*` always created; graph topology guarantees it |

---

## 2. Prometheus Metrics (`/metrics`)

All metrics are registered via `prometheus_client` and exported at `GET /metrics`:

| Metric | Type | Labels | Description |
|:---|:---|:---|:---|
| `threshold_http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP request count |
| `threshold_rag_queries_total` | Counter | `status` (`SUCCESS`, `INSUFFICIENT_CONTEXT`, `DENIED`) | RAG query count by outcome |
| `threshold_rag_retrieval_duration_seconds` | Histogram | — | Hybrid search latency distribution |
| `threshold_agent_requests_total` | Counter | `capability`, `status` | Agent graph execution count by capability and status |
| `threshold_governance_events_total` | Counter | `decision` (`decision_allow`, `decision_deny`, `decision_review`) | Policy decision counts |

### New in v2
- `threshold_agent_requests_total` now partitions by `capability` (`RAG_QUESTION`, `RETRIEVAL_SEARCH`, `GOVERNANCE_EVALUATION`).
- `threshold_governance_events_total` is recorded atomically per graph execution — no double-counting.
- `execution_time_ms` is captured end-to-end from graph `START` to `audit_node` completion.

---

## 3. Health & Readiness Probes

| Endpoint | Type | Checks |
|:---|:---|:---|
| `GET /health` | Liveness | Process is active and accepting connections |
| `GET /ready` | Readiness | Database connectivity + ChromaDB vector collection availability |
| `GET /metrics` | Prometheus scrape | All registered metrics in Prometheus text format |

---

## 4. Audit Log Schema (`AUD-LG-*`)

Every graph execution produces an immutable audit record with the following fields:

```json
{
  "audit_id": "AUD-LG-D871C8F61A",
  "request_id": "req-api-example-001",
  "user_id": "EMP-5002",
  "user_role": "ANALYST",
  "capability": "RAG_QUESTION",
  "governance_decision": "ALLOW",
  "tool_used": null,
  "status": "COMPLETED",
  "execution_time_ms": 32.4,
  "timestamp": "2026-10-03T09:14:26Z"
}
```
