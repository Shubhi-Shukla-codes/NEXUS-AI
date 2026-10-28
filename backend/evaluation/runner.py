"""
NEXUS Evaluation Suite Runner
Executes comprehensive benchmark evaluation comparing Dense vs Hybrid search,
computing information retrieval metrics (P@K, R@K, MRR, nDCG),
and measuring generation faithfulness and abstention accuracy.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from backend.config import settings
from backend.storage.db import get_db_connection
from backend.retrieval.retriever import SemanticRetriever
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.generation.rag_engine import RAGEngine
from backend.generation.ollama_client import MockLLMClient, OllamaClient
from backend.evaluation.benchmark_dataset import get_benchmark_cases
from backend.evaluation.retrieval_metrics import compute_aggregate_retrieval_metrics
from backend.evaluation.faithfulness import (
    evaluate_citation_validity,
    evaluate_keyword_coverage,
    evaluate_abstention_accuracy
)

logger = logging.getLogger("nexus.evaluation_runner")

DEFAULT_REPORT_PATH = settings.paths.data_dir / "evaluation_report.json"


def run_benchmark_evaluation(
    user_id: int,
    username: str = "BENCHMARK_OPERATOR",
    k: int = 4,
    similarity_threshold: float = 0.30,
    semantic_retriever: Optional[SemanticRetriever] = None,
    hybrid_retriever: Optional[HybridRetriever] = None,
    rag_engine: Optional[RAGEngine] = None,
    custom_path: Optional[Path] = None,
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Execute full quantitative benchmark across all defined evaluation cases.
    Evaluates both Dense and Hybrid search modes and generation metrics.
    """
    start_time = time.time()
    cases = get_benchmark_cases()

    s_retriever = semantic_retriever or SemanticRetriever(similarity_threshold=similarity_threshold, top_k=k)
    h_retriever = hybrid_retriever or HybridRetriever(
        semantic_retriever=s_retriever,
        similarity_threshold=similarity_threshold,
        top_k=k
    )

    if not rag_engine:
        # Check if local Ollama is available, else use Mock client
        ollama = OllamaClient()
        llm = ollama if ollama.is_available() else MockLLMClient()
        engine = RAGEngine(llm_client=llm, retriever=s_retriever, similarity_threshold=similarity_threshold)
    else:
        engine = rag_engine

    dense_cases: List[Dict[str, Any]] = []
    hybrid_cases: List[Dict[str, Any]] = []
    generation_cases: List[Dict[str, Any]] = []

    case_details: List[Dict[str, Any]] = []

    for case in cases:
        cid = case["id"]
        query = case["query"]
        domain = case["domain"]
        expected_doc = case.get("expected_document")
        relevant_docs = [expected_doc] if expected_doc else []
        is_abstention = case.get("is_abstention_case", False)
        keywords = case.get("relevant_keywords", [])

        # 1. Evaluate Dense Semantic Retrieval
        dense_res = s_retriever.retrieve_evidence(
            query=query,
            user_id=user_id,
            username=username,
            domain=domain if domain != "all" else None,
            top_k=k,
            threshold=similarity_threshold,
            custom_path=custom_path
        )
        dense_retrieved_docs = [c["filename"] for c in dense_res.get("citations", [])]
        dense_cases.append({
            "retrieved_documents": dense_retrieved_docs,
            "relevant_documents": relevant_docs
        })

        # 2. Evaluate Hybrid RRF Retrieval
        hybrid_res = h_retriever.retrieve_hybrid_evidence(
            query=query,
            user_id=user_id,
            username=username,
            domain=domain if domain != "all" else None,
            top_k=k,
            threshold=similarity_threshold,
            custom_path=custom_path
        )
        hybrid_retrieved_docs = [c["filename"] for c in hybrid_res.get("citations", [])]
        hybrid_cases.append({
            "retrieved_documents": hybrid_retrieved_docs,
            "relevant_documents": relevant_docs
        })

        # 3. Evaluate Grounded RAG Synthesis
        rag_res = engine.answer_query(
            query=query,
            user_id=user_id,
            username=username,
            domain=domain if domain != "all" else None,
            search_mode="hybrid",
            threshold=similarity_threshold,
            custom_path=custom_path
        )

        answer_text = rag_res.get("answer", "")
        abstained = rag_res.get("abstained", False)
        active_citations = rag_res.get("citations", [])

        cite_eval = evaluate_citation_validity(answer_text, len(active_citations))
        kw_cov = evaluate_keyword_coverage(answer_text, keywords) if not is_abstention else 1.0

        gen_record = {
            "id": cid,
            "is_abstention_case": is_abstention,
            "actual_abstained": abstained,
            "citation_validity": cite_eval["validity_rate"],
            "keyword_coverage": kw_cov
        }
        generation_cases.append(gen_record)

        case_details.append({
            "id": cid,
            "query": query,
            "domain": domain,
            "difficulty": case.get("difficulty", "direct_factual"),
            "expected_document": expected_doc,
            "dense_retrieved": dense_retrieved_docs,
            "hybrid_retrieved": hybrid_retrieved_docs,
            "abstained": abstained,
            "keyword_coverage": kw_cov,
            "citation_validity": cite_eval["validity_rate"]
        })

    # Compute aggregate metrics
    dense_metrics = compute_aggregate_retrieval_metrics(dense_cases, k=k)
    hybrid_metrics = compute_aggregate_retrieval_metrics(hybrid_cases, k=k)
    abstention_metrics = evaluate_abstention_accuracy(generation_cases)

    avg_citation_validity = (
        sum(g["citation_validity"] for g in generation_cases) / len(generation_cases)
        if generation_cases else 1.0
    )
    factual_cases = [g for g in generation_cases if not g["is_abstention_case"]]
    avg_keyword_coverage = (
        sum(g["keyword_coverage"] for g in factual_cases) / len(factual_cases)
        if factual_cases else 1.0
    )

    elapsed_seconds = round(time.time() - start_time, 2)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": elapsed_seconds,
        "total_cases_evaluated": len(cases),
        "factual_cases": len(factual_cases),
        "abstention_cases": len(cases) - len(factual_cases),
        "top_k": k,
        "similarity_threshold": similarity_threshold,
        "retrieval_comparison": {
            "dense_semantic": dense_metrics,
            "hybrid_rrf": hybrid_metrics
        },
        "generation_metrics": {
            "abstention_accuracy": abstention_metrics["accuracy"],
            "abstention_precision": abstention_metrics["precision"],
            "abstention_recall": abstention_metrics["recall"],
            "citation_validity_rate": round(avg_citation_validity, 4),
            "factual_keyword_coverage": round(avg_keyword_coverage, 4)
        },
        "case_details": case_details
    }

    # Save to disk
    save_path = output_path or DEFAULT_REPORT_PATH
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Evaluation report saved to: %s in %ss", save_path, elapsed_seconds)
    return report


def get_latest_evaluation_report(report_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load latest evaluation report JSON from disk if available."""
    target_path = report_path or DEFAULT_REPORT_PATH
    if not target_path.is_file():
        return None
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not read evaluation report from '%s': %s", target_path, exc)
        return None
