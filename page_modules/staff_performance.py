# dairy_farm_app/pages/staff_performance.py
import streamlit as st
import pandas as pd
import plotly.express as px
from firebase_utils import get_collection, add_document, log_audit_event
from datetime import date

def record_staff_performance(staff_name, task):
    add_document("staff_performance", {
        "date": date.today().isoformat(),
        "staff_name": staff_name,
        "task": task,
        "completed": 1
    })
    log_audit_event(staff_name, "ACTION_COMPLETED", f"Task: {task}")

def get_staff_performance():
    perf_df = get_collection("staff_performance")
    if perf_df.empty:
        return pd.DataFrame()
    
    perf = perf_df.groupby("staff_name").agg(
        total_tasks=("task", "count"),
        completed_tasks=("completed", "sum")
    ).reset_index()
    
    perf["completion_rate"] = round(100.0 * perf["completed_tasks"] / perf["total_tasks"], 1)
    return perf

def staff_performance_page():
    st.title("👥 Staff Performance")
    
    performance_data = get_staff_performance()
    
    if not performance_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Performance Metrics")
            st.dataframe(performance_data)
        
        with col2:
            st.subheader("Performance Chart")
            fig = px.bar(performance_data, x="staff_name", y="completion_rate",
                        title="Staff Completion Rates",
                        labels={"staff_name": "Staff Name", "completion_rate": "Completion Rate (%)"})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No staff performance data available")