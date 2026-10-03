# Threshold AI Governance — CHANGELOG

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v2.0.0] — LangGraph Governance Platform — 2026-10

### 🏛️ Summary
v2 is a **major architectural upgrade** introducing a production-grade, compiled **LangGraph `StateGraph`** as the authoritative request-orchestration engine. The custom, ad-hoc agent routing logic of v1 is replaced by an explicit, auditable graph with typed state, conditional routing, and fully integrated governance enforcement at every node boundary.

No existing working functionality was removed. All v1 services (`RAGService`, `HybridRetrievalService`, `AgentController`, `PolicyDecisionEngine`, `HITLReviewService`, `AuditService`) are **reused** within the new graph nodes rather than duplicated.

---

### ✅ Added

#### Core — LangGraph `StateGraph` Engine (`app/agent_graph/`)
| File | Change |
|:---|:---|
| `app/agent_graph/state.py` | NEW — Defines `AgentGraphState` TypedDict with 14 strongly-typed fields for request correlation, access context, governance decisions, retrieval results, audit metadata, and final status. |
| `app/agent_graph/graph.py` | NEW — Compiles and exports `compile_governance_graph()` using `StateGraph` with all 8 nodes and conditional edges. |
| `app/agent_graph/routing.py` | NEW — Conditional edge routing functions mapping `AgentGraphState.status` / `governance_result.decision` to the correct next node. |
| `app/agent_graph/nodes/request_router.py` | NEW — First graph node; applies `ResponsibleAIInputGuard` and resolves natural-language intent to a structured capability. |
| `app/agent_graph/nodes/governance_check.py` | NEW — Evaluates caller `AccessContext` against AG-01..AG-04 via `PolicyDecisionEngine` and `ToolAuthorizationEngine`. |
| `app/agent_graph/nodes/rag_node.py` | NEW — Calls `RAGService` for hybrid retrieval + Gemini synthesis under authorized context. |
| `app/agent_graph/nodes/tool_execution.py` | NEW — Executes `BaseAgentTool` implementations from `ToolRegistry` after authorization assertion. |
| `app/agent_graph/nodes/safe_denial_node.py` | NEW — Formats non-leaking refusal messages for `DENY` outcomes. |
| `app/agent_graph/nodes/hitl_review_node.py` | NEW — Generates `REV-GRAPH-*` tickets and halts automated execution for high-risk mutations. |
| `app/agent_graph/nodes/output_guard_node.py` | NEW — Post-generation scanning: credential leak detection, unauthorized doc ID scanner, CoT redaction. |
| `app/agent_graph/nodes/audit_node.py` | NEW — Creates immutable `AgentAuditRecord` (`AUD-LG-*`) and records Prometheus governance metrics. |

#### Agent Tooling
| File | Change |
|:---|:---|
| `app/agents/tools/base_tool.py` | ENHANCED — Added `input_schema`, `risk_level`, `required_permission`, and `clearance` metadata properties. |
| `app/agents/tool_registry.py` | ENHANCED — `ToolRegistry` now exposes tool metadata via `get_tool_metadata()` for governance enforcement. |

#### API
| File | Change |
|:---|:---|
| `app/api/routes/agent.py` | ENHANCED — `POST /api/v1/agent/graph/execute` returns structured `AgentGraphResponse` (`response`, `sources`, `audit_id`, `capability`, `execution_time_ms`). |

#### Testing
| File | Change |
|:---|:---|
| `tests/unit/agents/test_langgraph_governance_scenarios.py` | NEW — 15-test comprehensive LangGraph governance scenario suite (12 operational + 3 governance invariants). |

#### Dependencies
| Package | Change |
|:---|:---|
| `langgraph` | ADDED — Core graph orchestration framework. |
| `chromadb` | ADDED — Vector store for dense semantic retrieval. |
| `prometheus-client` | ADDED — Prometheus metrics export. |
| `rank-bm25` | ADDED — BM25 keyword search engine. |

---

### 🔄 Changed (v1 → v2 Comparison)

#### Agent Orchestration

