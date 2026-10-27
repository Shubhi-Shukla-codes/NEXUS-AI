"""
NEXUS Word DOCX Extractor
Extracts paragraphs, headings, and tabular data using python-docx.
"""

from pathlib import Path
from typing import List, Dict, Any
import docx


def extract_docx(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text, headings, and tables from a DOCX document.
    Since DOCX lacks native page boundaries, groups sections logically by major headings.
    """
    doc = docx.Document(str(file_path))
    sections: List[str] = []
    current_section: List[str] = []

    for para in doc.paragraphs:
        p_text = para.text.strip()
        if not p_text:
            continue

        # Check if heading
        if para.style and para.style.name and para.style.name.startswith("Heading"):
            if current_section:
                sections.append("\n".join(current_section))
                current_section = []
            current_section.append(f"## {p_text}")
        else:
            current_section.append(p_text)

    # Process tables in DOCX
    for table in doc.tables:
        table_rows = []
        for r_idx, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            if r_idx == 0:
                table_rows.append(f"| {' | '.join(cells)} |")
                table_rows.append(f"| {' | '.join(['---'] * len(cells))} |")
            else:
                table_rows.append(f"| {' | '.join(cells)} |")
        if table_rows:
            current_section.append("\n".join(table_rows))

    if current_section:
        sections.append("\n".join(current_section))

    if not sections:
        return []

    pages: List[Dict[str, Any]] = []
    for idx, s_text in enumerate(sections, start=1):
        pages.append({
            "page_number": idx,
            "text": s_text.strip(),
            "char_count": len(s_text.strip())
        })

    return pages
