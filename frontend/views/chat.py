"""
NEXUS Knowledge Workspace View (Grounded RAG Chat Interface)
Provides evidence-grounded natural language Q&A, source citation inspection,
insufficient evidence abstention, and multi-turn SQLite conversation memory.
"""

import html
import streamlit as st
from datetime import datetime
from frontend.components.header import render_header
from frontend.components.citation_card import render_citations_list
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
from backend.generation.rag_engine import get_default_rag_engine, ABSTENTION_MESSAGE


@st.cache_resource
def get_cached_rag_engine():
    """Cache singleton RAG engine instance to eliminate neural model reload overhead."""
    return get_default_rag_engine()
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
        if st.button("New Thread", use_container_width=True):
            created = create_conversation(
                user_id=user_id,
                title="New Tactical Briefing",
                domain_scope=domain_filter
            )
            st.session_state["active_conv_id"] = created["id"]
            st.rerun()

    with col_del:
        if st.button("Delete", use_container_width=True):
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
            tgt_badge = icon_html("target", f"Targeted Document Focus: <code>{target_doc_title}</code>", size=18, color=ICON_COLOR_GOLD)
            st.markdown(
                f"""
                <div class="nexus-alert-info" style="margin: 0; padding: 10px 14px;">
                    {tgt_badge}
                </div>
                """,
                unsafe_allow_html=True
            )
        with c_t_btn:
            if st.button("Clear Focus", use_container_width=True):
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
            dom_ico = domain_icon(domain_filter, size=16, color=ICON_COLOR_GOLD)
            st.markdown(
                f"<div style='font-size:var(--font-size-meta); color:#BAC2B8; display:flex; align-items:center; gap:8px;'>"
                f"{dom_ico} <span><b>{prof.display_name}</b>: <i>{prof.description}</i></span>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            layer_ico = get_icon_svg("layers", size=16, color=ICON_COLOR_GOLD)
            st.markdown(
                f"<div style='font-size:var(--font-size-meta); color:#BAC2B8; display:flex; align-items:center; gap:8px;'>"
                f"{layer_ico} <span>Scope: <code>ALL REPOSITORY DATA</code> | Model: <code>Qwen2.5 1.5B (Local)</code> | Engine: <code>{mode_val.upper()}</code></span>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<hr style='margin: 4px 0 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Fetch ordered messages from SQLite database
    messages = get_conversation_messages(active_conv_id, user_id=user_id)

    if not messages:
        with st.chat_message("assistant", avatar=":material/shield:"):
            st.markdown(
                "**NEXUS Intelligence Terminal active.** All inquiries are evaluated against "
                "locally indexed, authorized technical documentation. Answers provide exact source citations "
                "and page references. If sufficient evidence is absent, the system will explicitly abstain."
            )
            st.markdown(
                """
                <div class="nexus-alert-info" style="margin-top:10px;">
                    <b>Operational Guidance:</b> Submit technical inquiries such as <i>'What is the standard hydraulic pressure?'</i> or <i>'What are the emergency exposure protocols?'</i>. Synthesized outputs cite verified <code>[REF-X]</code> sources.
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            citations = msg.get("citations", [])
            ts = msg.get("created_at", "")[:19]

            if role == "user":
                with st.chat_message("user", avatar=":material/person:"):
                    st.markdown(
                        f"<div style='font-family:var(--font-display); font-size:var(--font-size-label); font-weight:700; color:#BAC2B8; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;'>"
                        f"<span>Operator Inquiry</span>"
                        f"<span style='font-size:var(--font-size-meta); color:#8C9B8E; font-family:var(--font-mono); font-weight:400;'>[{ts}]</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(content)
            else:
                with st.chat_message("assistant", avatar=":material/shield:"):
                    st.markdown(
                        f"<div style='font-family:var(--font-display); font-size:var(--font-size-label); font-weight:700; color:#D6C6A5; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;'>"
                        f"<span>NEXUS Grounded Synthesis</span>"
                        f"<span style='font-size:var(--font-size-meta); color:#8C9B8E; font-family:var(--font-mono); font-weight:400;'>[{ts}]</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
                    if ABSTENTION_MESSAGE in content or "insufficient verified information" in content.lower():
                        st.warning(content)
                        with st.expander("Retrieval Diagnostics (Grounding Inspection)", expanded=False):
                            st.markdown("<span class='nexus-badge status-pending'>CONTEXT REJECTED — INSUFFICIENT EVIDENCE</span>", unsafe_allow_html=True)
                            st.caption("No passages in authorized documents met the relevance threshold for this query. System strictly abstained to prevent fabrication.")
                    else:
                        st.markdown(content)
                        if citations:
                            render_citations_list(citations)
                            with st.expander(f"Retrieval Diagnostics ({len(citations)} Chunks Grounded)", expanded=False):
                                col_d1, col_d2, col_d3 = st.columns(3)
                                with col_d1:
                                    st.markdown("<span class='nexus-badge status-active'>PASSED TO LLM</span>", unsafe_allow_html=True)
                                with col_d2:
                                    st.markdown(f"**Grounded Chunks:** `{len(citations)}`")
                                with col_d3:
                                    top_sc = citations[0].get("similarity_score") or citations[0].get("relevance_score") or 0.0
                                    st.markdown(f"**Top Relevance:** `{float(top_sc)*100:.1f}%`")

                                for c_idx, c in enumerate(citations, start=1):
                                    score_val = float(c.get("similarity_score") or c.get("relevance_score") or 0.0)
                                    snippet_txt = html.escape((c.get("passage") or c.get("content") or "")[:280])
                                    esc_fname = html.escape(str(c.get("filename") or "Document"))
                                    file_ico = get_icon_svg("file_text", size=14, color=ICON_COLOR_MUTED_GOLD)
                                    st.markdown(
                                        f"""
                                        <div style="background: rgba(20, 28, 22, 0.7); border: 1px solid #303E32; border-radius: 4px; padding: 10px 12px; margin-top: 8px;">
                                            <div style="display:flex; justify-content:space-between; margin-bottom:4px; align-items:center;">
                                                <span style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#D6C6A5; display:inline-flex; align-items:center; gap:6px;">
                                                    {file_ico} <b>[REF-{c_idx}]</b> {esc_fname} (Page {c.get('page_number', 1)})
                                                </span>
                                                <span style="font-family:var(--font-mono); font-size:var(--font-size-meta); color:#76A379;">
                                                    Score: {score_val*100:.1f}%
                                                </span>
                                            </div>
                                            <div style="font-family:var(--font-body); font-size:14px; color:#BAC2B8; line-height:1.45;">
                                                {snippet_txt}...
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )

    # Chat Input Box
    user_query = st.chat_input("Enter natural language query or technical inquiry...")
    if user_query:
        effective_domain = None if (target_doc_id or domain_filter == "all") else domain_filter
        with st.spinner("Querying vector repository & generating grounded answer..."):
            rag_engine = get_cached_rag_engine()
            res = rag_engine.answer_query(
                query=user_query,
                user_id=user_id,
                username=username,
                domain=effective_domain,
                target_doc_id=target_doc_id,
                conversation_id=active_conv_id,
                search_mode=mode_val
            )
            st.session_state["last_diagnostics"] = res.get("diagnostics")
        st.rerun()
