"""
NEXUS Authentication & Session Management Engine
Provides user registration, credential validation, bcrypt verification,
cryptographic session tokens, and session lifecycle control.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from backend.config import settings
from backend.storage.db import get_db_connection
from backend.security.crypto import (
    hash_password,
    verify_password,
    generate_session_token,
    hash_session_token,
    validate_username,
    validate_password_strength
)
from backend.security.rbac import get_user_roles, get_user_permissions, assign_role_to_user
from backend.security.audit import (
    log_audit_event,
    EVENT_LOGIN_SUCCESS,
    EVENT_LOGIN_FAILURE,
    EVENT_LOGOUT,
    EVENT_USER_CREATE
)


class AuthenticationError(Exception):
    """Raised when an authentication check fails."""
    pass


def register_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    role: str = "trainee",
    actor_username: str = "SYSTEM",
    actor_user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Register a new user account with hashed password and initial role.
    Raises ValueError on validation failure or if username already exists.
    """
    # 1. Validate username & password
    valid_u, err_u = validate_username(username)
    if not valid_u:
        raise ValueError(err_u)

    valid_p, err_p = validate_password_strength(password)
    if not valid_p:
        raise ValueError(err_p)

    username_clean = username.strip()
    email_clean = email.strip().lower() if email else None
    hashed_pwd = hash_password(password)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        # Check duplicate username
        cur.execute("SELECT id FROM users WHERE username = ?", (username_clean,))
        if cur.fetchone():
            raise ValueError(f"User with username '{username_clean}' already exists.")

        if email_clean:
            cur.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
            if cur.fetchone():
                raise ValueError(f"User with email '{email_clean}' already exists.")

        # Insert user
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (username_clean, email_clean, hashed_pwd)
        )
        user_id = cur.lastrowid

    # 2. Assign initial role
    assign_role_to_user(
        user_id=user_id,
        role_name=role,
        actor_username=actor_username,
        actor_user_id=actor_user_id,
        custom_path=custom_path
    )

    # 3. Audit log
    log_audit_event(
        event_type=EVENT_USER_CREATE,
        actor_username=actor_username,
        actor_user_id=actor_user_id,
        description=f"Created user '{username_clean}' with role '{role}'",
        metadata={"created_user_id": user_id, "username": username_clean, "role": role},
        custom_path=custom_path
    )

    return {
        "id": user_id,
        "username": username_clean,
        "email": email_clean,
        "role": role,
        "is_active": True
    }


def login_user(
    username: str,
    password: str,
    ip_address: Optional[str] = "127.0.0.1",
    user_agent: Optional[str] = None,
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Authenticate user credentials, generate a secure session token, and record audit log.
    Raises AuthenticationError on invalid credentials.
    """
    username_clean = (username or "").strip()
    if not username_clean or not password:
        log_audit_event(
            event_type=EVENT_LOGIN_FAILURE,
            actor_username=username_clean or "UNKNOWN",
            description="Login failed: Missing username or password",
            ip_address=ip_address,
            custom_path=custom_path
        )
        raise AuthenticationError("Invalid username or password.")

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, password_hash, is_active FROM users WHERE username = ?",
            (username_clean,)
        )
        user_row = cur.fetchone()

        if not user_row:
            log_audit_event(
                event_type=EVENT_LOGIN_FAILURE,
                actor_username=username_clean,
                description=f"Login failed: User '{username_clean}' not found",
                ip_address=ip_address,
                custom_path=custom_path
            )
            raise AuthenticationError("Invalid username or password.")

        if not user_row["is_active"]:
            log_audit_event(
                event_type=EVENT_LOGIN_FAILURE,
                actor_username=username_clean,
                description=f"Login failed: User '{username_clean}' account is deactivated",
                ip_address=ip_address,
                custom_path=custom_path
            )
            raise AuthenticationError("Account is deactivated. Contact an administrator.")

        # Verify bcrypt hash
        if not verify_password(password, user_row["password_hash"]):
            log_audit_event(
                event_type=EVENT_LOGIN_FAILURE,
                actor_username=username_clean,
                description=f"Login failed: Incorrect password for user '{username_clean}'",
                ip_address=ip_address,
                custom_path=custom_path
            )
            raise AuthenticationError("Invalid username or password.")

        user_id = user_row["id"]

        # Generate cryptographic session token
        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        expires_at = datetime.now() + timedelta(hours=settings.security.session_expire_hours)

        cur.execute(
            """
            INSERT INTO sessions (token_hash, user_id, expires_at, is_active, ip_address, user_agent)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (token_hash, user_id, expires_at.isoformat(), ip_address, user_agent)
        )

    # Fetch user roles and permissions
    roles = get_user_roles(user_id, custom_path=custom_path)
    permissions = get_user_permissions(user_id, custom_path=custom_path)
    primary_role = roles[0] if roles else "trainee"

    log_audit_event(
        event_type=EVENT_LOGIN_SUCCESS,
        actor_username=username_clean,
        actor_user_id=user_id,
        description=f"User '{username_clean}' authenticated successfully",
        ip_address=ip_address,
        custom_path=custom_path
    )

    return {
        "session_token": raw_token,
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": user_id,
            "username": user_row["username"],
            "email": user_row["email"],
            "role": primary_role,
            "roles": roles,
            "permissions": list(permissions)
        }
    }


