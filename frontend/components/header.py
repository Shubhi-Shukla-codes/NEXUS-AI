"""
NEXUS Header Component
Provides a unified tactical top bar with status pills, active domain indicator,
and session identity.
"""

import streamlit as st
from frontend.components.logo import get_nexus_logo_svg


def render_header(title: str, domain_label: str = "ALL DOMAINS", show_badges: bool = False) -> None:
    """Render top application status bar with clean tactical view title."""
    topbar_html = (
        '<div class="nexus-topbar">'
        '<div style="display: flex; align-items: center;">'
        f'<span class="nexus-topbar-title">{title.upper()}</span>'
        '</div>'
        '</div>'
    )
    st.markdown(topbar_html, unsafe_allow_html=True)
