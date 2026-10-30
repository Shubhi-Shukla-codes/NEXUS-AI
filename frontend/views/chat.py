"""
NEXUS Knowledge Workspace View (Grounded RAG Chat Interface)
Provides evidence-grounded natural language Q&A, source citation inspection,
insufficient evidence abstention, and multi-turn SQLite conversation memory.
"""

import streamlit as st
from datetime import datetime
from frontend.components.header import render_header
from frontend.components.citation_card import render_citations_list
from backend.generation.rag_engine import get_default_rag_engine, ABSTENTION_MESSAGE
from backend.services.conversation_service import (
    create_conversation,
    list_conversations,
    get_conversation,
    get_conversation_messages,
    delete_conversation
)


def render_chat_view() -> None:
    """Render the interactive conversational Grounded RAG workspace."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("KNOWLEDGE WORKSPACE", domain_label=domain_filter)

    user = st.session_state.get("user") or {}
    user_id = user.get("id")
    username = user.get("username", "OPERATOR")
    user_permissions = set(user.get("permissions") or [])

    if "doc:view" not in user_permissions:
        st.error("⛔ Access Denied: Your clearance role lacks the 'doc:view' permission.")
        return

    # Ensure user has an active conversation thread
    convs = list_conversations(user_id=user_id)
    active_conv_id = st.session_state.get("active_conv_id")

    if not active_conv_id or not any(c["id"] == active_conv_id for c in convs):
        if convs:
            active_conv_id = convs[0]["id"]
        else:
            new_conv = create_conversation(
                user_id=user_id,
                title="New Tactical Briefing",
                domain_scope=domain_filter
            )
            active_conv_id = new_conv["id"]
            convs = [new_conv]
        st.session_state["active_conv_id"] = active_conv_id

    # Workspace Control Toolbar
    col_select, col_new, col_del = st.columns([3.2, 1.2, 0.8])
    with col_select:
        conv_options = {c["id"]: f"{c['title']} ({c.get('message_count', 0)} msgs)" for c in convs}
        selected_id = st.selectbox(
            "Active Briefing Thread",
            options=list(conv_options.keys()),
            format_func=lambda x: conv_options.get(x, x),
            index=list(conv_options.keys()).index(active_conv_id) if active_conv_id in conv_options else 0,
            label_visibility="collapsed"
        )
        if selected_id != active_conv_id:
            st.session_state["active_conv_id"] = selected_id
            st.rerun()

    with col_new:
        if st.button("➕ New Thread", use_container_width=True):
            created = create_conversation(
                user_id=user_id,
                title="New Tactical Briefing",
                domain_scope=domain_filter
            )
            st.session_state["active_conv_id"] = created["id"]
            st.rerun()

    with col_del:
        if st.button("🗑️ Delete", use_container_width=True):
            delete_conversation(active_conv_id, user_id=user_id)
            st.session_state["active_conv_id"] = None
            st.rerun()

    st.markdown("<hr style='margin: 4px 0 10px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Targeted Document Banner (if set from repository)
    target_doc_id = st.session_state.get("target_doc_id")
    target_doc_title = st.session_state.get("target_doc_title")
    if target_doc_id:
        c_t_msg, c_t_btn = st.columns([4, 1.2])
        with c_t_msg:
            st.info(f"🎯 **Targeted Document Focus**: `{target_doc_title}`")
        with c_t_btn:
            if st.button("🌐 Clear Focus", use_container_width=True):
                st.session_state["target_doc_id"] = None
                st.session_state["target_doc_title"] = None
                st.rerun()

    # Search Mode and Domain Telemetry
    col_mode, col_domain_info = st.columns([1.5, 2.5])
    with col_mode:
        search_mode_sel = st.selectbox(
            "Search Engine Mode",
            ["Hybrid (Dense + BM25 RRF)", "Dense Semantic (ChromaDB)"],
            index=0,
            label_visibility="collapsed"
        )
        mode_val = "hybrid" if "Hybrid" in search_mode_sel else "dense"

    with col_domain_info:
        from backend.retrieval.domain_manager import get_domain_profile
        prof = get_domain_profile(domain_filter)
        if prof and not target_doc_id:
            st.caption(f"🛡️ **{prof.display_name}**: *{prof.description}*")
        else:
            st.caption(f"🌐 Scope: `ALL REPOSITORY DATA` | Model: `Qwen2.5 1.5B (Ollama Local)` | Engine: `{mode_val.upper()}`")

    st.markdown("<hr style='margin: 4px 0 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Fetch ordered messages from SQLite database
    messages = get_conversation_messages(active_conv_id, user_id=user_id)

    if not messages:
        with st.chat_message("assistant", avatar="🛡️"):
            st.markdown(
                "**NEXUS Intelligence Terminal active.** All inquiries are evaluated against "
                "locally indexed, authorized technical documentation. Answers provide exact source citations "
                "and page references. If sufficient evidence is absent, the system will explicitly abstain."
            )
            st.info(
                "💡 **Operational Tip**: Submit inquiries such as *'What is the standard hydraulic pressure?'* "
                "or *'What are the emergency exposure protocols?'*. Answers will cite grounded `[REF-X]` sources."
            )
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            citations = msg.get("citations", [])
            ts = msg.get("created_at", "")[:19]

            if role == "user":
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(f"**Operator Inquiry** <span style='font-size:var(--font-size-meta); color:#8C9B8E; font-family:var(--font-mono);'>[{ts}]</span>", unsafe_allow_html=True)
                    st.markdown(content)
            else:
                with st.chat_message("assistant", avatar="🛡️"):
                    st.markdown(f"**NEXUS Grounded Synthesis** <span style='font-size:var(--font-size-meta); color:#8C9B8E; font-family:var(--font-mono);'>[{ts}]</span>", unsafe_allow_html=True)
                    
                    if ABSTENTION_MESSAGE in content or "insufficient verified information" in content.lower():
                        st.warning(content)
                    else:
                        st.markdown(content)

                    if citations:
                        render_citations_list(citations)

    # Chat Input Box
    user_query = st.chat_input("Enter natural language query or technical inquiry...")
    if user_query:
        effective_domain = None if (target_doc_id or domain_filter == "all") else domain_filter
        with st.spinner("Querying vector repository & generating grounded answer..."):
            rag_engine = get_default_rag_engine()
            rag_engine.answer_query(
                query=user_query,
                user_id=user_id,
                username=username,
                domain=effective_domain,
                conversation_id=active_conv_id,
                search_mode=mode_val
            )
        st.rerun()
