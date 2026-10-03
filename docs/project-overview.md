# Project Overview — Threshold AI Governance Platform

**Threshold AI Governance** is an enterprise-grade, production-style platform integrating **Python, Generative AI, Governance-Aware RAG (Retrieval-Augmented Generation), and LangGraph Agentic AI Orchestration**.

> **Current Version: v2.0 — LangGraph StateGraph Governance Platform**
> See [CHANGELOG.md](../CHANGELOG.md) for a full v1 → v2 migration breakdown.

---

## 1. Problem Statement
Modern enterprises deploying Large Language Models (LLMs) and autonomous agents face critical operational risks:
- **Unauthorized Context Leakage:** Sensitive corporate data stored in vector indexes leaking to low-clearance callers via LLM prompts.
- **Hallucinations & Ungrounded Answers:** Models answering questions without verifiable citations or grounded reference to authorized compliance documentation.
- **Adversarial Exploitation:** Malicious actors deploying prompt injection, system overrides, or jailbreaks to manipulate agent execution.
- **Uncontrolled Autonomy:** Agents executing destructive operations (e.g., dropping database tables, deleting employee records) without human confirmation or policy boundaries.
- **Lack of Observability & Auditability:** Missing cryptographic traceability, structured metric telemetry, or immutable audit logs across generative workflows.

---

## 2. The Threshold Solution
Threshold establishes a **Zero-Trust Governance Perimeter** around enterprise LLM interactions:
1. **Responsible AI Input Guard:** Real-time heuristic and regex pattern mitigation for prompt injection, system overrides, delimiter attacks, and excessive payloads.
2. **Deterministic Pre-Retrieval Governance:** Evaluating caller roles, departments, and clearance levels against codified policies (AG-01..AG-04) before executing tools or searches.
3. **Governance-Aware Hybrid Retrieval:** Combining BM25 lexical keyword search with dense ChromaDB vector similarity, ranking via Reciprocal Rank Fusion (RRF), and filtering out unauthorized chunks *before* context synthesis.
4. **Source-Grounded RAG Generation:** Answers strictly constrained to authorized citations with fallback to `INSUFFICIENT_CONTEXT` rather than hallucinating unsupported claims.
5. **LangGraph StateGraph Orchestration:** A typed, acyclic execution graph managing state, conditional routing, Human-in-the-Loop (HITL) escalations, and automated rollbacks.
6. **Responsible AI Output Guard:** Post-generation scanning for unauthorized document IDs, confidential metadata leaks, and template disclosures.
7. **End-to-End Audit & Observability:** Correlation of every API invocation via unique Request IDs, Prometheus metrics, and tamper-evident audit logs.

---

## 3. Version Evolution: v1 → v2

### v1 — Phase 14 Governance Baseline (2026-09)
The initial version established all foundational capabilities:
- **Synchronous `AgentController`** dispatched requests via inline `if/elif` routing to RAG, retrieval, or tool capabilities.
- Governance checks were **embedded inside controller methods** — not isolated or independently testable.
- Audit and HITL calls were **manual**, meaning a coding error could skip them.
- API responses were **inconsistently shaped** depending on path (RAG vs tool vs denial).

### v2 — LangGraph StateGraph Governance Platform (2026-10)
v2 replaces the ad-hoc orchestration model with a formal, compiled **LangGraph `StateGraph`**:
- **Explicit graph nodes** (`request_router` → `governance_check` → `rag_node` | `tool_execution` | `safe_denial` | `hitl_review` → `output_guard` → `audit_node`) replace implicit controller flow.
- **`AgentGraphState` TypedDict** carries all context immutably across nodes — no shared mutable state, no secret leakage.
- **`audit_node` is always the terminal step** — 100% audit coverage is a graph topology guarantee, not a coding convention.
- **HITL escalation is a graph edge** — it cannot be bypassed by control flow bugs.
- **Unified API response schema** returns `response`, `sources`, `audit_id`, `capability`, and `execution_time_ms` on every request type.

---

## 4. Core Capabilities Matrix

| Capability | Engine / Service | Governance Enforcement | v1 | v2 |
| :--- | :--- | :--- | :--- | :--- |
| **Grounded Policy Q&A** | `RAGService` + `GeminiLLM` | Chunk-level clearance filtering | ✅ | ✅ Integrated in `rag_node` |
| **Hybrid Document Search** | `HybridRetrievalService` (BM25 + ChromaDB) | Metadata clearance matching | ✅ | ✅ Integrated in `rag_node` |
| **Controlled Agent Actions** | `AgentController` & `ToolRegistry` | Role-based tool clearance | ✅ | ✅ Wrapped in `tool_execution` node |
| **LangGraph Orchestration** | `compile_governance_graph()` | Conditional branching: `ALLOW`, `DENY`, `REVIEW` | ❌ | ✅ NEW |
| **Typed Graph State** | `AgentGraphState` TypedDict | 14-field immutable state propagation | ❌ | ✅ NEW |
| **Human-in-the-Loop Review** | `HITLReviewNode` + Review Tickets | Autonomous halts; pending sign-off | ✅ | ✅ Enforced as graph edge |
| **Adversarial Mitigation** | `ResponsibleAIInputGuard` | Real-time blocking of jailbreaks | ✅ | ✅ Integrated in `request_router` |
| **Output Chain-of-Thought Redaction** | `output_guard` node | Strips hidden internal reasoning | ❌ | ✅ NEW |
| **Enterprise Observability** | Prometheus Exporter (`/metrics`) | Latencies, hit rates, denial counts | ✅ | ✅ Atomic in `audit_node` |
| **Immutable Audit Records** | `AuditService` (`AUD-LG-*`) | Tamper-evident log per request | ✅ | ✅ Always executed; returned to caller |

---

## 5. Quality Assurance

```
============================= test session results =============================
platform win32 — Python 3.13.5, pytest-7.4.3
287 passed, 2 skipped, 0 failures — 60.56s (100% pass rate)
```

### LangGraph Governance Invariants (v2)
| ID | Invariant | Status |
|:---|:---|:---|
| INV-01 | Unauthorized user cannot execute any registered tool | ✅ VERIFIED |
| INV-02 | Unauthorized document cannot reach LLM context | ✅ VERIFIED |
| INV-03 | Denied request cannot reach any execution node | ✅ VERIFIED |

---

*See [`docs/architecture.md`](architecture.md) for system topology.*
*See [`docs/ai-agent.md`](ai-agent.md) for LangGraph implementation guide.*
*See [`CHANGELOG.md`](../CHANGELOG.md) for the full v1 → v2 changelog.*