def validate_session(
    token: str,
    custom_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Validate a raw session token. Checks hash, active status, and expiry.
    Returns user session dictionary if valid, or None.
    """
    if not token:
        return None

    token_hash = hash_session_token(token)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id as session_id, s.user_id, s.expires_at, s.is_active,
                   u.username, u.email, u.is_active as user_active
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.is_active = 1
            """,
            (token_hash,)
        )
        row = cur.fetchone()
        if not row:
            return None

        # Check if user account is active
        if not row["user_active"]:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.now() > expires_at:
            # Mark session as expired
            cur.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (row["session_id"],))
            return None

        user_id = row["user_id"]

    roles = get_user_roles(user_id, custom_path=custom_path)
    permissions = get_user_permissions(user_id, custom_path=custom_path)
    primary_role = roles[0] if roles else "trainee"

    return {
        "user_id": user_id,
        "username": row["username"],
        "email": row["email"],
        "role": primary_role,
        "roles": roles,
        "permissions": list(permissions)
    }


def logout_user(
    token: str,
    custom_path: Optional[Path] = None
) -> bool:
    """Invalidate an active session token and record audit log."""
    if not token:
        return False

    token_hash = hash_session_token(token)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.user_id, u.username
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.is_active = 1
            """,
            (token_hash,)
        )
        row = cur.fetchone()
        if not row:
            return False

        cur.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (row["id"],))

    log_audit_event(
        event_type=EVENT_LOGOUT,
        actor_username=row["username"],
        actor_user_id=row["user_id"],
        description=f"User '{row['username']}' logged out",
        custom_path=custom_path
    )
    return True


def ensure_initial_admin(
    admin_username: str = "admin",
    admin_password: str = "Admin@Nexus2026!",
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Ensure at least one administrator account exists in a fresh database.
    If no users exist, creates the default initial administrator.
    """
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) as count FROM users")
        if cur.fetchone()["count"] > 0:
            cur.execute("SELECT id, username, email FROM users WHERE username = ?", (admin_username,))
            existing = cur.fetchone()
            if existing:
                return dict(existing)
            # Users exist, return first admin
            cur.execute("SELECT id, username, email FROM users LIMIT 1")
            return dict(cur.fetchone())

    # No users exist, create initial administrator
    return register_user(
        username=admin_username,
        password=admin_password,
        email="admin@nexus.local",
        role="administrator",
        actor_username="SYSTEM_BOOTSTRAP",
        custom_path=custom_path
    )
