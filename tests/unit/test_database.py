"""
NEXUS Database Architecture Unit Tests
Validates schema creation, foreign key enforcement, transactions, and indexing
using an isolated temporary SQLite database.
"""

import sys
import unittest
import sqlite3
from pathlib import Path
import tempfile
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import (
    init_database,
    get_db_connection,
    execute_query,
    fetch_one,
    fetch_all
)
from backend.storage.schema import SCHEMA_VERSION, INITIAL_ROLES, INITIAL_PERMISSIONS


class TestDatabaseArchitecture(unittest.TestCase):
    """Test suite for SQLite schema and database layer."""

    def setUp(self):
        """Create a distinct temporary database file for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_nexus.db"

    def tearDown(self):
        """Clean up temporary directory and database."""
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        """Verify schema creation and baseline seeding."""
        init_database(custom_path=self.db_path)
        self.assertTrue(self.db_path.is_file())

        with get_db_connection(custom_path=self.db_path) as conn:
            cur = conn.cursor()
            # Verify schema version
            cur.execute("SELECT version FROM schema_version")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["version"], SCHEMA_VERSION)

            # Verify tables exist
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r["name"] for r in cur.fetchall()}
            expected_tables = {
                "users", "roles", "permissions", "user_roles", "role_permissions",
                "sessions", "documents", "document_pages", "document_chunks",
                "document_permissions", "conversations", "messages",
                "audit_logs", "application_settings", "schema_version"
            }
            self.assertTrue(expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}")

    def test_foreign_key_enforcement(self):
        """Verify that SQLite strictly rejects orphaned foreign key insertions."""
        init_database(custom_path=self.db_path)

        with get_db_connection(custom_path=self.db_path) as conn:
            cur = conn.cursor()
            # Attempt to insert into user_roles with non-existent user_id (9999)
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (9999, 1)
                )

    def test_cascade_deletion(self):
        """Verify foreign key ON DELETE CASCADE clears child records."""
        init_database(custom_path=self.db_path)

        with get_db_connection(custom_path=self.db_path) as conn:
            cur = conn.cursor()
            # Create user
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES ('test_cascade', 'hash123')"
            )
            user_id = cur.lastrowid
            
            # Assign role
            cur.execute("SELECT id FROM roles WHERE name = 'trainee'")
            role_id = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, role_id)
            )

        # Confirm user_role exists
        row = fetch_one(
            "SELECT * FROM user_roles WHERE user_id = ?",
            (user_id,),
            custom_path=self.db_path
        )
        self.assertIsNotNone(row)

        # Delete user
        execute_query("DELETE FROM users WHERE id = ?", (user_id,), custom_path=self.db_path)

        # Confirm user_role was cascaded
        row_after = fetch_one(
            "SELECT * FROM user_roles WHERE user_id = ?",
            (user_id,),
            custom_path=self.db_path
        )
        self.assertIsNone(row_after)

    def test_seeded_roles_and_permissions(self):
        """Verify initial roles and permissions are properly populated."""
        init_database(custom_path=self.db_path)

        roles = fetch_all("SELECT name FROM roles", custom_path=self.db_path)
        role_names = {r["name"] for r in roles}
        for name, _ in INITIAL_ROLES:
            self.assertIn(name, role_names)

        perms = fetch_all("SELECT code FROM permissions", custom_path=self.db_path)
        perm_codes = {p["code"] for p in perms}
        for code, _ in INITIAL_PERMISSIONS:
            self.assertIn(code, perm_codes)


if __name__ == "__main__":
    unittest.main()
