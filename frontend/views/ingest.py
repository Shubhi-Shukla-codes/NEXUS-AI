"""
NEXUS Document Ingestion View
Provides secure file upload handling, format validation feedback, domain assignment,
extraction tracking, and indexing state pipeline indicators.
"""

import streamlit as st
from backend.config import settings
from backend.services.document_service import upload_document, DocumentError
from frontend.components.header import render_header


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
        st.error("⛔ Access Denied: Your clearance role lacks the 'doc:upload' permission.")
        return

    st.markdown(
        """
        <div style="background-color: #19231B; border: 1px solid #303E32; border-radius: 6px; padding: 14px 18px; margin-bottom: 18px;">
            <div style="font-size: 0.95rem; font-weight: 700; color: #F4F2E9; margin-bottom: 4px;">
                Authorized Document Intake Pipeline
            </div>
            <div style="font-size: 0.83rem; color: #BAC2B8; line-height: 1.45;">
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

        submit_btn = st.form_submit_button("🚀 Validate & Ingest into Vault", use_container_width=True)

    if submit_btn:
        if not uploaded_files:
            st.warning("⚠️ Please select at least one document to ingest.")
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
                        st.markdown(
                            f"""
                            <div style="background:#2D2817; border-left:4px solid #D4AC0D; padding:8px 12px; margin-bottom:6px; border-radius:3px;">
                                ⚠️ <b>{file.name}</b>: Duplicate fingerprint detected. Linked to existing document #{result['id']} (Status: {result['status'].upper()}).
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        success_count += 1
                        status_badge = "status-active" if result['status'] == "approved" else "status-pending"
                        st.markdown(
                            f"""
                            <div style="background:#1B241D; border-left:4px solid #556B2F; padding:8px 12px; margin-bottom:6px; border-radius:3px;">
                                ✅ <b>{file.name}</b> ({result['file_size']/1024:.1f} KB) &nbsp;—&nbsp;
                                <span class="nexus-badge {status_badge}">{result['status'].upper()}</span>
                                <span style="font-family:Consolas,monospace; font-size:0.75rem; color:#A4B0A3; margin-left:8px;">
                                    SHA: {result['file_hash'][:16]}...
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                except DocumentError as e:
                    error_count += 1
                    st.error(f"❌ Failed to ingest '{file.name}': {e}")
                except Exception as e:
                    error_count += 1
                    st.error(f"⚠️ System error ingesting '{file.name}': {e}")

            if success_count > 0:
                st.success(f"Ingested {success_count} new document(s) into the vault.")

    # Format Specification Card
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("<b>Supported File Formats & Parser Specifications:</b>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">PDF Documents</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Magic signature: %PDF<br/>Engine: PyMuPDF</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f2:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">Office DOCX</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Magic signature: PK ZIP<br/>Engine: python-docx</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f3:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">Tabular / Excel</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Formats: .xlsx, .csv<br/>Engine: openpyxl</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f4:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">Plaintext & MD</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Formats: .txt, .md, .json<br/>UTF-8 validated</div>
            </div>
            """,
            unsafe_allow_html=True
        )
