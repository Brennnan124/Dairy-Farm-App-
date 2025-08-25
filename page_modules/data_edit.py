# dairy_farm_app/page_modules/data_edit.py
import streamlit as st
import pandas as pd
from datetime import date
from utils.data_loader import load_table, to_date
from utils.calculations import get_all_cows, get_available_feed_types
from firebase_utils import update_document, delete_document, log_audit_event

def data_edit_page(username):
    st.title("📝 Edit Data Entries")
    
    st.header("Edit or Delete Data")
    
    # Search feature
    search_term = st.text_input("Search Data (e.g., Name, Feed Type, Cow Tag)", key="data_search")
    
    # List all data types for selection
    data_types = ["Cows", "Feed Inventory", "Feeds Used", "Employees", "Observations", "Milk Production", "Health Records", "AI Records"]
    selected_type = st.selectbox("Select Data Type to Edit/Delete", data_types, key="edit_type_select")
    
    if selected_type == "Cows":
        df = load_table("cows")
        if not df.empty:
            if search_term:
                df = df[df["name"].str.lower().str.contains(search_term.lower())]
            cow_names = df["name"].tolist()
            selected_cow_name = st.selectbox("Select Cow by Name", cow_names, key="edit_cow_name_select")
            selected_cow = df[df["name"] == selected_cow_name].index[0]
            if st.button("Delete Cow", key="delete_cow_btn"):
                delete_document("cows", df.loc[selected_cow, "id"])
                st.success("Cow deleted.")
                log_audit_event(username, "COW_DELETED", f"Name: {selected_cow_name}")
                st.rerun()
            if st.button("Edit Cow", key="edit_cow_btn"):
                name = st.text_input("Cow Name", value=selected_cow_name, key="edit_cow_name")
                status = st.selectbox("Status", ["Lactating", "Dry", "Calf"], index=["Lactating", "Dry", "Calf"].index(df.loc[selected_cow, "status"]), key="edit_cow_status")
                gender = st.selectbox("Gender", ["Male", "Female", "Unknown"], index=["Male", "Female", "Unknown"].index(df.loc[selected_cow, "gender"]), key="edit_cow_gender")
                if st.button("Save Edit", key="save_edit_cow_btn"):
                    if update_document("cows", df.loc[selected_cow, "id"], {
                        "name": name.strip(),
                        "status": status,
                        "gender": gender
                    }):
                        st.success("Cow updated.")
                        log_audit_event(username, "COW_UPDATED", f"Name: {name}")
                        st.rerun()
                    else:
                        st.error("Failed to update cow.")

    elif selected_type == "Feed Inventory":
        st.warning("Feed Inventory is calculated from Feeds Used. Edit Feeds Used to update inventory.")
        df_used = load_table("feeds_used")
        if not df_used.empty:
            if search_term:
                df_used = df_used[df_used["feed_type"].str.lower().str.contains(search_term.lower())]
            df_used = to_date(df_used, "date")
            feed_names = df_used["feed_type"].unique().tolist()
            selected_feed_name = st.selectbox("Select Feed to Edit", feed_names, key="edit_feed_inventory_select")
            selected_feed = df_used[df_used["feed_type"] == selected_feed_name].index[0]
            if st.button("Delete Feed Usage", key="delete_feed_usage_btn"):
                delete_document("feeds_used", df_used.loc[selected_feed, "id"])
                st.success("Feed usage deleted.")
                log_audit_event(username, "FEED_USED_DELETED", f"Feed: {selected_feed_name}")
                st.rerun()
            if st.button("Edit Feed Usage", key="edit_feed_inventory_btn"):
                category = st.selectbox("Cow Category", ["Grown Cow", "Calf"], index=["Grown Cow", "Calf"].index(df_used.loc[selected_feed, "category"]), key="edit_feed_inventory_cat")
                qty = st.number_input("Quantity Used (kg)", value=df_used.loc[selected_feed, "quantity"], key="edit_feed_inventory_qty")
                if st.button("Save Edit", key="save_edit_feed_inventory_btn"):
                    if update_document("feeds_used", df_used.loc[selected_feed, "id"], {
                        "category": category,
                        "quantity": float(qty)
                    }):
                        st.success("Feed usage updated, affecting inventory.")
                        log_audit_event(username, "FEED_INVENTORY_UPDATED", f"Feed: {selected_feed_name}")
                        st.rerun()
                    else:
                        st.error("Failed to update feed usage.")

    elif selected_type == "Feeds Used":
        df = load_table("feeds_used")
        if not df.empty:
            if search_term:
                df = df[df["feed_type"].str.lower().str.contains(search_term.lower())]
            df = to_date(df, "date")
            feed_names = df["feed_type"].tolist()
            selected_feed_name = st.selectbox("Select Feed Usage by Name", feed_names, key="edit_feeds_used_select")
            selected_feed = df[df["feed_type"] == selected_feed_name].index[0]
            if st.button("Delete Feed Usage", key="delete_feeds_used_btn"):
                delete_document("feeds_used", df.loc[selected_feed, "id"])
                st.success("Feed usage deleted.")
                log_audit_event(username, "FEED_USED_DELETED", f"Feed: {selected_feed_name}")
                st.rerun()
            if st.button("Edit Feed Usage", key="edit_feeds_used_btn"):
                category = st.selectbox("Cow Category", ["Grown Cow", "Calf"], index=["Grown Cow", "Calf"].index(df.loc[selected_feed, "category"]), key="edit_feeds_used_cat")
                qty = st.number_input("Quantity Used (kg)", value=df_used.loc[selected_feed, "quantity"], key="edit_feeds_used_qty")
                if st.button("Save Edit", key="save_edit_feeds_used_btn"):
                    if update_document("feeds_used", df.loc[selected_feed, "id"], {
                        "category": category,
                        "quantity": float(qty)
                    }):
                        st.success("Feed usage updated.")
                        log_audit_event(username, "FEED_USED_UPDATED", f"Feed: {selected_feed_name}")
                        st.rerun()
                    else:
                        st.error("Failed to update feed usage.")

    elif selected_type == "Employees":
        df = load_table("employees")
        if not df.empty:
            if search_term:
                df = df[df["name"].str.lower().str.contains(search_term.lower())]
            employee_names = df["name"].tolist()
            selected_employee_name = st.selectbox("Select Employee by Name", employee_names, key="edit_employee_select")
            selected_employee = df[df["name"] == selected_employee_name].index[0]
            if st.button("Delete Employee", key="delete_employee_btn"):
                delete_document("employees", df.loc[selected_employee, "id"])
                st.success("Employee deleted.")
                log_audit_event(username, "EMPLOYEE_DELETED", f"Name: {selected_employee_name}")
                st.rerun()
            if st.button("Edit Employee", key="edit_employee_btn"):
                name = st.text_input("Employee Name", value=selected_employee_name, key="edit_employee_name")
                role_options = ["Staff", "Manager", "Milker", "Feeder", "Cleaner", "Supervisor"]
                role = st.selectbox("Role", role_options, index=role_options.index(df.loc[selected_employee, "role"]) if df.loc[selected_employee, "role"] in role_options else 0, key="edit_employee_role")
                salary = st.number_input("Monthly Salary (KES)", min_value=1, value=int(df.loc[selected_employee, "salary"]), step=1000, key="edit_employee_salary")
                phone = st.text_input("Phone Number", value=df.loc[selected_employee, "phone"], key="edit_employee_phone")
                status = st.selectbox("Status", ["Active", "On Leave"], index=["Active", "On Leave"].index(df.loc[selected_employee, "status"]) if df.loc[selected_employee, "status"] in ["Active", "On Leave"] else 0, key="edit_employee_status")
                if st.button("Save Edit", key="save_edit_employee_btn"):
                    if update_document("employees", df.loc[selected_employee, "id"], {
                        "name": name.strip(),
                        "role": role,
                        "salary": salary,
                        "phone": phone,
                        "status": status
                    }):
                        st.success("Employee updated.")
                        log_audit_event(username, "EMPLOYEE_UPDATED", f"Name: {name}")
                        st.rerun()
                    else:
                        st.error("Failed to update employee.")

    elif selected_type == "Observations":
        df = load_table("observations")
        if not df.empty:
            if search_term:
                df = df[df["note"].str.lower().str.contains(search_term.lower())]
            df = to_date(df, "date")
            observation_notes = df["note"].tolist()
            selected_note = st.selectbox("Select Observation by Note", observation_notes, key="edit_obs_select")
            selected_obs = df[df["note"] == selected_note].index[0]
            if st.button("Delete Observation", key="delete_obs_btn"):
                delete_document("observations", df.loc[selected_obs, "id"])
                st.success("Observation deleted.")
                log_audit_event(username, "OBSERVATION_DELETED", f"Note: {selected_note[:50]}")
                st.rerun()
            if st.button("Edit Observation", key="edit_obs_btn"):
                note = st.text_area("Observation", value=selected_note, key="edit_obs_text")
                if st.button("Save Edit", key="save_edit_obs_btn"):
                    if update_document("observations", df.loc[selected_obs, "id"], {"note": note.strip()}):
                        st.success("Observation updated.")
                        log_audit_event(username, "OBSERVATION_UPDATED", f"Note: {note[:50]}")
                        st.rerun()
                    else:
                        st.error("Failed to update observation.")

    elif selected_type == "Milk Production":
        df = load_table("milk_production")
        if not df.empty:
            if search_term:
                df = df[df["cow"].str.lower().str.contains(search_term.lower())]
            df = to_date(df, "date")
            cow_names = df["cow"].unique().tolist()
            selected_cow_name = st.selectbox("Select Cow by Name", cow_names, key="edit_milk_cow_select")
            selected_record = df[df["cow"] == selected_cow_name].index[0]
            if st.button("Delete Milk Record", key="delete_milk_btn"):
                delete_document("milk_production", df.loc[selected_record, "id"])
                st.success("Milk record deleted.")
                log_audit_event(username, "MILK_RECORD_DELETED", f"Cow: {selected_cow_name}")
                st.rerun()
            if st.button("Edit Milk Record", key="edit_milk_btn"):
                time_of_milking = st.selectbox("Time of Milking", ["Morning", "Lunch", "Evening"], index=["Morning", "Lunch", "Evening"].index(df.loc[selected_record, "time_of_milking"]), key="edit_milk_time")
                litres_sell = st.number_input("Litres for Sale", value=float(df.loc[selected_record, "litres_sell"]), min_value=0.0, step=0.1, key="edit_milk_sell")
                litres_calves = st.number_input("Litres for Calves", value=float(df.loc[selected_record, "litres_calves"]), min_value=0.0, step=0.1, key="edit_milk_calves")
                if st.button("Save Edit", key="save_edit_milk_btn"):
                    if update_document("milk_production", df.loc[selected_record, "id"], {
                        "time_of_milking": time_of_milking,
                        "litres_sell": float(litres_sell),
                        "litres_calves": float(litres_calves)
                    }):
                        st.success("Milk record updated.")
                        log_audit_event(username, "MILK_RECORD_UPDATED", f"Cow: {selected_cow_name}")
                        st.rerun()
                    else:
                        st.error("Failed to update milk record.")

    elif selected_type == "Health Records":
        df = load_table("health_records")
        if not df.empty:
            if search_term:
                df = df[df["cow_tag"].str.lower().str.contains(search_term.lower())]
            df = to_date(df, "date")
            cow_tags = df["cow_tag"].unique().tolist()
            selected_cow_tag = st.selectbox("Select Cow by Tag", cow_tags, key="edit_health_cow_select")
            selected_record = df[df["cow_tag"] == selected_cow_tag].index[0]
            if st.button("Delete Health Record", key="delete_health_btn"):
                delete_document("health_records", df.loc[selected_record, "id"])
                st.success("Health record deleted.")
                log_audit_event(username, "HEALTH_RECORD_DELETED", f"Cow Tag: {selected_cow_tag}")
                st.rerun()
            if st.button("Edit Health Record", key="edit_health_btn"):
                disease = st.text_input("Disease", value=df.loc[selected_record, "disease"], key="edit_health_disease")
                medicine = st.text_input("Medicine Given", value=df.loc[selected_record, "medicine"], key="edit_health_medicine")
                medicine_price = st.number_input("Medicine Price (KES)", value=float(df.loc[selected_record, "medicine_price"]), min_value=0.0, step=10.0, key="edit_health_price")
                date = st.date_input("Date", value=pd.to_datetime(df.loc[selected_record, "date"]).date(), key="edit_health_date")
                vaccinations = st.text_input("Vaccinations", value=df.loc[selected_record, "vaccinations"], key="edit_health_vacc")
                observations = st.text_area("Observations", value=df.loc[selected_record, "observations"], key="edit_health_obs")
                if st.button("Save Edit", key="save_edit_health_btn"):
                    if update_document("health_records", df.loc[selected_record, "id"], {
                        "disease": disease.strip(),
                        "medicine": medicine.strip(),
                        "medicine_price": float(medicine_price),
                        "date": date.isoformat(),
                        "vaccinations": vaccinations.strip(),
                        "observations": observations.strip()
                    }):
                        st.success("Health record updated.")
                        log_audit_event(username, "HEALTH_RECORD_UPDATED", f"Cow Tag: {selected_cow_tag}")
                        st.rerun()
                    else:
                        st.error("Failed to update health record.")

    elif selected_type == "AI Records":
        df = load_table("ai_records")
        if not df.empty:
            if search_term:
                df = df[df["cow_tag"].str.lower().str.contains(search_term.lower())]
            df = to_date(df, "ai_date")
            cow_tags = df["cow_tag"].unique().tolist()
            selected_cow_tag = st.selectbox("Select Cow by Tag", cow_tags, key="edit_ai_cow_select")
            selected_record = df[df["cow_tag"] == selected_cow_tag].index[0]
            if st.button("Delete AI Record", key="delete_ai_btn"):
                delete_document("ai_records", df.loc[selected_record, "id"])
                st.success("AI record deleted.")
                log_audit_event(username, "AI_RECORD_DELETED", f"Cow Tag: {selected_cow_tag}")
                st.rerun()
            if st.button("Edit AI Record", key="edit_ai_btn"):
                heat_date = st.date_input("Heat Detection Date", value=pd.to_datetime(df.loc[selected_record, "heat_date"]).date(), key="edit_ai_heat_date")
                heat_signs = st.multiselect("Heat Signs Observed", [
                    "Mounting other cows", "Standing to be mounted", "Swollen vulva",
                    "Clear mucus discharge", "Restlessness", "Decreased milk production"
                ], default=df.loc[selected_record, "heat_signs"].split(", ") if df.loc[selected_record, "heat_signs"] else [], key="edit_ai_heat_signs")
                ai_date = st.date_input("AI Date", value=pd.to_datetime(df.loc[selected_record, "ai_date"]).date(), key="edit_ai_date")
                ai_time = st.time_input("AI Time", value=pd.to_datetime(df.loc[selected_record, "ai_time"], format="%H:%M").time(), key="edit_ai_time")
                technician = st.text_input("Technician Name", value=df.loc[selected_record, "technician"], key="edit_ai_tech")
                technician_id = st.text_input("Technician ID", value=df.loc[selected_record, "technician_id"], key="edit_ai_tech_id")
                bull_id = st.text_input("Bull ID", value=df.loc[selected_record, "bull_id"], key="edit_ai_bull_id")
                bull_breed = st.text_input("Bull Breed", value=df.loc[selected_record, "bull_breed"], key="edit_ai_bull_breed")
                semen_batch = st.text_input("Semen Batch", value=df.loc[selected_record, "semen_batch"], key="edit_ai_semen_batch")
                semen_expiry = st.date_input("Semen Expiry Date", value=pd.to_datetime(df.loc[selected_record, "semen_expiry"]).date() if df.loc[selected_record, "semen_expiry"] else date.today(), key="edit_ai_semen_expiry")
                semen_quality = st.selectbox("Semen Quality", ["Poor", "Fair", "Good", "Excellent"], index=["Poor", "Fair", "Good", "Excellent"].index(df.loc[selected_record, "semen_quality"]), key="edit_ai_semen_quality")
                success_rating = st.slider("Procedure Rating", 1, 5, int(df.loc[selected_record, "success_rating"]), key="edit_ai_success_rating")
                expected_calving_date = st.date_input("Expected Calving Date", value=pd.to_datetime(df.loc[selected_record, "expected_calving_date"]).date(), key="edit_ai_calving_date")
                observations = st.text_area("Observations", value=df.loc[selected_record, "observations"], key="edit_ai_obs")
                if st.button("Save Edit", key="save_edit_ai_btn"):
                    if update_document("ai_records", df.loc[selected_record, "id"], {
                        "heat_date": heat_date.isoformat(),
                        "heat_signs": ", ".join(heat_signs),
                        "ai_date": ai_date.isoformat(),
                        "ai_time": ai_time.strftime("%H:%M"),
                        "technician": technician.strip(),
                        "technician_id": technician_id.strip(),
                        "bull_id": bull_id.strip(),
                        "bull_breed": bull_breed.strip(),
                        "semen_batch": semen_batch.strip(),
                        "semen_expiry": semen_expiry.isoformat() if semen_expiry else None,
                        "semen_quality": semen_quality,
                        "success_rating": success_rating,
                        "expected_calving_date": expected_calving_date.isoformat(),
                        "observations": observations.strip()
                    }):
                        st.success("AI record updated.")
                        log_audit_event(username, "AI_RECORD_UPDATED", f"Cow Tag: {selected_cow_tag}")
                        st.rerun()
                    else:
                        st.error("Failed to update AI record.")