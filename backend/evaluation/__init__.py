"""
NEXUS Evaluation Package
Exposes benchmark datasets, retrieval metrics calculators, faithfulness evaluators,
corpus seeders, and benchmark execution runners.
"""

from backend.evaluation.benchmark_dataset import (
    BENCHMARK_CASES,
    SEED_DOCUMENTS,
    get_benchmark_cases,
    get_seed_documents
)
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
from backend.evaluation.runner import (
    run_benchmark_evaluation,
    get_latest_evaluation_report
)

__all__ = [
    "BENCHMARK_CASES",
    "SEED_DOCUMENTS",
    "get_benchmark_cases",
    "get_seed_documents",
    "seed_demonstration_dataset",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "dcg_at_k",
    "ndcg_at_k",
    "hit_rate_at_k",
    "compute_aggregate_retrieval_metrics",
    "evaluate_citation_validity",
    "evaluate_keyword_coverage",
    "evaluate_abstention_accuracy",
    "run_benchmark_evaluation",
    "get_latest_evaluation_report"
]
