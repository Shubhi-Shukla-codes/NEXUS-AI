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
    
    role_str = str(user.get("role", "GUEST")).upper()
    username_str = str(user.get("username", "GUEST")).upper()

    if is_authenticated:
        badge_html = f'<span class="nexus-badge status-active">SECURE // {role_str} : {username_str}</span>'
    else:
        badge_html = '<span class="nexus-badge status-offline">AUTH REQUIRED</span>'

    topbar_html = (
        '<div class="nexus-topbar">'
        '<div style="display: flex; align-items: center; gap: 14px;">'
        f'<span style="font-family: \'Segoe UI\', sans-serif; font-size: 1.15rem; font-weight: 700; color: #F4F2E9; letter-spacing: 0.05em;">{title.upper()}</span>'
        f'<span class="nexus-badge" style="background-color: #26382B; border-color: #556B2F;">SCOPE: {domain_label.upper()}</span>'
        '</div>'
        '<div style="display: flex; align-items: center; gap: 10px;">'
        '<span class="nexus-badge status-active">'
        '<span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#4CAF50; margin-right:4px;"></span>'
        'OFFLINE ENGINE'
        '</span>'
        f'{badge_html}'
        '</div>'
        '</div>'
    )
    st.markdown(topbar_html, unsafe_allow_html=True)
