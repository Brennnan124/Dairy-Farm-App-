# dairy_farm_app/pages/password_management.py
import streamlit as st
import os
from firebase_admin import auth
from firebase_utils import log_audit_event

def password_management_page():
    st.title("🔑 Password Management")
    
    st.subheader("Staff Password")
    staff_password = os.getenv("STAFF_PASSWORD", "dairy456")
    st.info(f"Current staff password: {staff_password}")
    
    with st.form("staff_password_form"):
        new_staff_password = st.text_input("New Staff Password", type="password")
        confirm_staff_password = st.text_input("Confirm New Staff Password", type="password")
        
        submitted_staff = st.form_submit_button("Update Staff Password")
        
        if submitted_staff:
            if new_staff_password != confirm_staff_password:
                st.error("Staff passwords do not match")
            elif not new_staff_password:
                st.error("Staff password cannot be empty")
            else:
                os.environ["STAFF_PASSWORD"] = new_staff_password
                st.success("Staff password updated successfully")
                st.info("Note: This change is temporary for this session. For permanent changes, update the STAFF_PASSWORD environment variable in your deployment.")
                log_audit_event("Manager", "STAFF_PASSWORD_UPDATED", "Staff password changed")
    
    st.subheader("Manager Passwords")
    manager_emails = os.getenv("MANAGER_EMAILS", "").split(",")
    if not manager_emails or manager_emails == [""]:
        st.warning("No manager emails configured in MANAGER_EMAILS environment variable.")
    else:
        st.info("Select a manager account to update its password.")
        selected_email = st.selectbox("Manager Email", manager_emails, key="manager_email_select")
        
        with st.form("manager_password_form"):
            new_manager_password = st.text_input("New Manager Password", type="password")
            confirm_manager_password = st.text_input("Confirm New Manager Password", type="password")
            
            submitted_manager = st.form_submit_button("Update Manager Password")
            
            if submitted_manager:
                if new_manager_password != confirm_manager_password:
                    st.error("Manager passwords do not match")
                elif len(new_manager_password) < 6:
                    st.error("Manager password must be at least 6 characters long")
                elif not new_manager_password:
                    st.error("Manager password cannot be empty")
                else:
                    try:
                        user = auth.get_user_by_email(selected_email)
                        auth.update_user(user.uid, password=new_manager_password)
                        st.success(f"Password updated successfully for {selected_email}")
                        log_audit_event("Manager", "MANAGER_PASSWORD_UPDATED", f"Password changed for {selected_email}")
                    except auth.UserNotFoundError:
                        st.error(f"User {selected_email} not found in Firebase Authentication")
                        log_audit_event("System", "MANAGER_PASSWORD_UPDATE_FAILED", f"User not found: {selected_email}")
                    except Exception as e:
                        st.error(f"Failed to update manager password: {e}")
                        log_audit_event("System", "MANAGER_PASSWORD_UPDATE_FAILED", f"Error for {selected_email}: {str(e)}")