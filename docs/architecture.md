# Architecture Specification — Threshold AI Governance

> **Current Version: v2.0 — LangGraph StateGraph Governance Platform**

---

## 1. Architecture Evolution

### v1 — Synchronous AgentController (Phase 14 Baseline)
In v1, request orchestration flowed through a single `AgentController` class:
```text
HTTP Request → AgentController.handle()
                    ├── if RAG_QUESTION  → RAGService.query()
                    ├── if RETRIEVAL     → HybridRetrievalService.search()
                    └── if TOOL          → ToolRegistry.execute()
                    (governance checks embedded inline in each branch)
```
**Limitations:**
- Governance enforcement was not isolated — bugs in one branch could skip policy checks.
- Audit calls were placed manually; control flow errors could skip them.
- State was carried as loose function arguments — no typed schema.
- HITL escalation was a conditional `if` statement — bypassable by refactoring.

---

### v2 — LangGraph StateGraph (Current)
v2 replaces the controller with a **compiled, typed, acyclic `StateGraph`**. Every node is isolated, testable, and required to produce a well-formed `AgentGraphState` output:

```text
                             USER / CLIENT
                                   │
                                   ▼
                   FastAPI Web Application & API
                   (Request Correlation Middleware)
                                   │
                                   ▼
                       LANGGRAPH ORCHESTRATOR
                         (AgentGraphState)
                                   │
                                   ▼
                         [request_router]
               RAI Input Guard + Intent Resolution
                                   │
                                   ▼
                         [governance_check]
             AG-01..AG-04 PolicyDecisionEngine
             + ToolAuthorizationEngine
                                   │
               ┌───────────────────┼───────────────────┐
               ▼                   ▼                   ▼
             ALLOW                DENY               REVIEW
               │                   │                   │
               │                   ▼                   ▼
               │           [safe_denial]          [hitl_review]
               │           (Refusal format)   (Ticket REV-GRAPH-*)
               │                   │                   │
               ▼                   │                   │
     ┌─────────┴──────────┐        │                   │
     ▼                    ▼        │                   │
 [rag_node]       [tool_execution] │                   │
 (Hybrid Search    (ToolRegistry   │                   │
  + Synthesis)      Sandbox)       │                   │
     │                    │        │                   │
     └──────────┬──────────┘        │                   │
                ▼                   │                   │
         [output_guard]             │                   │
     (Credential + CoT Scan)        │                   │
                │                   │                   │
                └─────────┬─────────┴───────────────────┘
                          ▼
                     [audit_node]
           (Prometheus Metrics + AUD-LG-* Record)
                          │
                          ▼
                    FINAL RESPONSE
```

---

## 2. LangGraph Node Responsibilities

| Node | Module | Responsibility |
|:---|:---|:---|
| `request_router` | `nodes/request_router.py` | RAI Input Guard; intent resolution to capability |
| `governance_check` | `nodes/governance_check.py` | PolicyDecisionEngine AG-01..AG-04; ToolAuthorizationEngine |
| `rag_node` | `nodes/rag_node.py` | Hybrid retrieval + authorized context synthesis |
| `tool_execution` | `nodes/tool_execution.py` | Sandboxed `BaseAgentTool` execution |
| `safe_denial` | `nodes/safe_denial_node.py` | Non-leaking DENY response formatting |
| `hitl_review` | `nodes/hitl_review_node.py` | `REV-GRAPH-*` ticket creation; PENDING_REVIEW halt |
| `output_guard` | `nodes/output_guard_node.py` | Credential scan; CoT redaction; citation check |
| `audit_node` | `nodes/audit_node.py` | Immutable `AUD-LG-*` record; Prometheus metrics |

---

## 3. Typed State Schema (`AgentGraphState`)

```python
class AgentGraphState(TypedDict):
    request_id:        str           # Correlation ID
    user_id:           str           # Authenticated principal
    user_role:         str           # RBAC role
    user_query:        str           # Sanitized input
    access_context:    Dict          # Roles, dept, clearance
    governance_result: Dict          # ALLOW/DENY/REVIEW + rules
    retrieval_context: List[Dict]    # Authorized chunks
    selected_action:   Optional[str] # Resolved tool ID
    tool_result:       Optional[Any] # Tool output
    final_response:    Optional[str] # Sanitized response text
    review_required:   bool          # HITL escalation flag
    error:             Optional[str] # Error if halted
    audit_metadata:    Dict          # Full audit event record
    audit_reference:   Optional[str] # AUD-LG-* identifier
    execution_time_ms: float         # End-to-end latency
    status:            str           # INITIALIZED → COMPLETED/DENIED/PENDING_REVIEW/ERROR
```

**Security Guardrail:** Storing API credentials, system prompts, or unredacted secrets in `AgentGraphState` is strictly prohibited.

---

## 4. Component Directory Layout

```text
threshold-ai-governance/
├── app/
│   ├── agent_graph/          # ← NEW in v2: LangGraph StateGraph engine
│   │   ├── nodes/            #   8 discrete graph nodes
│   │   │   ├── request_router.py
│   │   │   ├── governance_check.py
│   │   │   ├── rag_node.py
│   │   │   ├── tool_execution.py
│   │   │   ├── safe_denial_node.py
│   │   │   ├── hitl_review_node.py
│   │   │   ├── output_guard_node.py
│   │   │   └── audit_node.py
│   │   ├── graph.py          #   Compilation and graph invocation
│   │   ├── routing.py        #   Conditional branching functions
│   │   └── state.py          #   Typed AgentGraphState TypedDict
│   ├── agents/               # v1 AgentController & tools (still active)
│   ├── api/                  # FastAPI routers (auth, rag, agent, monitoring)
│   ├── core/                 # App lifecycle, database engine, logging
│   ├── engines/              # PolicyEngine, RiskEngine, DecisionEngine
│   ├── models/               # Domain dataclasses and SQL models
│   ├── repositories/         # Vector and relational repositories
│   ├── responsible_ai/       # InputGuard, OutputGuard, InjectionDetector
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # RAGService, HybridRetrievalService, AgentService
│   ├── static/               # Enterprise CSS, JavaScript SPA components
│   └── templates/            # Jinja2 templates (dashboard, rag, agent, search)
├── dataset/                  # Synthetic enterprise policy library
├── docs/                     # Technical specifications and guides
├── examples/                 # Canonical JSON request payloads
├── tests/                    # Unit, integration, and evaluation suites
│   ├── unit/agents/          # LangGraph + controller + tool unit tests
│   └── integration/          # End-to-end governance integration tests
└── scripts/                  # Production health checks and benchmarking
```

---

## 5. Data Integrity & Zero Trust Principles
- **No Prompt-Based Security:** Clearance filtering is applied deterministically in backend Python logic *before* candidate chunks are injected into LLM contexts.
- **Authoritative Backend Authorization:** The client UI cannot bypass clearance, role, or policy evaluation.
- **Fail-Safe Denials:** Requests with insufficient permissions or context return safe, non-revealing refusal messages rather than speculating.
- **Audit Topology Guarantee:** `audit_node` is the only terminal node in the StateGraph — every request, regardless of path, produces an immutable audit record.
