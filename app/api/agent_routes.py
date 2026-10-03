"""
agent_routes.py — Exposes agent API router.
"""
from app.api.routes.agent import router, get_agent_service

__all__ = ["router", "get_agent_service"]
