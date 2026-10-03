"""
governance_retrieval.py — Route adapter for hybrid governance-aware retrieval.
Allows importing from app.api.routes.governance_retrieval as specified in Phase 12 requirements.
"""
from app.api.retrieval_routes import router, governance_search, get_hybrid_retrieval_service

__all__ = ["router", "governance_search", "get_hybrid_retrieval_service"]
