# Testing & Verification Guide

## 1. Test Architecture
The test suite covers unit, integration, and security scenarios across all tiers:
- `tests/unit/`: Component-level validation (embeddings, BM25, policy engine, validators, LangGraph nodes).
- `tests/integration/`: Cross-boundary workflows (hybrid search, RAG service, agent controller, LangGraph state machine, frontend router).
- `tests/evaluation/`: Quality benchmarks (retrieval precision/recall, MRR, unauthorized exposure testing).

## 2. Running Test Commands
```bash
# Run all unit and integration tests
python -m pytest tests/unit tests/integration -v

# Run LangGraph specific tests
python -m pytest tests/unit/agents/test_agent_graph.py -v

# Run with test coverage
python -m pytest --cov=app --cov-report=term-missing

# Run production health check script
python scripts/production_health_check.py
```
