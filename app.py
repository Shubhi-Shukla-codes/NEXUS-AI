"""
NEXUS: Offline-First Intelligent Knowledge Management Platform
Streamlit Master Entry Point & Application Router
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure project root is in Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.storage.db import init_database
from backend.security.auth import validate_session, ensure_initial_admin

import importlib
import frontend.components.header
import frontend.components.sidebar
import frontend.views.dashboard
import frontend.views.chat
import frontend.views.repository
import frontend.views.ingest
import frontend.views.analytics
import frontend.views.settings
import frontend.views.login

importlib.reload(frontend.components.header)
importlib.reload(frontend.components.sidebar)
importlib.reload(frontend.views.dashboard)
importlib.reload(frontend.views.chat)
importlib.reload(frontend.views.repository)
importlib.reload(frontend.views.ingest)
importlib.reload(frontend.views.analytics)
importlib.reload(frontend.views.settings)
importlib.reload(frontend.views.login)

from frontend.components.sidebar import render_sidebar
from frontend.views.dashboard import render_dashboard_view
from frontend.views.chat import render_chat_view
from frontend.views.repository import render_repository_view
from frontend.views.ingest import render_ingest_view
from frontend.views.analytics import render_analytics_view
from frontend.views.settings import render_settings_view
from frontend.views.login import render_login_view


def load_custom_css() -> None:
    """Inject tactical military camouflage theme styles."""
    css_file = PROJECT_ROOT / "frontend" / "styles" / "theme.css"
    if css_file.exists():
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def init_session_state() -> None:
    """Ensure baseline session variables and validate persistent tokens."""
    # Ensure database is bootstrapped
    init_database()
    ensure_initial_admin()

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["session_token"] = None

    # If session_token exists, validate against SQLite sessions table
    token = st.session_state.get("session_token")
    if token and not st.session_state.get("authenticated", False):
        session_user = validate_session(token)
        if session_user:
            st.session_state["authenticated"] = True
            st.session_state["user"] = session_user
        else:
            st.session_state["authenticated"] = False
            st.session_state["user"] = None
            st.session_state["session_token"] = None

    if "current_view" not in st.session_state:
        st.session_state["current_view"] = "dashboard"
    if "active_domain" not in st.session_state:
        st.session_state["active_domain"] = "all"


def main() -> None:
    """Main application lifecycle and view routing engine."""
    st.set_page_config(
        page_title="NEXUS | Knowledge Intelligence Platform",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_session_state()
    load_custom_css()

    # Route based on authentication status
    if not st.session_state.get("authenticated", False):
        render_login_view()
        return

    # Render tactical navigation sidebar and obtain current view selection
    active_view = render_sidebar()

    # View Router
    view_dispatcher = {
        "dashboard": render_dashboard_view,
        "chat": render_chat_view,
        "repository": render_repository_view,
        "ingest": render_ingest_view,
        "analytics": render_analytics_view,
        "settings": render_settings_view,
    }

    render_func = view_dispatcher.get(active_view, render_dashboard_view)
    try:
        render_func()
    except Exception as exc:
        st.error(f"⚠️ Application View Exception: {exc}")
        if settings.debug:
            st.exception(exc)


if __name__ == "__main__":
    main()
