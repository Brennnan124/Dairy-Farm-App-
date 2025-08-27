import streamlit as st
from firebase_utils import add_document, log_audit_event, get_collection
from utils.calculations import get_all_cows, get_cows_by_status
from page_modules.staff_performance import record_staff_performance
from datetime import date

def milk_records_page(username):
    st.title("🥛 Milk Production Records")
    
    st.subheader("Record Milk Production")
    cows = get_cows_by_status("Lactating")  # Only lactating cows
    search_cow = st.text_input("Search Cow", key="milk_cow_search")
    filtered_cows = [c for c in cows if search_cow.lower() in c.lower()] if search_cow else cows
    selected_cow = st.selectbox("Select Cow", filtered_cows if filtered_cows else ["No lactating cows available"], key="milk_cow_select")
    
    if not filtered_cows and search_cow:
        st.warning("No lactating cow found. Please check the name or add a lactating cow in the Manager Dashboard.")
    
    col1, col2 = st.columns(2)
    with col1:
        time_of_milking = st.selectbox("Time of Milking", ["Morning", "Lunch", "Evening"], key="milk_time")
        # Allow decimal input with step=None
        litres_sell = st.number_input("Litres for Sale", min_value=0.0, max_value=10000.0, step=None, format="%f", key="milk_sell")
        record_date = st.date_input("Date of Recording", value=date.today(), key="milk_date")
    with col2:
        # Allow decimal input with step=None
        litres_calves = st.number_input("Litres for Calves", min_value=0.0, max_value=10000.0, step=None, format="%f", key="milk_calves")
    
    # Add total liters field
    total_litres = st.number_input("Total Litres Produced", min_value=0.0, max_value=10000.0, step=None, format="%f", 
                                  help="Total litres produced for the day (used for profit calculation)")
    
    if st.button("Record Milk"):
        if selected_cow == "No lactating cows available" or litres_sell < 0 or litres_calves < 0:
            st.warning("Please select a valid lactating cow and ensure litres are non-negative.")
        else:
            # Check for duplicate milking entries
            existing_records = get_collection("milk_production")
            if not existing_records.empty:
                duplicate = existing_records[
                    (existing_records["cow"] == selected_cow) & 
                    (existing_records["date"] == record_date.isoformat()) & 
                    (existing_records["time_of_milking"] == time_of_milking)
                ]
                
                if not duplicate.empty:
                    st.error(f"Error: {selected_cow} already has a milking record for {time_of_milking} on {record_date}.")
                    return
            
            add_document("milk_production", {
                "cow": selected_cow,
                "date": record_date.isoformat(),
                "time_of_milking": time_of_milking,
                "litres_sell": float(litres_sell),  # Store as float
                "litres_calves": float(litres_calves),  # Store as float
                "total_litres": float(total_litres)  # Store total litres
            })
            st.success("Milk production recorded!")
            record_staff_performance(username, f"Milk recorded for {selected_cow}")
            log_audit_event(username, "MILK_RECORDED", f"{selected_cow} - {litres_sell}L sell, {litres_calves}L calves, {total_litres}L total")
