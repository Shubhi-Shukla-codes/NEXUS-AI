"""
NEXUS Hybrid Retrieval Engine
Combines dense semantic vector search (ChromaDB) and sparse keyword search (BM25)
using Reciprocal Rank Fusion (RRF) for optimal conceptual and alphanumeric accuracy.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.config import settings
from backend.storage.vector_store import ChromaVectorStore
from backend.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider
from backend.retrieval.retriever import SemanticRetriever
from backend.retrieval.bm25 import BM25Index
from backend.retrieval.domain_manager import match_domain_by_query
from backend.security.rbac import enforce_permission, AuthorizationError
from backend.security.audit import log_audit_event

logger = logging.getLogger("nexus.hybrid_retriever")

RRF_K = 60  # Standard Reciprocal Rank Fusion smoothing parameter


class HybridRetriever:
    """
    Coordinates Dense Semantic Search and Sparse BM25 Keyword Search
    fused with Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        semantic_retriever: Optional[SemanticRetriever] = None,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        similarity_threshold: float = 0.35,
        top_k: int = 4
    ):
        self.semantic_retriever = semantic_retriever or SemanticRetriever()
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Merge ranked dense and sparse candidate lists using weighted RRF:
        RRF_score(d) = w_dense / (K + rank_dense) + w_sparse / (K + rank_sparse)
        """
        fused_scores: Dict[str, float] = {}
        candidate_map: Dict[str, Dict[str, Any]] = {}

        # 1. Process Dense candidates
        for rank, item in enumerate(dense_results, start=1):
            chunk_id = item.get("chunk_id")
            if not chunk_id:
                continue
            rrf_contrib = self.dense_weight / (RRF_K + rank)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + rrf_contrib
            text_body = item.get("content") or item.get("passage") or ""
            candidate_map[chunk_id] = {
                **item,
                "content": text_body,
                "passage": text_body,
                "dense_rank": rank,
                "dense_score": item.get("similarity_score", item.get("relevance_score", 0.0)),
                "sparse_score": 0.0,
                "sparse_rank": None
            }

        # 2. Process Sparse (BM25) candidates
        for rank, item in enumerate(sparse_results, start=1):
            chunk_id = item.get("chunk_id")
            if not chunk_id:
                continue
            rrf_contrib = self.sparse_weight / (RRF_K + rank)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + rrf_contrib
            text_body = item.get("content") or item.get("passage") or ""

            if chunk_id in candidate_map:
                candidate_map[chunk_id]["sparse_rank"] = rank
                candidate_map[chunk_id]["sparse_score"] = item.get("bm25_score", 0.0)
            else:
                candidate_map[chunk_id] = {
                    **item,
                    "content": text_body,
                    "passage": text_body,
                    "similarity_score": item.get("bm25_score", 0.0),
                    "dense_rank": None,
                    "dense_score": 0.0,
                    "sparse_rank": rank,
                    "sparse_score": item.get("bm25_score", 0.0)
                }

        if not fused_scores:
            return []

        # 3. Sort by combined RRF score
        sorted_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)[:top_k]
        max_rrf = fused_scores[sorted_ids[0]] if sorted_ids else 1.0

        fused_results = []
        for cid in sorted_ids:
            data = candidate_map[cid]
            raw_rrf = fused_scores[cid]
            # Normalize RRF to 0.0 - 1.0 range
            norm_combined = min(1.0, raw_rrf / max_rrf) if max_rrf > 0 else 0.0

            # Combined score reflects hybrid qualification
            data["rrf_raw_score"] = float(raw_rrf)
            data["combined_score"] = float(norm_combined)
            # Retain similarity_score for backward compatibility with RAG prompt
            dense_sc = data.get("dense_score", 0.0)
            sparse_sc = data.get("sparse_score", 0.0)
            effective_sim = max(dense_sc, sparse_sc * 0.8)
            data["similarity_score"] = float(effective_sim)
            data["retrieval_mode"] = "hybrid_rrf"
            fused_results.append(data)

        return fused_results

    def retrieve_hybrid_evidence(
        self,
        query: str,
        user_id: int,
        username: str,
        domain: Optional[str] = None,
        document_id: Optional[int] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        custom_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute full hybrid retrieval pipeline:
        1. RBAC authorization check.
        2. Automatic domain inference if domain='all'.
        3. Parallel execution of Dense and BM25 retrievals.
        4. Reciprocal Rank Fusion.
        5. Token budgeting and structured context formatting.
        """
        # Step 1: RBAC Enforcement
        enforce_permission(user_id, "doc:view", custom_path=custom_path)

        clean_query = query.strip()
        if not clean_query:
            return {
                "query": query,
                "is_sufficient": False,
                "citations": [],
                "context_text": "",
                "message": "Query cannot be empty."
            }

        k = top_k or self.top_k
        sim_threshold = threshold if threshold is not None else self.similarity_threshold

        # Step 2: Domain scope checking / auto-hinting
        target_domain = domain if (domain and domain != "all") else None
        if not target_domain and not document_id:
            inferred = match_domain_by_query(clean_query)
            if inferred:
                logger.info("Heuristic domain inference selected: '%s' for query '%s'", inferred, clean_query)

        # Step 3: Run Dense Semantic Retrieval (Top K * 2 for deeper fusion pool)
        dense_response = self.semantic_retriever.retrieve_evidence(
            query=clean_query,
            user_id=user_id,
            username=username,
            domain=target_domain,
            document_id=document_id,
            top_k=k * 2,
            threshold=0.15,  # Broader threshold for candidate pooling
            custom_path=custom_path
        )
        dense_candidates = dense_response.get("citations", [])

        # Step 4: Run BM25 Sparse Keyword Retrieval from SQLite
        bm25_index = BM25Index.build_from_database(
            domain=target_domain,
            approved_only=True,
            document_id=document_id,
            custom_path=custom_path
        )
        from backend.retrieval.query_expander import expand_query
        search_query, _ = expand_query(clean_query)
        sparse_candidates = bm25_index.search(
            query=search_query,
            top_k=k * 2,
            domain=target_domain
        )

        # Step 5: Reciprocal Rank Fusion
        fused_citations = self._reciprocal_rank_fusion(
            dense_results=dense_candidates,
            sparse_results=sparse_candidates,
            top_k=k
        )

        # Step 6: Threshold evaluation
        qualified_citations = [
            c for c in fused_citations
            if c.get("similarity_score", 0.0) >= sim_threshold
        ]

        is_sufficient = len(qualified_citations) > 0

        # Step 7: Format context blocks
        context_blocks = []
        for i, c in enumerate(qualified_citations, start=1):
            doc_name = c.get("filename", "Unknown")
            page = c.get("page_number", 1)
            score = c.get("similarity_score", 0.0)
            dom = c.get("domain", "General")
            content = c.get("content", "").strip()

            context_blocks.append(
                f"[Evidence Reference #{i} | Document: {doc_name} | Page: {page} | "
                f"Domain: {dom} | Hybrid Score: {score:.2f}]\n{content}"
            )

        assembled_context = "\n---\n".join(context_blocks).strip()

        # Step 8: Log audit record
        log_audit_event(
            event_type="HYBRID_QUERY",
            actor_username=username,
            actor_user_id=user_id,
            description=(
                f"Hybrid search executed: '{clean_query[:50]}' -> "
                f"{len(dense_candidates)} dense, {len(sparse_candidates)} sparse -> "
                f"{len(qualified_citations)} fused citations"
            ),
            metadata={
                "query": clean_query,
                "domain": target_domain,
                "dense_count": len(dense_candidates),
                "sparse_count": len(sparse_candidates),
                "fused_count": len(qualified_citations),
                "is_sufficient": is_sufficient
            },
            custom_path=custom_path
        )

        return {
            "query": clean_query,
            "is_sufficient": is_sufficient,
            "citations": qualified_citations,
            "context_text": assembled_context,
            "total_dense": len(dense_candidates),
            "total_sparse": len(sparse_candidates),
            "similarity_threshold": sim_threshold,
            "domain_scope": target_domain or "all",
            "message": (
                "Sufficient hybrid evidence retrieved from authorized documents."
                if is_sufficient else
                "Insufficient evidence: No indexed passages satisfied the relevance threshold under hybrid search."
            )
        }
