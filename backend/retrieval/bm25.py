"""
NEXUS BM25 Sparse Keyword Retrieval Engine
Self-contained, high-performance BM25Okapi implementation tailored for technical,
military, and emergency terminology (preserves hyphens and alphanumeric codes like B-12, MIL-STD-810G).
"""

import re
import math
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from backend.storage.db import get_db_connection

logger = logging.getLogger("nexus.bm25")

# Stopwords set to filter non-substantive grammatical tokens from BM25 scoring
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for", 
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", 
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", 
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", 
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", 
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", 
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", 
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", 
    "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself", "yourselves"
}

# Tokenizer pattern preserving technical hyphenated codes and alphanumeric tokens
TOKEN_PATTERN = re.compile(r'\b[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\b')


def tokenize_technical_text(text: str) -> List[str]:
    """
    Tokenize text into lowercase terms, preserving compound technical terms,
    model numbers, and alphanumeric codes (e.g. 'b-12', 'mil-std-810g', 'ip67').
    """
    if not text:
        return []
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


class BM25Index:
    """
    BM25Okapi sparse search index with technical tokenization and SQLite synchronization.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_ids: List[str] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.corpus_size: int = 0
        self.inverted_index: Dict[str, Dict[int, int]] = defaultdict(dict)  # token -> {doc_idx: freq}
        self.doc_frequencies: Dict[str, int] = Counter()  # token -> num_docs_containing
        self.idf_cache: Dict[str, float] = {}

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index a collection of passage dictionaries.
        Each dictionary must have 'chunk_id', 'content', and optional metadata.
        """
        self.doc_ids = []
        self.doc_metadata = []
        self.doc_lengths = []
        self.inverted_index = defaultdict(dict)
        self.doc_frequencies = Counter()
        self.idf_cache = {}

        self.corpus_size = len(documents)
        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return

        total_length = 0
        for idx, doc in enumerate(documents):
            chunk_id = doc.get("chunk_id", str(idx))
            content = doc.get("content", "")
            tokens = tokenize_technical_text(content)
            doc_len = len(tokens)

            self.doc_ids.append(chunk_id)
            self.doc_metadata.append(doc)
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            term_counts = Counter(tokens)
            for token, freq in term_counts.items():
                self.inverted_index[token][idx] = freq
                self.doc_frequencies[token] += 1

        self.avg_doc_len = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

        # Precalculate IDFs for all observed terms
        for token, df in self.doc_frequencies.items():
            # Standard Okapi IDF with +1.0 floor smoothing
            self.idf_cache[token] = math.log(
                (self.corpus_size - df + 0.5) / (df + 0.5) + 1.0
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
        domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Score and rank indexed chunks against a technical query.
        Returns Top-K matches with BM25 scores.
        """
        if self.corpus_size == 0 or not query.strip():
            return []

        query_tokens = [t for t in tokenize_technical_text(query) if t not in STOPWORDS]
        if not query_tokens:
            return []

        scores: Dict[int, float] = defaultdict(float)

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            idf = self.idf_cache.get(token, 0.0)
            postings = self.inverted_index[token]

            for doc_idx, freq in postings.items():
                # Apply domain filtering if requested
                if domain and domain != "all":
                    doc_domain = self.doc_metadata[doc_idx].get("domain")
                    if doc_domain != domain:
                        continue

                doc_len = self.doc_lengths[doc_idx]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                scores[doc_idx] += idf * (numerator / denominator)

        if not scores:
            return []

        # Sort candidate doc indices by score descending
        sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        max_score = sorted_candidates[0][1] if sorted_candidates else 1.0

        results = []
        for doc_idx, raw_score in sorted_candidates:
            meta = self.doc_metadata[doc_idx]
            # Normalized score scaled against max score in result set
            norm_score = raw_score / max_score if max_score > 0 else 0.0
            results.append({
                "chunk_id": self.doc_ids[doc_idx],
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename", "unknown"),
                "page_number": meta.get("page_number", 1),
                "domain": meta.get("domain", "general"),
                "content": meta.get("content", ""),
                "passage": meta.get("content", ""),
                "bm25_raw_score": float(raw_score),
                "bm25_score": float(norm_score),
                "retrieval_mode": "bm25_sparse"
            })

        return results

    @classmethod
    def build_from_database(
        cls,
        domain: Optional[str] = None,
        approved_only: bool = True,
        document_id: Optional[int] = None,
        custom_path: Optional[Path] = None
    ) -> "BM25Index":
        """
        Instantiate and index directly from the active SQLite database.
        """
        index = cls()
        conditions = []
        params = []
        if domain and domain != "all":
            conditions.append("d.domain = ?")
            params.append(domain)
        if document_id is not None:
            conditions.append("c.document_id = ?")
            params.append(document_id)
        if approved_only:
            conditions.append("d.status IN ('approved', 'indexed')")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT c.id as chunk_id, c.document_id, c.page_number, c.content,
                   d.filename, d.domain, d.status
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            {where_clause}
        """
        with get_db_connection(custom_path) as conn:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

        documents = [
            {
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "page_number": r["page_number"],
                "content": r["content"],
                "filename": r["filename"],
                "domain": r["domain"],
                "status": r["status"]
            }
            for r in rows
        ]

        index.index_documents(documents)
        return index
