"""
NEXUS Text Cleaning Engine
Provides sanitization, hyphenation normalization, whitespace standardization,
and structural preservation for technical documents.
"""

import re
from typing import List, Dict, Any, Optional


def clean_text(text: str) -> str:
    """
    Perform structural cleaning on raw extracted text:
    - Normalizes non-breaking spaces and irregular whitespace
    - Recombines broken hyphenated words at line breaks (e.g. 'com-\nponent' -> 'component')
    - Removes unprintable ASCII control characters (preserving tabs and newlines)
    - Normalizes repeated consecutive blank lines
    """
    if not text:
        return ""

    # Replace non-breaking spaces and zero-width spaces
    cleaned = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")

    # Remove non-printable control characters (except \n, \r, \t)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    # Recombine hyphenated word splits across line boundaries: 'con-\nnection' -> 'connection'
    cleaned = re.sub(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)", r"\1\2", cleaned)

    # Standardize Windows CRLF to LF
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse excessive horizontal spaces and tabs on a line
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    # Collapse 3 or more consecutive newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def remove_repetitive_headers_footers(
    pages: List[Dict[str, Any]],
    threshold_ratio: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Detect and strip recurring running headers and footers across pages.
    If a header or footer string appears on >= threshold_ratio of all pages,
    it is considered boilerplate and purged.
    """
    if len(pages) < 3:
        return pages

    first_lines: Dict[str, int] = {}
    last_lines: Dict[str, int] = {}
    total_pages = len(pages)

    for p in pages:
        lines = [line.strip() for line in p.get("text", "").split("\n") if line.strip()]
        if lines:
            first = lines[0]
            last = lines[-1]
            first_lines[first] = first_lines.get(first, 0) + 1
            last_lines[last] = last_lines.get(last, 0) + 1

    common_headers = {
        line for line, count in first_lines.items()
        if (count / total_pages) >= threshold_ratio and len(line) < 120
    }
    common_footers = {
        line for line, count in last_lines.items()
        if (count / total_pages) >= threshold_ratio and len(line) < 120
    }

    if not common_headers and not common_footers:
        return pages

    cleaned_pages = []
    for p in pages:
        lines = [line.strip() for line in p.get("text", "").split("\n") if line.strip()]
        if lines and lines[0] in common_headers:
            lines = lines[1:]
        if lines and lines[-1] in common_footers:
            lines = lines[:-1]
        
        cleaned_pages.append({
            **p,
            "text": "\n".join(lines).strip()
        })

    return cleaned_pages
