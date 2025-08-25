# dairy_farm_app/page_modules/health.py
import streamlit as st
import pandas as pd
from datetime import date
from utils.data_loader import to_date
from utils.calculations import get_all_cows
from firebase_utils import get_collection, add_document, update_document, delete_document, log_audit_event
from page_modules.staff_performance import record_staff_performance

def get_health_records():
    return get_collection("health_records")

def add_health_record(cow_tag, disease, medicine, medicine_price, date, vaccinations, observations):
    try:
        success = add_document("health_records", {
            "cow_tag": cow_tag,
            "disease": disease,
            "medicine": medicine,
            "medicine_price": medicine_price,
            "date": date,
            "vaccinations": vaccinations,
            "observations": observations,
            "cost": None
        })
        if success:
            log_audit_event("Staff", "HEALTH_RECORD_ADDED", f"{cow_tag}: {disease}")
        return success
    except Exception as e:
        st.error(f"Error saving health record: {e}")
        return False

def update_health_cost(record_id, cost):
    success = update_document("health_records", record_id, {"cost": cost})
    if success:
        log_audit_event("Manager", "HEALTH_COST_UPDATED", f"Record ID: {record_id}, Cost: {cost}")
    return success

def delete_health_record(record_id):
    success = delete_document("health_records", record_id)
    if success:
        log_audit_event("Manager", "HEALTH_RECORD_DELETED", f"Record ID: {record_id}")
    return success

def staff_health_page():
    st.title("🐄 Health Management")
    with st.expander("➕ Add New Health Record", expanded=True):
        search_cow = st.text_input("Search Cow", key="health_cow_search")
        cow_options = get_all_cows()
        filtered_cows = [c for c in cow_options if search_cow.lower() in c.lower()] if search_cow else cow_options
        cow_tag = st.selectbox("Select Cow", filtered_cows if filtered_cows else ["No cows available"], key="health_cow_select")
        
        if not filtered_cows and search_cow:
            st.warning("Cow not found. Please check the name or add the cow in the Manager Dashboard.")
        
        disease = st.text_input("Disease")
        medicine = st.text_input("Medicine Given")
        medicine_price = st.number_input("Medicine Price (KES)", min_value=0.0, step=10.0)
        record_date = st.date_input("Date", value=date.today())
        vaccinations = st.text_input("Vaccinations (if calf)")
        observations = st.text_area("Observations")
        if st.button("Submit Health Record"):
            success = add_health_record(cow_tag, disease, medicine, medicine_price, record_date.isoformat(), vaccinations, observations)
            if success:
                st.success("Health record added successfully!")
                record_staff_performance("Staff", f"Health record for {cow_tag}")
            else:
                st.error("Failed to add health record.")
    st.markdown("---")
    st.subheader("Health Observations")
    health_data = get_health_records()
    if not health_data.empty:
        health_data = to_date(health_data, "date")
        health_data_display = health_data.drop(columns=["id"])  # Remove id
        st.dataframe(health_data_display)
    else:
        st.info("No health records available")

def manager_health_page():
    st.title("🏥 Health Management")
    health_data = get_health_records()
    if not health_data.empty:
        health_data = to_date(health_data, "date")
        st.subheader("Health Records")
        health_data_display = health_data.drop(columns=["id"])  # Remove id
        st.dataframe(health_data_display)
        st.markdown("---")
        st.subheader("Cost Management")
        st.info("Add costs to health records that don't have pricing yet")
        if 'cost' in health_data.columns:
            unpriced_records = health_data[health_data['cost'].isna()]
        else:
            unpriced_records = health_data
            health_data['cost'] = None
        if unpriced_records.empty:
            st.success("All health records have costs assigned!")
        else:
            for idx, row in unpriced_records.iterrows():
                with st.expander(f"Unpriced: {row['cow_tag']} - {row['disease']} ({row['date']})"):
                    st.write(f"**Treatment:** {row['medicine']}")
                    st.write(f"**Medicine Price:** KES {row['medicine_price']:,.2f}")
                    st.write(f"**Vaccinations:** {row['vaccinations']}")
                    st.write(f"**Observations:** {row['observations']}")
                    cost = st.number_input("Treatment Cost (KES)", min_value=0.0, step=100.0, key=f"cost_{row['id']}")
                    if st.button("Save Cost", key=f"save_{row['id']}"):
                        update_health_cost(row['id'], cost)
                        st.success("Cost saved successfully!")
                        st.rerun()
    else:
        st.info("No health records available")
    st.markdown("---")
    st.subheader("Health Analytics")
    if not health_data.empty:
        common_diseases = health_data['disease'].value_counts().reset_index()
        common_diseases.columns = ['Disease', 'Count']
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Most Common Diseases**")
            st.dataframe(common_diseases)
        with col2:
            if 'cost' in health_data.columns and not health_data['cost'].isna().all():
                disease_costs = health_data.groupby('disease')['cost'].sum().reset_index()
                disease_costs.columns = ['Disease', 'Total Cost']
                st.write("**Treatment Costs by Disease**")
                st.dataframe(disease_costs)
    else:
        st.info("No health data available for analytics")