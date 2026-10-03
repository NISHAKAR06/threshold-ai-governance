# Governance Engine Specification — Threshold AI Governance

> **Current Version: v2.0** — Governance is now enforced as a dedicated, mandatory `governance_check` graph node in the LangGraph StateGraph.

---

## 1. Governance Architecture

### v1 (Before)
Governance checks in v1 were **embedded inline** within `AgentController` methods:
```python
# v1 — inline checks in AgentController
if user.clearance < required_clearance:
    return refusal_response()
if tool not in allowed_tools:
    return refusal_response()
result = execute(tool)
```
This approach made governance logic **tightly coupled** to routing code, difficult to test in isolation, and prone to being skipped under refactoring.

### v2 (After — Current)
Governance is now a **dedicated, mandatory node** in the LangGraph StateGraph:
```text
[request_router] → [governance_check] → conditional routing
```
The `governance_check` node **always executes** before any capability node. It cannot be bypassed by routing errors or code changes.

---

## 2. Policy Layers

### 2.1 Role-Based Access Control (RBAC)
Hierarchical roles (ascending privilege):
```
GUEST < EMPLOYEE < ANALYST < ENGINEER < REVIEWER < ADMIN < SUPERADMIN
```

Clearance hierarchy (ascending sensitivity):
```
PUBLIC (0) < INTERNAL (1) < CONFIDENTIAL (2) < RESTRICTED (3)
```

### 2.2 Codified Governance Policies (AG-01..AG-04)

| Policy ID | Name | Rule | v1 | v2 |
|:---|:---|:---|:---|:---|
| **AG-01** | Clearance Enforceability | Caller clearance rank ≥ resource sensitivity rank. | ✅ | ✅ Enforced in `governance_check` node |
| **AG-02** | Department Partitioning | Prevents cross-departmental access for CONFIDENTIAL/RESTRICTED assets unless caller holds global audit clearance. | ✅ | ✅ Enforced in `governance_check` node |
| **AG-03** | High-Impact Operational Guard | Mandates HITL review for state-mutating operations (table drops, credential rotations, user deletions). | ✅ | ✅ Routes to `hitl_review` node |
| **AG-04** | Zero-Trust Model Context | Forbids unauthorized chunk from being rendered in LLM prompts. | ✅ | ✅ Enforced in `rag_node` pre-context filter |

---

## 3. Policy Decisions

Every request produces one of three deterministic outcomes from the `governance_check` node:

| Decision | Routing | Description |
|:---|:---|:---|
| **ALLOW** | → `rag_node` or `tool_execution` | Access credentials satisfy all policy requirements. Capability executes automatically. |
| **DENY** | → `safe_denial` | Security policy violation or insufficient clearance. Safe refusal returned without leaking system internals. |
| **REVIEW** | → `hitl_review` | Action is conditionally permitted but carries high operational risk. Automated execution halted; `REV-GRAPH-*` ticket generated. |

---

## 4. Tool Authorization Engine

In addition to AG-01..AG-04 policy evaluation, the `governance_check` node invokes `ToolAuthorizationEngine` against every resolved tool before execution:

| Check | Description |
|:---|:---|
| **Permission Check** | Caller must hold the tool's `required_permission` capability. |
| **Clearance Check** | Caller clearance must meet or exceed the tool's `required_clearance` level. |
| **Risk-Level Check** | Tools with `risk_level = HIGH` require `is_admin = True` or trigger REVIEW routing. |
| **Destructive Pattern** | Keywords (`drop`, `delete`, `purge`, `truncate`) in requests trigger AG-03 REVIEW regardless of tool. |

---

## 5. Registered Tool Governance Metadata

| Tool | Required Permission | Required Clearance | Risk Level | Approval Required |
|:---|:---|:---|:---|:---|
| `GovernanceRAGTool` | `RAG_QUESTION` | `PUBLIC` | `LOW` | No |
| `GovernanceRetrievalTool` | `RETRIEVAL_SEARCH` | `INTERNAL` | `LOW` | No |
| `GovernanceEvaluationTool` | `GOVERNANCE_EVALUATION` | `INTERNAL` | `MEDIUM` | No |
