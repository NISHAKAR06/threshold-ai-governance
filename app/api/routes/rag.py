"""
rag.py — Route adapter for governance-aware RAG answer generation.
Allows importing from app.api.routes.rag as specified in Phase 13 requirements.
"""
from app.api.rag_routes import router, ask_question, get_rag_service

__all__ = ["router", "ask_question", "get_rag_service"]
