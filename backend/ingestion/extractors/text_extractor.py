"""
NEXUS Plaintext & Semi-Structured Data Extractor
Extracts text from TXT, Markdown, CSV, and JSON files, preserving page/section offsets.
"""

import json
import csv
import io
from pathlib import Path
from typing import List, Dict, Any


def extract_plaintext(file_path: Path) -> List[Dict[str, Any]]:
    """Extract plain text from .txt or .md files."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # If the file contains markdown headings, we can identify them
    return [{
        "page_number": 1,
        "text": content,
        "char_count": len(content)
    }]


def extract_csv(file_path: Path) -> List[Dict[str, Any]]:
    """Extract tabular CSV data into structured text representation."""
    pages = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return []

    header = rows[0]
    # Format rows in groups of 50 rows per 'page'
    page_size = 50
    current_page = 1

    for i in range(1, len(rows), page_size):
        chunk_rows = rows[i:i + page_size]
        text_lines = [f"Table Headers: {', '.join(header)}"]
        for r_idx, row in enumerate(chunk_rows, start=i):
            row_repr = " | ".join(f"{h}: {val}" for h, val in zip(header, row) if val.strip())
            text_lines.append(f"Row {r_idx}: {row_repr}")

        page_text = "\n".join(text_lines)
        pages.append({
            "page_number": current_page,
            "text": page_text,
            "char_count": len(page_text)
        })
        current_page += 1

    if not pages:
        # Header only
        pages.append({
            "page_number": 1,
            "text": f"Table Headers: {', '.join(header)} (No rows)",
            "char_count": len(header)
        })

    return pages


def extract_json(file_path: Path) -> List[Dict[str, Any]]:
    """Extract JSON documents into human-readable, semantic text representation."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    def serialize_obj(obj: Any, indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}{k}:")
                    lines.append(serialize_obj(v, indent + 1))
                else:
                    lines.append(f"{prefix}{k}: {v}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[Item {idx + 1}]:")
                    lines.append(serialize_obj(item, indent + 1))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{obj}")
        return "\n".join(lines)

    text_repr = serialize_obj(data)
    return [{
        "page_number": 1,
        "text": text_repr,
        "char_count": len(text_repr)
    }]
