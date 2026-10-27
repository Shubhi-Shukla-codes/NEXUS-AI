"""
NEXUS Role-Based Access Control (RBAC) Engine
Enforces backend authorization and permission boundaries across services.
"""

from functools import wraps
from pathlib import Path
from typing import List, Set, Optional, Callable, Any
from backend.storage.db import get_db_connection
from backend.security.audit import log_audit_event, EVENT_ROLE_ASSIGN, EVENT_PERMISSION_DENIED


class AuthorizationError(PermissionError):
    """Raised when an actor lacks sufficient privileges for a backend operation."""
    pass


def get_user_roles(user_id: int, custom_path: Optional[Path] = None) -> List[str]:
    """Retrieve all active role names assigned to a user."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.name 
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
            ORDER BY r.name
            """,
            (user_id,)
        )
        return [row["name"] for row in cur.fetchall()]


def get_user_permissions(user_id: int, custom_path: Optional[Path] = None) -> Set[str]:
    """Retrieve distinct permission codes granted to a user across all their roles."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT p.code
            FROM permissions p
            JOIN role_permissions rp ON rp.permission_id = p.id
            JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ?
            """,
            (user_id,)
        )
        return {row["code"] for row in cur.fetchall()}


def has_permission(
    user_id: int,
    permission_code: str,
    custom_path: Optional[Path] = None
) -> bool:
    """
    Verify if a user has a specific permission code.
    Backend enforced; cannot be bypassed by frontend tampering.
    """
    user_perms = get_user_permissions(user_id, custom_path=custom_path)
    return permission_code in user_perms


def assign_role_to_user(
    user_id: int,
    role_name: str,
    actor_username: str = "SYSTEM",
    actor_user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> bool:
    """Assign an existing role to a user and record an audit log."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        # Find role
        cur.execute("SELECT id FROM roles WHERE name = ?", (role_name.lower(),))
        role_row = cur.fetchone()
        if not role_row:
            raise ValueError(f"Role '{role_name}' does not exist.")
        role_id = role_row["id"]

        cur.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id)
        )
        changed = cur.rowcount > 0

    if changed:
        log_audit_event(
            event_type=EVENT_ROLE_ASSIGN,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            description=f"Assigned role '{role_name}' to user ID {user_id}",
            metadata={"target_user_id": user_id, "role": role_name},
            custom_path=custom_path
        )
    return changed


def remove_role_from_user(
    user_id: int,
    role_name: str,
    actor_username: str = "SYSTEM",
    actor_user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> bool:
    """Revoke a role from a user and record an audit log."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM roles WHERE name = ?", (role_name.lower(),))
        role_row = cur.fetchone()
        if not role_row:
            return False
        role_id = role_row["id"]

        cur.execute(
            "DELETE FROM user_roles WHERE user_id = ? AND role_id = ?",
            (user_id, role_id)
        )
        changed = cur.rowcount > 0

    if changed:
        log_audit_event(
            event_type=EVENT_ROLE_ASSIGN,
            actor_username=actor_username,
            actor_user_id=actor_user_id,
            description=f"Revoked role '{role_name}' from user ID {user_id}",
            metadata={"target_user_id": user_id, "revoked_role": role_name},
            custom_path=custom_path
        )
    return changed


def enforce_permission(
    user_id: int,
    permission_code: str,
    actor_username: str = "UNKNOWN",
    custom_path: Optional[Path] = None
) -> None:
    """
    Assert that user has permission. If not, log violation and raise AuthorizationError.
    """
    if not has_permission(user_id, permission_code, custom_path=custom_path):
        log_audit_event(
            event_type=EVENT_PERMISSION_DENIED,
            actor_username=actor_username,
            actor_user_id=user_id,
            description=f"Access denied: User {user_id} lacks permission '{permission_code}'",
            metadata={"required_permission": permission_code},
            custom_path=custom_path
        )
        raise AuthorizationError(
            f"Access Denied: Missing required permission '{permission_code}'"
        )
