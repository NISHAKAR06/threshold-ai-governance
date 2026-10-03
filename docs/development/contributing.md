# Contributing Guidelines — Threshold AI Governance

We welcome contributions to Threshold AI Governance! Please adhere to our engineering standards:

## 1. Core Principles
1. **Never Commit Secrets:** API keys, database credentials, or real PII must never be pushed to repository branches.
2. **Preserve Zero-Trust Semantics:** Every new retrieval or agent feature must maintain strict pre-retrieval clearance filtering.
3. **Comprehensive Test Coverage:** New endpoints and nodes must include corresponding unit and integration test coverage.
4. **Documentation Sync:** Update relevant files in `docs/` and `examples/` whenever API contracts or data models change.

## 2. Pull Request Workflow
1. Fork the repository and create a feature branch (`feature/my-enhancement`).
2. Implement your changes following PEP 8 style standards and explicit type annotations.
3. Verify test passage:
   ```bash
   python -m pytest tests/
   ```
4. Submit your Pull Request detailing:
   - Motivation and architectural rationale.
   - Test results and verification logs.
   - Any modifications to configuration or environment variables.
