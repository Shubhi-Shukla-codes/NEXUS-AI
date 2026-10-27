"""
NEXUS Knowledge Workspace View (Chat Interface)
Provides evidence-grounded natural language Q&A, source citation inspection,
insufficient evidence abstention, and multi-turn conversation memory.
"""

import streamlit as st
from datetime import datetime
from frontend.components.header import render_header
from frontend.components.citation_card import render_citations_list
from backend.retrieval.retriever import SemanticRetriever


def render_chat_view() -> None:
    """Render the interactive conversational RAG workspace."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("KNOWLEDGE WORKSPACE", domain_label=domain_filter)

    user = st.session_state.get("user") or {}
    user_id = user.get("id")
    username = user.get("username", "OPERATOR")
    user_permissions = set(user.get("permissions") or [])

    if "doc:view" not in user_permissions:
        st.error("⛔ Access Denied: Your clearance role lacks the 'doc:view' permission.")
        return

    # Initialize conversation state if not present
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": (
                    "**NEXUS Intelligence Terminal active.** All inquiries are evaluated against "
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
        st.caption(f"Domain Scoping: `{domain_filter.upper()}` | Retrieval: `DENSE SEMANTIC (Top-K=4, Threshold=0.35)`")
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
        st.session_state["messages"].append({
            "role": "user",
            "content": user_query,
            "timestamp": now_ts,
            "citations": []
        })

        with st.chat_message("assistant", avatar="🛡️"):
            with st.spinner("Executing semantic retrieval across local knowledge vault..."):
                retriever = SemanticRetriever()
                retrieval_res = retriever.retrieve_evidence(
                    query=user_query,
                    user_id=user_id,
                    username=username,
                    domain=domain_filter if domain_filter != "all" else None
                )

                if retrieval_res["is_sufficient"]:
                    citations = retrieval_res["citations"]
                    top_cite = citations[0]
                    response_content = (
                        f"**Evidence Retrieved ({len(citations)} source passages):**\n\n"
                        f"> Primary Ground Truth Reference: **{top_cite['filename']}** (Page {top_cite['page_number']}, Relevance: {top_cite['relevance_score']*100:.1f}%)\n\n"
                        f"**Relevant Passages:**\n\n"
                    )
                    for idx, c in enumerate(citations[:2], 1):
                        response_content += f"*{idx}.* \"{c['passage'][:300]}...\"\n\n"
                    response_content += (
                        "> [!NOTE]\n"
                        "> In Phase 7, the local Qwen2.5 1.5B model synthesizes these exact retrieved passages "
                        "into a coherent grounded summary."
                    )
                else:
                    citations = []
                    response_content = (
                        "> [!WARNING]\n"
                        "> **INSUFFICIENT EVIDENCE DETECTED (Abstention Policy Active)**\n"
                        "> No authorized technical documents in the local vault satisfied the required relevance threshold "
                        f"({retrieval_res['similarity_threshold']*100:.0f}%) for this query in scope `{domain_filter.upper()}`.\n\n"
                        "To prevent hallucinations, NEXUS abstains from answering until relevant documentation is uploaded and approved."
                    )
                st.markdown(response_content)
                if citations:
                    render_citations_list(citations)

        st.session_state["messages"].append({
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "citations": citations
        })
        st.rerun()
