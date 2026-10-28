"""
NEXUS Structured Table Parser & Extractor
Extracts, structures, and serializes document tables into Markdown and JSON representations,
preserving column header context and tabular matrix integrity for vector/BM25 indexing.
"""

import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.storage.db import get_db_connection

logger = logging.getLogger("nexus.table_parser")


def format_table_as_markdown(headers: List[str], rows: List[List[Any]]) -> str:
    """
    Format headers and 2D row values into standard GitHub Flavored Markdown table.
    """
    if not headers and not rows:
        return ""

    # Clean headers
    clean_headers = [str(h).strip().replace("\n", " ").replace("|", "/") if h else f"Col_{i+1}" for i, h in enumerate(headers)]
    if not clean_headers and rows:
        clean_headers = [f"Col_{i+1}" for i in range(len(rows[0]))]

    header_line = "| " + " | ".join(clean_headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(clean_headers)) + " |"

    row_lines = []
    for row in rows:
        # Pad row if fewer items than headers
        padded_row = list(row) + [""] * max(0, len(clean_headers) - len(row))
        clean_cells = [str(cell).strip().replace("\n", " ").replace("|", "/") for cell in padded_row[:len(clean_headers)]]
        row_lines.append("| " + " | ".join(clean_cells) + " |")

    return "\n".join([header_line, separator_line] + row_lines)


def format_table_as_json_records(headers: List[str], rows: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    Convert 2D tabular matrix into a list of row dictionaries mapping column header to cell value.
    """
    clean_headers = [str(h).strip().replace("\n", " ") if h else f"Col_{i+1}" for i, h in enumerate(headers)]
    records = []

    for row in rows:
        record = {}
        for i, h in enumerate(clean_headers):
            val = row[i] if i < len(row) else ""
            record[h] = str(val).strip()
        records.append(record)

    return records


def extract_tables_from_pdf_page(page: Any) -> List[Dict[str, Any]]:
    """
    Extract all detected tables from a PyMuPDF Page object using built-in table detection.
    """
    extracted_tables = []
    try:
        tabs = page.find_tables()
        for idx, tab in enumerate(tabs):
            raw_header = [h.strip() if h else f"Col_{i+1}" for i, h in enumerate(tab.header.names)]
            raw_rows = tab.extract()

            # Skip empty tables
            if not raw_rows:
                continue

            md_text = format_table_as_markdown(raw_header, raw_rows)
            json_records = format_table_as_json_records(raw_header, raw_rows)

            extracted_tables.append({
                "table_index": idx + 1,
                "row_count": len(raw_rows),
                "col_count": len(raw_header),
                "headers": raw_header,
                "markdown": md_text,
                "json_records": json_records
            })
    except Exception as exc:
        logger.debug("PDF table extraction encountered non-critical notice: %s", exc)

    return extracted_tables


def save_table_asset(
    document_id: int,
    page_number: int,
    table_index: int,
    headers: List[str],
    rows: List[List[Any]],
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Persist structured table into 'document_media' table with JSON metadata.
    """
    media_id = str(uuid.uuid4())
    md_content = format_table_as_markdown(headers, rows)
    records = format_table_as_json_records(headers, rows)

    caption = f"Table #{table_index} (Page {page_number}) - {len(rows)} rows, {len(headers)} cols"
    dims = f"{len(rows)}x{len(headers)}"
    meta_json = json.dumps({
        "table_index": table_index,
        "headers": headers,
        "row_count": len(rows),
        "col_count": len(headers),
        "records": records,
        "markdown": md_content
    })

    with get_db_connection(custom_path) as conn:
        conn.execute(
            """
            INSERT INTO document_media (
                id, document_id, page_number, media_type,
                file_path, caption, dimensions, metadata_json
            ) VALUES (?, ?, ?, 'table', '', ?, ?, ?)
            """,
            (media_id, document_id, page_number, caption, dims, meta_json)
        )

    return {
        "id": media_id,
        "document_id": document_id,
        "page_number": page_number,
        "caption": caption,
        "markdown": md_content,
        "records_count": len(records)
    }
