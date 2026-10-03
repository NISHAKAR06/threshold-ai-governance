# Controlled AI Agent & LangGraph Orchestration — Threshold

## 1. LangGraph StateGraph Architecture
Threshold integrates an explicit, compiled **LangGraph `StateGraph`** (`app/agent_graph/`) to orchestrate enterprise requests with governance-first enforcement, controlled tool execution, and immutable auditing.

```
START
  │
  ▼
[request_router] ── RAI Input Guard (Prompt Injection Mitigation)
  │
  ▼
[governance_check] ── Deterministic PolicyEngine (AG-01..AG-04) & ToolAuthorizationEngine
  │
  ├─── DENY ───► [safe_denial] ───────────────┐
  │                                           │
  ├─── REVIEW ─► [hitl_review] ───────────────┤
  │                                           │
  └─── ALLOW ──► [rag_node | tool_execution]  │
                        │                     │
                        ▼                     │
                 [output_guard]               │
                        │                     │
                        ▼                     ▼
                  [audit_node] ◄──────────────┘
                        │
                        ▼
                       END
```

---

## 2. Typed Graph State (`AgentGraphState`)
The state dictionary passed strictly between nodes contains only the context required for execution and governance:

| State Key | Type | Description |
|:---|:---|:---|
| `request_id` | `str` | Unique request correlation identifier. |
| `user_id` | `str` | Authenticated principal ID. |
| `user_role` | `str` | RBAC role (e.g. `EMPLOYEE`, `ANALYST`, `AUDITOR`, `ADMIN`). |
| `user_query` | `str` | Sanitized natural language request. |
| `governance_result` | `Dict[str, Any]` | Evaluation verdict (`ALLOW`, `DENY`, `REVIEW`), reasons, risk score, and rules. |
| `retrieval_context` | `List[Dict[str, Any]]` | Authorized chunks retrieved for RAG grounding. |
| `selected_action` | `Optional[str]` | Resolved registered tool identifier (e.g. `GovernanceEvaluationTool`). |
| `tool_result` | `Optional[Any]` | Structured output from tool execution. |
| `final_response` | `Optional[str]` | Final verified, sanitized response text. |
| `review_required` | `bool` | Flag indicating whether HITL review is mandated. |
| `error` | `Optional[str]` | Error message if execution halted. |
| `audit_metadata` | `Dict[str, Any]` | Complete audit event record. |
| `audit_reference` | `Optional[str]` | Immutable audit log event ID (`AUD-LG-...`). |
| `execution_time_ms`| `float` | End-to-end execution latency in milliseconds. |
| `status` | `str` | Status: `INITIALIZED`, `ROUTED`, `GOVERNED`, `COMPLETED`, `DENIED`, `PENDING_REVIEW`, `INSUFFICIENT_CONTEXT`, `ERROR`. |

*Security Guardrail:* Storing API credentials, system prompts, or unredacted secrets in `AgentGraphState` is strictly prohibited.

---

## 3. Node Responsibilities
1. **`request_router` (`request_router.py`):**
   - Applies early Responsible AI Input Guard to intercept adversarial prompt injections.
   - Maps natural language intent to capabilities (`RAG_QUESTION`, `RETRIEVAL_SEARCH`, `GOVERNANCE_EVALUATION`).
   - Resolves target tool candidate from `ToolRegistry`.

2. **`governance_check` (`governance_check.py`):**
   - Evaluates caller's `AccessContext` (role, clearance level, department) against deterministic policies (AG-01..AG-04) using `PolicyDecisionEngine`.
   - Invokes `ToolAuthorizationEngine` to verify tool permissions before any execution.
   - Detects destructive operations (`drop`, `delete`, `purge`, `truncate`) and enforces admin-only clearance or HITL escalation.

3. **`routing` (`routing.py`):**
   - Conditional edge router directing state based on governance verdict:
     - `DENY` -> `safe_denial`
     - `REVIEW` -> `hitl_review`
     - `ALLOW` (RAG) -> `rag_node`
     - `ALLOW` (Tool) -> `tool_execution`

4. **`safe_denial` (`safe_denial_node.py`):**
   - Generates safe, non-leaking refusal messages without exposing internal policies or system prompts.

5. **`hitl_review` (`hitl_review_node.py`):**
   - Generates human review ticket (`REV-GRAPH-...`), halts autonomous execution, and sets status to `PENDING_REVIEW`.

