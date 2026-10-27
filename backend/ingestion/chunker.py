"""
NEXUS Structure-Aware Chunking Engine
Splits extracted document pages into coherent, contextual chunks with page-boundary
preservation, heading awareness, and deterministic chunk UUIDs.
"""

import uuid
import re
from typing import List, Dict, Any, Optional
from backend.config import settings


def generate_chunk_id(document_id: int, page_number: int, chunk_index: int) -> str:
    """Generate a deterministic UUIDv5 for consistent vector store references."""
    seed = f"nexus_doc_{document_id}_p{page_number}_c{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def estimate_token_count(text: str) -> int:
    """Approximate token count for low-resource CPU profiling (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def split_text_into_chunks(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    heading_context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Split text into sliding window passages, breaking preferentially at paragraph
    or sentence boundaries.
    """
    if not text or len(text.strip()) == 0:
        return []

    # If text is already smaller than chunk size, return as single chunk
    if len(text) <= chunk_size:
        full_content = f"[{heading_context}]\n{text}" if heading_context else text
        return [{
            "content": full_content.strip(),
            "char_length": len(full_content.strip()),
            "token_count": estimate_token_count(full_content)
        }]

    # Paragraph-aware split
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[Dict[str, Any]] = []
    current_chunk = ""

    for para in paragraphs:
        # If adding paragraph fits inside chunk_size
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
        else:
            # Current chunk has enough content
            if current_chunk:
                content_with_hdr = f"[{heading_context}]\n{current_chunk}" if heading_context else current_chunk
                chunks.append({
                    "content": content_with_hdr.strip(),
                    "char_length": len(content_with_hdr.strip()),
                    "token_count": estimate_token_count(content_with_hdr)
                })

            # If the paragraph itself exceeds chunk_size, split by sentences or sliding window
            if len(para) > chunk_size:
                start = 0
                while start < len(para):
                    end = min(start + chunk_size, len(para))
                    # Try to break at a sentence boundary if possible
                    if end < len(para):
                        last_period = para.rfind(". ", start, end)
                        if last_period > start + (chunk_size // 2):
                            end = last_period + 1

                    sub_text = para[start:end].strip()
                    if sub_text:
                        content_with_hdr = f"[{heading_context}]\n{sub_text}" if heading_context else sub_text
                        chunks.append({
                            "content": content_with_hdr.strip(),
                            "char_length": len(content_with_hdr.strip()),
                            "token_count": estimate_token_count(content_with_hdr)
                        })
                    start += (chunk_size - chunk_overlap)
                current_chunk = ""
            else:
                current_chunk = para

    # Flush remaining text
    if current_chunk:
        content_with_hdr = f"[{heading_context}]\n{current_chunk}" if heading_context else current_chunk
        chunks.append({
            "content": content_with_hdr.strip(),
            "char_length": len(content_with_hdr.strip()),
            "token_count": estimate_token_count(content_with_hdr)
        })

    return chunks


def chunk_document_pages(
    document_id: int,
    pages: List[Dict[str, Any]],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Structure-aware chunking preserving exact page numbers and stable IDs.
    Input pages: list of dicts with 'page_number' and 'text'.
    Output chunks: list of dicts with id, document_id, page_number, chunk_index,
                   content, char_length, token_count.
    """
    c_size = chunk_size or settings.ingestion.chunk_size
    c_overlap = chunk_overlap or settings.ingestion.chunk_overlap

    all_chunks: List[Dict[str, Any]] = []
    chunk_counter = 0

    for p in pages:
        page_num = p.get("page_number", 1)
        raw_text = p.get("text", "").strip()
        heading = p.get("heading")

        if not raw_text:
            continue

        page_chunks = split_text_into_chunks(
            text=raw_text,
            chunk_size=c_size,
            chunk_overlap=c_overlap,
            heading_context=heading
        )

        for pc in page_chunks:
            chunk_id = generate_chunk_id(document_id, page_num, chunk_counter)
            all_chunks.append({
                "id": chunk_id,
                "document_id": document_id,
                "page_number": page_num,
                "chunk_index": chunk_counter,
                "content": pc["content"],
                "char_length": pc["char_length"],
                "token_count": pc["token_count"]
            })
            chunk_counter += 1

    return all_chunks
