"""
NEXUS Semantic Retrieval Engine
Provides query vectorization, similarity thresholding, Top-K ranking,
permission-aware boundary enforcement, evidence deduplication, and context assembly.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from backend.config import settings
from backend.storage.db import get_db_connection
from backend.storage.vector_store import ChromaVectorStore
from backend.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider
from backend.security.rbac import has_permission, enforce_permission, AuthorizationError
from backend.security.audit import log_audit_event


DEFAULT_SIMILARITY_THRESHOLD = 0.35  # Minimum cosine similarity for evidence qualification
DEFAULT_TOP_K = 4
DEFAULT_CONTEXT_TOKEN_BUDGET = 2048


class SemanticRetriever:
    """
    Orchestrates semantic knowledge retrieval, permission checks,
    and evidence assembly for Grounded RAG.
    """

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        top_k: int = DEFAULT_TOP_K,
        context_token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET
    ):
        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.context_token_budget = context_token_budget

    def _get_permitted_document_ids(
        self,
        user_id: Optional[int],
        custom_path: Optional[Path] = None
    ) -> Optional[Set[int]]:
        """
        Query SQLite for document IDs accessible by the user.
        If user is administrator, returns None (all documents permitted).
        Otherwise checks document_permissions and approved status.
        """
        if not user_id:
            return None

        with get_db_connection(custom_path) as conn:
            cur = conn.cursor()
            # Check if user has administrator role
            cur.execute(
                """
                SELECT r.name FROM roles r
                JOIN user_roles ur ON ur.role_id = r.id
                WHERE ur.user_id = ? AND r.name = 'administrator'
                """,
                (user_id,)
            )
            if cur.fetchone():
                return None  # Admin has global clearance

            # Fetch documents where user or their roles have explicit access OR standard approved docs
            cur.execute(
                """
                SELECT d.id FROM documents d
                WHERE d.status IN ('approved', 'indexed')
                AND (
                    NOT EXISTS (SELECT 1 FROM document_permissions dp WHERE dp.document_id = d.id)
                    OR EXISTS (
                        SELECT 1 FROM document_permissions dp
                        JOIN user_roles ur ON ur.role_id = dp.role_id
                        WHERE dp.document_id = d.id AND ur.user_id = ? AND dp.can_view = 1
                    )
                    OR EXISTS (
                        SELECT 1 FROM document_permissions dp
                        WHERE dp.document_id = d.id AND dp.user_id = ? AND dp.can_view = 1
                    )
                )
                """,
                (user_id, user_id)
            )
            return {row["id"] for row in cur.fetchall()}

    def retrieve_evidence(
        self,
        query: str,
        user_id: Optional[int] = None,
        username: str = "OPERATOR",
        domain: Optional[str] = None,
        document_id: Optional[int] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        approved_only: bool = True,
        custom_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute semantic retrieval pipeline:
        1. Verify user view permissions
        2. Vectorize query
        3. Query ChromaDB with domain/status/document_id filter
        4. Enforce document-level permission access boundary
        5. Filter candidates by similarity threshold
        6. Deduplicate overlapping passages
        7. Assemble context within token budget
        """
        clean_query = query.strip()
        if not clean_query:
            return {
                "query": query,
                "is_sufficient": False,
                "citations": [],
                "context_text": "",
                "total_candidates": 0,
                "message": "Query string is empty."
            }

        # 1. Enforce RBAC permission
        if user_id:
            enforce_permission(user_id, "doc:view", actor_username=username, custom_path=custom_path)

        k = top_k or self.top_k
        sim_threshold = threshold if threshold is not None else self.similarity_threshold

        # Expand query acronyms & state abbreviations (e.g. 'up' -> 'Uttar Pradesh')
        from backend.retrieval.query_expander import expand_query
        search_query, expansions = expand_query(clean_query)

        # 2. Vectorize query
        query_vector = self.embedding_provider.embed_query(search_query)

        # 3. Retrieve candidates from ChromaDB (fetch 2x for post-filtering)
        raw_candidates = self.vector_store.query_similar(
            query_embedding=query_vector,
            top_k=k * 2,
            domain=domain,
            approved_only=approved_only,
            document_id=document_id
        )

        total_candidates_found = len(raw_candidates)

        # 4. Enforce Document Access Permissions
        permitted_doc_ids = self._get_permitted_document_ids(user_id, custom_path=custom_path)
        permission_filtered = []
        for cand in raw_candidates:
            doc_id = cand.get("document_id")
            if permitted_doc_ids is None or (doc_id and doc_id in permitted_doc_ids):
                permission_filtered.append(cand)

        # 5. Filter by Similarity Threshold
        qualified_candidates = [
            c for c in permission_filtered
            if c["similarity_score"] >= sim_threshold
        ]

        # 6. Deduplicate Passages
        seen_passages: Set[str] = set()
        deduped_candidates: List[Dict[str, Any]] = []

        for c in qualified_candidates:
            # Normalize snippet for deduplication
            snippet = " ".join(c["content"].lower().split()[:25])
            if snippet not in seen_passages:
                seen_passages.add(snippet)
                deduped_candidates.append(c)
            if len(deduped_candidates) >= k:
                break

        # 7. Assemble Context within Token Budget
        # Budget estimation: ~4 chars per token
        max_char_budget = self.context_token_budget * 4
        current_char_count = 0
        context_blocks: List[str] = []
        citations: List[Dict[str, Any]] = []

        for idx, c in enumerate(deduped_candidates, start=1):
            chunk_content = c["content"].strip()
            block_header = f"[Evidence Reference {idx} | Source: {c.get('filename')} | Page: {c.get('page_number')} | Domain: {c.get('domain')} | Relevance: {c.get('similarity_score')*100:.1f}%]"
            formatted_block = f"{block_header}\n{chunk_content}\n"

            if current_char_count + len(formatted_block) > max_char_budget:
                break

            context_blocks.append(formatted_block)
            current_char_count += len(formatted_block)

            citations.append({
                "doc_title": c.get("filename"),
                "filename": c.get("filename"),
                "page_number": c.get("page_number", 1),
                "relevance_score": c["similarity_score"],
                "similarity_score": c["similarity_score"],
                "passage": chunk_content,
                "content": chunk_content,
                "domain": c.get("domain"),
                "document_id": c.get("document_id"),
                "chunk_id": c.get("chunk_id"),
                "approved": True
            })

        is_sufficient = len(citations) > 0
        assembled_context = "\n---\n".join(context_blocks).strip()

        # 8. Record Retrieval Audit
        log_audit_event(
            event_type="SEMANTIC_QUERY",
            actor_username=username,
            actor_user_id=user_id,
            description=f"Query executed: '{clean_query[:50]}...' -> {len(citations)} citations assembled (Sufficient: {is_sufficient})",
            metadata={
                "query": clean_query,
                "domain": domain,
                "top_k": k,
                "threshold": sim_threshold,
                "total_candidates": total_candidates_found,
                "qualified_citations": len(citations),
                "is_sufficient": is_sufficient
            },
            custom_path=custom_path
        )

        return {
            "query": clean_query,
            "is_sufficient": is_sufficient,
            "citations": citations,
            "context_text": assembled_context,
            "total_candidates": total_candidates_found,
            "qualified_count": len(citations),
            "similarity_threshold": sim_threshold,
            "domain_scope": domain or "all",
            "message": (
                "Sufficient evidence retrieved from authorized documents."
                if is_sufficient else
                "Insufficient evidence: No indexed document passages satisfied the required relevance threshold."
            )
        }


def get_default_retriever() -> SemanticRetriever:
    """Return a default configured SemanticRetriever instance."""
    return SemanticRetriever()

