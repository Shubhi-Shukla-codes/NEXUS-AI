"""
NEXUS Document Ingestion View
Provides secure file upload handling, format validation feedback, domain assignment,
extraction tracking, and indexing state pipeline indicators.
"""

import streamlit as st
from backend.config import settings
from frontend.components.header import render_header


def render_ingest_view() -> None:
    """Render the document upload and ingestion interface."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("DOCUMENT INGESTION ENGINE", domain_label=domain_filter)

    st.markdown(
        """
        <div style="background-color: #19231B; border: 1px solid #303E32; border-radius: 6px; padding: 14px 18px; margin-bottom: 18px;">
            <div style="font-size: 0.95rem; font-weight: 700; color: #F4F2E9; margin-bottom: 4px;">
                Authorized Document Intake Pipeline
            </div>
            <div style="font-size: 0.83rem; color: #BAC2B8; line-height: 1.45;">
                Ingest technical manuals, emergency guides, or cybersecurity documentation into the local vault. 
                All files undergo SHA-256 fingerprinting, layout-aware extraction, structural chunking, 
                and permission validation before indexing.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Ingestion Configuration Form
    with st.form("ingest_form", clear_on_submit=False):
        col_d, col_a = st.columns([2, 1])
        with col_d:
            selected_domain = st.selectbox(
                "Assign Knowledge Domain",
                options=settings.domains,
                format_func=lambda x: x.replace("_", " ").upper(),
                help="Determines domain scope filtering and retrieval boundaries."
            )
        with col_a:
            auto_approve = st.checkbox(
                "Auto-Approve for Retrieval",
                value=False,
                help="If unchecked, documents require administrative review before appearing in RAG."
            )

        uploaded_files = st.file_uploader(
            "Select or drop files for local processing",
            type=["pdf", "txt", "docx", "md", "csv", "json", "xlsx"],
            accept_multiple_files=True,
            help="Supported: PDF, TXT, DOCX, MD, CSV, JSON, XLSX (Max 50MB per file)."
        )

        submit_btn = st.form_submit_button("🚀 Validate & Process Documents", use_container_width=True)

    if submit_btn:
        if not uploaded_files:
            st.warning("⚠️ Please select at least one document to ingest.")
        else:
            st.info(f"Received {len(uploaded_files)} file(s). Ingestion engine will parse and chunk documents.")
            for file in uploaded_files:
                file_size_kb = len(file.getvalue()) / 1024
                st.markdown(
                    f"""
                    <div style="background:#1B241D; border-left:3px solid #556B2F; padding:8px 12px; margin-bottom:6px; border-radius:3px;">
                        <b>{file.name}</b> ({file_size_kb:.1f} KB) &nbsp;—&nbsp;
                        <span class="nexus-badge status-pending">READY FOR PIPELINE</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.success("File validation complete. Proceeding to Extraction & Chunking in Phase 4.")

    # Format Specification Card
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("<b>Supported File Formats & Parser Specifications:</b>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">PDF Documents</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Engine: PyMuPDF (fitz)<br/>Page & table tracking</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f2:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">Office DOCX</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Engine: python-docx<br/>Section & style awareness</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f3:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">Tabular / Excel</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Engine: openpyxl / csv<br/>Row-column serialization</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with f4:
        st.markdown(
            """
            <div class="nexus-stat-card" style="padding:10px 12px;">
                <div style="font-weight:700; color:#F4F2E9;">Plaintext & MD</div>
                <div style="font-size:0.75rem; color:#BAC2B8;">Engine: Native UTF-8<br/>Header-aware splitting</div>
            </div>
            """,
            unsafe_allow_html=True
        )
