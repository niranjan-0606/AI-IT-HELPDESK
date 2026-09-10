"""
🖥️ AI IT Helpdesk Agent - Main Application
Entry point for the Streamlit web application.
Coordinates the AI Helpdesk Chat, Diagnostics, RAG Caching, and Navigation.
"""

import uuid
import streamlit as st

from config import (
    SUGGESTED_QUESTIONS,
    GOOGLE_API_KEY,
    DEFAULT_MODEL,
    AVAILABLE_MODELS
)
from agent import AITTHelpdeskAgent
from memory import ConversationMemory
from database import init_db, get_dashboard_metrics
from rag import get_knowledge_base_stats, rebuild_knowledge_base
from tools import execute_tool, TOOL_DEFINITIONS
from utils.helpers import (
    inject_custom_css,
    render_header,
    get_badge_html
)

# Page configuration
st.set_page_config(
    page_title="AI IT Helpdesk Agent",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern IT Helpdesk CSS theme
inject_custom_css()

# Initialize SQLite database
init_db()

# ---------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

if "api_key" not in st.session_state:
    st.session_state["api_key"] = GOOGLE_API_KEY

if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = DEFAULT_MODEL

if "agent" not in st.session_state:
    st.session_state["agent"] = AITTHelpdeskAgent(
        api_key=st.session_state["api_key"],
        model_name=st.session_state["selected_model"]
    )

if "memory" not in st.session_state:
    st.session_state["memory"] = ConversationMemory(session_id=st.session_state["session_id"])

# Auto-rebuild initial knowledge base if empty
kb_stats = get_knowledge_base_stats()
if not kb_stats["is_indexed"]:
    rebuild_knowledge_base()
    kb_stats = get_knowledge_base_stats()

# ---------------------------------------------------------------------
# Sidebar Navigation & Settings
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🖥️ IT Helpdesk Hub")
    st.markdown("Campus Intelligent Support & Diagnostic Assistant")
    st.markdown("---")

    # Navigation menu
    selected_view = st.radio(
        "Navigation",
        ["💬 AI Helpdesk", "📊 Dashboard", "📚 Knowledge Base", "🎫 Support Tickets", "⚙️ Settings"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # System Health Card
    st.markdown("##### 🟢 System Status")
    is_live_ai = bool(st.session_state["agent"].client)
    st.markdown(f"• **AI Engine:** {'🟢 Gemini Live' if is_live_ai else '🟡 Offline Mode'}")
    st.markdown(f"• **Vector Store:** 🟢 Active ({kb_stats['total_chunks']} chunks)")
    st.markdown(f"• **Database:** 🟢 SQLite Ready")
    st.markdown(f"• **Session:** `{st.session_state['session_id']}`")

    st.markdown("---")

    # Action buttons in sidebar
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
        st.session_state["memory"] = ConversationMemory(session_id=st.session_state["session_id"])
        st.rerun()

    if st.button("🗑️ Clear Chat Memory", use_container_width=True):
        st.session_state["memory"].clear()
        st.rerun()


# =====================================================================
# VIEW 1: AI HELPDESK CHAT (MAIN)
# =====================================================================
if selected_view == "💬 AI Helpdesk":
    render_header(
        title="🖥️ AI IT Helpdesk Agent",
        subtitle="Intelligent troubleshooting powered by AI, RAG and diagnostic tools"
    )

    # Top notification banner if in demo/offline mode
    if not is_live_ai:
        st.info(
            "💡 **Running in Demonstration Mode:** Gemini API key is not configured or offline. "
            "The AI agent will utilize its built-in rule-based expert engine + RAG + live diagnostic tools. "
            "To activate live Gemini LLM generation, add your API key in **⚙️ Settings**."
        )

    # Clickable Suggested Questions
    st.markdown("##### 💡 Suggested Questions")
    cols = st.columns(len(SUGGESTED_QUESTIONS))
    clicked_question = None

    for i, question in enumerate(SUGGESTED_QUESTIONS):
        with cols[i % len(cols)]:
            if st.button(question, key=f"sug_{i}", use_container_width=True):
                clicked_question = question

    st.markdown("---")

    # Display Conversation History
    history = st.session_state["memory"].get_messages()

    if not history:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 20px; color: #64748B;">
                <h3>👋 Hello! How can IT Support assist you today?</h3>
                <p>Describe your issue, ask for network diagnostics, or click any suggested question above.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        for msg in history:
            role = msg["role"]
            avatar = "👤" if role == "user" else "🤖"

            with st.chat_message(role, avatar=avatar):
                # Classification Badges for assistant turns
                if role == "assistant" and msg.get("category"):
                    badge_cat = get_badge_html(msg["category"], "category")
                    badge_prio = get_badge_html(msg.get("priority", "Medium"), "priority")
                    st.markdown(f"{badge_cat} {badge_prio}", unsafe_allow_html=True)

                st.markdown(msg["content"])

                # Expandable Tool Output
                if msg.get("tool_called") and msg.get("tool_result"):
                    with st.expander(f"🔍 Diagnostic Output: `{msg['tool_called']}()`", expanded=False):
                        st.json(msg["tool_result"])

                # Source Citations
                if msg.get("sources"):
                    source_pills = " ".join([f"<span class='source-pill'>📄 {s}</span>" for s in msg["sources"]])
                    st.markdown(f"<div style='margin-top: 8px;'>{source_pills}</div>", unsafe_allow_html=True)

    # Chat Input Handling
    user_input = st.chat_input("Type your technical problem or question here...")

    # Determine prompt to process (typed input or clicked suggested chip)
    prompt_to_process = user_input or clicked_question

    if prompt_to_process:
        # Display user message immediately
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt_to_process)

        # Save user message to memory
        st.session_state["memory"].add_user_message(prompt_to_process)

        # Process with Agent
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing problem, querying diagnostic tools & knowledge base..."):
                agent_result = st.session_state["agent"].process_query(
                    query=prompt_to_process,
                    conversation_history=history
                )

            # Show Category and Priority Badges
            cat = agent_result["category"]
            prio = agent_result["priority"]
            st.markdown(f"{get_badge_html(cat, 'category')} {get_badge_html(prio, 'priority')}", unsafe_allow_html=True)

            # Show Response Text
            st.markdown(agent_result["response"])

            # Expandable Diagnostic Box
            if agent_result.get("tool_called") and agent_result.get("tool_result"):
                with st.expander(f"🔍 Diagnostic Output: `{agent_result['tool_called']}()`", expanded=True):
                    st.json(agent_result["tool_result"])

            # Source citations
            if agent_result.get("sources"):
                source_pills = " ".join([f"<span class='source-pill'>📄 {s}</span>" for s in agent_result["sources"]])
                st.markdown(f"<div style='margin-top: 8px;'>{source_pills}</div>", unsafe_allow_html=True)

            # Save assistant response to memory
            st.session_state["memory"].add_assistant_message(
                content=agent_result["response"],
                category=cat,
                priority=prio,
                tool_called=agent_result.get("tool_called"),
                tool_result=agent_result.get("tool_result"),
                sources=agent_result.get("sources")
            )

            # Quick Action Button to open Ticket prefill
            st.markdown("---")
            col_act1, col_act2 = st.columns([2, 3])
            with col_act1:
                if st.button("🎫 Open Support Ticket from this Issue", key=f"btn_ticket_{uuid.uuid4().hex[:6]}"):
                    st.session_state["ticket_prefill_title"] = prompt_to_process[:80]
                    st.session_state["ticket_prefill_desc"] = (
                        f"Problem: {prompt_to_process}\n\n"
                        f"Diagnosis: {agent_result['response'][:300]}...\n\n"
                        f"Diagnostic Tool: {agent_result.get('tool_called') or 'None'}"
                    )
                    st.session_state["ticket_prefill_category"] = cat
                    st.session_state["ticket_prefill_priority"] = prio
                    st.info("Ticket form pre-filled! Click **🎫 Support Tickets** in the sidebar to review and submit.")


# =====================================================================
# VIEW 2: DASHBOARD (EMBEDDED)
# =====================================================================
elif selected_view == "📊 Dashboard":
    from pages.dashboard import render_dashboard
    render_dashboard()


# =====================================================================
# VIEW 3: KNOWLEDGE BASE (EMBEDDED)
# =====================================================================
elif selected_view == "📚 Knowledge Base":
    from pages.knowledge_base import render_knowledge_base
    render_knowledge_base()


# =====================================================================
# VIEW 4: SUPPORT TICKETS (EMBEDDED)
# =====================================================================
elif selected_view == "🎫 Support Tickets":
    from pages.tickets import render_tickets
    render_tickets()


# =====================================================================
# VIEW 5: SETTINGS
# =====================================================================
elif selected_view == "⚙️ Settings":
    render_header(
        title="⚙️ Application Settings & Diagnostic Lab",
        subtitle="Manage Gemini API credentials, models, and test diagnostic tools manually"
    )

    tab_api, tab_diag = st.tabs(["🔑 API & Model Configuration", "🛠️ Diagnostic Tools Live Test"])

    with tab_api:
        st.subheader("Google Gemini API Credentials")
        st.write("Enter your Gemini API key to enable live LLM reasoning and agent orchestration.")

        current_key = st.session_state.get("api_key", "")
        input_key = st.text_input(
            "Gemini API Key",
            value=current_key,
            type="password",
            placeholder="AIzaSy...",
            help="Get your free API key from https://aistudio.google.com/app/apikey"
        )

        selected_model = st.selectbox(
            "Gemini Model",
            AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(st.session_state.get("selected_model", DEFAULT_MODEL))
            if st.session_state.get("selected_model", DEFAULT_MODEL) in AVAILABLE_MODELS else 0
        )

        if st.button("Save & Update Credentials", type="primary"):
            st.session_state["api_key"] = input_key.strip()
            st.session_state["selected_model"] = selected_model
            st.session_state["agent"].update_credentials(input_key.strip(), selected_model)
            st.success("Credentials updated successfully!")
            st.rerun()

    with tab_diag:
        st.subheader("🛠️ Manual Diagnostic Tool Sandbox")
        st.write("Test each predefined diagnostic tool directly to verify system health.")

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            if st.button("Run: check_internet()", use_container_width=True):
                with st.spinner("Checking internet connectivity..."):
                    res = execute_tool("check_internet")
                    st.json(res)

            if st.button("Run: get_ip_address()", use_container_width=True):
                with st.spinner("Resolving IP addresses..."):
                    res = execute_tool("get_ip_address")
                    st.json(res)

            if st.button("Run: check_disk_space()", use_container_width=True):
                with st.spinner("Reading disk space..."):
                    res = execute_tool("check_disk_space")
                    st.json(res)

        with col_t2:
            ping_target = st.text_input("Host to ping", value="8.8.8.8")
            if st.button("Run: ping_server()", use_container_width=True):
                with st.spinner(f"Pinging {ping_target}..."):
                    res = execute_tool("ping_server", host=ping_target)
                    st.json(res)

            if st.button("Run: system_information()", use_container_width=True):
                with st.spinner("Querying system hardware & OS..."):
                    res = execute_tool("system_information")
                    st.json(res)

            if st.button("Run: network_information()", use_container_width=True):
                with st.spinner("Querying network adapters..."):
                    res = execute_tool("network_information")
                    st.json(res)
