"""
NEXUS Authentication & Session Unit Tests
Validates password hashing, verification, login, logout, duplicate prevention,
session generation, and expiry using an isolated temporary SQLite database.
"""

import sys
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database, get_db_connection
from backend.security.crypto import hash_password, verify_password
from backend.security.auth import (
    register_user,
    login_user,
    logout_user,
    validate_session,
    ensure_initial_admin,
    AuthenticationError
)


class TestAuthentication(unittest.TestCase):
    """Test suite for user management and authentication."""

    def setUp(self):
        """Initialize a fresh isolated database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_auth.db"
        init_database(custom_path=self.db_path)

    def tearDown(self):
        """Clean up temporary resources."""
        self.temp_dir.cleanup()

    def test_password_hashing_and_verification(self):
        """Verify bcrypt generates secure non-plaintext hashes and verifies accurately."""
        password = "SecurePassword@123"
        hashed = hash_password(password)
        
        self.assertNotEqual(password, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword@123", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_user_registration_success(self):
        """Verify successful user creation with assigned role."""
        user = register_user(
            username="analyst_john",
            password="StrongPassword#2026",
            email="john@nexus.local",
            role="trainee",
            custom_path=self.db_path
        )
        self.assertIsNotNone(user["id"])
        self.assertEqual(user["username"], "analyst_john")
        self.assertEqual(user["role"], "trainee")

    def test_duplicate_user_rejection(self):
        """Verify duplicate username registration is prevented."""
        register_user(
            username="unique_user",
            password="StrongPassword#2026",
            role="trainee",
            custom_path=self.db_path
        )
        with self.assertRaises(ValueError) as ctx:
            register_user(
                username="unique_user",
                password="AnotherPassword#2026",
                role="trainee",
                custom_path=self.db_path
            )
        self.assertIn("already exists", str(ctx.exception))

    def test_login_success(self):
        """Verify correct credentials yield active session token and user roles."""
        register_user(
            username="commander_mark",
            password="StrongPassword#2026",
            role="instructor",
            custom_path=self.db_path
        )
        login_res = login_user(
            username="commander_mark",
            password="StrongPassword#2026",
            custom_path=self.db_path
        )
        self.assertIn("session_token", login_res)
        self.assertEqual(login_res["user"]["username"], "commander_mark")
        self.assertIn("instructor", login_res["user"]["roles"])
        self.assertIn("doc:upload", login_res["user"]["permissions"])

    def test_login_invalid_password(self):
        """Verify login failure with incorrect password."""
        register_user(
            username="user_test",
            password="CorrectPassword#1",
            custom_path=self.db_path
        )
        with self.assertRaises(AuthenticationError):
            login_user(
                username="user_test",
                password="WrongPassword#99",
                custom_path=self.db_path
            )

    def test_login_nonexistent_user(self):
        """Verify login failure for non-existent username."""
        with self.assertRaises(AuthenticationError):
            login_user(
                username="ghost_user",
                password="SomePassword#1",
                custom_path=self.db_path
            )

    def test_session_validation_and_logout(self):
        """Verify session token validation, user retrieval, and logout invalidation."""
        register_user(
            username="session_tester",
            password="TestPassword#123",
            role="trainee",
            custom_path=self.db_path
        )
        login_res = login_user(
            username="session_tester",
            password="TestPassword#123",
            custom_path=self.db_path
        )
        token = login_res["session_token"]

        # Validate session
        session_info = validate_session(token, custom_path=self.db_path)
        self.assertIsNotNone(session_info)
        self.assertEqual(session_info["username"], "session_tester")

        # Logout user
        logged_out = logout_user(token, custom_path=self.db_path)
        self.assertTrue(logged_out)

        # Validate session after logout
        session_after_logout = validate_session(token, custom_path=self.db_path)
        self.assertIsNone(session_after_logout)

    def test_session_expiry(self):
        """Verify expired session token is automatically rejected."""
        register_user(
            username="expiry_user",
            password="TestPassword#123",
            role="trainee",
            custom_path=self.db_path
        )
        login_res = login_user(
            username="expiry_user",
            password="TestPassword#123",
            custom_path=self.db_path
        )
        token = login_res["session_token"]

        # Artificially expire the session in the database
        past_time = (datetime.now() - timedelta(hours=1)).isoformat()
        with get_db_connection(custom_path=self.db_path) as conn:
            conn.execute("UPDATE sessions SET expires_at = ?", (past_time,))

        # Validate session should fail
        session_res = validate_session(token, custom_path=self.db_path)
        self.assertIsNone(session_res)

    def test_ensure_initial_admin(self):
        """Verify bootstrap creates default administrator when DB is empty."""
        admin = ensure_initial_admin(
            admin_username="superadmin",
            admin_password="AdminPassword#999",
            custom_path=self.db_path
        )
        self.assertEqual(admin["username"], "superadmin")
        
        # Second call returns existing admin without re-creating
        admin_repeat = ensure_initial_admin(
            admin_username="superadmin",
            admin_password="AdminPassword#999",
            custom_path=self.db_path
        )
        self.assertEqual(admin["id"], admin_repeat["id"])


if __name__ == "__main__":
    unittest.main()
