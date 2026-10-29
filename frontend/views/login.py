"""
NEXUS Authentication & Welcome View
Provides tactical welcome screen, database-backed credential authentication,
bcrypt verification, registration for new operators, and session initialization.
"""

import streamlit as st
from frontend.components.logo import get_nexus_logo_svg
from backend.storage.db import init_database
from backend.security.auth import (
    login_user,
    register_user,
    ensure_initial_admin,
    AuthenticationError
)


def render_login_view() -> None:
    """Render the tactical welcome and authentication gateway."""
    # Ensure database tables exist and initial admin is bootstrapped
    init_database()
    ensure_initial_admin()

    col_l, col_center, col_r = st.columns([1, 2, 1])

    with col_center:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        # Tactical Center Logo
        st.markdown(get_nexus_logo_svg("full"), unsafe_allow_html=True)
        
        st.markdown(
            """
            <div style="background: rgba(22, 32, 25, 0.82); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid #3A4A3C; border-radius: 8px; padding: 22px 26px; margin-top: 16px; box-shadow: 0 4px 18px rgba(0,0,0,0.4);">
                <div style="font-family: Consolas, monospace; font-size: 0.72rem; color: #D6C6A5; letter-spacing: 0.12em; text-transform: uppercase;">
                    SECURE AIR-GAPPED GATEWAY // ROLE ENFORCED
                </div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #F4F2E9; margin: 4px 0 12px 0;">
                    Authenticate Terminal Session
                </div>
            """,
            unsafe_allow_html=True
        )

        tab_login, tab_register = st.tabs(["🔐 Sign In", "📝 Register Operator"])

        with tab_login:
            with st.form("nexus_login_form"):
                username = st.text_input(
                    "Operator Identifier (Username)",
                    value="admin",
                    placeholder="Enter username..."
                )
                password = st.text_input(
                    "Access Credential (Password)",
                    type="password",
                    placeholder="Enter password..."
                )

                submit_login = st.form_submit_button("🔓 Authenticate & Enter", use_container_width=True)

            if submit_login:
                try:
                    auth_result = login_user(
                        username=username,
                        password=password,
                        ip_address="127.0.0.1"
                    )
                    st.session_state["authenticated"] = True
                    st.session_state["session_token"] = auth_result["session_token"]
                    st.session_state["user"] = auth_result["user"]
                    st.session_state["current_view"] = "dashboard"
                    st.success(f"Access granted. Initialized session as {auth_result['user']['role'].upper()}.")
                    st.rerun()
                except AuthenticationError as e:
                    st.error(f"❌ {e}")
                except Exception as e:
                    st.error(f"⚠️ System Error during authentication: {e}")

            st.markdown(
                """
                <div style="background:#131B15; border-left:3px solid #B49A5A; padding:8px 10px; border-radius:3px; margin-top:10px; font-size:0.75rem; color:#C3B091;">
                    <b>Default Setup Credentials:</b><br/>
                    Username: <code>admin</code> &nbsp;|&nbsp; Password: <code>Admin@Nexus2026!</code>
                </div>
                """,
                unsafe_allow_html=True
            )

        with tab_register:
            with st.form("nexus_register_form"):
                reg_username = st.text_input("New Operator Username", placeholder="e.g. operator_02")
                reg_email = st.text_input("Email (Optional)", placeholder="e.g. op@nexus.local")
                reg_password = st.text_input("Password (Min 8 chars)", type="password")
                reg_role = st.selectbox(
                    "Clearance Role",
                    options=["trainee", "authorised_user", "instructor"],
                    format_func=lambda r: r.replace("_", " ").title()
                )

                submit_reg = st.form_submit_button("🛡️ Create Operator Account", use_container_width=True)

            if submit_reg:
                try:
                    new_user = register_user(
                        username=reg_username,
                        password=reg_password,
                        email=reg_email if reg_email else None,
                        role=reg_role,
                        actor_username="SELF_REGISTER"
                    )
                    st.success(f"Account for '{new_user['username']}' created successfully! You may now sign in.")
                except ValueError as e:
                    st.error(f"❌ {e}")
                except Exception as e:
                    st.error(f"⚠️ Error creating user: {e}")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="text-align: center; margin-top: 14px; font-size: 0.72rem; color: #8A988B; font-family: Consolas, monospace;">
                OFFLINE-FIRST // 100% LOCAL ENCLAVE // ZERO TELEMETRY
            </div>
            """,
            unsafe_allow_html=True
        )
