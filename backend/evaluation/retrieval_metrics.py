"""
NEXUS Information Retrieval Metrics Engine
Calculates standard quantitative IR evaluation metrics:
Precision@K, Recall@K, Mean Reciprocal Rank (MRR), nDCG@K, and Hit Rate.
"""

import math
from typing import List, Dict, Any, Optional, Set


def precision_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 4
) -> float:
    """
    Calculate Precision@K: Proportion of retrieved items in top-K that are relevant.
    """
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / float(k)


def recall_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 4
) -> float:
    """
    Calculate Recall@K: Proportion of all relevant items captured in top-K.
    """
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / float(len(relevant))


def reciprocal_rank(
    retrieved: List[str],
    relevant: Set[str],
    max_k: Optional[int] = None
) -> float:
    """
    Calculate Reciprocal Rank (RR): 1 / rank of the first relevant document.
    Returns 0.0 if no relevant document appears within max_k.
    """
    candidates = retrieved[:max_k] if max_k else retrieved
    for idx, doc in enumerate(candidates, start=1):
        if doc in relevant:
            return 1.0 / float(idx)
    return 0.0


def dcg_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 4
) -> float:
    """
    Calculate Discounted Cumulative Gain (DCG@K) using standard logarithmic discount.
    """
    score = 0.0
    top_k = retrieved[:k]
    for idx, doc in enumerate(top_k, start=1):
        rel = 1.0 if doc in relevant else 0.0
        score += rel / math.log2(idx + 1)
    return score


def ndcg_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 4
) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (nDCG@K).
    """
    if not relevant:
        return 0.0

    actual_dcg = dcg_at_k(retrieved, relevant, k=k)

    # Calculate Ideal DCG (all relevant items ranked at the very top)
    ideal_retrieved = list(relevant)
    ideal_dcg = dcg_at_k(ideal_retrieved, relevant, k=min(k, len(relevant)))

    if ideal_dcg <= 0.0:
        return 0.0
    return actual_dcg / ideal_dcg


def hit_rate_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 4
) -> float:
    """
    Calculate Hit Rate @ K: 1.0 if any relevant item is present in top-K, else 0.0.
    """
    top_k = retrieved[:k]
    return 1.0 if any(doc in relevant for doc in top_k) else 0.0


def compute_aggregate_retrieval_metrics(
    eval_cases: List[Dict[str, Any]],
    k: int = 4
) -> Dict[str, float]:
    """
    Compute aggregate macro-averaged metrics across a list of evaluated cases.
    Each case dictionary must contain:
      - 'retrieved_documents': List[str]
      - 'relevant_documents': Set[str] or List[str]
    """
    if not eval_cases:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "case_count": 0
        }

    p_scores = []
    r_scores = []
    rr_scores = []
    ndcg_scores = []
    hit_scores = []

    for case in eval_cases:
        retrieved = case.get("retrieved_documents", [])
        relevant = set(case.get("relevant_documents", []))

        # Skip cases that have no ground-truth relevant documents (e.g. abstention cases)
        if not relevant:
            continue

        p_scores.append(precision_at_k(retrieved, relevant, k=k))
        r_scores.append(recall_at_k(retrieved, relevant, k=k))
        rr_scores.append(reciprocal_rank(retrieved, relevant, max_k=k))
        ndcg_scores.append(ndcg_at_k(retrieved, relevant, k=k))
        hit_scores.append(hit_rate_at_k(retrieved, relevant, k=k))

    count = len(p_scores)
    if count == 0:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "case_count": 0
        }

    return {
        "precision_at_k": round(sum(p_scores) / count, 4),
        "recall_at_k": round(sum(r_scores) / count, 4),
        "mrr": round(sum(rr_scores) / count, 4),
        "ndcg_at_k": round(sum(ndcg_scores) / count, 4),
        "hit_rate_at_k": round(sum(hit_scores) / count, 4),
        "evaluated_cases": count
    }
