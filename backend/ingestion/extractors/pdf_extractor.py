"""
NEXUS PDF Document Extractor
Extracts page-by-page text, layout headings, tables, and document metadata
using high-performance PyMuPDF (fitz).
"""

from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF


def extract_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text, page numbers, and tables from a PDF document.
    Returns list of page dicts: [{'page_number': int, 'text': str, 'char_count': int, 'tables': list}]
    """
    doc = fitz.open(str(file_path))
    pages: List[Dict[str, Any]] = []

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

        pages.append({
            "page_number": page_idx,
            "text": combined_text.strip(),
            "char_count": len(combined_text.strip()),
            "has_tables": len(tables_data) > 0
        })

    doc.close()
    return pages
