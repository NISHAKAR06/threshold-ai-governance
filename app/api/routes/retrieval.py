"""
retrieval.py — Route adapter for semantic retrieval.
Allows importing from app.api.routes.retrieval as specified in Phase 11 requirements.
"""
from app.api.retrieval_routes import router, semantic_search, get_retrieval_service

__all__ = ["router", "semantic_search", "get_retrieval_service"]
