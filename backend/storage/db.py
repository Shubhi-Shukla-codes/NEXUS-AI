"""
NEXUS Database Connection & Lifecycle Manager
Provides thread-safe SQLite connections, foreign key enforcement, WAL mode,
transaction management, and schema initialization.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Any, List, Tuple, Dict
from backend.config import settings
from backend.storage.schema import (
    CREATE_TABLES_SQL,
    SCHEMA_VERSION,
    INITIAL_ROLES,
    INITIAL_PERMISSIONS,
    ROLE_PERMISSION_MAP
)


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve active database path, ensuring parent directories exist."""
    path = custom_path or settings.paths.sqlite_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db_connection(custom_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide transactional SQLite connection with foreign key enforcement
    and WAL journal mode.
    """
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.row_factory = sqlite3.Row

    # Enforce SQLite foreign keys and WAL mode for concurrent readers
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(custom_path: Optional[Path] = None) -> None:
    """
    Initialize SQLite database schema, register version, and seed
    baseline roles and permissions.
    """
    with get_db_connection(custom_path) as conn:
        # 1. Execute DDL tables and indexes
        conn.executescript(CREATE_TABLES_SQL)

        # 2. Check and record schema version
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (SCHEMA_VERSION, "Baseline schema initialization for Phase 2")
            )

        # 3. Seed Roles
        for role_name, role_desc in INITIAL_ROLES:
            cur.execute(
                "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
                (role_name, role_desc)
            )

        # 4. Seed Permissions
        for perm_code, perm_desc in INITIAL_PERMISSIONS:
            cur.execute(
                "INSERT OR IGNORE INTO permissions (code, description) VALUES (?, ?)",
                (perm_code, perm_desc)
            )

        # 5. Seed Role Permissions
        for role_name, perm_codes in ROLE_PERMISSION_MAP.items():
            cur.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            role_row = cur.fetchone()
            if not role_row:
                continue
            role_id = role_row["id"]

            for code in perm_codes:
                cur.execute("SELECT id FROM permissions WHERE code = ?", (code,))
                perm_row = cur.fetchone()
                if not perm_row:
                    continue
                perm_id = perm_row["id"]

                cur.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                    (role_id, perm_id)
                )


def execute_query(
    query: str,
    params: Tuple[Any, ...] = (),
    custom_path: Optional[Path] = None
) -> int:
    """Execute write query and return lastrowid or affected rows."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.lastrowid or cur.rowcount


def fetch_one(
    query: str,
    params: Tuple[Any, ...] = (),
    custom_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Execute select query and return a single row as dict, or None."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_all(
    query: str,
    params: Tuple[Any, ...] = (),
    custom_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Execute select query and return all matching rows as list of dicts."""
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
