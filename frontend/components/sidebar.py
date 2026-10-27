"""
NEXUS Navigation Sidebar
Provides tactical military navigation, domain scoping, hardware telemetry,
and permission-governed view routing.
"""

import streamlit as st
from frontend.components.logo import get_nexus_logo_svg
from backend.security.auth import logout_user
from backend.security.rbac import has_permission


NAV_VIEWS = [
    ("dashboard", "📊 Tactical Dashboard", None),
    ("chat", "💬 Knowledge Workspace", "doc:view"),
    ("repository", "📁 Document Vault", "doc:view"),
    ("ingest", "📥 Ingestion Engine", "doc:upload"),
    ("analytics", "📈 System Analytics", "audit:view"),
    ("settings", "⚙️ Control & Settings", "app:configure"),
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
        st.markdown(
            "<div style='font-size:0.72rem; font-family:Consolas,monospace; color:#D6C6A5; margin-bottom:4px; font-weight:700;'>DOMAIN SCOPE FILTER</div>",
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
        st.markdown(
            "<div style='font-size:0.72rem; font-family:Consolas,monospace; color:#D6C6A5; margin-bottom:6px; font-weight:700;'>TACTICAL NAVIGATION</div>",
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
        st.markdown(
            """
            <div style="background-color: #161D18; border: 1px solid #303E32; border-radius: 5px; padding: 10px 12px; margin-bottom: 12px;">
                <div style="font-family: Consolas, monospace; font-size: 0.68rem; color: #D6C6A5; letter-spacing: 0.05em; margin-bottom: 5px; font-weight: 700;">
                    SYSTEM TELEMETRY
                </div>
                <div style="font-size: 0.75rem; color: #BAC2B8; line-height: 1.55;">
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
            st.markdown(
                f"""
                <div style="background:#19221B; border:1px solid #303E32; padding:8px 10px; border-radius:4px; margin-bottom:10px;">
                    <div style="font-size:0.75rem; color:#A4B0A3;">OPERATOR: <b style="color:#F4F2E9;">{username.upper()}</b></div>
                    <div style="font-size:0.7rem; color:#D6C6A5; font-family:Consolas,monospace;">CLEARANCE: {role.upper()}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🚪 Terminate Session (Logout)", use_container_width=True):
                token = st.session_state.get("session_token")
                if token:
                    logout_user(token)
                st.session_state["authenticated"] = False
                st.session_state["session_token"] = None
                st.session_state["user"] = None
                st.session_state["current_view"] = "dashboard"
                st.rerun()

        return st.session_state.get("current_view", "dashboard")
