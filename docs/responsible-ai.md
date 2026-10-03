# Responsible AI Controls — Threshold AI Governance

> **Current Version: v2.0** — Responsible AI controls are now enforced at dedicated graph nodes (`request_router` for input, `output_guard` for output) rather than ad-hoc service calls.

---

## 1. Multi-Stage Guardrail Architecture

Threshold implements defense-in-depth safety controls at input, retrieval, model execution, and output boundaries:

```text
[Input Prompt]
      │
      ▼
[request_router node] — Responsible AI Input Guard
  ├── Prompt Injection Detector (Regex heuristics & adversarial patterns)
  ├── System Override Mitigation ("Ignore all previous instructions")
  ├── Payload Size & Delimiter Scrutiny (< 4096 chars, no escaped system tokens)
  └── Harmful Content Detection
      │
      ▼
[governance_check node] — Zero-Trust Policy Enforcement
  └── AG-01..AG-04 deterministic policy evaluation
      │
      ▼
[rag_node] — Zero-Trust Retrieval & Context Filtering
  └── Chunks evaluated strictly by metadata clearance; unauthorized chunks dropped
      │
      ▼
LLM Inference (Gemini)
      │
      ▼
[output_guard node] — Responsible AI Output Guard  ← NEW in v2
  ├── Confidential Pattern Scanner (AWS keys, JWTs, credentials, PII)
  ├── Unauthorized Document Leak Scanner (Restricted IDs or classifications)
  ├── Chain-of-Thought Redactor (strips "thought:", "internal reasoning:" blocks)
  └── Citation Consistency Validator (cited sources ⊆ authorized retrieval context)
      │
      ▼
[audit_node] → [Safe Response + AUD-LG-* record]
```

---

## 2. v1 vs v2 Responsible AI Comparison

| Control | v1 | v2 |
|:---|:---|:---|
| **Input Guard** | Called manually in `AgentController` | Integrated in `request_router` node — mandatory for all requests |
| **Output Guard** | Basic response sanity check | Dedicated `output_guard` node with credential scanning, CoT redaction, citation validation |
| **Chain-of-Thought Redaction** | Not implemented | `output_guard` strips hidden internal reasoning from all responses |
| **Citation Validation** | Not enforced | `output_guard` verifies cited sources are a strict subset of authorized retrieved chunks |
| **Violation Audit** | Manual log call | `audit_node` always records violation events with full metadata |

---

## 3. Safe Refusal Specifications

When an input or output violation is detected:
- The system returns structured refusal messaging: `"Governance Refusal: This operation cannot be completed."`
- The violation reason is sanitized — internal regex patterns or security rules are **never** disclosed to the caller.
- An alert event is dispatched to the security audit log with full metadata (violation category, input hash, user ID, timestamp).
- The `safe_denial` node ensures refusal messages are uniform regardless of the actual violation type, preventing information leakage through error differentiation.

---

## 4. Realistic Safety Posture

> [!IMPORTANT]
> Prompt injection defense is treated as a **risk mitigation** layer, not an impenetrable silver bullet. The true security boundary is established by **backend authorization logic** (`governance_check` node + pre-context chunk filtering) that prevents protected documents from entering LLM context regardless of prompt manipulation attempts.

The defense stack operates on the principle of **minimum required trust**:
- The LLM is **never trusted** to enforce access control.
- The retrieval pipeline is **never trusted** to produce only authorized content without deterministic post-filtering.
- The API client is **never trusted** to self-report clearance levels.
