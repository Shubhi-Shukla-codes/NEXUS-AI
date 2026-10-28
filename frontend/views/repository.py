"""
NEXUS Document Repository View
Provides document listing, multi-parameter filtering, domain classification,
metadata inspection, and permission-governed lifecycle management.
"""

import streamlit as st
from backend.config import settings
from backend.services.document_service import (
    list_documents,
    get_document_by_id,
    approve_document,
    delete_document,
    DocumentError
)
from frontend.components.header import render_header
from frontend.components.document_card import render_document_card


def render_repository_view() -> None:
    """Render the document repository management interface."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("DOCUMENT REPOSITORY & VAULT", domain_label=domain_filter)

    user = st.session_state.get("user") or {}
    user_id = user.get("id")
    username = user.get("username", "OPERATOR")
    user_permissions = set(user.get("permissions") or [])

    # Search and Filter Toolbar
    c_search, c_domain, c_status = st.columns([2.5, 1.5, 1.2])
    with c_search:
        search_query = st.text_input("🔍 Search Document Metadata or Filename", placeholder="e.g. manual, guideline, SDS...")
    with c_domain:
        domain_options = ["all"] + list(settings.domains)
        selected_dom_idx = 0
        if domain_filter in domain_options:
            selected_dom_idx = domain_options.index(domain_filter)

        filter_domain = st.selectbox(
            "Category Filter",
            options=domain_options,
            index=selected_dom_idx,
            format_func=lambda x: "All Domains" if x == "all" else x.replace("_", " ").upper()
        )
    with c_status:
        filter_status = st.selectbox(
            "Lifecycle Status",
            options=["all", "approved", "pending", "rejected", "indexed", "failed"],
            format_func=lambda x: "All Statuses" if x == "all" else x.upper(),
            index=0
        )

    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Document details preview modal/box
    if "preview_doc_id" in st.session_state and st.session_state["preview_doc_id"]:
        preview_id = st.session_state["preview_doc_id"]
        doc_details = get_document_by_id(preview_id, user_id=user_id)
        if doc_details:
            with st.expander(f"📄 Detailed Metadata: {doc_details['title']}", expanded=True):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.markdown(f"**Filename:** `{doc_details['filename']}`")
                    st.markdown(f"**Domain:** `{doc_details['domain'].upper()}`")
                    st.markdown(f"**Status:** `{doc_details['status'].upper()}`")
                    st.markdown(f"**File Size:** `{doc_details['file_size']/1024:.1f} KB`")
                with col_p2:
                    st.markdown(f"**Uploaded By:** `{doc_details.get('creator_name') or 'N/A'}`")
                    st.markdown(f"**Created At:** `{doc_details.get('created_at') or 'N/A'}`")
                    st.markdown(f"**Approved By:** `{doc_details.get('approver_name') or 'N/A'}`")
                    st.markdown(f"**SHA-256:** `{doc_details.get('file_hash')}`")

                # Multimodal Assets Inspector (Extracted Tables and Diagrams)
                from backend.ingestion.multimodal import list_document_media
                media_assets = list_document_media(doc_details["id"])
                if media_assets:
                    st.markdown("<hr style='margin: 8px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)
                    st.markdown(f"**Extracted Multimodal Assets ({len(media_assets)} items):**")
                    t_diag, t_tabs = st.tabs(["🖼️ Technical Diagrams & Schematics", "📊 Structured Tables"])
                    
                    with t_diag:
                        diagrams = [m for m in media_assets if m["media_type"] in ("diagram", "image")]
                        if not diagrams:
                            st.caption("No raster diagrams detected in document pages.")
                        else:
                            for d in diagrams[:6]:
                                st.caption(f"📌 {d['caption']} (Dimensions: `{d['dimensions']}`)")
                                if d["file_path"] and Path(d["file_path"]).is_file():
                                    st.image(d["file_path"], width=350)

                    with t_tabs:
                        tables = [m for m in media_assets if m["media_type"] == "table"]
                        if not tables:
                            st.caption("No structured tables detected in document pages.")
                        else:
                            for t in tables[:6]:
                                st.caption(f"📋 {t['caption']}")
                                md_tab = t["metadata"].get("markdown", "")
                                if md_tab:
                                    st.markdown(md_tab)

                if st.button("Close Preview"):
                    st.session_state["preview_doc_id"] = None
                    st.rerun()

    # Fetch Documents from Backend Service
    try:
        filtered_docs = list_documents(
            domain=filter_domain,
            status=filter_status,
            search_query=search_query,
            user_id=user_id
        )
    except Exception as e:
        st.error(f"⚠️ Error querying repository: {e}")
        filtered_docs = []

    # Action Handlers
    def handle_view(doc_dict):
        st.session_state["preview_doc_id"] = doc_dict["id"]
        st.rerun()

    def handle_approve(doc_id):
        try:
            approve_document(doc_id, user_id=user_id, username=username)
            st.success(f"Document ID #{doc_id} cleared and approved for retrieval!")
            st.rerun()
        except Exception as exc:
            st.error(f"Approval error: {exc}")

    def handle_delete(doc_id):
        try:
            delete_document(doc_id, user_id=user_id, username=username)
            st.warning(f"Document ID #{doc_id} permanently removed from vault.")
            st.rerun()
        except Exception as exc:
            st.error(f"Deletion error: {exc}")

    # Render Documents or Clean Empty State
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
        if "doc:upload" in user_permissions:
            col_btn, _ = st.columns([1.5, 4])
            with col_btn:
                if st.button("📥 Go to Document Ingestion", use_container_width=True):
                    st.session_state["current_view"] = "ingest"
                    st.rerun()
    else:
        st.caption(f"Displaying {len(filtered_docs)} document{'s' if len(filtered_docs) != 1 else ''} in vault")
        can_manage = ("doc:approve" in user_permissions) or ("doc:delete" in user_permissions)

        for doc in filtered_docs:
            render_document_card(
                doc,
                on_view=handle_view,
                on_approve=handle_approve,
                on_delete=handle_delete,
                can_manage=can_manage
            )
