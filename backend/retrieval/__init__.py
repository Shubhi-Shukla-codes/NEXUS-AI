"""
NEXUS Retrieval Package
Exposes dense semantic, BM25 sparse keyword, and hybrid RRF retrieval engines,
along with institutional domain taxonomy profiles.
"""

from backend.retrieval.retriever import SemanticRetriever, get_default_retriever
from backend.retrieval.bm25 import BM25Index, tokenize_technical_text
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.retrieval.domain_manager import (
    DomainProfile,
    DOMAIN_PROFILES,
    get_domain_profile,
    list_domain_profiles,
    match_domain_by_query
)

__all__ = [
    "SemanticRetriever",
    "get_default_retriever",
    "BM25Index",
    "tokenize_technical_text",
    "HybridRetriever",
    "DomainProfile",
    "DOMAIN_PROFILES",
    "get_domain_profile",
    "list_domain_profiles",
    "match_domain_by_query"
]
