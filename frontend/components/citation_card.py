"""
NEXUS Citation & Provenance Component
Renders evidence-grounded source citations, page numbers, similarity metrics,
and expandable passage content.
"""

import streamlit as st
from typing import Dict, Any, List


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
    doc_title = citation.get("doc_title") or citation.get("filename", "Unknown Document")
    filename = citation.get("filename", "")
    page = citation.get("page_number", "N/A")
    score = citation.get("relevance_score", 0.0)
    passage = citation.get("passage", "").strip()
    domain = citation.get("domain", "GENERAL").upper()
    approved = citation.get("approved", True)

    score_pct = f"{score * 100:.1f}%" if isinstance(score, (int, float)) else str(score)
    approval_badge = (
        '<span style="color:#A5D6A7; font-size:0.7rem; font-family:Consolas,monospace;">[VERIFIED]</span>'
        if approved else
        '<span style="color:#F9E79F; font-size:0.7rem; font-family:Consolas,monospace;">[UNAPPROVED]</span>'
    )

    st.markdown(
        f"""
        <div class="nexus-citation-card">
            <div class="nexus-citation-title">
                <span style="color:#B49A5A; font-family:Consolas,monospace;">[{index}]</span>
                <span style="color:#F4F2E9; font-weight:700;">{doc_title}</span>
                <span style="color:#C3B091; font-size:0.8rem;">(Page {page})</span>
                {approval_badge}
                <span style="margin-left:auto; font-family:Consolas,monospace; font-size:0.75rem; color:#A5D6A7;">
                    RELEVANCE: {score_pct}
                </span>
            </div>
            <div style="font-size:0.75rem; color:#8C9B8E; margin-top:3px; font-family:Consolas,monospace;">
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
    with st.expander(f"📚 Verified Source Citations ({len(citations)} Reference{'s' if len(citations) != 1 else ''})", expanded=False):
        for idx, cit in enumerate(citations, 1):
            render_citation_card(cit, index=idx)
