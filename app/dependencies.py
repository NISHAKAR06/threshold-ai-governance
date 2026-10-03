"""
dependencies.py — FastAPI dependency injection providers.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Mapping, Optional

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorisationError, to_http_exception
from app.core.security import decode_access_token, extract_token
from app.database.session import AsyncSessionLocal
from app.core.logger import get_logger

logger = get_logger("THRESHOLD.deps")


# ── Database session ──────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session; commit on success, rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Auth helpers ──────────────────────────────────────────────
def _parse_bearer(authorization: Optional[str]) -> Optional[dict]:
    if not authorization:
        return None
    try:
        token   = extract_token(authorization)
        payload = decode_access_token(token)
        return payload
    except Exception:
        return None


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Require a valid JWT. Returns decoded payload."""
    payload = _parse_bearer(authorization)
    if payload is None:
        raise to_http_exception(AuthenticationError("Missing or invalid Authorization header"))
    return payload


async def get_optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Return decoded JWT payload or None (unauthenticated access allowed)."""
    return _parse_bearer(authorization)


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require the current user to have the 'admin' role."""
    if current_user.get("role") not in ("admin", "superadmin"):
        raise to_http_exception(AuthorisationError("Admin role required"))
    return current_user


def trusted_access_context(
    supplied_context: Mapping[str, Any], current_user: Mapping[str, Any]
) -> dict[str, Any]:
    """Build governance context from signed JWT claims, never request JSON.

    The request still carries an access context for API compatibility, but any
    disagreement with the authenticated identity is rejected rather than
    allowing callers to select a more privileged role or clearance.
    """
    subject = str(current_user.get("sub", "")).strip()
    role = str(current_user.get("role", "")).strip().upper()
    department = current_user.get("dept")
    if not subject or not role:
        raise to_http_exception(AuthenticationError("Token is missing required identity claims"))

    supplied_user = str(supplied_context.get("user_id", "")).strip()
    supplied_role = str(supplied_context.get("role", "")).strip().upper()
    if supplied_user != subject or supplied_role != role:
        raise to_http_exception(AuthorisationError("Request access context does not match authenticated user"))
    if supplied_context.get("department") and department and supplied_context["department"] != department:
        raise to_http_exception(AuthorisationError("Request access context does not match authenticated user"))

    clearance_by_role = {
        "SUPERADMIN": "RESTRICTED",
        "ADMIN": "RESTRICTED",
        "SECURITY_ANALYST": "CONFIDENTIAL",
        "GOVERNANCE_OFFICER": "CONFIDENTIAL",
        "MANAGER": "CONFIDENTIAL",
        "SECURITY_ENGINEER": "RESTRICTED",
        "GUEST": "PUBLIC",
    }
    return {
        "user_id": subject,
        "role": role,
        "department": department,
        "clearance_level": str(current_user.get("clearance_level") or clearance_by_role.get(role, "INTERNAL")).upper(),
        "is_admin": role in {"ADMIN", "SUPERADMIN"},
    }


# ── Repository convenience factories ─────────────────────────
# These are imported where needed to avoid circular imports.
# Usage in routers:
#   from app.dependencies import get_db
#   from app.repositories.employee_repository import EmployeeRepository
#   db: AsyncSession = Depends(get_db)
#   repo = EmployeeRepository(db)
