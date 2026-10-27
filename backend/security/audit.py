"""
NEXUS Audit Logging Engine
Provides tamper-resistant, structured logging of security, authentication,
and administrative events into the SQLite relational database.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from backend.storage.db import get_db_connection


# Standard Audit Event Types
EVENT_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
EVENT_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
EVENT_LOGOUT = "AUTH_LOGOUT"
EVENT_USER_CREATE = "USER_CREATE"
EVENT_USER_STATUS_CHANGE = "USER_STATUS_CHANGE"
EVENT_ROLE_ASSIGN = "ROLE_ASSIGN"
EVENT_DOC_UPLOAD = "DOC_UPLOAD"
EVENT_DOC_APPROVE = "DOC_APPROVE"
EVENT_DOC_REJECT = "DOC_REJECT"
EVENT_DOC_DELETE = "DOC_DELETE"
EVENT_CONFIG_CHANGE = "CONFIG_CHANGE"
EVENT_PERMISSION_DENIED = "PERMISSION_DENIED"


def log_audit_event(
    event_type: str,
    actor_username: str,
    description: str,
    actor_user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    custom_path: Optional[Path] = None
) -> int:
    """
    Persist an audit record. Excludes sensitive data (passwords, tokens).
    Returns the inserted audit log record ID.
    """
    safe_metadata = dict(metadata or {})
    # Strip sensitive keys if present
    for sensitive_key in ("password", "token", "password_hash", "secret"):
        safe_metadata.pop(sensitive_key, None)

    metadata_json = json.dumps(safe_metadata, default=str)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_logs (
                event_type, actor_user_id, actor_username,
                ip_address, description, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                actor_user_id,
                actor_username,
                ip_address or "127.0.0.1",
                description,
                metadata_json
            )
        )
        return cur.lastrowid


def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    custom_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Retrieve audit records with optional event filtering."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        if event_type:
            cur.execute(
                """
                SELECT id, event_type, actor_user_id, actor_username,
                       ip_address, description, metadata_json, created_at
                FROM audit_logs
                WHERE event_type = ?
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (event_type, limit, offset)
            )
        else:
            cur.execute(
                """
                SELECT id, event_type, actor_user_id, actor_username,
                       ip_address, description, metadata_json, created_at
                FROM audit_logs
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
