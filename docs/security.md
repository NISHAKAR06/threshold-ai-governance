# Security Architecture — Threshold AI Governance

## 1. Zero-Trust Principles
- **No Reliance on Client State:** Security context (clearance, roles, departments) is validated cryptographically from session tokens or database records.
- **No Prompt-Bound Authorization:** LLM prompt instructions ("Please only answer if user has permission") are never relied upon for security boundaries.
- **Pre-Context Document Filtering:** Chunks are filtered in deterministic Python memory *before* LLM prompt formatting occurs.

## 2. Credential & Secret Management
- **Environment Variables:** All API keys (e.g. `GEMINI_API_KEY`, `JWT_SECRET_KEY`) are loaded via `app/config.py` using `pydantic-settings`.
- **Zero Committed Secrets:** Git repositories are protected with pre-commit hooks and `.gitignore` rules preventing `.env` leaks.
- **Masking & Sanitization:** Audit logs and UI errors sanitize API keys, passwords, and PII tokens.

## 3. Human-in-the-Loop Safeguards
Administrative tasks (such as dropping databases, deleting policy indices, or rotating root credentials) are hardcoded with high risk scores and automatically diverted to the HITL workflow, generating approval tickets (`REV-*`) that require two-person rule authorization before execution.

## Production hardening

Governed retrieval, RAG, agent execution, and agent-audit endpoints require a valid JWT. The server derives the effective role, department, administrator flag, and clearance from signed token claims; conflicting client-supplied `access_context` values are rejected. Raw semantic search is administrator-only because it bypasses governance filtering.

WebSocket connections require a JWT. Audit events are administrator-only and review events require an administrator, superadministrator, or reviewer. Clients cannot elevate a subscription after connecting.

Use `.env.example` as the configuration template. Production startup rejects default secrets, wildcard CORS, debug mode, and API documentation exposure. Docker Compose intentionally has no secret defaults.

The input and output guards provide layered mitigation for known prompt-injection, secret-leak, unauthorized-source, and hidden-reasoning patterns. They do not provide perfect prompt-injection prevention.
