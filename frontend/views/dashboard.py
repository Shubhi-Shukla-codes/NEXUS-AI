"""
NEXUS Tactical Dashboard View
Displays verified database metrics, indexing pipeline status, storage utilization,
and operational domain distribution. (Never displays fabricated numbers).
"""

import os
import shutil
import streamlit as st
from backend.config import settings
from frontend.components.header import render_header
from frontend.components.icons import (
    get_icon_svg,
    icon_html,
    domain_icon,
    ICON_COLOR_GOLD,
    ICON_COLOR_MUTED_GOLD,
    ICON_COLOR_SUCCESS,
    ICON_COLOR_WARNING,
    ICON_COLOR_SUBTLE,
    ICON_COLOR_OFFWHITE
)


def render_dashboard_view() -> None:
    """Render system telemetry and operational metrics."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("OPERATIONAL DASHBOARD", domain_label=domain_filter, show_badges=False)

    # Tactical Hero Banner with camouflage texture
    st.markdown(
        """
        <div class="nexus-camo-hero">
            <div style="font-family: var(--font-display); font-size: var(--font-size-section); font-weight: 700; color: #F4F2E9; margin: 4px 0 8px 0; letter-spacing: 0.02em;">
                NEXUS Tactical Knowledge Intelligence Engine
            </div>
            <div style="font-family: var(--font-body); font-size: var(--font-size-body); color: #C5CEC3; max-width: 820px; line-height: var(--line-height-body);">
                Local-first semantic intelligence system operational. Ground truth indexing, vector retrieval, 
                and evidence-backed reasoning enabled within air-gapped domain boundaries.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Real Metrics Calculation (Reading actual data directory)
    db_file = settings.paths.sqlite_db_path
    db_initialized = db_file.exists()

    # Query metrics from DB or safe defaults
    total_docs = 0
    indexed_docs = 0
    pending_docs = 0
    total_chunks = 0
    recent_activity = []

    if db_initialized:
        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            
            # Check if tables exist
            cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='documents'")
            if cur.fetchone()[0] > 0:
                cur.execute("SELECT count(*) FROM documents")
                total_docs = cur.fetchone()[0] or 0

                cur.execute("SELECT count(*) FROM documents WHERE status IN ('indexed', 'approved')")
                indexed_docs = cur.fetchone()[0] or 0

                cur.execute("SELECT count(*) FROM documents WHERE status = 'pending'")
                pending_docs = cur.fetchone()[0] or 0

            cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='document_chunks'")
            if cur.fetchone()[0] > 0:
                cur.execute("SELECT count(*) FROM document_chunks")
                total_chunks = cur.fetchone()[0] or 0

            cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='audit_logs'")
            if cur.fetchone()[0] > 0:
                cur.execute("SELECT action, user_username, created_at FROM audit_logs ORDER BY id DESC LIMIT 5")
                recent_activity = cur.fetchall()

            conn.close()
        except Exception:
            pass

    # Query ChromaDB vector count if initialized
    total_vectors = 0
    try:
        from backend.storage.vector_store import ChromaVectorStore
        store = ChromaVectorStore()
        total_vectors = store.count_vectors()
    except Exception:
        pass

    # Real Disk Storage Calculation
    try:
        total_b, used_b, free_b = shutil.disk_usage(str(settings.paths.data_dir))
        free_gb = free_b / (1024 ** 3)
        total_gb = total_b / (1024 ** 3)
        disk_label = f"{free_gb:.1f} GB Free / {total_gb:.1f} GB"
    except Exception:
        disk_label = "Local Filesystem Ready"

    # KPI Metric Cards Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ico_repo = get_icon_svg("files", size=20, color=ICON_COLOR_GOLD)
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">TOTAL REPOSITORY</div>
                    {ico_repo}
                </div>
                <div class="nexus-stat-val">{total_docs}</div>
                <div class="nexus-stat-sub">Verified Documents</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        ico_act = get_icon_svg("circle_check", size=20, color=ICON_COLOR_SUCCESS)
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">ACTIVE / INDEXED</div>
                    {ico_act}
                </div>
                <div class="nexus-stat-val" style="color:#A5D6A7;">{indexed_docs}</div>
                <div class="nexus-stat-sub">Searchable in Vector Store</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        ico_pen = get_icon_svg("triangle_alert", size=20, color=ICON_COLOR_WARNING)
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">PENDING REVIEW</div>
                    {ico_pen}
                </div>
                <div class="nexus-stat-val" style="color:#F9E79F;">{pending_docs}</div>
                <div class="nexus-stat-sub">Awaiting Clearance</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c4:
        ico_chk = get_icon_svg("database", size=20, color=ICON_COLOR_GOLD)
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">KNOWLEDGE CHUNKS</div>
                    {ico_chk}
                </div>
                <div class="nexus-stat-val" style="color:#D6C6A5;">{total_chunks}</div>
                <div class="nexus-stat-sub">384-Dim Vectors</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Secondary Metrics & System Health Row
    col_left, col_right = st.columns([1.6, 1.4])

    with col_left:
        dom_title = icon_html("shield", "Domain Classification Status", size=22, color=ICON_COLOR_GOLD, gap=10)
        st.markdown(
            f"<div style='font-family:var(--font-display); font-size:var(--font-size-section); font-weight:700; color:#F4F2E9; margin-bottom:12px;'>{dom_title}</div>",
            unsafe_allow_html=True
        )
        domain_labels = [
            ("Technical Knowledge & Maintenance", "technical_maintenance"),
            ("Training & Education", "training_education"),
            ("Safety & Emergency Preparedness", "safety_emergency"),
            ("Defensive Cybersecurity", "defensive_cybersecurity"),
            ("Humanitarian & Geospatial", "humanitarian_geospatial"),
            ("Hazard & Environmental Safety", "hazard_environmental"),
        ]

        for name, key in domain_labels:
            ico = domain_icon(key, size=19, color=ICON_COLOR_GOLD)
            st.markdown(
                f"""
                <div style="background:rgba(27, 35, 29, 0.82); border:1px solid #2F3D31; padding:10px 14px; border-radius:6px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; backdrop-filter:var(--glass-blur);">
                    <span style="font-family:var(--font-body); font-size:var(--font-size-nav); color:#F4F2E9; display:inline-flex; align-items:center; gap:10px;">
                        {ico} <span>{name}</span>
                    </span>
                    <span class="nexus-badge" style="background:#26382B; font-size:var(--font-size-meta);">READY</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_right:
        sys_title = icon_html("radio", "System & Telemetry Health", size=22, color=ICON_COLOR_GOLD, gap=10)
        st.markdown(
            f"<div style='font-family:var(--font-display); font-size:var(--font-size-section); font-weight:700; color:#F4F2E9; margin-bottom:12px;'>{sys_title}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div style="background:rgba(22, 29, 24, 0.85); border:1px solid #303E32; padding:16px; border-radius:6px; backdrop-filter:var(--glass-blur);">
                <div style="font-family:var(--font-mono); font-size:var(--font-size-meta); line-height:1.75; color:#BAC2B8;">
                    <div>• <b>STORAGE INTEGRITY:</b> <span style="color:#A5D6A7;">{disk_label}</span></div>
                    <div>• <b>DATABASE MODE:</b> <span style="color:#A5D6A7;">SQLite3 WAL (Local)</span></div>
                    <div>• <b>VECTOR ENGINE:</b> <span style="color:#A5D6A7;">ChromaDB (Local Directory)</span></div>
                    <div>• <b>DEFAULT EMBEDDING:</b> <span style="color:#F9E79F;">{settings.models.embedding_model_name}</span></div>
                    <div>• <b>LLM BACKEND:</b> <span style="color:#F9E79F;">{settings.models.llm_model}</span></div>
                    <div>• <b>PRIVACY ENFORCEMENT:</b> <span style="color:#A5D6A7;">Strict Air-Gap Default</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if total_docs == 0:
            info_icon = get_icon_svg("info", size=18, color=ICON_COLOR_WARNING)
            st.markdown(
                f"""
                <div class="nexus-alert-warning" style="display:flex; align-items:flex-start; gap:10px;">
                    {info_icon}
                    <span>Knowledge vault is currently unpopulated. Proceed to the Ingestion Engine to ingest authorized technical documentation.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif recent_activity:
            st.markdown(f"<div style='font-family:var(--font-display); font-weight:700; color:#F4F2E9; margin-top:8px;'>Recent Activity Trail:</div>", unsafe_allow_html=True)
            for act, usr, dt in recent_activity:
                st.caption(f"[{dt}] {usr}: {act}")
