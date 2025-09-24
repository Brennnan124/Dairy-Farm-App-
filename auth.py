import streamlit as st
import time
from firebase_utils import log_audit_event, initialize_firebase

# Initialize Firebase
firebase_app = initialize_firebase()

def initialize_session():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()

def check_inactivity():
    """Check for session inactivity and log out if exceeded."""
    if 'last_activity' in st.session_state and st.session_state.authenticated:
        current_time = time.time()
        inactive_duration = current_time - st.session_state.last_activity
        if inactive_duration > 300:  # 5 minutes
            logout()
            st.warning("Session timed out due to inactivity. Please log in again.")
            st.rerun()

def logout():
    """Handle logout by clearing session state and logging the event."""
    username = st.session_state.get("username")
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.last_activity = time.time()
    log_audit_event("System" if not username else username, "LOGOUT", f"User {username or 'unknown'} logged out")

def login_form():
    """Display a unified login form for managers and staff with simple password check."""
    initialize_session()
    check_inactivity()

    with st.sidebar:
        st.subheader("Farm Login")
        with st.form("login_form"):
            role = st.selectbox("Role", ["Manager", "Staff"], index=None, placeholder="Select your role", key="role_select")
            username = st.text_input("Username", value="Staff" if role == "Staff" else "", key="username")
            password = st.text_input("Password", type="password", key="password")
            submit = st.form_submit_button("Login")

            if submit:
                if not role:
                    st.error("Please select a role.")
                    log_audit_event("System", "LOGIN_FAILED", "No role selected")
                    return
                if not username or not password:
                    st.error("Please enter both username and password.")
                    log_audit_event("System", "LOGIN_FAILED", f"Missing username or password for {username or 'unknown'}")
                    return

                # Get passwords from Streamlit secrets
                manager_password = st.secrets.get("MANAGER_PASSWORD", "BMaina@456")
                staff_password = st.secrets.get("STAFF_PASSWORD", "dairy456")

                # Check password based on selected role
                if role == "Manager" and password == manager_password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = "Manager"
                    st.session_state.user_id = f"manager_{username}"
                    st.session_state.last_activity = time.time()
                    log_audit_event(username, "MANAGER_LOGIN", f"{username} logged in as Manager")
                    st.rerun()
                elif role == "Staff" and password == staff_password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = "Staff"
                    st.session_state.user_id = f"staff_{username}"
                    st.session_state.last_activity = time.time()
                    log_audit_event(username, "STAFF_LOGIN", f"{username} logged in as Staff")
                    st.rerun()
                else:
                    st.error("Invalid password or role.")
                    log_audit_event("System", "LOGIN_FAILED", f"Invalid password for {username} as {role}")

def get_role():
    """Return the user's role from session state."""
    return st.session_state.get("role", None)

def is_authenticated():
    """Check if the user is authenticated."""
    return st.session_state.get("authenticated", False)

def logout_button():
    """Handle logout by displaying a button in the sidebar and triggering logout."""
    if st.sidebar.button("Logout"):
        logout()

# Ensure all functions are exportable
__all__ = ['login_form', 'logout_button', 'is_authenticated', 'get_role']
