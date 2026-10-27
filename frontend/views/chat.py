"""
NEXUS Knowledge Workspace View (Chat Interface)
Provides evidence-grounded natural language Q&A, source citation inspection,
insufficient evidence abstention, and multi-turn conversation memory.
"""

import streamlit as st
from datetime import datetime
from frontend.components.header import render_header
from frontend.components.citation_card import render_citations_list


def render_chat_view() -> None:
    """Render the interactive conversational RAG workspace."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("KNOWLEDGE WORKSPACE", domain_label=domain_filter)

    # Initialize conversation state if not present
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": (
                    "**NEXUS Intelligence Terminal initialized.** All queries are evaluated against "
                    "locally indexed, authorized technical documentation. Answers provide exact source citations "
                    "and page references. If sufficient evidence is absent, the system will explicitly abstain."
                ),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "citations": []
            }
        ]

    # Workspace Control Toolbar
    col_scope, col_actions = st.columns([2.5, 1])
    with col_scope:
        st.caption(f"Active Domain Scoping: `{domain_filter.upper()}` | Retrieval Mode: `DENSE SEMANTIC (Top-K=4)`")
    with col_actions:
        if st.button("🔄 New Conversation", use_container_width=True):
            st.session_state["messages"] = [
                {
                    "role": "assistant",
                    "content": "Conversation context cleared. Ready for new query.",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "citations": []
                }
            ]
            st.rerun()

    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Message History Stream
    for msg in st.session_state["messages"]:
        role = msg["role"]
        content = msg["content"]
        ts = msg.get("timestamp", "")
        citations = msg.get("citations", [])

        if role == "user":
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(f"**Query** <span style='font-size:0.75rem; color:#8C9B8E;'>[{ts}]</span>", unsafe_allow_html=True)
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="🛡️"):
                st.markdown(f"**NEXUS Terminal** <span style='font-size:0.75rem; color:#8C9B8E;'>[{ts}]</span>", unsafe_allow_html=True)
                st.markdown(content)
                if citations:
                    render_citations_list(citations)

    # Chat Input Box
    user_query = st.chat_input("Enter natural language query or technical inquiry...")
    if user_query:
        now_ts = datetime.now().strftime("%H:%M:%S")
        # Add user query to conversation
        st.session_state["messages"].append({
            "role": "user",
            "content": user_query,
            "timestamp": now_ts,
            "citations": []
        })

        # Process Query Placeholder (Integrated with Backend in Phase 7)
        with st.chat_message("assistant", avatar="🛡️"):
            with st.spinner("Searching local vector repository & assembling evidence..."):
                # Check if documents exist in vault
                db_path = st.session_state.get("db_path")
                # For Phase 1, provide a clean grounded placeholder explaining pipeline state
                response_content = (
                    f"**Query Evaluated**: `{user_query}`\n\n"
                    "> [!NOTE]\n"
                    "> **Pipeline State (Phase 1 Shell)**: UI and component foundation active. "
                    "The local Ingestion Engine (PyMuPDF + Chunking) and RAG integration (ChromaDB + Ollama Qwen2.5 1.5B) "
                    "will execute query vectorization once documents are uploaded and indexed."
                )
                sample_citations = []
                st.markdown(response_content)

        # Append assistant response
        st.session_state["messages"].append({
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "citations": sample_citations
        })
        st.rerun()
