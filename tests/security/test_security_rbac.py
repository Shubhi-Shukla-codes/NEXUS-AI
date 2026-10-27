"""
NEXUS Security & RBAC Unit Tests
Validates role permissions, backend access boundary enforcement,
and audit log generation.
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database
from backend.security.auth import register_user
from backend.security.rbac import (
    get_user_roles,
    get_user_permissions,
    has_permission,
    assign_role_to_user,
    remove_role_from_user,
    enforce_permission,
    AuthorizationError
)
from backend.security.audit import get_audit_logs, log_audit_event, EVENT_LOGIN_SUCCESS


class TestSecurityRBAC(unittest.TestCase):
    """Test suite for Role-Based Access Control and Audit Logging."""

    def setUp(self):
        """Create fresh isolated test database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_rbac.db"
        init_database(custom_path=self.db_path)

    def tearDown(self):
        """Clean up temporary test resources."""
        self.temp_dir.cleanup()

    def test_role_permissions_assignment(self):
        """Verify role privileges match the security matrix."""
        # Create an administrator
        admin = register_user(
            username="admin_user",
            password="AdminPassword#123",
            role="administrator",
            custom_path=self.db_path
        )
        admin_perms = get_user_permissions(admin["id"], custom_path=self.db_path)
        self.assertIn("user:manage", admin_perms)
        self.assertIn("doc:delete", admin_perms)
        self.assertIn("audit:view", admin_perms)

        # Create a trainee
        trainee = register_user(
            username="trainee_user",
            password="TraineePassword#123",
            role="trainee",
            custom_path=self.db_path
        )
        trainee_perms = get_user_permissions(trainee["id"], custom_path=self.db_path)
        self.assertIn("doc:view", trainee_perms)
        self.assertNotIn("user:manage", trainee_perms)
        self.assertNotIn("doc:delete", trainee_perms)

    def test_backend_enforce_permission_success_and_failure(self):
        """Verify backend raises AuthorizationError when permission is lacking."""
        trainee = register_user(
            username="strict_trainee",
            password="TraineePassword#123",
            role="trainee",
            custom_path=self.db_path
        )

        # Trainee has doc:view -> should pass without error
        try:
            enforce_permission(
                user_id=trainee["id"],
                permission_code="doc:view",
                custom_path=self.db_path
            )
        except AuthorizationError:
            self.fail("enforce_permission raised AuthorizationError unexpectedly for doc:view")

        # Trainee lacks doc:delete -> must raise AuthorizationError
        with self.assertRaises(AuthorizationError):
            enforce_permission(
                user_id=trainee["id"],
                permission_code="doc:delete",
                custom_path=self.db_path
            )

    def test_dynamic_role_elevation_and_revocation(self):
        """Verify adding and revoking roles dynamically updates permissions."""
        user = register_user(
            username="dynamic_operator",
            password="OperatorPassword#123",
            role="trainee",
            custom_path=self.db_path
        )
        self.assertFalse(has_permission(user["id"], "doc:upload", custom_path=self.db_path))

        # Assign instructor role
        assign_role_to_user(
            user_id=user["id"],
            role_name="instructor",
            custom_path=self.db_path
        )
        self.assertTrue(has_permission(user["id"], "doc:upload", custom_path=self.db_path))

        # Revoke instructor role
        remove_role_from_user(
            user_id=user["id"],
            role_name="instructor",
            custom_path=self.db_path
        )
        self.assertFalse(has_permission(user["id"], "doc:upload", custom_path=self.db_path))

    def test_audit_log_creation_and_sanitization(self):
        """Verify audit logs are persisted and sensitive fields stripped."""
        log_audit_event(
            event_type=EVENT_LOGIN_SUCCESS,
            actor_username="test_audit_actor",
            description="Testing audit log persistance",
            metadata={"ip": "127.0.0.1", "password": "supersecretpassword"},
            custom_path=self.db_path
        )

        logs = get_audit_logs(limit=10, custom_path=self.db_path)
        self.assertGreaterEqual(len(logs), 1)

        latest_log = logs[0]
        self.assertEqual(latest_log["actor_username"], "test_audit_actor")
        # Ensure password was purged from metadata_json
        self.assertNotIn("supersecretpassword", latest_log["metadata_json"])


if __name__ == "__main__":
    unittest.main()
