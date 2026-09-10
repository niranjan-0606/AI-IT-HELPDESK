"""
AI IT Helpdesk Agent - Helpers & Modern UI Styling Module
Provides modern CSS theme injection, styled badges, metric cards,
and UI helper components for a professional enterprise IT support look.
"""

import streamlit as st
from typing import Dict, Any, Optional
from config import CATEGORY_COLORS, PRIORITY_COLORS


def inject_custom_css():
    """Injects a modern blue-and-white IT-support theme into Streamlit."""
    custom_css = """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Primary Accent Headers */
    h1, h2, h3 {
        color: #1E3A8A !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* IT Helpdesk Header Card */
    .it-header-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #3B82F6 100%);
        color: white;
        padding: 24px 30px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25);
        margin-bottom: 24px;
    }
    .it-header-card h1 {
        color: white !important;
        margin: 0;
        font-size: 1.85rem;
        font-weight: 700;
    }
    .it-header-card p {
        color: #DBEAFE !important;
        margin: 6px 0 0 0;
        font-size: 0.95rem;
    }

    /* Metric Cards */
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: #BFDBFE;
    }
    .metric-title {
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #1E293B;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #10B981;
        margin-top: 4px;
        font-weight: 500;
    }

    /* Badges */
    .it-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    /* Chat Styling */
    .stChatMessage {
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 12px;
        border: 1px solid #E2E8F0;
    }

    /* Tool Call Output Container */
    .tool-output-box {
        background: #F8FAFC;
        border-left: 4px solid #2563EB;
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        font-size: 0.88rem;
        color: #334155;
    }

    /* Source Citation Pill */
    .source-pill {
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 0.78rem;
        font-family: 'JetBrains Mono', monospace;
        margin-right: 6px;
        display: inline-block;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        border-color: #2563EB;
        color: #2563EB;
    }

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def render_header(title: str = "🖥️ AI IT Helpdesk Agent", subtitle: str = "Intelligent troubleshooting powered by AI, RAG and diagnostic tools"):
    """Renders the top banner hero card."""
    st.markdown(f"""
        <div class="it-header-card">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)


def get_badge_html(text: str, badge_type: str = "category") -> str:
    """Generates an HTML styled badge pill."""
    if badge_type == "category":
        bg_color = CATEGORY_COLORS.get(text, "#6B7280")
    elif badge_type == "priority":
        bg_color = PRIORITY_COLORS.get(text, "#6B7280")
    elif badge_type == "status":
        status_colors = {"Open": "#EF4444", "In Progress": "#F59E0B", "Resolved": "#10B981"}
        bg_color = status_colors.get(text, "#6B7280")
    else:
        bg_color = "#3B82F6"

    return f"""
        <span class="it-badge" style="background-color: {bg_color}18; color: {bg_color}; border: 1px solid {bg_color}40;">
            ● {text}
        </span>
    """


def render_metric_card(title: str, value: Any, subtext: str = "", delta_color: str = "#10B981"):
    """Renders a dashboard metric tile."""
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            {f'<div class="metric-sub" style="color: {delta_color};">{subtext}</div>' if subtext else ''}
        </div>
    """, unsafe_allow_html=True)
