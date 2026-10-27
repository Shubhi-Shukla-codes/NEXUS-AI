"""
NEXUS Generation & Grounded RAG Unit Tests
Validates Ollama client abstractions, grounded prompt assembly, citation mapping,
abstention enforcement, and multi-turn SQLite conversation persistence.
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
from backend.generation.ollama_client import MockLLMClient, LLMConnectionError
from backend.generation.rag_engine import RAGEngine, ABSTENTION_MESSAGE
from backend.services.conversation_service import (
    create_conversation,
    list_conversations,
    get_conversation,
    add_message,
    get_conversation_messages,
    delete_conversation
)


class TestGroundedGeneration(unittest.TestCase):
    """Test suite for Grounded RAG Generation and conversation tracking."""

    def setUp(self):
        """Create isolated temporary database, vault, and vector store."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_generation.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        self.chroma_path = Path(self.temp_dir.name) / "chroma"
        init_database(custom_path=self.db_path)

        # Seed test user
        self.user = register_user(
            username="rag_operator",
            password="Password@123",
            role="instructor",
            custom_path=self.db_path
        )

        # Ingest approved technical document
        self.mock_embedder = MockEmbeddingProvider(dimension=384)
        self.vector_store = ChromaVectorStore(persist_dir=self.chroma_path)
        self.retriever = SemanticRetriever(
            vector_store=self.vector_store,
            embedding_provider=self.mock_embedder,
            similarity_threshold=0.30,
            top_k=2
        )

        self.doc = upload_document(
            file_bytes=b"Standard Hydraulic Pressure: Normal operating level is 2500 to 3000 PSI. Inspect relief valve weekly.",
            filename="hydraulic_manual.txt",
            domain="technical_maintenance",
            user_id=self.user["id"],
            auto_approve=True,
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        process_document(self.doc["id"], custom_path=self.db_path)
        index_document_in_vector_store(
            document_id=self.doc["id"],
            embedding_provider=self.mock_embedder,
            vector_store=self.vector_store,
            custom_path=self.db_path
        )

        self.mock_llm = MockLLMClient()
        self.rag_engine = RAGEngine(
            llm_client=self.mock_llm,
            retriever=self.retriever,
            similarity_threshold=0.30
        )

    def tearDown(self):
        if hasattr(self, "vector_store") and self.vector_store:
            self.vector_store.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_conversation_service_lifecycle(self):
        """Verify conversation thread creation, message additions, citations JSON, and deletion."""
        # 1. Create conversation
        conv = create_conversation(
            user_id=self.user["id"],
            title="Hydraulics Review",
            domain_scope="technical_maintenance",
            custom_path=self.db_path
        )
        self.assertIsNotNone(conv["id"])
        self.assertEqual(conv["title"], "Hydraulics Review")

        # 2. Add user message
        msg1 = add_message(
            conversation_id=conv["id"],
            role="user",
            content="What is normal hydraulic pressure?",
            user_id=self.user["id"],
            custom_path=self.db_path
        )
        self.assertEqual(msg1["role"], "user")

        # 3. Add assistant response with citations
        mock_citations = [
            {"filename": "hydraulic_manual.txt", "page_number": 1, "score": 0.92}
        ]
        msg2 = add_message(
            conversation_id=conv["id"],
            role="assistant",
            content="Normal hydraulic pressure is 2500-3000 PSI [REF-1].",
            citations=mock_citations,
            user_id=self.user["id"],
            custom_path=self.db_path
        )
        self.assertEqual(len(msg2["citations"]), 1)
        self.assertEqual(msg2["citations"][0]["filename"], "hydraulic_manual.txt")

        # 4. Fetch history
        history = get_conversation_messages(conv["id"], user_id=self.user["id"], custom_path=self.db_path)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

        # 5. List conversations
        convs = list_conversations(self.user["id"], custom_path=self.db_path)
        self.assertEqual(len(convs), 1)
        self.assertEqual(convs[0]["message_count"], 2)

        # 6. Delete conversation
        deleted = delete_conversation(conv["id"], user_id=self.user["id"], custom_path=self.db_path)
        self.assertTrue(deleted)
        self.assertEqual(len(get_conversation_messages(conv["id"], custom_path=self.db_path)), 0)

    def test_mock_llm_client_behavior(self):
        """Verify Mock LLM client returns deterministic responses and handles availability."""
        client = MockLLMClient()
        self.assertTrue(client.is_available())

        # With evidence in prompt
        ans = client.generate("AUTHORIZED PASSAGES: [REF-1] Hydraulic info")
        self.assertIn("[REF-1]", ans)

        # Without evidence
        ans_empty = client.generate("No references here")
        self.assertIn("does not contain sufficient", ans_empty)

        # Unavailable raises error
        client.set_available(False)
        with self.assertRaises(LLMConnectionError):
            client.generate("Test prompt")

    def test_rag_engine_generates_grounded_answer_with_citations(self):
        """Verify RAG engine retrieves evidence, passes to LLM, and attaches citations."""
        conv = create_conversation(user_id=self.user["id"], custom_path=self.db_path)

        res = self.rag_engine.answer_query(
            query="hydraulic pressure operating range",
            user_id=self.user["id"],
            username=self.user["username"],
            domain="technical_maintenance",
            conversation_id=conv["id"],
            threshold=0.0,
            custom_path=self.db_path
        )

        self.assertFalse(res["abstained"])
        self.assertIn("[REF-1]", res["answer"])
        self.assertGreater(len(res["citations"]), 0)
        self.assertEqual(res["citations"][0]["filename"], "hydraulic_manual.txt")

        # Check SQLite persistence
        history = get_conversation_messages(conv["id"], custom_path=self.db_path)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "hydraulic pressure operating range")
        self.assertIn("[REF-1]", history[1]["content"])

    def test_rag_engine_abstention_when_below_threshold(self):
        """Verify RAG engine immediately abstains and skips LLM when evidence score is low."""
        # Client that would fail if called
        failing_client = MockLLMClient()
        failing_client.set_available(False)

        strict_engine = RAGEngine(
            llm_client=failing_client,
            retriever=self.retriever,
            similarity_threshold=0.9999  # Impossible threshold
        )

        res = strict_engine.answer_query(
            query="hydraulic pressure operating range",
            user_id=self.user["id"],
            username=self.user["username"],
            threshold=0.9999,
            custom_path=self.db_path
        )

        self.assertTrue(res["abstained"])
        self.assertEqual(res["answer"], ABSTENTION_MESSAGE)
        self.assertEqual(len(res["citations"]), 0)

    def test_rag_engine_empty_query_safety(self):
        """Verify empty query returns safe prompt without error."""
        res = self.rag_engine.answer_query(
            query="   ",
            user_id=self.user["id"],
            username=self.user["username"],
            custom_path=self.db_path
        )
        self.assertTrue(res["abstained"])
        self.assertEqual(len(res["citations"]), 0)

    def test_rag_engine_citation_extraction(self):
        """Verify parsing of [REF-X] tags from model generated output."""
        retrieved = [
            {"filename": "doc_a.txt", "page_number": 1, "similarity_score": 0.88, "content": "A"},
            {"filename": "doc_b.txt", "page_number": 2, "similarity_score": 0.75, "content": "B"},
        ]
        text_with_cites = "According to doc A [REF-1], condition holds, and further details [REF-2]."
        extracted = self.rag_engine._extract_citations(text_with_cites, retrieved)

        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted[0]["filename"], "doc_a.txt")
        self.assertEqual(extracted[0]["ref_tag"], "[REF-1]")
        self.assertEqual(extracted[1]["filename"], "doc_b.txt")
        self.assertEqual(extracted[1]["ref_tag"], "[REF-2]")


if __name__ == "__main__":
    unittest.main()