6. **`rag_node` (`rag_node.py`):**
   - Calls `RAGService` to retrieve hybrid semantic+keyword policy chunks.
   - Excludes unauthorized documents at the chunk level before prompting the LLM.
   - Handles insufficient context safely without fabricating answers or hallucinations.

7. **`tool_execution` (`tool_execution.py`):**
   - Verifies authorization assertion before tool invocation.
   - Validates input arguments using `tool.validate_input()`.
   - Executes registered `BaseAgentTool`.
   - Validates tool output with `ToolOutputValidator`.

8. **`output_guard` (`output_guard_node.py`):**
   - Validates response structure.
   - Validates citations against authorized retrieved sources.
   - Scans for API keys, bearer tokens, database URIs, or private keys.
   - Detects and strips hidden internal chain-of-thought (`thought:`, `internal reasoning:`).

9. **`audit_node` (`audit_node.py`):**
   - Creates immutable audit record (`AgentAuditRecord`) containing correlation ID, user ID, role, capability, tool, decisions, and latencies.
   - Records Prometheus metrics (`record_agent_metrics`, `record_governance_event`).

---

## 4. Controlled Tool Registry
Dynamic code execution (`eval()`, `exec()`, shell commands, subprocess) is strictly forbidden. The system executes only tools implementing `BaseAgentTool` registered in `ToolRegistry`:

| Tool Name | Capability | Input Schema | Required Permission | Required Clearance | Risk Level | Requires Approval |
|:---|:---|:---|:---|:---|:---|:---|
| `GovernanceRAGTool` | `RAG_QUESTION` | `{"question": str, "top_k": int}` | `RAG_QUESTION` | `PUBLIC` | `LOW` | No |
| `GovernanceRetrievalTool` | `RETRIEVAL_SEARCH` | `{"query": str, "top_k": int}` | `RETRIEVAL_SEARCH` | `INTERNAL` | `LOW` | No |
| `GovernanceEvaluationTool` | `GOVERNANCE_EVALUATION` | `{"request": str}` | `GOVERNANCE_EVALUATION` | `INTERNAL` | `MEDIUM` | No |

---

## 5. API Usage

### `POST /api/v1/agent/graph/execute`
Executes user requests through the LangGraph StateGraph engine.

**Request:**
```json
{
  "request": "What is the retention period for financial audit logs?",
  "access_context": {
    "user_id": "EMP-5002",
    "role": "ANALYST",
    "department": "FINANCE",
    "clearance_level": "INTERNAL",
    "is_admin": false
  },
  "request_id": "req-api-example-001"
}
```

**Response:**
```json
{
  "request_id": "req-api-example-001",
  "status": "COMPLETED",
  "response": "Financial audit logs must be retained for a mandatory period of 7 years...",
  "sources": [
    {
      "source_id": "SRC-001",
      "document_id": "POL-FIN-004",
      "classification": "INTERNAL",
      "is_cited": true
    }
  ],
  "audit_id": "AUD-LG-D871C8F61A",
  "capability": "RAG_QUESTION",
  "execution_time_ms": 32.4
}
```

---

## 6. Testing Strategy
A comprehensive 15-test validation suite (`tests/unit/agents/test_langgraph_governance_scenarios.py`) verifies all required operational flows and governance invariants:

1. **Valid Authorized Request:** Successful end-to-end traversal yielding grounded response.
2. **Unauthorized Request:** Insufficient clearance triggers safe denial.
3. **Denied Request:** Adversarial prompt injection halted by Responsible AI guard.
4. **Review-Required Request:** Destructive admin actions routed to HITL queue.
5. **Authorized Tool Execution:** Registered tool executed under verified credentials.
6. **Unauthorized Tool Execution:** Disallowed tool invocation blocked prior to execution.
7. **RAG Request:** Grounded policy generation with authorized citations.
8. **Insufficient-Context Request:** Graceful handling without hallucinations or false citations.
9. **Invalid Tool Input:** Parameter validation rejects bad payloads.
10. **Output Validation Failure:** Secret leaks or chain-of-thought redacted by Output Guard.
11. **Audit Creation:** Complete audit metadata persisted in append-only log.
12. **Graph Routing:** Conditional decision router maps outcomes deterministically.
13. **Invariant 1:** UNAUTHORIZED USER CANNOT EXECUTE TOOL.
14. **Invariant 2:** UNAUTHORIZED DOCUMENT CANNOT REACH LLM.
15. **Invariant 3:** DENIED REQUEST CANNOT REACH EXECUTION NODE.
