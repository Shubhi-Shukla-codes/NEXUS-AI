"""
NEXUS Retrieval Package
Exposes dense semantic, BM25 sparse keyword, and hybrid RRF retrieval engines,
along with institutional domain taxonomy profiles.
"""

"""
NEXUS Retrieval Package
Exposes dense semantic, BM25 sparse keyword, and hybrid RRF retrieval engines,
along with institutional domain taxonomy profiles.
"""

def __getattr__(name: str):
    if name in ("SemanticRetriever", "get_default_retriever"):
        from backend.retrieval.retriever import SemanticRetriever, get_default_retriever
        val = SemanticRetriever if name == "SemanticRetriever" else get_default_retriever
        globals()[name] = val
        return val
    if name in ("BM25Index", "tokenize_technical_text"):
        from backend.retrieval.bm25 import BM25Index, tokenize_technical_text
        val = BM25Index if name == "BM25Index" else tokenize_technical_text
        globals()[name] = val
        return val
    if name == "HybridRetriever":
        from backend.retrieval.hybrid_retriever import HybridRetriever
        globals()[name] = HybridRetriever
        return HybridRetriever
    if name in ("DomainProfile", "DOMAIN_PROFILES", "get_domain_profile", "list_domain_profiles", "match_domain_by_query"):
        from backend.retrieval import domain_manager
        val = getattr(domain_manager, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__} has no attribute {name}")

