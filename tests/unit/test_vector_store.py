"""
NEXUS Vector Storage & Embeddings Unit Tests
Validates embedding generation, ChromaDB vector indexing, metadata filtering,
and document lifecycle synchronization.
"""

import sys
import unittest
import tempfile
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database
from backend.security.auth import register_user
from backend.services.document_service import upload_document
from backend.ingestion.pipeline import process_document
from backend.retrieval.embeddings import MockEmbeddingProvider
from backend.storage.vector_store import (
    ChromaVectorStore,
    index_document_in_vector_store
)
from backend.retrieval.reindex import reindex_all_approved_documents


class TestVectorStore(unittest.TestCase):
    """Test suite for embedding generation and ChromaDB vector persistence."""

    def setUp(self):
        """Create isolated temporary database and vector directory."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_vectors.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        self.chroma_path = Path(self.temp_dir.name) / "chroma"
        init_database(custom_path=self.db_path)

        self.mock_embedder = MockEmbeddingProvider(dimension=384)
        self.vector_store = ChromaVectorStore(persist_dir=self.chroma_path)

        # Seed operator
        self.operator = register_user(
            username="vector_tester",
            password="Password@123",
            role="instructor",
            custom_path=self.db_path
        )

    def tearDown(self):
        if hasattr(self, "vector_store") and self.vector_store:
            self.vector_store.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_mock_embedding_provider_properties(self):
        """Verify vector dimensionality and unit norm."""
        texts = ["Turbine generator calibration", "Safety shield checklist"]
        embeddings = self.mock_embedder.embed_texts(texts)

        self.assertEqual(len(embeddings), 2)
        for vec in embeddings:
            self.assertEqual(len(vec), 384)
            # Check unit length (L2 norm ~ 1.0)
            norm = np.linalg.norm(vec)
            self.assertAlmostEqual(norm, 1.0, places=4)

        # Verify query vector
        q_vec = self.mock_embedder.embed_query("Turbine query")
        self.assertEqual(len(q_vec), 384)
        self.assertAlmostEqual(np.linalg.norm(q_vec), 1.0, places=4)

    def test_index_and_query_chunks(self):
        """Verify adding chunks to Chroma and querying with metadata filters."""
        # Create a document and process chunks
        doc = upload_document(
            file_bytes=b"Turbine maintenance protocol. Check oil valve daily.",
            filename="turbine.txt",
            domain="technical_maintenance",
            user_id=self.operator["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(doc["id"], custom_path=self.db_path)

        # Index in ChromaDB
        res = index_document_in_vector_store(
            document_id=doc["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )
        self.assertGreater(res["indexed_chunks"], 0)
        self.assertEqual(self.vector_store.count_vectors(), res["indexed_chunks"])

        # Query vector store
        q_emb = self.mock_embedder.embed_query("Turbine oil valve")
        matches = self.vector_store.query_similar(
            query_embedding=q_emb,
            top_k=2,
            domain="technical_maintenance",
            approved_only=True
        )

        self.assertGreaterEqual(len(matches), 1)
        top_match = matches[0]
        self.assertEqual(top_match["document_id"], doc["id"])
        self.assertEqual(top_match["domain"], "technical_maintenance")
        self.assertIn("Turbine maintenance", top_match["content"])
        self.assertGreaterEqual(top_match["similarity_score"], 0.0)

    def test_domain_filtering_excludes_other_domains(self):
        """Verify vector search with domain filter excludes chunks from other domains."""
        # 1. Tech doc
        d_tech = upload_document(
            file_bytes=b"Radio communication manual.",
            filename="radio.txt",
            domain="technical_maintenance",
            user_id=self.operator["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d_tech["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=d_tech["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        # 2. Cyber doc
        d_cyber = upload_document(
            file_bytes=b"Firewall rule baseline.",
            filename="firewall.txt",
            domain="defensive_cybersecurity",
            user_id=self.operator["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d_cyber["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=d_cyber["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        # Search specifically within 'defensive_cybersecurity'
        q_emb = self.mock_embedder.embed_query("security rule")
        results = self.vector_store.query_similar(
            query_embedding=q_emb,
            top_k=5,
            domain="defensive_cybersecurity"
        )
        for r in results:
            self.assertEqual(r["domain"], "defensive_cybersecurity")

    def test_delete_document_vectors(self):
        """Verify deleting a document clears its vector embeddings from Chroma."""
        doc = upload_document(
            file_bytes=b"Emergency exit instructions.",
            filename="exit.txt",
            domain="safety_emergency",
            user_id=self.operator["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(doc["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=doc["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        self.assertGreater(self.vector_store.count_vectors(), 0)

        # Delete document vectors
        deleted_count = self.vector_store.delete_document_vectors(doc["id"])
        self.assertGreater(deleted_count, 0)
        self.assertEqual(self.vector_store.count_vectors(), 0)

    def test_reindex_all_approved_documents(self):
        """Verify controlled full re-indexing populates all approved document vectors."""
        # Add 2 approved docs
        d1 = upload_document(
            file_bytes=b"Doc one content.",
            filename="doc1.txt",
            domain="training_education",
            user_id=self.operator["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d1["id"], custom_path=self.db_path)

        d2 = upload_document(
            file_bytes=b"Doc two content.",
            filename="doc2.txt",
            domain="safety_emergency",
            user_id=self.operator["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d2["id"], custom_path=self.db_path)

        reindex_res = reindex_all_approved_documents(
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )
        self.assertEqual(reindex_res["total_documents"], 2)
        self.assertGreaterEqual(reindex_res["total_chunks_indexed"], 2)


if __name__ == "__main__":
    unittest.main()
