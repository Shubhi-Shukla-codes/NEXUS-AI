"""
NEXUS Document Repository View
Provides document listing, multi-parameter filtering, domain classification,
interactive document page reader, structured table inspector, and lifecycle management.
"""

from pathlib import Path
import streamlit as st
from backend.config import settings
from backend.storage.db import get_db_connection
from backend.services.document_service import (
    list_documents,
    get_document_by_id,
    approve_document,
    delete_document,
    DocumentError
)
from frontend.components.header import render_header
from frontend.components.document_card import render_document_card


def get_document_page_texts(doc_id: int) -> dict:
    """Retrieve full reconstructed text grouped by page number from document chunks."""
    pages = {}
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT page_number, content
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY page_number ASC, chunk_index ASC
            """,
            (doc_id,)
        ).fetchall()
        for r in rows:
            p_num = r["page_number"]
            if p_num not in pages:
                pages[p_num] = []
            pages[p_num].append(r["content"])
    return {p: "\n\n".join(chunks) for p, chunks in pages.items()}


def render_repository_view() -> None:
    """Render the document repository management interface."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("DOCUMENT REPOSITORY & VAULT", domain_label=domain_filter)

    user = st.session_state.get("user") or {}
    user_id = user.get("id")
    username = user.get("username", "OPERATOR")
    user_permissions = set(user.get("permissions") or [])

    # Fetch all available documents to check repository state
    all_docs = list_documents(domain="all", status="all", user_id=user_id)
    total_repo_count = len(all_docs)

    # Search and Filter Toolbar
    c_search, c_domain, c_status = st.columns([2.5, 1.5, 1.2])
    with c_search:
        search_query = st.text_input("🔍 Search Document Metadata or Filename", placeholder="e.g. state, manual, directory...")
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

    # Fetch Filtered Documents from Backend Service
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

    # Quick interactive document selector if documents exist
    if all_docs:
        doc_options = {d["id"]: f"#{d['id']} - {d['title']} ({d['filename']}, {d['file_size']/1024:.1f} KB)" for d in all_docs}
        selected_preview_id = st.session_state.get("preview_doc_id")
        
        # Determine dropdown default index
        dropdown_idx = 0
        doc_ids_list = [None] + list(doc_options.keys())
        if selected_preview_id in doc_ids_list:
            dropdown_idx = doc_ids_list.index(selected_preview_id)

        col_sel_label, col_sel_box = st.columns([1.2, 3.8])
        with col_sel_label:
            st.markdown("<div style='margin-top:6px; font-weight:700; color:#D6C6A5;'>📖 Inspect Document:</div>", unsafe_allow_html=True)
        with col_sel_box:
            chosen_doc_id = st.selectbox(
                "Select Document to Read / Inspect",
                options=doc_ids_list,
                format_func=lambda x: "-- Select a document to read pages & view tables --" if x is None else doc_options[x],
                index=dropdown_idx,
                label_visibility="collapsed"
            )
            if chosen_doc_id != selected_preview_id:
                st.session_state["preview_doc_id"] = chosen_doc_id
                st.rerun()

    # Document Details & Reader Modal/Box
    if "preview_doc_id" in st.session_state and st.session_state["preview_doc_id"]:
        preview_id = st.session_state["preview_doc_id"]
        doc_details = get_document_by_id(preview_id, user_id=user_id)
        if doc_details:
            with st.container():
                st.markdown(
                    f"""
                    <div style="background:#18221A; border:1px solid #4B644D; border-radius:6px; padding:18px 20px; margin-bottom:20px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-family:var(--font-display); font-size:var(--font-size-card); font-weight:700; color:#F4F2E9;">📄 {doc_details['title']}</span>
                                <span class="nexus-badge status-active" style="margin-left:10px;">{doc_details['status'].upper()}</span>
                                <span class="nexus-badge" style="margin-left:6px; background:#2A382C;">{doc_details['domain'].upper()}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Action bar for selected document
                c_chat_btn, c_close_btn = st.columns([2.5, 1.2])
                with c_chat_btn:
                    if st.button(f"💬 Query '{doc_details['title'][:35]}...' in Knowledge Workspace", key="btn_chat_with_doc", type="primary"):
                        st.session_state["target_doc_id"] = doc_details["id"]
                        st.session_state["target_doc_title"] = doc_details["title"]
                        st.session_state["current_view"] = "chat"
                        st.rerun()
                with c_close_btn:
                    if st.button("❌ Close Inspector", key="btn_close_inspector"):
                        st.session_state["preview_doc_id"] = None
                        st.rerun()

                # Inspector Tabs: Read Content, Tables, Diagrams, Metadata
                t_reader, t_tables, t_diagrams, t_meta = st.tabs([
                    "📖 Document Text & Pages",
                    "📊 Structured Tables",
                    "🖼️ Diagrams & Schematics",
                    "ℹ️ Provenance & Metadata"
                ])

                with t_reader:
                    page_dict = get_document_page_texts(doc_details["id"])
                    if not page_dict:
                        st.info("No text chunks found for this document.")
                    else:
                        page_nums = sorted(page_dict.keys())
                        col_p_sel, _ = st.columns([1.5, 3.5])
                        with col_p_sel:
                            selected_page = st.selectbox(
                                "Select Page",
                                options=page_nums,
                                format_func=lambda p: f"Page {p} of {len(page_nums)}",
                                index=0
                            )
                        page_text = page_dict.get(selected_page, "")
                        st.markdown(
                            f"""
                            <div style="background:#111713; border:1px solid #2D3D30; border-radius:6px; padding:18px 20px; font-family:var(--font-body); font-size:var(--font-size-body); line-height:var(--line-height-body); color:#E0E6DF; max-height:500px; overflow-y:auto; white-space:pre-wrap;">
{page_text}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                with t_tables:
                    from backend.ingestion.multimodal import list_document_media
                    media_assets = list_document_media(doc_details["id"])
                    table_assets = [m for m in media_assets if m["media_type"] == "table"]
                    if not table_assets:
                        st.caption("No structured tables extracted for this document.")
                    else:
                        for tab_idx, t in enumerate(table_assets, start=1):
                            st.markdown(f"#### 📋 {t['caption']}")
                            md_tab = t["metadata"].get("markdown", "")
                            if md_tab:
                                st.markdown(md_tab)
                            st.markdown("<hr style='margin:12px 0; border-color:#2A3A2C;'/>", unsafe_allow_html=True)

                with t_diagrams:
                    diagrams = [m for m in media_assets if m["media_type"] in ("diagram", "image")]
                    if not diagrams:
                        st.caption("No raster diagrams or visual assets detected.")
                    else:
                        for d in diagrams[:6]:
                            st.caption(f"📌 {d['caption']} (Dimensions: `{d['dimensions']}`)")
                            if d["file_path"] and Path(d["file_path"]).is_file():
                                st.image(d["file_path"], width=400)

                with t_meta:
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
                        st.markdown(f"**SHA-256 Hash:** `{doc_details.get('file_hash')}`")

                st.markdown("<hr style='margin: 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

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

    # Render Documents or Helpful Empty State
    if not filtered_docs:
        if total_repo_count > 0:
            st.info(
                f"ℹ️ No documents found matching Category: **{filter_domain.upper()}** and Status: **{filter_status.upper()}**. "
                f"However, **{total_repo_count} authorized documents** are available across other categories."
            )
            if st.button("🌐 Show All Categories & Documents", key="btn_show_all_repo"):
                st.session_state["active_domain"] = "all"
                st.rerun()
        else:
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
