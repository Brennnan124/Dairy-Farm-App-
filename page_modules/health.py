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

def get_medicines():
    return get_collection("medicines")

def add_medicine(name, supplier, quantity, unit_price, expiry_date=None):
    try:
        medicine_data = {
            "name": name,
            "supplier": supplier,
            "quantity": quantity,
            "unit_price": unit_price,
            "remaining": quantity,
            "created_date": date.today().isoformat()
        }
        
        if expiry_date:
            medicine_data["expiry_date"] = expiry_date.isoformat()
            
        success = add_document("medicines", medicine_data)
        if success:
            log_audit_event("Manager", "MEDICINE_ADDED", f"{name} (Qty: {quantity})")
        return success
    except Exception as e:
        st.error(f"Error saving medicine: {e}")
        return False

def add_health_record(cow_tag, disease, medicine, medicine_id, medicine_quantity, medicine_price, date, vaccinations, observations):
    try:
        success = add_document("health_records", {
            "cow_tag": cow_tag,
            "disease": disease,
            "medicine": medicine,
            "medicine_id": medicine_id,
            "medicine_quantity": medicine_quantity,
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
    
    # Get available medicines
    medicines = get_medicines()
    medicine_options = {}
    if not medicines.empty:
        medicine_options = {row["name"]: row["id"] for _, row in medicines.iterrows()}
    
    with st.expander("➕ Add New Health Record", expanded=True):
        search_cow = st.text_input("Search Cow", key="health_cow_search")
        cow_options = get_all_cows()
        filtered_cows = [c for c in cow_options if search_cow.lower() in c.lower()] if search_cow else cow_options
        cow_tag = st.selectbox("Select Cow", filtered_cows if filtered_cows else ["No cows available"], key="health_cow_select")
        
        if not filtered_cows and search_cow:
            st.warning("Cow not found. Please check the name or add the cow in the Manager Dashboard.")
        
        disease = st.text_input("Disease")
        
        # Medicine selection
        col1, col2 = st.columns(2)
        with col1:
            if medicine_options:
                selected_medicine = st.selectbox("Select Medicine", ["None"] + list(medicine_options.keys()))
                medicine_id = medicine_options[selected_medicine] if selected_medicine != "None" else None
                medicine = selected_medicine if selected_medicine != "None" else ""
            else:
                st.info("No medicines available. Manager needs to add medicines first.")
                medicine = st.text_input("Medicine Given")
                medicine_id = None
                
        with col2:
            if medicine_options and selected_medicine != "None":
                # Get selected medicine details
                selected_med = medicines[medicines["id"] == medicine_id].iloc[0]
                st.info(f"Available: {selected_med['remaining']}")
                medicine_quantity = st.number_input("Quantity Used", min_value=1, max_value=selected_med["remaining"], step=1, value=1)
                medicine_price = selected_med["unit_price"] * medicine_quantity
                st.write(f"Cost: KES {medicine_price:,.2f}")
            else:
                medicine_quantity = 0
                medicine_price = st.number_input("Medicine Price (KES)", min_value=0.0, max_value=100000.0, step=100.0)
        
        record_date = st.date_input("Date", value=date.today())
        vaccinations = st.text_input("Vaccinations (if calf)")
        observations = st.text_area("Observations")
        
        if st.button("Submit Health Record"):
            success = add_health_record(
                cow_tag, disease, medicine, medicine_id, medicine_quantity, 
                medicine_price, record_date.isoformat(), vaccinations, observations
            )
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
    
    # Medicine inventory section for managers
    with st.expander("💊 Medicine Inventory", expanded=True):
        st.subheader("Add New Medicine")
        col1, col2 = st.columns(2)
        
        with col1:
            med_name = st.text_input("Medicine Name")
            med_supplier = st.text_input("Supplier")
            med_quantity = st.number_input("Quantity", min_value=1, step=1)
            
        with col2:
            med_unit_price = st.number_input("Unit Price (KES)", min_value=0.0, max_value=100000.0, step=100.0)
            med_expiry = st.date_input("Expiry Date (optional)", value=None)
            
        if st.button("Add Medicine to Inventory"):
            if not med_name.strip():
                st.warning("Medicine name is required.")
            elif med_quantity <= 0:
                st.warning("Quantity must be greater than 0.")
            elif med_unit_price <= 0:
                st.warning("Unit price must be greater than 0.")
            else:
                success = add_medicine(med_name, med_supplier, med_quantity, med_unit_price, med_expiry)
                if success:
                    st.success("Medicine added to inventory successfully!")
                else:
                    st.error("Failed to add medicine.")
        
        st.markdown("---")
        st.subheader("Current Medicine Stock")
        medicines = get_medicines()
        
        if not medicines.empty:
            # Calculate low stock items
            low_stock = medicines[medicines["remaining"] < 10]
            
            if not low_stock.empty:
                st.warning("⚠️ Low stock alert for these medicines:")
                for _, med in low_stock.iterrows():
                    st.write(f"- {med['name']}: Only {med['remaining']} remaining")
            
            # Show all medicines
            medicines_display = medicines.drop(columns=["id"])
            st.dataframe(medicines_display)
        else:
            st.info("No medicines in inventory.")
    
    st.markdown("---")
    
    # Existing health records section
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
