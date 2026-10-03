# Evaluation Framework — Threshold AI Governance

> **Current Version: v2.0** — Evaluation now covers LangGraph governance scenario testing in addition to retrieval quality benchmarks.

---

## 1. Overview
The platform includes automated evaluation harnesses to test retrieval quality, answer grounding, access-control integrity, and LangGraph governance correctness against standardized synthetic test datasets.

---

## 2. Evaluation Layers

### Layer 1 — Retrieval Quality (v1 + v2)
Standard information-retrieval metrics against the 200-document synthetic enterprise policy library:

| Metric | Description | Target |
|:---|:---|:---|
| **Precision@K** | Proportion of retrieved chunks relevant to the query | ≥ 0.85 |
| **Recall@K** | Proportion of ground-truth relevant chunks in top-K results | ≥ 0.80 |
| **MRR** | Mean Reciprocal Rank of first relevant chunk | ≥ 0.75 |
| **Document Hit Rate** | % of test queries with ≥ 1 ground-truth document retrieved | ≥ 0.90 |

### Layer 2 — RAG Grounding & Safety (v1 + v2)
| Metric | Description | Target |
|:---|:---|:---|
| **Grounding Fidelity** | Generated answers cite only sources in authorized context | 100% |
| **Unauthorized Exposure Rate** | Unauthorized chunk reaches LLM prompt or output | **0.00%** |
| **Hallucination Rate** | Answers fabricated without authorized source chunks | **0.00%** |

### Layer 3 — LangGraph Governance Scenarios (v2 NEW)
15-scenario unit test suite verifying all operational paths and invariants:

| # | Scenario | Expected Outcome |
|:---|:---|:---|
| 1 | Valid authorized request | `COMPLETED`, response grounded, audit `AUD-LG-*` created |
| 2 | Unauthorized user (insufficient clearance) | `DENIED`, safe refusal, no content leaked |
| 3 | Adversarial prompt injection | `DENIED` at `request_router`, `SYSTEM_OVERRIDE` category |
| 4 | Destructive admin action | `PENDING_REVIEW`, `REV-GRAPH-*` ticket created |
| 5 | Authorized tool execution | Tool result returned, audit persisted |
| 6 | Unauthorized tool execution | `DENIED` before tool invokes; no execution |
| 7 | RAG policy question | Grounded answer with cited sources |
| 8 | Insufficient context | `INSUFFICIENT_CONTEXT` status, no LLM call |
| 9 | Invalid tool input | Validation error; input rejected |
| 10 | Output containing secret leak | Secret redacted by `output_guard` node |
| 11 | Audit record creation | `AUD-LG-*` persisted with full metadata |
| 12 | Graph routing determinism | `DENY`→`safe_denial`, `REVIEW`→`hitl_review`, `ALLOW`→execution |
| INV-01 | Unauthorized user attempts tool | Tool node never invoked — **INVARIANT** |
| INV-02 | Unauthorized document path | Document never enters LLM context — **INVARIANT** |
| INV-03 | Denied request execution path | Execution node never reached — **INVARIANT** |

---

## 3. Running Evaluation

```bash
# Run the full test suite (unit + integration)
python -m pytest tests/unit tests/integration -v

# Run LangGraph-specific governance scenarios only
python -m pytest tests/unit/agents/test_langgraph_governance_scenarios.py -v

# Run the RAG quality evaluation benchmark
python scripts/run_rag_eval.py

# Or via API
curl -X POST http://localhost:8000/api/v1/evaluation/run
```

Results are persisted to the database and visualized in the Evaluation Dashboard UI.

---

## 4. v2 Test Results (Latest Run)

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-7.4.3
collected 289 items

287 passed, 2 skipped, 0 failures in 60.56s (100% pass rate)
```

| Governance Invariant | Result |
|:---|:---|
| INV-01: Unauthorized user cannot execute tool | ✅ PASS |
| INV-02: Unauthorized document cannot reach LLM | ✅ PASS |
| INV-03: Denied request cannot reach execution | ✅ PASS |
