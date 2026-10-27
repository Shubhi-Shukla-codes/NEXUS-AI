"""
NEXUS Semantic Retrieval Unit Tests
Validates query vectorization, similarity thresholding, Top-K ranking,
permission-aware boundary enforcement, evidence deduplication, and context assembly.
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
from backend.services.document_service import upload_document
from backend.ingestion.pipeline import process_document
from backend.retrieval.embeddings import MockEmbeddingProvider
from backend.storage.vector_store import ChromaVectorStore, index_document_in_vector_store
from backend.retrieval.retriever import SemanticRetriever


class TestSemanticRetrieval(unittest.TestCase):
    """Test suite for semantic evidence retrieval and thresholding."""

    def setUp(self):
        """Create isolated temporary database and vector store."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_retrieval.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        self.chroma_path = Path(self.temp_dir.name) / "chroma"
        init_database(custom_path=self.db_path)

        self.mock_embedder = MockEmbeddingProvider(dimension=384)
        self.vector_store = ChromaVectorStore(persist_dir=self.chroma_path)
        self.retriever = SemanticRetriever(
            vector_store=self.vector_store,
            embedding_provider=self.mock_embedder,
            similarity_threshold=0.30,
            top_k=3
        )

        # Seed users
        self.admin = register_user(
            username="admin_retrieval",
            password="AdminPassword#123",
            role="administrator",
            custom_path=self.db_path
        )
        self.trainee = register_user(
            username="trainee_retrieval",
            password="TraineePassword#123",
            role="trainee",
            custom_path=self.db_path
        )

        # Ingest approved technical document
        self.doc_tech = upload_document(
            file_bytes=b"Generator electrical troubleshooting. Check circuit breaker B-12 before restarting engine.",
            filename="generator_guide.txt",
            domain="technical_maintenance",
            user_id=self.admin["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(self.doc_tech["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=self.doc_tech["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        # Ingest approved safety document
        self.doc_safety = upload_document(
            file_bytes=b"Emergency chemical exposure protocol. Flush affected area with clean water for 15 minutes.",
            filename="chemical_sds.txt",
            domain="safety_emergency",
            user_id=self.admin["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(self.doc_safety["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=self.doc_safety["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

    def tearDown(self):
        if hasattr(self, "vector_store") and self.vector_store:
            self.vector_store.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_retrieve_evidence_success(self):
        """Verify query returns citations with high relevance and formatted context."""
        res = self.retriever.retrieve_evidence(
            query="Generator electrical troubleshooting circuit breaker",
            user_id=self.trainee["id"],
            username="trainee_retrieval",
            domain="technical_maintenance",
            threshold=0.0,  # Zero threshold to capture candidate
            custom_path=self.db_path
        )

        self.assertTrue(res["is_sufficient"])
        self.assertGreater(len(res["citations"]), 0)
        self.assertIn("generator_guide.txt", res["citations"][0]["filename"])
        self.assertIn("Evidence Reference", res["context_text"])
        self.assertIn("circuit breaker B-12", res["context_text"])

    def test_abstention_when_below_threshold(self):
        """Verify that an extremely high threshold triggers abstention (is_sufficient = False)."""
        res = self.retriever.retrieve_evidence(
            query="Random unmatched search terms",
            user_id=self.trainee["id"],
            username="trainee_retrieval",
            threshold=0.9999,  # Impossibly high threshold
            custom_path=self.db_path
        )

        self.assertFalse(res["is_sufficient"])
        self.assertEqual(len(res["citations"]), 0)
        self.assertEqual(res["context_text"], "")
        self.assertIn("Insufficient evidence", res["message"])

    def test_top_k_selection_limit(self):
        """Verify retriever strictly caps output at requested Top-K limit."""
        res = self.retriever.retrieve_evidence(
            query="protocol",
            user_id=self.admin["id"],
            username="admin_retrieval",
            top_k=1,
            threshold=0.0,
            custom_path=self.db_path
        )
        self.assertLessEqual(len(res["citations"]), 1)

    def test_domain_filtering_scoping(self):
        """Verify search scoped to domain only returns chunks from that domain."""
        res = self.retriever.retrieve_evidence(
            query="protocol water flush",
            user_id=self.trainee["id"],
            username="trainee_retrieval",
            domain="safety_emergency",
            threshold=0.0,
            custom_path=self.db_path
        )

        for c in res["citations"]:
            self.assertEqual(c["domain"], "safety_emergency")
            self.assertEqual(c["filename"], "chemical_sds.txt")

    def test_empty_query_handling(self):
        """Verify empty query string returns safe empty response without crashing."""
        res = self.retriever.retrieve_evidence(
            query="   ",
            user_id=self.trainee["id"],
            username="trainee_retrieval",
            custom_path=self.db_path
        )
        self.assertFalse(res["is_sufficient"])
        self.assertEqual(len(res["citations"]), 0)

    def test_unauthorized_user_permission_check(self):
        """Verify user lacking 'doc:view' permission is denied retrieval."""
        import sqlite3
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password_hash) VALUES ('no_roles_user', 'hash')")
            no_roles_uid = cur.lastrowid

        with self.assertRaises(AuthorizationError):
            self.retriever.retrieve_evidence(
                query="Any query",
                user_id=no_roles_uid,
                username="no_roles_user",
                custom_path=self.db_path
            )


if __name__ == "__main__":
    unittest.main()
