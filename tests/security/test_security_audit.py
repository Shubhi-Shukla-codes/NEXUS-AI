"""
NEXUS Security Hardening & Penetration Defense Tests
Validates defenses against SQL Injection, Directory Traversal, Privilege Escalation,
File Format Spoofing, and Audit Trail integrity.
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database, get_db_connection
from backend.security.auth import register_user, login_user, AuthenticationError
from backend.security.rbac import AuthorizationError
from backend.storage.vault import sanitize_filename, validate_file
from backend.services.document_service import (
    upload_document,
    list_documents,
    approve_document,
    delete_document,
    DocumentError
)
from backend.retrieval.bm25 import BM25Index


class TestSecurityAuditAndHardening(unittest.TestCase):
    """Rigorous security audit verifying resilience against adversarial inputs."""

    def setUp(self):
        """Create isolated test environment."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_security.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        init_database(custom_path=self.db_path)

        # Seed test users
        self.admin = register_user(
            username="sec_admin",
            password="AdminPassword#123",
            role="administrator",
            custom_path=self.db_path
        )
        self.trainee = register_user(
            username="sec_trainee",
            password="TraineePassword#123",
            role="trainee",
            custom_path=self.db_path
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_sql_injection_defense_in_search_and_auth(self):
        """Verify SQL injection vectors are neutralized by parameterized queries."""
        # 1. SQL injection in authentication login
        sqli_usernames = [
            "' OR '1'='1",
            "admin' --",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --"
        ]
        for malicious_user in sqli_usernames:
            # Login should safely fail, never grant admin access or throw database syntax error
            with self.assertRaises(AuthenticationError):
                login_user(malicious_user, "any_pass", custom_path=self.db_path)

        # 2. SQL injection in document listing
        sqli_queries = [
            "'; DROP TABLE documents; --",
            "' OR 1=1 --",
            "' UNION SELECT id, username FROM users --"
        ]
        for malicious_query in sqli_queries:
            docs = list_documents(search_query=malicious_query, user_id=self.admin["id"], custom_path=self.db_path)
            self.assertIsInstance(docs, list)

        # Confirm users table was never dropped or corrupted
        with get_db_connection(self.db_path) as conn:
            user_count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
            self.assertEqual(user_count, 2)

    def test_directory_traversal_defense(self):
        """Verify path traversal attack vectors are stripped to safe basenames."""
        traversal_filenames = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\cmd.exe",
            "/var/log/../../sensitive.pdf",
            "....//....//boot.ini",
            "c:/nexus/vault/payload.txt"
        ]

        for mal_name in traversal_filenames:
            clean = sanitize_filename(mal_name)
            # Must not contain directory separators or parent directory references
            self.assertNotIn("..", clean)
            self.assertNotIn("/", clean)
            self.assertNotIn("\\", clean)

    def test_privilege_escalation_backend_denial(self):
        """Verify trainee role is blocked from document approval and deletion."""
        # Admin uploads a pending document
        doc = upload_document(
            file_bytes=b"Sensitive technical procedure",
            filename="procedure.txt",
            domain="technical_maintenance",
            user_id=self.admin["id"],
            auto_approve=False,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        self.assertEqual(doc["status"], "pending")

        # Trainee attempts to approve document -> MUST RAISE AuthorizationError
        with self.assertRaises(AuthorizationError):
            approve_document(
                document_id=doc["id"],
                user_id=self.trainee["id"],
                username=self.trainee["username"],
                custom_path=self.db_path
            )

        # Trainee attempts to delete document -> MUST RAISE AuthorizationError
        with self.assertRaises(AuthorizationError):
            delete_document(
                document_id=doc["id"],
                user_id=self.trainee["id"],
                username=self.trainee["username"],
                custom_path=self.db_path
            )

    def test_file_format_spoofing_defense(self):
        """Verify executable disguised as PDF is rejected by magic byte inspection."""
        # Windows executable header (MZ) disguised as PDF
        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This is an executable"
        valid, err, _ = validate_file("malicious_tool.pdf", fake_pdf)
        self.assertFalse(valid)
        self.assertIn("signature", err.lower())

        with self.assertRaises(DocumentError):
            upload_document(
                file_bytes=fake_pdf,
                filename="malicious_tool.pdf",
                domain="defensive_cybersecurity",
                user_id=self.admin["id"],
                vault_dir=self.vault_path,
                custom_path=self.db_path
            )

    def test_audit_log_records_security_events(self):
        """Verify audit trail records actions with sanitized metadata."""
        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM audit_logs")
            log_count = cur.fetchone()[0]
            self.assertGreater(log_count, 0)

            # Check that sensitive passwords are never written in audit descriptions
            cur.execute("SELECT description, metadata_json FROM audit_logs")
            for desc, meta in cur.fetchall():
                self.assertNotIn("AdminPassword#123", desc)
                self.assertNotIn("TraineePassword#123", desc)


if __name__ == "__main__":
    unittest.main()
