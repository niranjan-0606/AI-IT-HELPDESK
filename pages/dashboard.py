"""
AI IT Helpdesk Agent - Dashboard Page
Visual analytics for IT administrators and helpdesk supervisors.
Displays ticket volumes, category distributions, priority breakdowns, and recent queries.
"""

import streamlit as st
import pandas as pd
import altair as alt

from database import get_dashboard_metrics, update_ticket_status
from utils.helpers import inject_custom_css, render_header, get_badge_html


def render_dashboard():
    """Renders the dashboard analytics UI."""
    inject_custom_css()

    render_header(
        title="📊 IT Helpdesk Analytics Dashboard",
        subtitle="Live operational metrics, ticket resolution status, and issue category analytics"
    )

    # Fetch live metrics from database
    metrics = get_dashboard_metrics()

    # Top KPI Metric Cards
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric(
            label="💬 Total Conversations",
            value=metrics["total_conversations"],
            delta="Active sessions"
        )
    with c2:
        st.metric(
            label="🚨 Open Tickets",
            value=metrics["open_tickets"],
            delta="Action required",
            delta_color="inverse"
        )
    with c3:
        st.metric(
            label="⏳ In Progress",
            value=metrics["in_progress_tickets"],
            delta="Under investigation"
        )
    with c4:
        st.metric(
            label="✅ Resolved Tickets",
            value=metrics["resolved_tickets"],
            delta="Successfully closed"
        )
    with c5:
        st.metric(
            label="📚 Knowledge Chunks",
            value=metrics["total_chunks"],
            delta=f"{metrics['total_docs']} files indexed"
        )

    st.markdown("---")

    # Analytics Charts
    col_chart_left, col_chart_right = st.columns(2)

    with col_chart_left:
        st.subheader("📁 Tickets by Issue Category")
        cat_data = metrics["ticket_categories"]
        if cat_data:
            df_cat = pd.DataFrame(cat_data)
            chart_cat = (
                alt.Chart(df_cat)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#2563EB")
                .encode(
                    x=alt.X("category:N", title="Category", sort="-y"),
                    y=alt.Y("count:Q", title="Number of Tickets"),
                    tooltip=["category", "count"]
                )
                .properties(height=280)
            )
            st.altair_chart(chart_cat, use_container_width=True)
        else:
            st.info("No ticket category records available yet.")

    with col_chart_right:
        st.subheader("🔥 Tickets by Priority Level")
        prio_data = metrics["ticket_priorities"]
        if prio_data:
            df_prio = pd.DataFrame(prio_data)
            color_scale = alt.Scale(
                domain=["Low", "Medium", "High", "Critical"],
                range=["#10B981", "#F59E0B", "#EF4444", "#991B1B"]
            )
            chart_prio = (
                alt.Chart(df_prio)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("priority:N", title="Priority", sort=["Low", "Medium", "High", "Critical"]),
                    y=alt.Y("count:Q", title="Tickets"),
                    color=alt.Color("priority:N", scale=color_scale, legend=None),
                    tooltip=["priority", "count"]
                )
                .properties(height=280)
            )
            st.altair_chart(chart_prio, use_container_width=True)
        else:
            st.info("No ticket priority records available yet.")

    st.markdown("---")

    # Recent Support Tickets Table & Quick Actions
    st.subheader("🎫 Recent Support Tickets")
    recent_tickets = metrics["recent_tickets"]

    if recent_tickets:
        for t in recent_tickets:
            with st.expander(f"**{t['ticket_id']}**: {t['title']} — {t['status']}", expanded=(t['status'] == 'Open')):
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**Requester:** {t['user_name']} ({t.get('email', 'N/A')}) | **Created:** {t['created_at']}")
                    st.markdown(f"{get_badge_html(t['category'], 'category')} {get_badge_html(t['priority'], 'priority')} {get_badge_html(t['status'], 'status')}", unsafe_allow_html=True)
                    st.write(t['description'])
                    if t.get("resolution_notes"):
                        st.info(f"**Resolution Notes:** {t['resolution_notes']}")

                with col_action:
                    st.markdown("##### Quick Status")
                    new_status = st.selectbox(
                        "Update Status",
                        ["Open", "In Progress", "Resolved"],
                        index=["Open", "In Progress", "Resolved"].index(t['status']),
                        key=f"dash_status_{t['ticket_id']}"
                    )
                    if st.button("Apply", key=f"btn_apply_{t['ticket_id']}"):
                        update_ticket_status(t['ticket_id'], new_status)
                        st.success(f"Updated {t['ticket_id']} to {new_status}")
                        st.rerun()
    else:
        st.info("No support tickets created yet.")

    # Recent AI Helpdesk Inquiries
    st.subheader("💬 Recent Student/Employee Questions")
    recent_chats = metrics.get("recent_chats", [])

    if recent_chats:
        df_chats = pd.DataFrame(recent_chats)
        df_chats = df_chats.rename(columns={
            "session_id": "Session ID",
            "content": "Question",
            "category": "Category",
            "priority": "Priority",
            "timestamp": "Time"
        })
        st.dataframe(df_chats[["Question", "Category", "Priority", "Time"]], use_container_width=True)
    else:
        st.info("No recent chat interactions logged.")


try:
    st.set_page_config(page_title="IT Helpdesk - Dashboard", page_icon="📊", layout="wide")
except Exception:
    pass

render_dashboard()
