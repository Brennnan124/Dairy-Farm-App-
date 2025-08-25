import streamlit as st
from firebase_utils import get_collection

def audit_log_page():
    st.title("📝 Audit Log")
    audit_logs = get_collection("audit_log")
    
    if not audit_logs.empty:
        st.dataframe(audit_logs.sort_values("timestamp", ascending=False))
    else:
        st.info("No audit logs available")