"""
NEXUS Hybrid Search & Domain Modules Unit Tests
Validates BM25 technical tokenization, alphanumeric code matching,
domain taxonomy profiles, Reciprocal Rank Fusion (RRF), and hybrid RAG retrieval.
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
from backend.services.document_service import upload_document
from backend.ingestion.pipeline import process_document
from backend.retrieval.embeddings import MockEmbeddingProvider
from backend.storage.vector_store import ChromaVectorStore, index_document_in_vector_store
from backend.retrieval.retriever import SemanticRetriever
from backend.retrieval.bm25 import BM25Index, tokenize_technical_text
from backend.retrieval.domain_manager import (
    DOMAIN_PROFILES,
    get_domain_profile,
    list_domain_profiles,
    match_domain_by_query
)
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.generation.ollama_client import MockLLMClient
from backend.generation.rag_engine import RAGEngine


class TestHybridSearchAndDomains(unittest.TestCase):
    """Test suite for sparse BM25, domain taxonomy, and hybrid RRF retrieval."""

    def setUp(self):
        """Create isolated temporary database, vault, and vector store."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_hybrid.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        self.chroma_path = Path(self.temp_dir.name) / "chroma"
        init_database(custom_path=self.db_path)

        # Seed operator user
        self.user = register_user(
            username="hybrid_operator",
            password="Password@123",
            role="instructor",
            custom_path=self.db_path
        )

        self.mock_embedder = MockEmbeddingProvider(dimension=384)
        self.vector_store = ChromaVectorStore(persist_dir=self.chroma_path)
        self.semantic_retriever = SemanticRetriever(
            vector_store=self.vector_store,
            embedding_provider=self.mock_embedder,
            similarity_threshold=0.20,
            top_k=3
        )

        # Ingest document 1: Technical maintenance with specific code B-12
        self.doc1 = upload_document(
            file_bytes=b"Maintenance Bulletin: Inspect circuit breaker B-12 on alternator assembly before starting generator.",
            filename="bulletin_b12.txt",
            domain="technical_maintenance",
            user_id=self.user["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(self.doc1["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=self.doc1["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        # Ingest document 2: Safety emergency protocol
        self.doc2 = upload_document(
            file_bytes=b"Chemical Spill Protocol: Toxic ammonia exposure requires Level B PPE and immediate eye-wash triage.",
            filename="safety_ammonia.txt",
            domain="safety_emergency",
            user_id=self.user["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(self.doc2["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=self.doc2["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        self.hybrid_retriever = HybridRetriever(
            semantic_retriever=self.semantic_retriever,
            dense_weight=0.6,
            sparse_weight=0.4,
            similarity_threshold=0.20,
            top_k=2
        )

    def tearDown(self):
        if hasattr(self, "vector_store") and self.vector_store:
            self.vector_store.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_tokenize_technical_text(self):
        """Verify tokenization preserves compound codes, hyphens, and alphanumeric tokens."""
        text = "Replace circuit breaker B-12 and inspect MIL-STD-810G casing on IP67 unit."
        tokens = tokenize_technical_text(text)

        self.assertIn("b-12", tokens)
        self.assertIn("mil-std-810g", tokens)
        self.assertIn("ip67", tokens)
        self.assertIn("circuit", tokens)

    def test_bm25_exact_code_matching(self):
        """Verify BM25 accurately isolates document containing specific technical identifier."""
        bm25 = BM25Index.build_from_database(custom_path=self.db_path)
        results = bm25.search("circuit breaker B-12", top_k=2)

        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertEqual(top["filename"], "bulletin_b12.txt")
        self.assertGreater(top["bm25_raw_score"], 0.0)

    def test_domain_profiles_and_heuristic_matching(self):
        """Verify 6 domain profiles exist and taxonomy matcher infers domain correctly."""
        profiles = list_domain_profiles()
        self.assertEqual(len(profiles), 6)

        tech_prof = get_domain_profile("technical_maintenance")
        self.assertIsNotNone(tech_prof)
        self.assertIn("hydraulic", tech_prof.taxonomy_keywords)

        # Test query matching
        domain_match1 = match_domain_by_query("How to calibrate hydraulic valve pressure?")
        self.assertEqual(domain_match1, "technical_maintenance")

        domain_match2 = match_domain_by_query("Decontamination eye-wash triage for chemical exposure")
        self.assertEqual(domain_match2, "safety_emergency")

    def test_reciprocal_rank_fusion_logic(self):
        """Verify RRF elevates candidate present in both dense and sparse result lists."""
        dense_candidates = [
            {"chunk_id": "chunk_A", "similarity_score": 0.90, "filename": "doc_a.txt"},
            {"chunk_id": "chunk_B", "similarity_score": 0.70, "filename": "doc_b.txt"},
        ]
        sparse_candidates = [
            {"chunk_id": "chunk_B", "bm25_score": 1.0, "filename": "doc_b.txt"},
            {"chunk_id": "chunk_C", "bm25_score": 0.8, "filename": "doc_c.txt"},
        ]

        fused = self.hybrid_retriever._reciprocal_rank_fusion(
            dense_results=dense_candidates,
            sparse_results=sparse_candidates,
            top_k=3
        )

        self.assertEqual(len(fused), 3)
        # chunk_B appears in both, so its reciprocal rank sum should place it at or near top
        chunk_ids = [c["chunk_id"] for c in fused]
        self.assertIn("chunk_B", chunk_ids)
        self.assertEqual(fused[0]["retrieval_mode"], "hybrid_rrf")

    def test_hybrid_retriever_full_pipeline(self):
        """Verify retrieve_hybrid_evidence returns fused citations with structured context."""
        res = self.hybrid_retriever.retrieve_hybrid_evidence(
            query="circuit breaker B-12 alternator",
            user_id=self.user["id"],
            username=self.user["username"],
            domain="technical_maintenance",
            top_k=2,
            threshold=0.10,
            custom_path=self.db_path
        )

        self.assertTrue(res["is_sufficient"])
        self.assertGreater(len(res["citations"]), 0)
        top = res["citations"][0]
        self.assertEqual(top["filename"], "bulletin_b12.txt")
        self.assertIn("combined_score", top)
        self.assertIn("Evidence Reference", res["context_text"])

    def test_rag_engine_with_hybrid_search_mode(self):
        """Verify RAGEngine correctly runs with search_mode='hybrid'."""
        mock_llm = MockLLMClient()
        engine = RAGEngine(
            llm_client=mock_llm,
            retriever=self.semantic_retriever,
            similarity_threshold=0.10
        )

        res = engine.answer_query(
            query="Inspect circuit breaker B-12",
            user_id=self.user["id"],
            username=self.user["username"],
            domain="technical_maintenance",
            search_mode="hybrid",
            threshold=0.10,
            custom_path=self.db_path
        )

        self.assertFalse(res["abstained"])
        self.assertIn("[REF-1]", res["answer"])
        self.assertGreater(len(res["citations"]), 0)
        self.assertEqual(res["citations"][0]["filename"], "bulletin_b12.txt")


if __name__ == "__main__":
    unittest.main()
