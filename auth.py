import streamlit as st
import os
import time
import requests
from firebase_admin import auth
from firebase_utils import log_audit_event, initialize_firebase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "dairy456")
MANAGER_EMAILS = os.getenv("MANAGER_EMAILS", "").split(",")

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
    """Display the login form for managers and staff."""
    initialize_session()
    check_inactivity()

    with st.sidebar:
        st.subheader("Farm Login")
        role = st.selectbox("Role", ["Manager", "Staff"], index=None, placeholder="Select your role", key="role_select")

        if role == "Manager":
            with st.form("manager_login_form"):
                email = st.text_input("Email", key="manager_email")
                password = st.text_input("Password", type="password", key="manager_password")
                submit = st.form_submit_button("Login")
                reset_password = st.form_submit_button("Reset Password")

                if submit:
                    try:
                        manager_emails = [e.strip() for e in MANAGER_EMAILS]
                        if email not in manager_emails:
                            st.error("Not authorized for manager access")
                            log_audit_event("System", "LOGIN_FAILED", f"Unauthorized manager access attempt: {email}")
                            return

                        api_key = os.getenv("FIREBASE_API_KEY")
                        if not api_key:
                            st.error("Firebase API key not configured. Please contact administrator.")
                            return

                        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
                        auth_data = {
                            "email": email,
                            "password": password,
                            "returnSecureToken": True
                        }

                        response = requests.post(auth_url, json=auth_data)
                        result = response.json()

                        if 'error' in result:
                            st.error("Invalid email or password")
                            log_audit_event("System", "LOGIN_FAILED", f"Invalid credentials for: {email}")
                            return

                        st.session_state.authenticated = True
                        st.session_state.username = email
                        st.session_state.role = "Manager"
                        st.session_state.user_id = result['localId']
                        st.session_state.last_activity = time.time()
                        log_audit_event(email, "MANAGER_LOGIN", f"{email} logged in")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")
                        log_audit_event("System", "LOGIN_FAILED", f"Attempt with email: {email}")

                if reset_password:
                    try:
                        auth.get_user_by_email(email)  # Verify user exists
                        auth.generate_password_reset_link(email)
                        st.success(f"Password reset link sent to {email}")
                        log_audit_event("System", "PASSWORD_RESET_REQUEST", f"Reset requested for {email}")
                    except auth.UserNotFoundError:
                        st.error("User not found")
                        log_audit_event("System", "PASSWORD_RESET_FAILED", f"User not found: {email}")
                    except Exception as e:
                        st.error(f"Password reset failed: {e}")
                        log_audit_event("System", "PASSWORD_RESET_FAILED", f"Error for {email}: {str(e)}")

        elif role == "Staff":
            with st.form("staff_login_form"):
                username = st.text_input("Username", value="Staff", key="staff_username")  # Auto-populate
                password = st.text_input("Password", type="password", key="staff_password")
                submit = st.form_submit_button("Login")

                if submit:
                    if password == STAFF_PASSWORD:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = "Staff"
                        st.session_state.user_id = "staff_user"
                        st.session_state.last_activity = time.time()
                        log_audit_event(username, "STAFF_LOGIN", f"{username} logged in")
                        st.rerun()
                    else:
                        st.error("Invalid staff password")
                        log_audit_event("System", "LOGIN_FAILED", f"Invalid staff password attempt for: {username}")

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