| Aspect | v1 (Before) | v2 (After) |
|:---|:---|:---|
| **Orchestration Model** | `AgentController` — linear, synchronous class-based handler | `StateGraph` — compiled, typed, acyclic graph with conditional edges |
| **State Management** | Ad-hoc local variables, no typed schema | `AgentGraphState` TypedDict — 14 strongly-typed fields propagated immutably |
| **Governance Enforcement** | Inline conditionals scattered in controller methods | Dedicated `governance_check` node — mandatory for every request |
| **Routing Logic** | `if/elif` chains | Declarative conditional edge functions in `routing.py` |
| **Output Safety** | Basic response formatting | Dedicated `output_guard` node: credential scanning, CoT redaction, citation verification |
| **Audit Trail** | Manual service-level calls | `audit_node` — always terminal step, 100% audit coverage guaranteed |
| **Observability** | Manual Prometheus calls in service methods | Atomic `record_agent_metrics` + `record_governance_event` in `audit_node` |
| **HITL Review** | Optional escalation path | `hitl_review` node is mandatory graph vertex for `REVIEW` decisions — cannot be bypassed |

#### API Response Schema

| Field | v1 | v2 |
|:---|:---|:---|
| `response` | `answer` (RAG-only field) | `response` (unified across RAG, tool, denial) |
| `sources` | Only in RAG responses | Always present; empty list for non-RAG responses |
| `audit_id` | Not returned to caller | `AUD-LG-*` returned in every response |
| `capability` | Not returned | `RAG_QUESTION`, `RETRIEVAL_SEARCH`, `GOVERNANCE_EVALUATION` |
| `execution_time_ms` | Not returned | Returned in every response |

---

### 🧪 Test Results — v2 Final Verified Run

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-7.4.3
collected 289 items

tests/unit/agents/test_agent_controller.py               PASSED [12/12]
tests/unit/agents/test_agent_graph.py                    PASSED [11/11]
tests/unit/agents/test_agent_router.py                   PASSED [ 6/6]
tests/unit/agents/test_agent_service.py                  PASSED [ 9/9]
tests/unit/agents/test_agent_validator.py                PASSED [ 7/7]
tests/unit/agents/test_governance_rag_tool.py            PASSED [ 4/4]
tests/unit/agents/test_langgraph_governance_scenarios.py PASSED [15/15]
tests/unit/agents/test_tool_authorization.py             PASSED [ 8/8]
tests/unit/agents/test_tool_registry.py                  PASSED [ 6/6]
tests/integration/test_langgraph_agent.py                PASSED [ 8/8]
tests/integration/test_governance_rag.py                 PASSED [18/18]
tests/integration/test_governance_retrieval.py           PASSED [22/22]
...rest of suite...

287 passed, 2 skipped, 0 failures in 60.56s (100% pass rate)
```

---

### 🔒 Governance Invariants — Verified

| ID | Invariant | Test | Status |
|:---|:---|:---|:---|
| INV-01 | Unauthorized user **cannot** execute any registered tool | `test_invariant_unauthorized_user_cannot_execute_tool` | ✅ PASS |
| INV-02 | Unauthorized document **cannot** reach LLM context | `test_invariant_unauthorized_document_cannot_reach_llm` | ✅ PASS |
| INV-03 | Denied request **cannot** reach any execution node | `test_invariant_denied_request_cannot_reach_execution` | ✅ PASS |

---

## [v1.0.0] — Phase 14 Governance Baseline — 2026-09

### Summary
v1 established the foundational governance platform: RBAC access control, hybrid retrieval pipeline (BM25 + ChromaDB + RRF), Responsible AI guardrails, and a synchronous `AgentController` for capability routing. This version defined all domain models, policy engines, and integration test infrastructure subsequently reused by v2.

### Key Deliverables
- `AgentController` — Synchronous capability dispatcher with inline governance checks.
- `PolicyDecisionEngine` — Deterministic AG-01..AG-04 policy evaluator.
- `HybridRetrievalService` — BM25 + ChromaDB with Reciprocal Rank Fusion.
- `RAGService` — Governance-aware RAG with `INSUFFICIENT_CONTEXT` guard.
- `HITLReviewService` — Human-in-the-Loop review ticket workflow.
- `AuditService` — Tamper-evident audit log with Prometheus metrics.
- `ResponsibleAIInputGuard` + `ResponsibleAIOutputGuard` — Multi-stage safety controls.
- `ToolRegistry` + `BaseAgentTool` — Sandboxed tool execution framework.
- 200+ unit and integration tests — Comprehensive quality gate.
- Vanilla JS/CSS Enterprise SPA — Dashboard, RAG, Search, Agent, Evaluation, Monitoring UIs.

---

*For full API reference, see [`docs/api-guide.md`](docs/api-guide.md).*
*For architecture details, see [`docs/architecture.md`](docs/architecture.md).*
*For LangGraph implementation guide, see [`docs/ai-agent.md`](docs/ai-agent.md).*
