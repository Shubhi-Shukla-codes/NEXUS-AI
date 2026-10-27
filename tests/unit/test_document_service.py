"""
NEXUS Document Service Unit Tests
Validates upload pipeline, duplicate detection, approval workflow,
listing filters, and deletion across isolated temporary SQLite databases.
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
from backend.security.rbac import AuthorizationError
from backend.services.document_service import (
    upload_document,
    list_documents,
    get_document_by_id,
    approve_document,
    reject_document,
    delete_document,
    DocumentError
)


class TestDocumentService(unittest.TestCase):
    """Test suite for document repository lifecycle and permissions."""

    def setUp(self):
        """Create isolated temporary database and vault directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_docs.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        init_database(custom_path=self.db_path)

        # Seed test users
        self.admin = register_user(
            username="doc_admin",
            password="AdminPassword#123",
            role="administrator",
            custom_path=self.db_path
        )
        self.instructor = register_user(
            username="doc_instructor",
            password="InstructorPassword#123",
            role="instructor",
            custom_path=self.db_path
        )
        self.trainee = register_user(
            username="doc_trainee",
            password="TraineePassword#123",
            role="trainee",
            custom_path=self.db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_upload_document_success(self):
        """Verify upload creates document with 'pending' status by default."""
        file_bytes = b"%PDF-1.4 Generator Maintenance Guide"
        doc = upload_document(
            file_bytes=file_bytes,
            filename="generator_guide.pdf",
            domain="technical_maintenance",
            user_id=self.instructor["id"],
            username="doc_instructor",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        self.assertIsNotNone(doc["id"])
        self.assertEqual(doc["status"], "pending")
        self.assertFalse(doc["is_duplicate"])
        self.assertTrue(Path(doc["vault_path"]).is_file())

    def test_upload_with_auto_approve_when_permitted(self):
        """Verify auto-approve sets status to 'approved' for authorized users."""
        file_bytes = b"%PDF-1.4 Emergency Evacuation Protocol"
        doc = upload_document(
            file_bytes=file_bytes,
            filename="evac_protocol.pdf",
            domain="safety_emergency",
            user_id=self.instructor["id"],
            username="doc_instructor",
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        self.assertEqual(doc["status"], "approved")

    def test_duplicate_upload_detection(self):
        """Verify identical file content is detected as duplicate and not re-inserted."""
        file_bytes = b"%PDF-1.4 Identical Content For Deduplication"
        doc1 = upload_document(
            file_bytes=file_bytes,
            filename="doc_original.pdf",
            domain="defensive_cybersecurity",
            user_id=self.instructor["id"],
            username="doc_instructor",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        # Upload exact same bytes with different filename
        doc2 = upload_document(
            file_bytes=file_bytes,
            filename="doc_copy.pdf",
            domain="defensive_cybersecurity",
            user_id=self.instructor["id"],
            username="doc_instructor",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        self.assertTrue(doc2["is_duplicate"])
        self.assertEqual(doc1["id"], doc2["id"])

    def test_unauthorized_upload_rejected(self):
        """Verify trainee role lacks 'doc:upload' permission and is rejected."""
        file_bytes = b"Sample text"
        with self.assertRaises(AuthorizationError):
            upload_document(
                file_bytes=file_bytes,
                filename="unauth.txt",
                domain="training_education",
                user_id=self.trainee["id"],
                username="doc_trainee",
                vault_dir=self.vault_path,
                custom_path=self.db_path
            )

    def test_list_documents_filtering(self):
        """Verify repository listing with domain and status filters."""
        # Ingest 2 documents in different domains
        upload_document(
            file_bytes=b"%PDF-1.4 Technical Manual A",
            filename="manual_a.pdf",
            domain="technical_maintenance",
            user_id=self.instructor["id"],
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        upload_document(
            file_bytes=b"%PDF-1.4 Cyber Defense Baseline",
            filename="cyber_b.pdf",
            domain="defensive_cybersecurity",
            user_id=self.instructor["id"],
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        # Filter by domain
        tech_docs = list_documents(
            domain="technical_maintenance",
            user_id=self.instructor["id"],
            custom_path=self.db_path
        )
        self.assertEqual(len(tech_docs), 1)
        self.assertEqual(tech_docs[0]["filename"], "manual_a.pdf")

        # Filter by query
        search_res = list_documents(
            search_query="Cyber",
            user_id=self.instructor["id"],
            custom_path=self.db_path
        )
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["filename"], "cyber_b.pdf")

    def test_approval_and_rejection_lifecycle(self):
        """Verify document status transitions through approval and rejection."""
        doc = upload_document(
            file_bytes=b"%PDF-1.4 Safety Protocol",
            filename="safety.pdf",
            domain="safety_emergency",
            user_id=self.instructor["id"],
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        doc_id = doc["id"]

        # Approve document
        approve_document(doc_id, user_id=self.admin["id"], username="doc_admin", custom_path=self.db_path)
        d_approved = get_document_by_id(doc_id, user_id=self.admin["id"], custom_path=self.db_path)
        self.assertEqual(d_approved["status"], "approved")
        self.assertEqual(d_approved["approver_name"], "doc_admin")

        # Reject document
        reject_document(doc_id, user_id=self.admin["id"], username="doc_admin", custom_path=self.db_path)
        d_rejected = get_document_by_id(doc_id, user_id=self.admin["id"], custom_path=self.db_path)
        self.assertEqual(d_rejected["status"], "rejected")

    def test_delete_document_clears_db_and_vault(self):
        """Verify deletion removes SQLite entry and physical file from vault."""
        doc = upload_document(
            file_bytes=b"%PDF-1.4 Document to Delete",
            filename="to_delete.pdf",
            domain="hazard_environmental",
            user_id=self.admin["id"],
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        doc_id = doc["id"]
        vault_file = Path(doc["vault_path"])
        self.assertTrue(vault_file.is_file())

        # Trainee cannot delete (lacks doc:delete)
        with self.assertRaises(AuthorizationError):
            delete_document(doc_id, user_id=self.trainee["id"], custom_path=self.db_path)

        # Admin deletes
        deleted = delete_document(doc_id, user_id=self.admin["id"], username="doc_admin", custom_path=self.db_path)
        self.assertTrue(deleted)

        # Verify DB row is gone
        self.assertIsNone(get_document_by_id(doc_id, user_id=self.admin["id"], custom_path=self.db_path))
        # Verify physical file is gone
        self.assertFalse(vault_file.exists())


if __name__ == "__main__":
    unittest.main()
