"""
NEXUS Controlled Re-indexing Engine
Provides administrator-controlled synchronization and full re-indexing
between SQLite relational document chunks and ChromaDB vector collections.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from backend.storage.db import get_db_connection
from backend.storage.vector_store import ChromaVectorStore, index_document_in_vector_store
from backend.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider
from backend.security.audit import log_audit_event


def reindex_all_approved_documents(
    embedding_provider: Optional[BaseEmbeddingProvider] = None,
    vector_store: Optional[ChromaVectorStore] = None,
    actor_username: str = "ADMINISTRATOR",
    actor_user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Perform controlled full re-indexing of all approved documents.
    Used when changing embedding models or repairing vector storage.
    """
    store = vector_store or ChromaVectorStore()
    embedder = embedding_provider or get_embedding_provider()

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, filename, title
            FROM documents
            WHERE status IN ('approved', 'indexed')
            ORDER BY id ASC
            """
        )
        approved_docs = cur.fetchall()

    total_docs = len(approved_docs)
    total_chunks_indexed = 0

    for doc in approved_docs:
        doc_id = doc["id"]
        # Clear existing vectors for document to prevent duplicate accumulation
        store.delete_document_vectors(doc_id)
        # Re-index chunks
        res = index_document_in_vector_store(
            document_id=doc_id,
            embedding_provider=embedder,
            vector_store=store,
            custom_path=custom_path
        )
        total_chunks_indexed += res["indexed_chunks"]

    log_audit_event(
        event_type="REINDEX_ALL_COMPLETE",
        actor_username=actor_username,
        actor_user_id=actor_user_id,
        description=f"Completed full re-indexing: {total_docs} documents, {total_chunks_indexed} vectors ({embedder.model_name})",
        metadata={
            "total_documents": total_docs,
            "total_chunks_indexed": total_chunks_indexed,
            "model_name": embedder.model_name
        },
        custom_path=custom_path
    )

    return {
        "status": "success",
        "total_documents": total_docs,
        "total_chunks_indexed": total_chunks_indexed,
        "embedding_model": embedder.model_name
    }
