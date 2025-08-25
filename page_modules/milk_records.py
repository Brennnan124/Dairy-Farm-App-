# dairy_farm_app/page_modules/milk_records.py
import streamlit as st
from firebase_utils import add_document, log_audit_event
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
        litres_sell = st.number_input("Litres for Sale", min_value=0.0, step=0.1, key="milk_sell")
    with col2:
        litres_calves = st.number_input("Litres for Calves", min_value=0.0, step=0.1, key="milk_calves")
    
    if st.button("Record Milk"):
        if selected_cow == "No lactating cows available" or litres_sell < 0 or litres_calves < 0:
            st.warning("Please select a valid lactating cow and ensure litres are non-negative.")
        else:
            add_document("milk_production", {
                "cow": selected_cow,
                "date": date.today().isoformat(),
                "time_of_milking": time_of_milking,
                "litres_sell": float(litres_sell),
                "litres_calves": float(litres_calves)
            })
            st.success("Milk production recorded!")
            record_staff_performance(username, f"Milk recorded for {selected_cow}")
            log_audit_event(username, "MILK_RECORDED", f"{selected_cow} - {litres_sell}L sell, {litres_calves}L calves")