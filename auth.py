def login_form():
    """Display a unified login form for managers and staff with simple password check."""
    initialize_session()
    check_inactivity()

    with st.sidebar:
        st.subheader("Farm Login")
        with st.form("login_form"):
            # Use a unique key for role selectbox
            role = st.selectbox(
                "Role",
                ["Manager", "Staff"],
                index=None,
                placeholder="Select your role",
                key="role_selectbox"
            )

            # Reset username in session state when role changes
            if role and st.session_state.username != role:
                st.session_state.username = role

            # Use the session state username directly, with a unique key
            username = st.text_input(
                "Username",
                value=st.session_state.username,
                key="username_input_field",
                disabled=True  # Make it read-only to prevent user edits
            )
            password = st.text_input("Password", type="password", key="password")
            submit = st.form_submit_button("Login")

            if submit:
                if not role:
                    st.error("Please select a role.")
                    log_audit_event("System", "LOGIN_FAILED", "No role selected")
                    return
                if not password:
                    st.error("Please enter your password.")
                    log_audit_event("System", "LOGIN_FAILED", f"Missing password for {username or 'unknown'}")
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
