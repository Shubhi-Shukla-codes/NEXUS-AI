"""
NEXUS Document Card Component
Renders technical document summary cards with lifecycle badges, permissions,
domain classification, and action triggers.
"""

import streamlit as st
from typing import Dict, Any, Callable, Optional
from frontend.components.icons import (
    get_icon_svg,
    ICON_COLOR_GOLD,
    ICON_COLOR_SUCCESS,
    ICON_COLOR_WARNING,
    ICON_COLOR_MUTED_GOLD
)


def render_document_card(
    doc: Dict[str, Any],
    on_view: Optional[Callable] = None,
    on_approve: Optional[Callable] = None,
    on_index: Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
    can_manage: bool = False,
) -> None:
    """
    Render a single document summary card.
    Keys expected: id, filename, title, domain, status, file_size, chunk_count, created_at
    """
    doc_id = doc.get("id", "N/A")
    filename = doc.get("filename", "Untitled")
    title = doc.get("title") or filename
    domain = doc.get("domain", "general").replace("_", " ").upper()
    status = doc.get("status", "pending").lower()
    size_kb = doc.get("file_size", 0) / 1024
    chunk_count = doc.get("chunk_count", 0)
    created_at = doc.get("created_at", "Unknown")

    # Status badge styling
    status_class = "status-offline"
    status_ico = ""
    if status == "approved" or status == "indexed":
        status_class = "status-active"
        status_ico = get_icon_svg("circle_check", size=13, color=ICON_COLOR_SUCCESS)
    elif status == "pending":
        status_class = "status-pending"
        status_ico = get_icon_svg("triangle_alert", size=13, color=ICON_COLOR_WARNING)

    doc_ico = get_icon_svg("file_text", size=18, color=ICON_COLOR_GOLD)
    st.markdown(
        f"""
        <div class="nexus-doc-item">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="font-family: var(--font-display); font-weight: 700; font-size: var(--font-size-card); color: #F4F2E9; margin-bottom: 4px; display: inline-flex; align-items: center; gap: 8px;">
                        {doc_ico} <span>{title}</span>
                    </div>
                    <div style="font-family: var(--font-mono); font-size: var(--font-size-meta); color: #BAC2B8;">
                        FILE: {filename} &nbsp;|&nbsp; DOMAIN: <span style="color:#D6C6A5;">{domain}</span> &nbsp;|&nbsp; SIZE: {size_kb:.1f} KB &nbsp;|&nbsp; CHUNKS: {chunk_count}
                    </div>
                </div>
                <div>
                    <span class="nexus-badge {status_class}" style="display:inline-flex; align-items:center; gap:5px;">
                        {status_ico} {status.upper()}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Action buttons row
    col1, col2, col3, _ = st.columns([1.2, 1.4, 1.2, 3.8])
    with col1:
        if st.button("Preview", key=f"preview_{doc_id}"):
            if on_view:
                on_view(doc)
            else:
                st.info(f"Viewing document preview for ID: {doc_id}")
    with col2:
        if can_manage:
            if status == "pending":
                if st.button("Approve", key=f"appr_{doc_id}"):
                    if on_approve:
                        on_approve(doc_id)
            elif status in ("approved", "processed"):
                if st.button("Index Vectors", key=f"idx_{doc_id}"):
                    if on_index:
                        on_index(doc_id)
            elif status == "indexed":
                if st.button("Re-Index", key=f"reidx_{doc_id}"):
                    if on_index:
                        on_index(doc_id)
    with col3:
        if can_manage:
            if st.button("Delete", key=f"del_{doc_id}"):
                if on_delete:
                    on_delete(doc_id)
                else:
                    st.warning(f"Document {doc_id} deletion requested.")
