import streamlit as st
import time
from datetime import date
from utils.data_loader import load_table, to_date

def main():
    st.set_page_config(page_title="Dairy Farm Management", page_icon="🐄", layout="wide")
    if "show_sidebar" not in st.session_state:
        st.session_state.show_sidebar = True
    if "last_page" not in st.session_state:
        st.session_state.last_page = None

    if not st.session_state.get("authenticated", False):
        with st.sidebar:
            st.title("Farm Login")
            from auth import login_form
            login_form()  # Call without parameters
            if st.session_state.get("authenticated", False):
                st.session_state.last_activity = time.time()  # Update last activity on login
                st.rerun()
        st.title("Dairy Farm Management System")
        st.info("Please log in from the sidebar to proceed.")
        return

    # Update last activity time
    st.session_state.last_activity = time.time()
    username = st.session_state.get("username")
    role = st.session_state.get("role")
    with st.sidebar:
        st.title(f"Welcome {role}")
        st.title("Navigation")
        from auth import logout_button
        logout_button()

        if role == "Manager":
            from page_modules.dashboard import dashboard_page
            from page_modules.health import manager_health_page
            from page_modules.ai import manager_ai_page
            from page_modules.reports import reports_page
            from page_modules.audit_log import audit_log_page
            from page_modules.staff_performance import staff_performance_page
            from page_modules.employee_management import employee_management_page
            from page_modules.password_management import password_management_page
            from page_modules.data_edit import data_edit_page
            nav_options = [
                "Dashboard", "Health", "Artificial Insemination", "Reports",
                "Audit Log", "Staff Performance", "Employee Management", "Password Management", "Edit Data"
            ]
        else:  # Staff
            from page_modules.dashboard import dashboard_page
            from page_modules.health import staff_health_page
            from page_modules.ai import staff_ai_page
            from page_modules.knowledge_base import knowledge_base_page
            from page_modules.milk_records import milk_records_page
            from page_modules.feed_records import feed_records_page
            nav_options = ["Dashboard", "Milk Production Records", "Feed Records", "Health", "Artificial Insemination", "Knowledge Base"]

        page = st.sidebar.selectbox("Go to", nav_options, key="page_select")

    # Hide sidebar on any page selection
    if st.session_state.last_page != page:
        st.session_state.show_sidebar = False
        st.session_state.last_page = page

    # Apply CSS to hide sidebar if show_sidebar is False
    if not st.session_state.get("show_sidebar", True):
        st.markdown("<style>button[title='View fullscreen']{display: none;} div[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

    all_milk = to_date(load_table("milk_production"), "date")
    all_feeds_recv = to_date(load_table("feeds_received"), "date")
    all_feeds_used = to_date(load_table("feeds_used"), "date")
    all_cows = load_table("cows")
    all_obs = to_date(load_table("observations"), "date")

    min_date = min([d for d in [all_milk["date"].min() if not all_milk.empty else None,
                                all_feeds_recv["date"].min() if not all_feeds_recv.empty else None,
                                all_feeds_used["date"].min() if not all_feeds_used.empty else None,
                                all_obs["date"].min() if not all_obs.empty else None] if d is not None], default=date.today())
    max_date = max([d for d in [all_milk["date"].max() if not all_milk.empty else None,
                                all_feeds_recv["date"].max() if not all_feeds_recv.empty else None,
                                all_feeds_used["date"].max() if not all_feeds_used.empty else None,
                                all_obs["date"].max() if not all_obs.empty else None] if d is not None], default=date.today())

    if role == "Manager" and page == "Reports":
        with st.sidebar:
            st.markdown("### Analysis Filters")
            date_range = st.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date if max_date >= min_date else min_date, key="date_range")
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date = date_range
                end_date = date_range
            if isinstance(start_date, tuple):
                start_date = start_date[0]
            if isinstance(end_date, tuple):
                end_date = end_date[0]
            granularity = st.selectbox("Aggregation", ["Daily", "Weekly", "Monthly"], key="granularity_select")
        reports_page(start_date, end_date, granularity)
    elif page == "Dashboard":
        dashboard_page(role, username)
    elif page == "Health":
        if role == "Manager":
            manager_health_page()
        else:
            staff_health_page()
    elif page == "Artificial Insemination":
        if role == "Manager":
            manager_ai_page()
        else:
            staff_ai_page()
    elif page == "Knowledge Base":
        knowledge_base_page()
    elif page == "Milk Production Records" and role == "Staff":
        milk_records_page(username)
    elif page == "Feed Records" and role == "Staff":
        feed_records_page(username)
    elif page == "Reports" and role == "Manager":
        reports_page(start_date, end_date, granularity)
    elif page == "Audit Log" and role == "Manager":
        audit_log_page()
    elif page == "Staff Performance" and role == "Manager":
        staff_performance_page()
    elif page == "Employee Management" and role == "Manager":
        employee_management_page()
    elif page == "Password Management" and role == "Manager":
        password_management_page()
    elif page == "Edit Data" and role == "Manager":
        data_edit_page(username)

if __name__ == "__main__":
    main()
