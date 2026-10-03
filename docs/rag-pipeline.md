# RAG Pipeline Specification — Threshold AI Governance

## 1. Grounded RAG Flow
The Retrieval-Augmented Generation pipeline ensures zero unauthorized data leakage and verifiable source grounding:

```text
Caller Question + AccessContext
              │
              ▼
   Responsible AI Input Guard
              │
              ▼
  Governance-Aware Hybrid Retrieval
  (BM25 Lexical + ChromaDB Vector)
              │
              ▼
   Governance Filtering Engine
  (Clearance & Role Verification)
              │
      ┌───────┴───────┐
      ▼               ▼
Authorized Chunks   Denied Chunks
  (>= 1 chunk)     (0 chunks remaining)
      │               │
      │               ▼
      │        Return INSUFFICIENT_CONTEXT
      │        (No LLM call made)
      ▼
 Grounded Context Assembly
      │
      ▼
LLM Generation (Gemini / Mock Provider)
      │
      ▼
 Responsible AI Output Guard
      │
      ▼
Grounded Answer + Verifiable Citations
```

## 2. Chunk-Level Security Clearance
Every chunk in the vector index and BM25 store retains immutable security metadata:
- `document_id`: Deterministic policy identifier
- `chunk_id`: Hierarchical chunk identifier (`DOC-POLICY-01-chunk-001`)
- `classification`: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, or `RESTRICTED`
- `department`: Originating operational unit (`SECURITY`, `FINANCE`, `HR`, `LEGAL`, etc.)
- `allowed_roles`: Explicit list of permitted roles (or `*` for public)

## 3. Insufficient Context Protocol
When zero authorized chunks match a user's query or when retrieved similarity falls below threshold, the system immediately returns:
```json
{
  "status": "INSUFFICIENT_CONTEXT",
  "answer": "I do not have access to sufficient authorized corporate policy documentation to answer this question.",
  "sources": []
}
```
Under no circumstances are model hallucinations permitted when verified source chunks are missing.
