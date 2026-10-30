"""
NEXUS Navigation Sidebar
Provides tactical military navigation, domain scoping, hardware telemetry,
and permission-governed view routing.
"""

import streamlit as st
from frontend.components.logo import get_nexus_logo_svg
from frontend.components.icons import icon_html, get_icon_svg, ICON_COLOR_GOLD, ICON_COLOR_SUBTLE, ICON_COLOR_MUTED_GOLD
from backend.security.auth import logout_user
from backend.security.rbac import has_permission


NAV_VIEWS = [
    ("dashboard", "Tactical Dashboard", None),
    ("chat", "Knowledge Workspace", "doc:view"),
    ("repository", "Document Vault", "doc:view"),
    ("ingest", "Ingestion Engine", "doc:upload"),
    ("analytics", "System Analytics", "audit:view"),
    ("settings", "Control & Settings", "app:configure"),
]

DOMAIN_OPTIONS = [
    ("all", "All Permitted Scopes"),
    ("technical_maintenance", "Technical & Maintenance"),
    ("training_education", "Training & Education"),
    ("safety_emergency", "Safety & Emergency"),
    ("defensive_cybersecurity", "Defensive Cybersecurity"),
    ("humanitarian_geospatial", "Humanitarian & Geospatial"),
    ("hazard_environmental", "Hazard & Environmental Safety"),
]


def render_sidebar() -> str:
    """Render the sidebar and return the currently selected view key."""
    user = st.session_state.get("user") or {}
    user_id = user.get("id")
    user_permissions = set(user.get("permissions") or [])

    with st.sidebar:
        # Render Logo
        st.markdown(get_nexus_logo_svg("sidebar"), unsafe_allow_html=True)
        st.markdown("<hr style='margin: 10px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

        # Domain Scoping Selector
        domain_hdr = icon_html("filter", "DOMAIN SCOPE FILTER", size=15, color=ICON_COLOR_GOLD, gap=6)
        st.markdown(
            f"<div style='font-size:var(--font-size-label); font-family:var(--font-mono); color:#D6C6A5; margin-bottom:6px; font-weight:700; letter-spacing:0.06em;'>{domain_hdr}</div>",
            unsafe_allow_html=True
        )
        selected_domain_idx = 0
        current_domain = st.session_state.get("active_domain", "all")
        for i, (k, _) in enumerate(DOMAIN_OPTIONS):
            if k == current_domain:
                selected_domain_idx = i
                break

        domain_choice = st.selectbox(
            "Select Domain Scope",
            options=[k for k, _ in DOMAIN_OPTIONS],
            format_func=lambda x: dict(DOMAIN_OPTIONS).get(x, x),
            index=selected_domain_idx,
            label_visibility="collapsed",
            key="sidebar_domain_selector"
        )
        st.session_state["active_domain"] = domain_choice

        st.markdown("<hr style='margin: 10px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

        # Tactical Navigation Menu (Filtered by Permissions)
        nav_hdr = icon_html("crosshair", "TACTICAL NAVIGATION", size=15, color=ICON_COLOR_GOLD, gap=6)
        st.markdown(
            f"<div style='font-size:var(--font-size-label); font-family:var(--font-mono); color:#D6C6A5; margin-bottom:8px; font-weight:700; letter-spacing:0.06em;'>{nav_hdr}</div>",
            unsafe_allow_html=True
        )

        current_view = st.session_state.get("current_view", "dashboard")
        for view_key, view_label, req_perm in NAV_VIEWS:
            # Check backend permissions for view visibility
            if req_perm and req_perm not in user_permissions:
                continue

            is_active = (current_view == view_key)
            btn_type = "primary" if is_active else "secondary"
            if st.button(view_label, key=f"nav_{view_key}", use_container_width=True, type=btn_type):
                st.session_state["current_view"] = view_key
                st.rerun()

        st.markdown("<hr style='margin: 14px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

        # Telemetry Box
        telemetry_hdr = icon_html("radio", "SYSTEM TELEMETRY", size=14, color=ICON_COLOR_GOLD, gap=6)
        st.markdown(
            f"""
            <div style="background-color: rgba(20, 29, 22, 0.82); border: 1px solid #303E32; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; backdrop-filter: var(--glass-blur);">
                <div style="font-family: var(--font-mono); font-size: var(--font-size-label); color: #D6C6A5; letter-spacing: 0.06em; margin-bottom: 8px; font-weight: 700;">
                    {telemetry_hdr}
                </div>
                <div style="font-family: var(--font-mono); font-size: var(--font-size-meta); color: #BAC2B8; line-height: 1.65;">
                    <div>• <b>RUNTIME:</b> <span style="color:#A5D6A7;">OFFLINE-LOCAL</span></div>
                    <div>• <b>AUTH:</b> <span style="color:#A5D6A7;">RBAC ACTIVE</span></div>
                    <div>• <b>LLM:</b> <span style="color:#F9E79F;">Qwen2.5 1.5B</span></div>
                    <div>• <b>DB:</b> <span style="color:#A5D6A7;">SQLite3 WAL</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Operator Session Card & Logout Button
        if st.session_state.get("authenticated", False):
            username = user.get("username", "OPERATOR")
            role = user.get("role", "USER")
            op_label = icon_html("user", f"OPERATOR: {username.upper()}", size=14, color="#C5CEC3", gap=6)
            st.markdown(
                f"""
                <div style="background: rgba(22, 32, 24, 0.82); border: 1px solid #303E32; padding: 12px 14px; border-radius: 6px; margin-bottom: 12px; backdrop-filter: var(--glass-blur);">
                    <div style="font-family: var(--font-display); font-size: var(--font-size-label); color: #A4B0A3;">{op_label}</div>
                    <div style="font-size: var(--font-size-meta); color: #D6C6A5; font-family: var(--font-mono); margin-top: 4px; margin-left: 20px;">CLEARANCE: {role.upper()}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Terminate Session (Logout)", use_container_width=True):
                token = st.session_state.get("session_token")
                if token:
                    logout_user(token)
                st.session_state["authenticated"] = False
                st.session_state["session_token"] = None
                st.session_state["user"] = None
                st.session_state["current_view"] = "dashboard"
                st.rerun()

        return st.session_state.get("current_view", "dashboard")
