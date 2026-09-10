"""
AI IT Helpdesk Agent - Support Tickets Page
Allows users and technicians to create, search, filter, and resolve IT support tickets.
"""

import streamlit as st
import pandas as pd

from config import CATEGORIES, PRIORITIES, STATUSES
from database import (
    create_ticket,
    get_all_tickets,
    update_ticket_status
)
from utils.helpers import inject_custom_css, render_header, get_badge_html


def render_tickets():
    """Renders the ticket management and ticket creation UI."""
    inject_custom_css()

    render_header(
        title="🎫 IT Support Ticket Management",
        subtitle="Submit technical issues, track ticket progress, and manage resolutions"
    )

    # Tabs: View Tickets vs. Create New Ticket
    tab_view, tab_create = st.tabs(["📋 View & Manage Tickets", "➕ Submit New Ticket"])

    # =====================================================================
    # Tab 1: View & Manage Tickets
    # =====================================================================
    with tab_view:
        # Filter Bar
        col_f1, col_f2, col_f3, col_search = st.columns([1, 1, 1, 2])

        with col_f1:
            selected_status = st.selectbox("Status", ["All"] + STATUSES, key="filter_status")
        with col_f2:
            selected_category = st.selectbox("Category", ["All"] + CATEGORIES, key="filter_cat")
        with col_f3:
            selected_priority = st.selectbox("Priority", ["All"] + PRIORITIES, key="filter_prio")
        with col_search:
            search_kw = st.text_input("Search Keyword", placeholder="Search by title, ID, or user...", key="filter_kw")

        # Query tickets from database
        tickets = get_all_tickets(
            status_filter=selected_status,
            category_filter=selected_category,
            priority_filter=selected_priority,
            search_term=search_kw
        )

        st.markdown(f"**Found {len(tickets)} tickets matching criteria.**")

        if tickets:
            for t in tickets:
                with st.expander(f"**[{t['ticket_id']}]** {t['title']} — {t['status']}", expanded=False):
                    col_left, col_right = st.columns([2, 1])

                    with col_left:
                        st.markdown(f"**Requester:** {t['user_name']} (`{t.get('email', 'N/A')}`)")
                        st.markdown(f"**Created:** {t['created_at']} | **Last Updated:** {t.get('updated_at', 'N/A')}")
                        st.markdown(
                            f"{get_badge_html(t['category'], 'category')} "
                            f"{get_badge_html(t['priority'], 'priority')} "
                            f"{get_badge_html(t['status'], 'status')}",
                            unsafe_allow_html=True
                        )
                        st.markdown("##### Problem Description")
                        st.write(t['description'])

                        if t.get("resolution_notes"):
                            st.markdown("##### 📝 Resolution Notes")
                            st.info(t["resolution_notes"])

                    with col_right:
                        st.markdown("##### Update Ticket")
                        with st.form(key=f"form_update_{t['ticket_id']}"):
                            new_status = st.selectbox(
                                "Status",
                                STATUSES,
                                index=STATUSES.index(t['status']),
                                key=f"sel_status_{t['ticket_id']}"
                            )
                            notes = st.text_area(
                                "Resolution Notes",
                                value=t.get("resolution_notes") or "",
                                placeholder="Add action taken or troubleshooting notes...",
                                height=80,
                                key=f"notes_{t['ticket_id']}"
                            )
                            submitted = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                            if submitted:
                                update_ticket_status(t['ticket_id'], new_status, notes)
                                st.success(f"Ticket {t['ticket_id']} updated successfully!")
                                st.rerun()
        else:
            st.info("No tickets match the selected filters.")

    # =====================================================================
    # Tab 2: Create New Ticket
    # =====================================================================
    with tab_create:
        st.subheader("📝 Open a New IT Helpdesk Ticket")
        st.write("Provide detailed information so our support staff can diagnose and address the issue promptly.")

        # Check for query params / session prefill from chat
        prefill_title = st.session_state.get("ticket_prefill_title", "")
        prefill_desc = st.session_state.get("ticket_prefill_desc", "")
        prefill_cat = st.session_state.get("ticket_prefill_category", "Other")
        prefill_prio = st.session_state.get("ticket_prefill_priority", "Medium")

        with st.form(key="create_ticket_form"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                user_name = st.text_input("Full Name *", placeholder="e.g., Alex Mercer")
            with col_u2:
                user_email = st.text_input("Email Address *", placeholder="e.g., alex.m@college.edu")

            ticket_title = st.text_input("Issue Summary / Title *", value=prefill_title, placeholder="e.g., Wi-Fi keeps disconnecting in Physics Building")

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                cat_idx = CATEGORIES.index(prefill_cat) if prefill_cat in CATEGORIES else 0
                ticket_cat = st.selectbox("Issue Category", CATEGORIES, index=cat_idx)
            with col_c2:
                prio_idx = PRIORITIES.index(prefill_prio) if prefill_prio in PRIORITIES else 1
                ticket_prio = st.selectbox("Estimated Priority", PRIORITIES, index=prio_idx)

            ticket_desc = st.text_area(
                "Detailed Description *",
                value=prefill_desc,
                placeholder="Describe the exact error message, device model, operating system, and steps you already tried...",
                height=140
            )

            submit_ticket = st.form_submit_button("Submit Support Ticket", type="primary", use_container_width=True)

            if submit_ticket:
                if not user_name.strip() or not ticket_title.strip() or not ticket_desc.strip():
                    st.error("Please fill in all required fields (Name, Title, Description).")
                else:
                    new_id = create_ticket(
                        user_name=user_name.strip(),
                        email=user_email.strip(),
                        title=ticket_title.strip(),
                        description=ticket_desc.strip(),
                        category=ticket_cat,
                        priority=ticket_prio
                    )
                    st.success(f"Support Ticket **{new_id}** created successfully! Our IT team has received your submission.")
                    # Clear prefill
                    st.session_state["ticket_prefill_title"] = ""
                    st.session_state["ticket_prefill_desc"] = ""


try:
    st.set_page_config(page_title="IT Helpdesk - Support Tickets", page_icon="🎫", layout="wide")
except Exception:
    pass

render_tickets()
