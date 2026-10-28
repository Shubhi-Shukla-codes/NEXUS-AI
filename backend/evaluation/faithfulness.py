"""
NEXUS Generation Faithfulness & Citation Evaluator
Measures citation validity, hallucination detection, factual keyword coverage,
and out-of-domain abstention precision.
"""

import re
from typing import List, Dict, Any, Optional, Set


def evaluate_citation_validity(
    answer_text: str,
    retrieved_citations_count: int
) -> Dict[str, Any]:
    """
    Verify that all [REF-X] citation tags in the generated answer
    refer strictly to valid passages provided in the prompt context.
    """
    matches = re.findall(r'\[REF-(\d+)\]', answer_text, flags=re.IGNORECASE)
    total_tags_found = len(matches)

    if total_tags_found == 0:
        return {
            "total_citations": 0,
            "valid_citations": 0,
            "invalid_citations": 0,
            "validity_rate": 1.0,
            "has_citations": False
        }

    valid_count = 0
    invalid_count = 0

    for m in matches:
        try:
            ref_idx = int(m)
            if 1 <= ref_idx <= retrieved_citations_count:
                valid_count += 1
            else:
                invalid_count += 1
        except ValueError:
            invalid_count += 1

    rate = valid_count / float(total_tags_found) if total_tags_found > 0 else 1.0

    return {
        "total_citations": total_tags_found,
        "valid_citations": valid_count,
        "invalid_citations": invalid_count,
        "validity_rate": round(rate, 4),
        "has_citations": True
    }


def evaluate_keyword_coverage(
    answer_text: str,
    relevant_keywords: List[str]
) -> float:
    """
    Measure fraction of essential factual keywords present in the answer text.
    """
    if not relevant_keywords:
        return 1.0

    clean_answer = answer_text.lower()
    matches = sum(1 for kw in relevant_keywords if kw.lower() in clean_answer)
    return round(matches / float(len(relevant_keywords)), 4)


def evaluate_abstention_accuracy(
    eval_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate classification metrics for the abstention policy:
    - Correctly abstaining when evidence is absent (True Positives for Abstention)
    - Correctly answering when evidence is present (True Negatives for Abstention)
    """
    tp = 0  # Expected to abstain and did abstain
    fp = 0  # Expected to answer, but falsely abstained
    tn = 0  # Expected to answer and did answer
    fn = 0  # Expected to abstain, but attempted to answer (hallucination risk)

    for case in eval_cases:
        expected_abstain = case.get("is_abstention_case", False)
        actual_abstain = case.get("actual_abstained", False)

        if expected_abstain and actual_abstain:
            tp += 1
        elif not expected_abstain and actual_abstain:
            fp += 1
        elif not expected_abstain and not actual_abstain:
            tn += 1
        elif expected_abstain and not actual_abstain:
            fn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / float(total) if total > 0 else 0.0
    precision = tp / float(tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / float(tp + fn) if (tp + fn) > 0 else 1.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "true_abstentions": tp,
        "false_abstentions": fp,
        "true_answers": tn,
        "false_answers": fn,
        "total_evaluated": total
    }
