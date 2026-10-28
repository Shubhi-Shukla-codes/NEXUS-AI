"""
NEXUS Evaluation Framework Unit Tests
Validates Information Retrieval metrics (P@K, Recall@K, MRR, nDCG@K),
generation faithfulness, abstention accuracy, benchmark datasets, and evaluation runner.
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
from backend.retrieval.embeddings import MockEmbeddingProvider
from backend.storage.vector_store import ChromaVectorStore
from backend.retrieval.retriever import SemanticRetriever
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.generation.ollama_client import MockLLMClient
from backend.generation.rag_engine import RAGEngine
from backend.evaluation.benchmark_dataset import get_benchmark_cases, get_seed_documents
from backend.evaluation.seed_dataset import seed_demonstration_dataset
from backend.evaluation.retrieval_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    dcg_at_k,
    ndcg_at_k,
    hit_rate_at_k,
    compute_aggregate_retrieval_metrics
)
from backend.evaluation.faithfulness import (
    evaluate_citation_validity,
    evaluate_keyword_coverage,
    evaluate_abstention_accuracy
)
from backend.evaluation.runner import run_benchmark_evaluation


class TestEvaluationFramework(unittest.TestCase):
    """Test suite for evaluation metrics, benchmark datasets, and runner."""

    def test_precision_at_k_calculation(self):
        """Verify precision@K correctly scores fraction of relevant hits."""
        retrieved = ["doc_A", "doc_B", "doc_C", "doc_D"]
        relevant = {"doc_A", "doc_C"}

        self.assertEqual(precision_at_k(retrieved, relevant, k=2), 0.5)  # 1 hit in 2
        self.assertEqual(precision_at_k(retrieved, relevant, k=4), 0.5)  # 2 hits in 4
        self.assertEqual(precision_at_k(retrieved, {"doc_Z"}, k=4), 0.0) # 0 hits
        self.assertEqual(precision_at_k([], relevant, k=4), 0.0)

    def test_recall_at_k_calculation(self):
        """Verify recall@K correctly scores fraction of total relevant items retrieved."""
        retrieved = ["doc_A", "doc_B", "doc_C"]
        relevant = {"doc_A", "doc_C", "doc_D", "doc_E"}  # Total 4 relevant

        self.assertEqual(recall_at_k(retrieved, relevant, k=1), 0.25) # 1 of 4
        self.assertEqual(recall_at_k(retrieved, relevant, k=3), 0.50) # 2 of 4
        self.assertEqual(recall_at_k(retrieved, set(), k=3), 0.0)

    def test_reciprocal_rank_calculation(self):
        """Verify MRR reciprocal ranking scores."""
        relevant = {"target_doc"}

        # Rank 1 -> 1.0
        self.assertEqual(reciprocal_rank(["target_doc", "other"], relevant), 1.0)
        # Rank 2 -> 0.5
        self.assertEqual(reciprocal_rank(["other", "target_doc"], relevant), 0.5)
        # Rank 3 -> 0.333...
        self.assertAlmostEqual(reciprocal_rank(["other1", "other2", "target_doc"], relevant), 0.3333, places=3)
        # Not found -> 0.0
        self.assertEqual(reciprocal_rank(["other1", "other2"], relevant), 0.0)

    def test_ndcg_at_k_calculation(self):
        """Verify nDCG@K ranking discounted metric."""
        relevant = {"doc_1", "doc_2"}

        # Perfect ranking: relevant items first
        perfect_retrieved = ["doc_1", "doc_2", "doc_3", "doc_4"]
        self.assertEqual(ndcg_at_k(perfect_retrieved, relevant, k=4), 1.0)

        # Sub-optimal ranking: relevant items pushed lower
        imperfect_retrieved = ["doc_3", "doc_1", "doc_4", "doc_2"]
        imperfect_score = ndcg_at_k(imperfect_retrieved, relevant, k=4)
        self.assertLess(imperfect_score, 1.0)
        self.assertGreater(imperfect_score, 0.0)

        # Zero hits
        zero_retrieved = ["doc_x", "doc_y"]
        self.assertEqual(ndcg_at_k(zero_retrieved, relevant, k=2), 0.0)

    def test_aggregate_retrieval_metrics(self):
        """Verify macro-average retrieval computation across multiple queries."""
        cases = [
            {"retrieved_documents": ["A", "B"], "relevant_documents": ["A"]},       # P=0.5, R=1.0, RR=1.0
            {"retrieved_documents": ["C", "A"], "relevant_documents": ["A"]},       # P=0.5, R=1.0, RR=0.5
            {"retrieved_documents": ["X", "Y"], "relevant_documents": ["Z"]},       # P=0.0, R=0.0, RR=0.0
        ]
        agg = compute_aggregate_retrieval_metrics(cases, k=2)

        self.assertEqual(agg["evaluated_cases"], 3)
        self.assertAlmostEqual(agg["mrr"], (1.0 + 0.5 + 0.0) / 3.0, places=3)
        self.assertGreater(agg["hit_rate_at_k"], 0.6)

    def test_citation_validity_evaluation(self):
        """Verify detection of valid vs hallucinated [REF-X] citation tags."""
        # Case 1: Valid citations referencing available passages
        ans1 = "According to [REF-1] and verified in [REF-2], oil pressure is stable."
        eval1 = evaluate_citation_validity(ans1, retrieved_citations_count=2)
        self.assertEqual(eval1["validity_rate"], 1.0)
        self.assertEqual(eval1["valid_citations"], 2)

        # Case 2: Hallucinated / out-of-bounds reference tag
        ans2 = "As claimed in [REF-99], the system operates fine."
        eval2 = evaluate_citation_validity(ans2, retrieved_citations_count=2)
        self.assertEqual(eval2["validity_rate"], 0.0)
        self.assertEqual(eval2["invalid_citations"], 1)

    def test_abstention_accuracy_metrics(self):
        """Verify abstention confusion matrix and metrics calculation."""
        cases = [
            {"is_abstention_case": True, "actual_abstained": True},    # TP
            {"is_abstention_case": True, "actual_abstained": True},    # TP
            {"is_abstention_case": False, "actual_abstained": False},  # TN
            {"is_abstention_case": False, "actual_abstained": True},   # FP
            {"is_abstention_case": True, "actual_abstained": False},   # FN
        ]
        res = evaluate_abstention_accuracy(cases)

        self.assertEqual(res["total_evaluated"], 5)
        self.assertEqual(res["true_abstentions"], 2)
        self.assertEqual(res["false_abstentions"], 1)
        self.assertEqual(res["true_answers"], 1)
        self.assertEqual(res["false_answers"], 1)
        self.assertAlmostEqual(res["accuracy"], 3.0 / 5.0)

    def test_benchmark_cases_schema_integrity(self):
        """Verify benchmark test suite has complete schema definitions and balance."""
        cases = get_benchmark_cases()
        self.assertGreaterEqual(len(cases), 30)

        domains = set()
        abstention_count = 0
        for c in cases:
            self.assertIn("id", c)
            self.assertIn("query", c)
            self.assertIn("domain", c)
            self.assertIn("ground_truth_answer", c)
            domains.add(c["domain"])
            if c["is_abstention_case"]:
                abstention_count += 1

        self.assertGreaterEqual(len(domains), 6)
        self.assertGreaterEqual(abstention_count, 6)

    def test_seed_dataset_and_runner_execution(self):
        """Verify seeding institutional corpus and executing benchmark evaluation."""
        temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            db_path = Path(temp_dir.name) / "test_eval.db"
            vault_path = Path(temp_dir.name) / "vault"
            chroma_path = Path(temp_dir.name) / "chroma"
            report_path = Path(temp_dir.name) / "report.json"
            init_database(custom_path=db_path)

            admin = register_user(
                username="eval_admin",
                password="Password@123",
                role="administrator",
                custom_path=db_path
            )

            mock_embed = MockEmbeddingProvider(dimension=384)
            v_store = ChromaVectorStore(persist_dir=chroma_path)

            # Seed documents
            seed_res = seed_demonstration_dataset(
                user_id=admin["id"],
                vault_dir=vault_path,
                custom_path=db_path,
                vector_store=v_store,
                embedding_provider=mock_embed
            )
            self.assertEqual(seed_res["seeded_count"], 6)
            self.assertGreater(seed_res["total_chunks"], 5)

            # Setup RAG engine with MockLLM
            s_retriever = SemanticRetriever(
                vector_store=v_store,
                embedding_provider=mock_embed,
                similarity_threshold=0.10,
                top_k=2
            )
            h_retriever = HybridRetriever(
                semantic_retriever=s_retriever,
                similarity_threshold=0.10,
                top_k=2
            )
            mock_llm = MockLLMClient()
            engine = RAGEngine(
                llm_client=mock_llm,
                retriever=s_retriever,
                similarity_threshold=0.10
            )

            # Run benchmark evaluation
            report = run_benchmark_evaluation(
                user_id=admin["id"],
                username="eval_admin",
                k=2,
                similarity_threshold=0.10,
                semantic_retriever=s_retriever,
                hybrid_retriever=h_retriever,
                rag_engine=engine,
                custom_path=db_path,
                output_path=report_path
            )

            self.assertIn("retrieval_comparison", report)
            self.assertIn("generation_metrics", report)
            self.assertTrue(report_path.is_file())
            v_store.close()

        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
