# dairy_farm_app/pages/employee_management.py
import streamlit as st
import pandas as pd
from datetime import date
from firebase_utils import get_collection, add_document

def get_employees():
    employees = get_collection("employees")
    if employees.empty:
        return pd.DataFrame()
    return employees[employees["end_date"].isna()]

def get_all_employees():
    return get_collection("employees")

def employee_management_page():
    st.title("👥 Employee Management")
    
    employees = get_all_employees()
    
    if not employees.empty:
        st.subheader("Current Employees")
        current_employees = employees[employees["end_date"].isna()]
        current_employees_display = current_employees.drop(columns=["id"])  # Remove id
        st.dataframe(current_employees_display)
        
        st.markdown("---")
        st.subheader("Add New Employee")
        
        with st.form("add_employee_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name")
                role = st.selectbox("Role", ["Milker", "Feeder", "Cleaner", "Supervisor"])
                salary = st.number_input("Monthly Salary (KES)", min_value=1, step=1000)  # Minimum 1 to avoid 0
            
            with col2:
                phone = st.text_input("Phone Number")
                start_date = st.date_input("Start Date", value=date.today())
                status = st.selectbox("Status", ["Active", "On Leave"])
            
            submitted = st.form_submit_button("Add Employee")
            
            if submitted:
                if not name.strip():
                    st.error("Name is required")
                else:
                    employee_data = {
                        "name": name.strip(),
                        "role": role,
                        "salary": salary,
                        "phone": phone,
                        "start_date": start_date.isoformat(),
                        "status": status,
                        "end_date": None
                    }
                    
                    if add_document("employees", employee_data):
                        st.success(f"Employee {name} added successfully")
                    else:
                        st.error("Failed to add employee")
    
    else:
        st.info("No employees in the system")
        st.markdown("---")
        st.subheader("Add New Employee")
        
        with st.form("add_first_employee_form"):
            name = st.text_input("Full Name")
            role = st.selectbox("Role", ["Milker", "Feeder", "Cleaner", "Supervisor"])
            salary = st.number_input("Monthly Salary (KES)", min_value=1, step=1000)  # Minimum 1 to avoid 0
            phone = st.text_input("Phone Number")
            start_date = st.date_input("Start Date", value=date.today())
            
            submitted = st.form_submit_button("Add Employee")
            
            if submitted:
                if not name.strip():
                    st.error("Name is required")
                else:
                    employee_data = {
                        "name": name.strip(),
                        "role": role,
                        "salary": salary,
                        "phone": phone,
                        "start_date": start_date.isoformat(),
                        "status": "Active",
                        "end_date": None
                    }
                    
                    if add_document("employees", employee_data):
                        st.success(f"Employee {name} added successfully")
                    else:
                        st.error("Failed to add employee")