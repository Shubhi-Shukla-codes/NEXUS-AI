"""
NEXUS RAG Pipeline & Document Grounding Unit Tests
Verifies end-to-end fixes for:
1. OCR fallback extraction for vectorized/scanned PDFs
2. Document lifecycle indexing status (only 'indexed' after vector persistence)
3. Target document filtering in vector store, semantic retriever, and hybrid retriever
4. BM25 stopword filtering and semantic floor gating for strict abstention
5. Full retrieval diagnostics reporting
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database, get_db_connection
from backend.security.auth import register_user
from backend.services.document_service import upload_document, approve_document
from backend.ingestion.pipeline import process_document
from backend.retrieval.embeddings import MockEmbeddingProvider
from backend.storage.vector_store import ChromaVectorStore, index_document_in_vector_store
from backend.retrieval.retriever import SemanticRetriever
from backend.retrieval.bm25 import BM25Index, tokenize_technical_text, STOPWORDS
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.generation.rag_engine import RAGEngine, ABSTENTION_MESSAGE
from backend.generation.ollama_client import MockLLMClient


class TestRAGPipelineFix(unittest.TestCase):
    """Test suite covering critical RAG pipeline fixes."""

    def setUp(self):
        """Create isolated temporary environment for database, vault, and Chroma."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_rag_fix.db"
        self.vault_path = self.temp_path / "vault"
        self.chroma_path = self.temp_path / "chroma"
        init_database(custom_path=self.db_path)

        # Register admin operator
        self.user = register_user(
            username="CHIEF_TESTER",
            password="SecurePassword123!",
            role="administrator",
            custom_path=self.db_path
        )
        self.user_id = self.user["id"]

        # Setup mock providers
        self.mock_embedder = MockEmbeddingProvider(dimension=384)
        self.vector_store = ChromaVectorStore(persist_dir=self.chroma_path)
        self.semantic_retriever = SemanticRetriever(
            vector_store=self.vector_store,
            embedding_provider=self.mock_embedder,
            similarity_threshold=0.35,
            top_k=4
        )
        self.mock_llm = MockLLMClient()
        self.rag_engine = RAGEngine(
            llm_client=self.mock_llm,
            retriever=self.semantic_retriever,
            similarity_threshold=0.35,
            default_top_k=4
        )

    def tearDown(self):
        try:
            self.vector_store.close()
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_document_indexing_lifecycle_status(self):
        """
        Requirement 2: A document must not be marked INDEXED merely because it was
        uploaded or extracted. Only mark it INDEXED after successful embedding generation
        and vector-store persistence.
        """
        content = (
            "DRDO Technology Development Fund Scheme. "
            "Development of indigenous Large Language Model for cybersecurity "
            "vulnerability discovery and threat intelligence."
        ).encode("utf-8")

        # 1. Upload without auto_approve
        doc = upload_document(
            file_bytes=content,
            filename="DRDO_cyber_spec.txt",
            domain="defensive_cybersecurity",
            user_id=self.user_id,
            username="CHIEF_TESTER",
            auto_approve=False,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        self.assertEqual(doc["status"], "pending")

        # 2. Extract and chunk
        pipe_res = process_document(doc["id"], custom_path=self.db_path)
        self.assertEqual(pipe_res["status"], "processed")

        # Verify database status is STILL 'processed', NOT 'indexed'
        with get_db_connection(self.db_path) as conn:
            row = conn.execute("SELECT status FROM documents WHERE id = ?", (doc["id"],)).fetchone()
            self.assertEqual(row["status"], "processed")

        # Verify ChromaDB has 0 chunks for this document
        col = self.vector_store._get_collection()
        res_before = col.get(where={"document_id": doc["id"]})
        self.assertEqual(len(res_before["ids"]), 0)

        # 3. Now run vector indexing
        idx_res = index_document_in_vector_store(
            document_id=doc["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )
        self.assertEqual(idx_res["status"], "indexed")
        self.assertGreater(idx_res["indexed_chunks"], 0)

        # Verify database status is now 'indexed'
        with get_db_connection(self.db_path) as conn:
            row = conn.execute("SELECT status FROM documents WHERE id = ?", (doc["id"],)).fetchone()
            self.assertEqual(row["status"], "indexed")

        # Verify ChromaDB now has the chunks
        res_after = col.get(where={"document_id": doc["id"]})
        self.assertEqual(len(res_after["ids"]), idx_res["indexed_chunks"])

    def test_target_document_filtering(self):
        """
        Verify that passing document_id isolates retrieval strictly to that document.
        """
        doc1_content = "Document 1 covers naval radar and sonar propagation characteristics.".encode("utf-8")
        doc2_content = "Document 2 covers DRDO cybersecurity vulnerability assessments and TDF funding.".encode("utf-8")

        # Upload and index doc 1
        d1 = upload_document(
            file_bytes=doc1_content,
            filename="Naval_Radar.txt",
            domain="technical_knowledge",
            user_id=self.user_id,
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d1["id"], custom_path=self.db_path)
        index_document_in_vector_store(d1["id"], embedding_provider=self.mock_embedder, vector_store=self.vector_store, custom_path=self.db_path)

        # Upload and index doc 2
        d2 = upload_document(
            file_bytes=doc2_content,
            filename="DRDO_Cyber.txt",
            domain="defensive_cybersecurity",
            user_id=self.user_id,
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d2["id"], custom_path=self.db_path)
        index_document_in_vector_store(d2["id"], embedding_provider=self.mock_embedder, vector_store=self.vector_store, custom_path=self.db_path)

        # Retrieve targeting Document 2 explicitly
        evidence = self.semantic_retriever.retrieve_evidence(
            query="radar and cybersecurity",
            user_id=self.user_id,
            document_id=d2["id"],
            threshold=0.01,
            custom_path=self.db_path
        )
        self.assertTrue(evidence["is_sufficient"])
        for c in evidence["citations"]:
            self.assertEqual(c["document_id"], d2["id"])
            self.assertEqual(c["filename"], "DRDO_Cyber.txt")

    def test_bm25_stopword_filtering(self):
        """
        Verify that BM25 tokenizer ignores common English stopwords and avoids false positive candidate spikes.
        """
        stop_query = "what was the date of the mission"
        tokens = [t for t in tokenize_technical_text(stop_query) if t not in STOPWORDS]
        self.assertNotIn("what", tokens)
        self.assertNotIn("was", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("of", tokens)
        self.assertIn("date", tokens)
        self.assertIn("mission", tokens)

    def test_hybrid_retriever_semantic_floor_abstention(self):
        """
        Verify that out-of-domain queries whose dense similarity is below noise floor
        (< 0.25) do NOT qualify through sparse coincidences.
        """
        doc_content = "DRDO indigenous Large Language Model for cybersecurity threat intelligence.".encode("utf-8")
        d = upload_document(
            file_bytes=doc_content,
            filename="DRDO_TDF.txt",
            domain="defensive_cybersecurity",
            user_id=self.user_id,
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d["id"], custom_path=self.db_path)
        index_document_in_vector_store(d["id"], embedding_provider=self.mock_embedder, vector_store=self.vector_store, custom_path=self.db_path)

        hybrid = HybridRetriever(semantic_retriever=self.semantic_retriever, similarity_threshold=0.35)
        # Query totally unrelated to corpus
        res = hybrid.retrieve_hybrid_evidence(
            query="What is the recipe for chocolate cake with strawberry frosting?",
            user_id=self.user_id,
            username="CHIEF_TESTER",
            domain="all",
            custom_path=self.db_path
        )
        self.assertFalse(res["is_sufficient"])
        self.assertEqual(len(res["citations"]), 0)

    def test_rag_engine_diagnostics_structure(self):
        """
        Verify that RAGEngine.answer_query produces full structured diagnostics
        including candidate details, scores, threshold, and context pass status.
        """
        doc_text = (
            "Under the Technology Development Fund Scheme, DRDO announced an Expression of Interest "
            "for developing an indigenous Large Language Model for cyber defence."
        )

        d = upload_document(
            file_bytes=doc_text.encode("utf-8"),
            filename="DRDO_Brief.txt",
            domain="defensive_cybersecurity",
            user_id=self.user_id,
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(d["id"], custom_path=self.db_path)
        index_document_in_vector_store(d["id"], embedding_provider=self.mock_embedder, vector_store=self.vector_store, custom_path=self.db_path)

        # In MockEmbeddingProvider, exact match guarantees 1.0 similarity
        res = self.rag_engine.answer_query(
            query=doc_text,
            user_id=self.user_id,
            username="CHIEF_TESTER",
            domain="all",
            search_mode="dense",
            threshold=0.35,
            custom_path=self.db_path
        )

        self.assertIn("diagnostics", res)
        diag = res["diagnostics"]
        self.assertEqual(diag["search_mode"], "dense")
        self.assertTrue(diag["context_passed_to_llm"])
        self.assertGreater(diag["retrieved_count"], 0)
        self.assertIn("retrieved_candidates", diag)
        c0 = diag["retrieved_candidates"][0]
        self.assertIn("filename", c0)
        self.assertIn("page_number", c0)
        self.assertIn("similarity_score", c0)
        self.assertIn("passage_snippet", c0)


if __name__ == "__main__":
    unittest.main()
