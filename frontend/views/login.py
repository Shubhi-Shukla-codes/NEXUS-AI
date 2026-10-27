"""
NEXUS Authentication & Welcome View
Provides tactical welcome screen, role-based login form, password visibility control,
and session initialization.
"""

import streamlit as st
from frontend.components.logo import get_nexus_logo_svg


def render_login_view() -> None:
    """Render the tactical welcome and login interface."""
    col_l, col_center, col_r = st.columns([1, 2, 1])

    with col_center:
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        # Center Logo
        st.markdown(get_nexus_logo_svg("full"), unsafe_allow_html=True)
        
        st.markdown(
            """
            <div style="background: linear-gradient(180deg, #1A241C 0%, #151D17 100%); border: 1px solid #3A4A3C; border-radius: 8px; padding: 24px 28px; margin-top: 18px; box-shadow: 0 4px 18px rgba(0,0,0,0.4);">
                <div style="font-family: Consolas, monospace; font-size: 0.75rem; color: #D6C6A5; letter-spacing: 0.1em; text-transform: uppercase;">
                    TERMINAL AUTHENTICATION GATEWAY
                </div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #F4F2E9; margin: 4px 0 14px 0;">
                    Sign In to Access Knowledge Vault
                </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("nexus_login_form"):
            username = st.text_input(
                "Operator Identifier (Username)",
                value=st.session_state.get("login_user_pref", "admin"),
                placeholder="e.g. admin, operator_01"
            )
            password = st.text_input(
                "Access Credential (Password)",
                type="password",
                placeholder="Enter password..."
            )

            # Pre-configured role for demonstration
            role = st.selectbox(
                "Select Access Clearance Role",
                options=["Administrator", "Instructor", "Trainee", "Authorised User"],
                index=0,
                help="RBAC clearance determines document visibility and action permissions."
            )

            submit_login = st.form_submit_button("🔓 Authenticate & Enter", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if submit_login:
            if not username or not password:
                st.error("⚠️ Authentication Failed: Username and password must be provided.")
            else:
                # Initialize session state
                st.session_state["authenticated"] = True
                st.session_state["user"] = {
                    "username": username.strip(),
                    "role": role.lower().replace(" ", "_"),
                    "role_display": role
                }
                st.session_state["current_view"] = "dashboard"
                st.success(f"Access Granted. Initializing NEXUS interface as {role}...")
                st.rerun()

        # Offline notice
        st.markdown(
            """
            <div style="text-align: center; margin-top: 16px; font-size: 0.75rem; color: #8A988B; font-family: Consolas, monospace;">
                OFFLINE-FIRST // ZERO EXTERNAL TELEMETRY // LOCAL SECURE ENCLAVE
            </div>
            """,
            unsafe_allow_html=True
        )
