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
