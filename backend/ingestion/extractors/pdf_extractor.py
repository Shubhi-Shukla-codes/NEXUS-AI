"""
NEXUS PDF Document Extractor
Extracts page-by-page text, layout headings, tables, and document metadata
using high-performance PyMuPDF (fitz) with automatic offline OCR fallback
for scanned or vectorized PDF documents.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF

logger = logging.getLogger("nexus.ingestion.pdf")


def extract_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text, page numbers, and tables from a PDF document.
    Automatically applies native offline OCR fallback if pages contain < 30 characters
    (e.g., scanned documents or print-to-pdf vector art).
    Returns list of page dicts: [{'page_number': int, 'text': str, 'char_count': int, 'has_tables': bool, 'ocr_applied': bool}]
    """
    doc = fitz.open(str(file_path))
    pages: List[Dict[str, Any]] = []
    pages_needing_ocr: List[int] = []

    for page_idx, page in enumerate(doc, start=1):
        # Extract text blocks
        text = page.get_text("text").strip()

        # Extract tables if available in PyMuPDF
        tables_data = []
        try:
            tabs = page.find_tables()
            for tab in tabs:
                df = tab.extract()
                if df and len(df) > 1:
                    header = [str(col or "").strip() for col in df[0]]
                    tab_lines = [f"| {' | '.join(header)} |", f"| {' | '.join(['---'] * len(header))} |"]
                    for row in df[1:]:
                        clean_row = [str(val or "").strip() for val in row]
                        tab_lines.append(f"| {' | '.join(clean_row)} |")
                    table_md = "\n".join(tab_lines)
                    tables_data.append(table_md)
        except Exception:
            pass

        # Append table content to text if found
        combined_text = text
        if tables_data:
            combined_text += "\n\n[Extracted Tables]:\n" + "\n\n".join(tables_data)

        combined_text = combined_text.strip()
        pages.append({
            "page_number": page_idx,
            "text": combined_text,
            "char_count": len(combined_text),
            "has_tables": len(tables_data) > 0,
            "ocr_applied": False
        })

        # Flag page for OCR if text is sparse or missing
        if len(combined_text) < 30:
            pages_needing_ocr.append(page_idx - 1)  # 0-indexed for fitz

    doc.close()

    # Trigger offline native OCR fallback for pages lacking text streams
    if pages_needing_ocr:
        try:
            from backend.ingestion.ocr import ocr_pdf_pages_fallback
            logger.info("Applying offline native OCR fallback for %d page(s) in '%s'...", len(pages_needing_ocr), file_path.name)
            ocr_results = ocr_pdf_pages_fallback(file_path, pages_needing_ocr)
            for page_idx_0, ocr_text in ocr_results.items():
                if ocr_text and len(ocr_text.strip()) > 0:
                    clean_ocr = ocr_text.strip()
                    existing_text = pages[page_idx_0]["text"]
                    if existing_text:
                        pages[page_idx_0]["text"] = f"{clean_ocr}\n\n{existing_text}".strip()
                    else:
                        pages[page_idx_0]["text"] = clean_ocr
                    pages[page_idx_0]["char_count"] = len(pages[page_idx_0]["text"])
                    pages[page_idx_0]["ocr_applied"] = True
                    logger.info("OCR successfully extracted %d characters for page %d of '%s'.", len(clean_ocr), page_idx_0 + 1, file_path.name)
        except Exception as ocr_err:
            logger.warning("OCR fallback encountered an error: %s", ocr_err)

    return pages
