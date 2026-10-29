"""
NEXUS Settings & System Configuration View
Provides local model configuration, storage path management, administrative user controls,
and air-gapped privacy enforcement settings.
"""

import sys
import platform
import streamlit as st
from backend.config import settings
from frontend.components.header import render_header


def render_settings_view() -> None:
    """Render the system control, preferences, and security settings."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("SYSTEM CONFIGURATION & SECURITY", domain_label=domain_filter)

    tab_models, tab_storage, tab_privacy, tab_sysinfo = st.tabs([
        "🧠 Local AI Runtime",
        "💾 Storage & Paths",
        "🛡️ Privacy & Security",
        "💻 System Diagnostics"
    ])

    with tab_models:
        st.subheader("Local Inference Engine Configuration")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.text_input("Ollama Base URL", value=settings.models.ollama_base_url, disabled=True)
            st.text_input("Active Target LLM", value=settings.models.llm_model, disabled=True)
            st.caption("Low-resource target: Qwen2.5 1.5B (Fast inference on CPU/iGPU)")
        with c_m2:
            st.slider("Generation Temperature", min_value=0.0, max_value=1.0, value=settings.models.llm_temperature, step=0.05)
            st.slider("Max Context Output Tokens", min_value=256, max_value=4096, value=settings.models.llm_max_tokens, step=256)

        st.markdown("<hr style='margin:12px 0; border-color:#3A4A3C;'/>", unsafe_allow_html=True)
        st.subheader("Embedding Configuration")
        c_e1, c_e2 = st.columns(2)
        with c_e1:
            st.text_input("Embedding Model", value=settings.models.embedding_model_name, disabled=True)
        with c_e2:
            st.text_input("Vector Dimensionality", value=f"{settings.models.embedding_dimension} dimensions", disabled=True)

    with tab_storage:
        st.subheader("Local Filesystem & Vault Paths")
        st.text_input("Database Directory", value=str(settings.paths.db_dir), disabled=True)
        st.text_input("Vector Store Directory", value=str(settings.paths.vector_store_dir), disabled=True)
        st.text_input("Document Vault (SHA-256 Storage)", value=str(settings.paths.vault_dir), disabled=True)
        st.text_input("Evaluation Benchmark Directory", value=str(settings.paths.eval_dir), disabled=True)

    with tab_privacy:
        st.subheader("Air-Gap & Privacy Policies")
        st.markdown(
            """
            <div class="nexus-alert-info">
                <b>STRICT AIR-GAP COMPLIANCE:</b><br/>
                NEXUS never transmits prompts, vector embeddings, uploaded files, or metadata across external networks.
                All models run in local memory on this device.
            </div>
            """,
            unsafe_allow_html=True
        )
        st.checkbox("Enforce Document-Level RBAC Permissions", value=True, disabled=True)
        st.checkbox("Log Authentication & Ingestion Events into Local Audit Trail", value=True, disabled=True)
        st.checkbox("Strip Document Metadata PII During Ingestion", value=True)

    with tab_sysinfo:
        st.subheader("Host Machine Diagnostics")
        st.markdown(
            f"""
            <div style="background:rgba(22, 29, 24, 0.85); border:1px solid #303E32; padding:16px; border-radius:6px; font-family:var(--font-mono); font-size:var(--font-size-meta); line-height:1.75; backdrop-filter:var(--glass-blur);">
                <div>• <b>APPLICATION:</b> {settings.app_name} v{settings.app_version}</div>
                <div>• <b>OPERATING SYSTEM:</b> {platform.platform()}</div>
                <div>• <b>PYTHON INTERPRETER:</b> {sys.version.split()[0]} ({sys.executable})</div>
                <div>• <b>HARDWARE PROFILE:</b> Intel Core i5 / Low-Resource 8-16GB Optimization</div>
                <div>• <b>DATABASE BACKEND:</b> SQLite3 with Foreign Key Constraints</div>
                <div>• <b>VECTOR STORE:</b> ChromaDB (DuckDB/Parquet Native Local Store)</div>
            </div>
            """,
            unsafe_allow_html=True
        )
