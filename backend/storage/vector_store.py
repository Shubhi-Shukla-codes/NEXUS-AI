"""
NEXUS Vector Storage Engine (ChromaDB Integration)
Provides persistent on-disk embedding storage, cosine distance indexing,
metadata filtering (domain, approval state), and relational synchronization.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider
from backend.storage.db import get_db_connection
from backend.security.audit import log_audit_event

COLLECTION_NAME = "nexus_knowledge_vault"


class ChromaVectorStore:
    """
    Local ChromaDB vector database manager with disk persistence.
    Operates in-process without requiring external servers.
    """

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or settings.paths.vector_store_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    def _get_collection(self):
        """Lazy load persistent Chroma client and collection."""
        if self._collection is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            # Create or get collection with cosine distance metric
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        document_metadata: Dict[str, Any]
    ) -> int:
        """
        Add or update chunk vectors in the persistent collection.
        Chunks input: list of dicts with id, page_number, content, token_count, etc.
        """
        if not chunks or not embeddings or len(chunks) != len(embeddings):
            return 0

        collection = self._get_collection()

        ids = []
        documents = []
        metadatas = []

        doc_id = document_metadata.get("id")
        domain = document_metadata.get("domain", "general").lower()
        status = document_metadata.get("status", "pending").lower()
        filename = document_metadata.get("filename", "")

        for chunk, emb in zip(chunks, embeddings):
            c_id = str(chunk["id"])
            ids.append(c_id)
            documents.append(chunk["content"])
            metadatas.append({
                "document_id": int(doc_id),
                "page_number": int(chunk.get("page_number", 1)),
                "domain": domain,
                "status": status,
                "filename": filename,
                "char_length": int(chunk.get("char_length", len(chunk["content"]))),
                "token_count": int(chunk.get("token_count", 0))
            })

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return len(ids)

    def delete_document_vectors(self, document_id: int) -> int:
        """Purge all vector embeddings associated with a document ID."""
        collection = self._get_collection()
        try:
            # Query IDs belonging to this document
            results = collection.get(
                where={"document_id": int(document_id)},
                include=["metadatas"]
            )
            matching_ids = results.get("ids", [])
            if matching_ids:
                collection.delete(ids=matching_ids)
                return len(matching_ids)
            return 0
        except Exception:
            return 0

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        domain: Optional[str] = None,
        approved_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search vector collection using cosine similarity.
        Applies domain and approval state metadata filters.
        """
        collection = self._get_collection()

        where_filter: Dict[str, Any] = {}
        conditions = []

        if approved_only:
            conditions.append({"status": {"$in": ["approved", "indexed"]}})

        if domain and domain != "all":
            conditions.append({"domain": domain.lower()})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        # Execute query
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )

        matches: List[Dict[str, Any]] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return matches

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for c_id, content, meta, dist in zip(ids, docs, metas, distances):
            # Convert cosine distance to cosine similarity score [0.0, 1.0]
            # In Chroma with hnsw:space=cosine, distance = 1 - cosine_similarity
            sim_score = max(0.0, min(1.0, 1.0 - dist))
            matches.append({
                "chunk_id": c_id,
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename"),
                "page_number": meta.get("page_number", 1),
                "domain": meta.get("domain", "general"),
                "status": meta.get("status", "approved"),
                "content": content,
                "similarity_score": round(sim_score, 4),
                "distance": round(dist, 4)
            })

        return matches

    def count_vectors(self) -> int:
        """Return total number of vector embeddings in collection."""
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def close(self):
        """Release Chroma client handles and run garbage collection."""
        self._collection = None
        self._client = None
        import gc
        gc.collect()


def index_document_in_vector_store(
    document_id: int,
    embedding_provider: Optional[BaseEmbeddingProvider] = None,
    vector_store: Optional[ChromaVectorStore] = None,
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    High-level service function: retrieves document chunks from SQLite,
    generates embeddings in batches, and indexes them in ChromaDB.
    """
    store = vector_store or ChromaVectorStore()
    embedder = embedding_provider or get_embedding_provider()

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, filename, title, domain, status
            FROM documents WHERE id = ?
            """,
            (document_id,)
        )
        doc = cur.fetchone()
        if not doc:
            raise ValueError(f"Document ID #{document_id} not found.")

        doc_meta = dict(doc)

        cur.execute(
            """
            SELECT id, document_id, page_number, chunk_index,
                   content, char_length, token_count
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY chunk_index ASC
            """,
            (document_id,)
        )
        chunks = [dict(r) for r in cur.fetchall()]

    if not chunks:
        return {"document_id": document_id, "indexed_chunks": 0, "message": "No chunks found to index."}

    # Generate embeddings in batches of 16
    texts = [c["content"] for c in chunks]
    embeddings = embedder.embed_texts(texts, batch_size=16)

    # Upsert into ChromaDB
    indexed_count = store.index_chunks(
        chunks=chunks,
        embeddings=embeddings,
        document_metadata=doc_meta
    )

    # Update document status to 'indexed' if approved
    if doc_meta["status"] == "approved":
        with get_db_connection(custom_path) as conn:
            conn.execute(
                "UPDATE documents SET status = 'indexed' WHERE id = ?",
                (document_id,)
            )

    log_audit_event(
        event_type="VECTOR_INDEX_SUCCESS",
        actor_username="VECTOR_ENGINE",
        description=f"Indexed {indexed_count} chunks in ChromaDB for document #{document_id} ('{doc_meta['filename']}')",
        metadata={
            "document_id": document_id,
            "indexed_chunks": indexed_count,
            "model": embedder.model_name
        },
        custom_path=custom_path
    )

    return {
        "document_id": document_id,
        "indexed_chunks": indexed_count,
        "model_name": embedder.model_name,
        "status": "indexed" if doc_meta["status"] == "approved" else doc_meta["status"]
    }
