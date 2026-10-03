"""
access_context.py — Domain model representing user identity and security credentials.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class AccessContext:
    """Encapsulates the requester's identity, role, department, and clearance level."""
    user_id: str
    role: str
    department: Optional[str] = None
    clearance_level: Optional[str] = "INTERNAL"
    is_admin: bool = False

    def __post_init__(self):
        if self.role:
            self.role = self.role.strip().upper()
            if self.role in ("ADMIN", "SUPERADMIN"):
                self.is_admin = True
        if self.clearance_level:
            self.clearance_level = self.clearance_level.strip().upper()
        if self.department:
            self.department = self.department.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert AccessContext to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessContext":
        """Reconstruct AccessContext from dictionary."""
        return cls(
            user_id=str(data.get("user_id", "")),
            role=str(data.get("role", "EMPLOYEE")),
            department=data.get("department"),
            clearance_level=data.get("clearance_level", "INTERNAL"),
            is_admin=bool(data.get("is_admin", False)),
        )
