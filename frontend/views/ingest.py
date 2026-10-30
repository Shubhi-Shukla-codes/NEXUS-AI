"""
NEXUS Document Ingestion View
Provides secure file upload handling, format validation feedback, domain assignment,
extraction tracking, and indexing state pipeline indicators.
"""

import streamlit as st
from backend.config import settings
from backend.services.document_service import upload_document, DocumentError
from frontend.components.header import render_header
from frontend.components.icons import (
    get_icon_svg,
    icon_html,
    ICON_COLOR_GOLD,
    ICON_COLOR_MUTED_GOLD,
    ICON_COLOR_SUCCESS,
    ICON_COLOR_WARNING,
    ICON_COLOR_DANGER,
    ICON_COLOR_SUBTLE
)


def render_ingest_view() -> None:
    """Render the document upload and ingestion interface."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("DOCUMENT INGESTION ENGINE", domain_label=domain_filter)

    user = st.session_state.get("user") or {}
    user_id = user.get("id")
    username = user.get("username", "OPERATOR")
    user_permissions = set(user.get("permissions") or [])

    # Check backend permission
    if "doc:upload" not in user_permissions:
        st.error("Access Denied: Your clearance role lacks the 'doc:upload' permission.")
        return

    banner_hdr = icon_html("upload_cloud", "Authorized Document Intake Pipeline", size=20, color=ICON_COLOR_GOLD, gap=8)
    st.markdown(
        f"""
        <div style="background-color: rgba(25, 35, 27, 0.82); border: 1px solid #303E32; border-radius: 6px; padding: 16px 20px; margin-bottom: 20px; backdrop-filter: var(--glass-blur);">
            <div style="font-family: var(--font-display); font-size: var(--font-size-card); font-weight: 700; color: #F4F2E9; margin-bottom: 6px;">
                {banner_hdr}
            </div>
            <div style="font-family: var(--font-body); font-size: var(--font-size-body); color: #BAC2B8; line-height: var(--line-height-body);">
                Ingest technical manuals, emergency guides, or cybersecurity documentation into the local vault. 
                All files undergo SHA-256 fingerprinting, layout-aware validation, and permission verification before storage.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Ingestion Configuration Form
    with st.form("ingest_form", clear_on_submit=False):
        col_d, col_a = st.columns([2, 1])
        with col_d:
            domain_default_idx = 0
            if domain_filter in settings.domains:
                domain_default_idx = settings.domains.index(domain_filter)
            selected_domain = st.selectbox(
                "Assign Knowledge Domain",
                options=settings.domains,
                index=domain_default_idx,
                format_func=lambda x: x.replace("_", " ").upper(),
                help="Determines domain scope filtering and retrieval boundaries."
            )
        with col_a:
            can_approve = "doc:approve" in user_permissions
            auto_approve = st.checkbox(
                "Auto-Approve for Retrieval",
                value=can_approve,
                disabled=not can_approve,
                help="Requires 'doc:approve' clearance. Approved documents immediately enter the search index."
            )

        uploaded_files = st.file_uploader(
            "Select or drop files for local processing",
            type=["pdf", "txt", "docx", "md", "csv", "json", "xlsx"],
            accept_multiple_files=True,
            help="Supported: PDF, TXT, DOCX, MD, CSV, JSON, XLSX (Max 50MB per file)."
        )

        submit_btn = st.form_submit_button("Validate & Ingest into Vault", use_container_width=True)

    if submit_btn:
        if not uploaded_files:
            st.warning("Please select at least one document to ingest.")
        else:
            success_count = 0
            duplicate_count = 0
            error_count = 0

            for file in uploaded_files:
                file_bytes = file.getvalue()
                try:
                    result = upload_document(
                        file_bytes=file_bytes,
                        filename=file.name,
                        domain=selected_domain,
                        user_id=user_id,
                        username=username,
                        auto_approve=auto_approve
                    )

                    if result.get("is_duplicate"):
                        duplicate_count += 1
                        dup_ico = get_icon_svg("triangle_alert", size=16, color=ICON_COLOR_WARNING)
                        st.markdown(
                            f"""
                            <div style="background:#2D2817; border-left:4px solid #D4AC0D; padding:10px 14px; margin-bottom:8px; border-radius:4px; display:flex; align-items:flex-start; gap:8px;">
                                {dup_ico}
                                <span><b>{file.name}</b>: Duplicate fingerprint detected. Linked to existing document #{result['id']} (Status: {result['status'].upper()}).</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        success_count += 1
                        # Execute extraction and chunking pipeline
                        from backend.ingestion.pipeline import process_document
                        pipeline_res = process_document(result["id"])

                        current_status = pipeline_res['status']
                        # If approved, immediately index chunks into ChromaDB vector store
                        if current_status == "approved":
                            try:
                                from backend.storage.vector_store import index_document_in_vector_store
                                idx_res = index_document_in_vector_store(result["id"])
                                current_status = idx_res.get("status", "indexed")
                            except Exception as v_err:
                                st.warning(f"Note: Vector indexing queued/pending for {file.name}: {v_err}")

                        status_badge = "status-active" if current_status in ("approved", "indexed") else "status-pending"
                        chk_ico = get_icon_svg("circle_check", size=18, color=ICON_COLOR_SUCCESS)
                        st.markdown(
                            f"""
                            <div style="background:rgba(27, 36, 29, 0.82); border-left:4px solid #556B2F; padding:10px 14px; margin-bottom:8px; border-radius:4px; backdrop-filter:var(--glass-blur); display:flex; align-items:center; gap:8px;">
                                {chk_ico}
                                <div>
                                    <b>{file.name}</b> ({result['file_size']/1024:.1f} KB) &nbsp;—&nbsp;
                                    <span class="nexus-badge {status_badge}">{current_status.upper()}</span>
                                    <span style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#A4B0A3; margin-left:8px;">
                                        PAGES: {pipeline_res['pages_count']} | CHUNKS: {pipeline_res['chunks_count']} | VECTOR STORE: {'PERSISTED' if current_status == 'indexed' else 'PENDING'}
                                    </span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                except DocumentError as e:
                    error_count += 1
                    st.error(f"Failed to ingest '{file.name}': {e}")
                except Exception as e:
                    error_count += 1
                    st.error(f"System error ingesting '{file.name}': {e}")

            if success_count > 0:
                st.success(f"Ingested {success_count} new document(s) into the vault.")

    # Format Specification Card
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    fmt_hdr = icon_html("files", "Supported File Formats & Parser Specifications:", size=16, color=ICON_COLOR_GOLD, gap=8)
    st.markdown(f"<div style='font-family:var(--font-display); font-size:var(--font-size-label); color:var(--sand-beige); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:10px;'>{fmt_hdr}</div>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        pdf_ico = get_icon_svg("file_text", size=18, color=ICON_COLOR_GOLD)
        st.markdown(
            f"""
            <div class="nexus-stat-card" style="padding:14px 16px;">
                <div style="font-family:var(--font-display); font-weight:700; font-size:var(--font-size-nav); color:#F4F2E9; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                    <span>PDF Documents</span> {pdf_ico}
                </div>
                <div style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#BAC2B8; line-height:1.5;">Magic signature: %PDF<br/>Engine: PyMuPDF</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f2:
        docx_ico = get_icon_svg("files", size=18, color=ICON_COLOR_GOLD)
        st.markdown(
            f"""
            <div class="nexus-stat-card" style="padding:14px 16px;">
                <div style="font-family:var(--font-display); font-weight:700; font-size:var(--font-size-nav); color:#F4F2E9; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                    <span>Office DOCX</span> {docx_ico}
                </div>
                <div style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#BAC2B8; line-height:1.5;">Magic signature: PK ZIP<br/>Engine: python-docx</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f3:
        db_ico = get_icon_svg("database", size=18, color=ICON_COLOR_GOLD)
        st.markdown(
            f"""
            <div class="nexus-stat-card" style="padding:14px 16px;">
                <div style="font-family:var(--font-display); font-weight:700; font-size:var(--font-size-nav); color:#F4F2E9; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                    <span>Tabular / Excel</span> {db_ico}
                </div>
                <div style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#BAC2B8; line-height:1.5;">Formats: .xlsx, .csv<br/>Engine: openpyxl</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f4:
        txt_ico = get_icon_svg("file_text", size=18, color=ICON_COLOR_GOLD)
        st.markdown(
            f"""
            <div class="nexus-stat-card" style="padding:14px 16px;">
                <div style="font-family:var(--font-display); font-weight:700; font-size:var(--font-size-nav); color:#F4F2E9; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                    <span>Plaintext & MD</span> {txt_ico}
                </div>
                <div style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#BAC2B8; line-height:1.5;">Formats: .txt, .md, .json<br/>UTF-8 validated</div>
            </div>
            """,
            unsafe_allow_html=True
        )
