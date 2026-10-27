"""
NEXUS Document Repository View
Provides document listing, multi-parameter filtering, domain classification,
metadata inspection, and permission-governed lifecycle management.
"""

import streamlit as st
from backend.config import settings
from frontend.components.header import render_header
from frontend.components.document_card import render_document_card


def render_repository_view() -> None:
    """Render the document repository management interface."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("DOCUMENT REPOSITORY & VAULT", domain_label=domain_filter)

    # Search and Filter Toolbar
    c_search, c_domain, c_status = st.columns([2.5, 1.5, 1.2])
    with c_search:
        search_query = st.text_input("🔍 Search Document Metadata or Filename", placeholder="e.g. maintenance manual, SDS...")
    with c_domain:
        filter_domain = st.selectbox(
            "Category Filter",
            options=["All Domains"] + list(settings.domains),
            index=0
        )
    with c_status:
        filter_status = st.selectbox(
            "Lifecycle Status",
            options=["All Statuses", "Approved", "Indexed", "Pending", "Failed"],
            index=0
        )

    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Fetch Documents from Database (or empty state)
    docs = []
    db_file = settings.paths.sqlite_db_path
    if db_file.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='documents'")
            if cur.fetchone()[0] > 0:
                cur.execute(
                    "SELECT id, filename, title, domain, status, file_size, chunk_count, created_at FROM documents ORDER BY id DESC"
                )
                rows = cur.fetchall()
                for r in rows:
                    docs.append({
                        "id": r[0],
                        "filename": r[1],
                        "title": r[2],
                        "domain": r[3],
                        "status": r[4],
                        "file_size": r[5],
                        "chunk_count": r[6],
                        "created_at": r[7]
                    })
            conn.close()
        except Exception:
            pass

    # Apply Filters
    filtered_docs = docs
    if search_query:
        sq = search_query.lower()
        filtered_docs = [
            d for d in filtered_docs
            if sq in d["filename"].lower() or sq in d["title"].lower()
        ]
    if filter_domain != "All Domains":
        filtered_docs = [d for d in filtered_docs if d["domain"] == filter_domain]
    if filter_status != "All Statuses":
        filtered_docs = [d for d in filtered_docs if d["status"].lower() == filter_status.lower()]

    # Render Documents or Empty State
    if not filtered_docs:
        st.markdown(
            """
            <div class="nexus-empty-state">
                <div style="font-size: 2.2rem;">📁</div>
                <div class="nexus-empty-title">Document Vault is Currently Empty</div>
                <div class="nexus-empty-subtitle">
                    No matching authorized technical documents found. Navigate to the Ingestion Engine to upload
                    manuals, guidelines, or reference materials.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        col_btn, _ = st.columns([1.5, 4])
        with col_btn:
            if st.button("📥 Go to Document Ingestion", use_container_width=True):
                st.session_state["current_view"] = "ingest"
                st.rerun()
    else:
        st.caption(f"Displaying {len(filtered_docs)} document{'s' if len(filtered_docs) != 1 else ''}")
        user_role = st.session_state.get("user", {}).get("role", "guest")
        can_manage = user_role in ("administrator", "instructor")

        for doc in filtered_docs:
            render_document_card(doc, can_manage=can_manage)
