"""
NEXUS Header Component
Provides a unified tactical top bar with status pills, active domain indicator,
and session identity.
"""

import streamlit as st
from frontend.components.logo import get_nexus_logo_svg


def render_header(title: str, domain_label: str = "ALL DOMAINS") -> None:
    """Render top application status bar."""
    user = st.session_state.get("user", {"username": "GUEST", "role": "GUEST"})
    is_authenticated = st.session_state.get("authenticated", False)
    
    auth_badge = f"""
    <span class="nexus-badge status-active">
        SECURE // {user.get('role', 'GUEST').upper()} : {user.get('username', 'GUEST').upper()}
    </span>
    """ if is_authenticated else """
    <span class="nexus-badge status-offline">
        AUTH REQUIRED
    </span>
    """

    st.markdown(
        f"""
        <div class="nexus-topbar">
            <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-family: 'Segoe UI', sans-serif; font-size: 1.15rem; font-weight: 700; color: #F4F2E9; letter-spacing: 0.05em;">
                    {title.upper()}
                </span>
                <span class="nexus-badge" style="background-color: #26382B; border-color: #556B2F;">
                    SCOPE: {domain_label.upper()}
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="nexus-badge status-active">
                    <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#4CAF50; margin-right:4px;"></span>
                    OFFLINE ENGINE
                </span>
                {auth_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
