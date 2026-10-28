"""
NEXUS Ingestion Package
Exposes text extraction, cleaning, structure-aware chunking,
table parsing, diagram extraction, and multimodal pipelines.
"""

from backend.ingestion.cleaner import clean_text, remove_repetitive_headers_footers
from backend.ingestion.chunker import chunk_document_pages, generate_chunk_id, split_text_into_chunks
from backend.ingestion.pipeline import process_document, extract_document_pages
from backend.ingestion.table_parser import (
    format_table_as_markdown,
    format_table_as_json_records,
    extract_tables_from_pdf_page,
    save_table_asset
)
from backend.ingestion.multimodal import (
    extract_images_from_pdf_page,
    is_scanned_page,
    list_document_media,
    get_ocr_engine,
    BaseOCREngine,
    FallbackVisualDescriptor
)

__all__ = [
    "clean_text",
    "remove_repetitive_headers_footers",
    "chunk_document_pages",
    "generate_chunk_id",
    "split_text_into_chunks",
    "process_document",
    "extract_document_pages",
    "format_table_as_markdown",
    "format_table_as_json_records",
    "extract_tables_from_pdf_page",
    "save_table_asset",
    "extract_images_from_pdf_page",
    "is_scanned_page",
    "list_document_media",
    "get_ocr_engine",
    "BaseOCREngine",
    "FallbackVisualDescriptor"
]
