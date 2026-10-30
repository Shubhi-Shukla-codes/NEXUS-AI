"""
NEXUS Citation & Provenance Component
Renders evidence-grounded source citations, page numbers, similarity metrics,
and expandable passage content.
"""

import html
import streamlit as st
from typing import Dict, Any, List
from frontend.components.icons import (
    get_icon_svg,
    ICON_COLOR_GOLD,
    ICON_COLOR_SUCCESS,
    ICON_COLOR_WARNING,
    ICON_COLOR_MUTED_GOLD
)


def render_citation_card(citation: Dict[str, Any], index: int = 1) -> None:
    """
    Render a structured citation card.
    Expected keys:
      - doc_title: str
      - filename: str
      - page_number: int or str
      - relevance_score: float (0.0 to 1.0)
      - passage: str
      - domain: str
      - approved: bool
    """
    raw_title = citation.get("doc_title") or citation.get("filename", "Unknown Document")
    doc_title = html.escape(str(raw_title))
    filename = html.escape(str(citation.get("filename", "")))
    page = html.escape(str(citation.get("page_number", "N/A")))
    score = citation.get("relevance_score", 0.0)
    passage = html.escape(str(citation.get("passage", "")).strip())
    domain = html.escape(str(citation.get("domain", "GENERAL")).upper())
    approved = citation.get("approved", True)

    score_pct = f"{score * 100:.1f}%" if isinstance(score, (int, float)) else str(score)
    if approved:
        v_ico = get_icon_svg("circle_check", size=13, color=ICON_COLOR_SUCCESS)
        approval_badge = f'<span style="color:#A5D6A7; font-size:var(--font-size-meta); font-family:var(--font-mono); font-weight:600; display:inline-flex; align-items:center; gap:4px;">{v_ico} [VERIFIED]</span>'
    else:
        w_ico = get_icon_svg("triangle_alert", size=13, color=ICON_COLOR_WARNING)
        approval_badge = f'<span style="color:#F9E79F; font-size:var(--font-size-meta); font-family:var(--font-mono); font-weight:600; display:inline-flex; align-items:center; gap:4px;">{w_ico} [UNAPPROVED]</span>'

    doc_ico = get_icon_svg("file_text", size=15, color=ICON_COLOR_GOLD)
    st.markdown(
        f"""
        <div class="nexus-citation-card">
            <div class="nexus-citation-title">
                <span style="color:#B49A5A; font-family:var(--font-mono); font-weight:700;">[{index}]</span>
                <span style="color:#F4F2E9; font-weight:700; font-family:var(--font-display); display:inline-flex; align-items:center; gap:6px;">{doc_ico} {doc_title}</span>
                <span style="color:#C3B091; font-size:var(--font-size-meta); font-family:var(--font-body);">(Page {page})</span>
                {approval_badge}
                <span style="margin-left:auto; font-family:var(--font-mono); font-size:var(--font-size-meta); color:#A5D6A7;">
                    RELEVANCE: {score_pct}
                </span>
            </div>
            <div style="font-size:var(--font-size-meta); color:#8C9B8E; margin-top:4px; font-family:var(--font-mono);">
                SOURCE: {filename} // DOMAIN: {domain}
            </div>
            <div class="nexus-citation-passage">
                "{passage}"
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_citations_list(citations: List[Dict[str, Any]]) -> None:
    """Render an expandable accordion list of citations."""
    if not citations:
        return
    with st.expander(f"Verified Source Citations ({len(citations)} Reference{'s' if len(citations) != 1 else ''})", expanded=False):
        for idx, cit in enumerate(citations, 1):
            render_citation_card(cit, index=idx)
