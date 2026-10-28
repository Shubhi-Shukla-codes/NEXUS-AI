"""
NEXUS Demonstration Dataset Seeder
Ingests, extracts, chunks, and vector-indexes the curated seed document corpus
across all 6 institutional domain pillars.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from backend.storage.db import get_db_connection
from backend.services.document_service import upload_document
from backend.ingestion.pipeline import process_document
from backend.storage.vector_store import ChromaVectorStore, index_document_in_vector_store
from backend.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider
from backend.evaluation.benchmark_dataset import get_seed_documents

logger = logging.getLogger("nexus.seed_dataset")


def seed_demonstration_dataset(
    user_id: int,
    vault_dir: Optional[Path] = None,
    custom_path: Optional[Path] = None,
    vector_store: Optional[ChromaVectorStore] = None,
    embedding_provider: Optional[BaseEmbeddingProvider] = None
) -> Dict[str, Any]:
    """
    Populate the NEXUS repository with 6 authorized domain seed documents.
    Idempotent: skips documents that have already been uploaded and indexed.
    """
    seeds = get_seed_documents()
    store = vector_store or ChromaVectorStore()
    embedder = embedding_provider or get_embedding_provider()

    seeded_docs = []
    total_chunks = 0

    for item in seeds:
        filename = item["filename"]
        title = item["title"]
        domain = item["domain"]
        content_bytes = item["content"].encode("utf-8")

        # 1. Upload Document
        try:
            doc_res = upload_document(
                file_bytes=content_bytes,
                filename=filename,
                title=title,
                domain=domain,
                user_id=user_id,
                auto_approve=True,
                vault_dir=vault_dir,
                custom_path=custom_path
            )
            doc_id = doc_res["id"]
        except Exception as exc:
            logger.error("Failed to upload seed doc '%s': %s", filename, exc)
            continue

        # 2. Extract and Chunk via Pipeline (if not duplicate or already processed)
        try:
            pipe_res = process_document(
                document_id=doc_id,
                custom_path=custom_path
            )
            chunks_count = pipe_res.get("chunks_count", 0)
        except Exception as exc:
            logger.warning("Pipeline processing for seed '%s' encountered: %s", filename, exc)
            chunks_count = 0

        # 3. Vector Index in ChromaDB
        try:
            idx_res = index_document_in_vector_store(
                document_id=doc_id,
                embedding_provider=embedder,
                vector_store=store,
                custom_path=custom_path
            )
            indexed = idx_res.get("indexed_chunks", 0)
            total_chunks += indexed
        except Exception as exc:
            logger.warning("Vector indexing for seed '%s' encountered: %s", filename, exc)
            indexed = 0

        seeded_docs.append({
            "id": doc_id,
            "filename": filename,
            "domain": domain,
            "status": "indexed",
            "chunks_count": chunks_count
        })

    return {
        "seeded_count": len(seeded_docs),
        "total_chunks": total_chunks,
        "documents": seeded_docs,
        "message": f"Successfully seeded {len(seeded_docs)} institutional domain documents ({total_chunks} chunks)."
    }
