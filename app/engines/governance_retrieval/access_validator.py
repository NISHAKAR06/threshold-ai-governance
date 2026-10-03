"""
access_validator.py — Evaluates access permissions between an AccessContext and Chunk governance metadata.
Applies Role checks, Classification clearance checks, and Department boundary checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Set, List

from app.models.access_context import AccessContext
from app.config import settings
from app.core.logger import engine_logger


@dataclass
class AccessDecision:
    """Outcome of governance permission evaluation for a single chunk."""
    is_allowed: bool
    reason: str


class AccessValidator:
    """
    Evaluates role permissions, clearance levels, and department rules.
    Secure by default: denies access if required metadata is missing or invalid.
    """

    CLASSIFICATION_LEVELS: Dict[str, int] = {
        "PUBLIC": 1,
        "INTERNAL": 2,
        "CONFIDENTIAL": 3,
        "RESTRICTED": 4,
    }

    # Universal roles that grant broad organizational access across departments
    UNIVERSAL_ROLES: Set[str] = {"ALL", "ALL_EMPLOYEES", "EVERYONE"}

    # Departments whose policies are cross-cutting across the entire enterprise
    CROSS_CUTTING_DEPARTMENTS: Set[str] = {
        "enterprise governance",
        "human resources",
    }

    def __init__(self, strict_department_check: Optional[bool] = None):
        self.strict_department_check = (
            strict_department_check
            if strict_department_check is not None
            else settings.GOVERNANCE_STRICT_DEPARTMENT_CHECK
        )

    def validate_access(
        self,
        context: Optional[AccessContext],
        chunk_metadata: Dict[str, Any],
    ) -> AccessDecision:
        """
        Validate whether the requesting AccessContext is authorized to view a chunk.

        Args:
            context: The authenticated requester's AccessContext.
            chunk_metadata: Metadata dictionary associated with the chunk.

        Returns:
            AccessDecision with is_allowed (bool) and explanation reason.
        """
        # 1. Reject missing or empty access context
        if context is None:
            return AccessDecision(is_allowed=False, reason="Missing AccessContext")

        user_role = (context.role or "").strip().upper()
        if not user_role:
            return AccessDecision(is_allowed=False, reason="User role is missing or empty")

        # 2. Reject missing or invalid metadata
        if not isinstance(chunk_metadata, dict) or not chunk_metadata:
            return AccessDecision(is_allowed=False, reason="Chunk governance metadata is missing or malformed")

        # 3. Administrator bypass for role/department (still respects clearance unless SUPERADMIN)
        is_admin = context.is_admin or user_role in ("ADMIN", "SUPERADMIN")

        # 4. Role validation
        allowed_roles_raw = chunk_metadata.get("allowed_roles")
        if not allowed_roles_raw:
            return AccessDecision(is_allowed=False, reason="Chunk metadata missing allowed_roles")

        # Normalize allowed roles to uppercase set
        if isinstance(allowed_roles_raw, (list, set, tuple)):
            allowed_roles = {str(r).strip().upper() for r in allowed_roles_raw}
        else:
            allowed_roles = {str(allowed_roles_raw).strip().upper()}

        has_role_match = (
            user_role in allowed_roles
            or is_admin
            or any(univ in allowed_roles for univ in self.UNIVERSAL_ROLES)
        )

        if not has_role_match:
            return AccessDecision(
                is_allowed=False,
                reason=f"Role '{user_role}' not permitted in chunk allowed_roles: {sorted(allowed_roles)}",
            )

        # 5. Classification clearance validation
        chunk_classif = str(chunk_metadata.get("classification", "INTERNAL")).strip().upper()
        doc_level = self.CLASSIFICATION_LEVELS.get(chunk_classif, 3)  # default to CONFIDENTIAL if unknown

        user_clearance = str(context.clearance_level or "INTERNAL").strip().upper()
        user_level = self.CLASSIFICATION_LEVELS.get(user_clearance, 2)  # default to INTERNAL

        # Admin with SUPERADMIN gets maximum clearance
        if user_role == "SUPERADMIN":
            user_level = 99

        if user_level < doc_level:
            return AccessDecision(
                is_allowed=False,
                reason=(
                    f"User clearance '{user_clearance}' (level {user_level}) is below chunk classification "
                    f"'{chunk_classif}' (level {doc_level})"
                ),
            )

        # 6. Department validation (if strict check is active)
        if self.strict_department_check and not is_admin:
            chunk_dept = str(chunk_metadata.get("department", "")).strip()
            user_dept = str(context.department or "").strip()

            is_cross_cutting = chunk_dept.lower() in self.CROSS_CUTTING_DEPARTMENTS
            dept_matches = chunk_dept.lower() == user_dept.lower()
            universal_access = any(univ in allowed_roles for univ in self.UNIVERSAL_ROLES)

            if not (dept_matches or is_cross_cutting or universal_access):
                return AccessDecision(
                    is_allowed=False,
                    reason=f"User department '{user_dept}' does not match chunk department '{chunk_dept}'",
                )

        # 7. Document Lifecycle Status check
        status = str(chunk_metadata.get("status", "ACTIVE")).strip().upper()
        if status in ("ARCHIVED", "SUPERSEDED") and not is_admin:
            return AccessDecision(
                is_allowed=False,
                reason=f"Document status '{status}' is not active",
            )

        return AccessDecision(is_allowed=True, reason="Authorized")
