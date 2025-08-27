import streamlit as st
import pandas as pd
from datetime import date
from utils.data_loader import load_table, to_date
from utils.helpers import show_table, money, liters
from utils.calculations import get_feed_inventory, get_available_feed_types, get_all_cows
from firebase_utils import add_document, log_audit_event
from page_modules.staff_performance import record_staff_performance

def dashboard_page(role, username):
    st.title("🐄 Dairy Farm Management System")
    
    all_milk = to_date(load_table("milk_production"), "date")
    all_cows = load_table("cows")
    
    if role == "Staff":
        st.header("Data Overview")
        
        if not all_milk.empty and 'date' in all_milk.columns:
            todays_milk = all_milk[all_milk["date"] == date.today()]
        else:
            todays_milk = pd.DataFrame()
        
        if not todays_milk.empty:
            st.subheader("Milk Production for Today")
            morning = todays_milk[todays_milk["time_of_milking"] == "Morning"]["litres_sell"].sum()
            lunch = todays_milk[todays_milk["time_of_milking"] == "Lunch"]["litres_sell"].sum()
            evening = todays_milk[todays_milk["time_of_milking"] == "Evening"]["litres_sell"].sum()
            total = morning + lunch + evening
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Morning", f"{morning:.1f} L", delta_color="off")
            col2.metric("Lunch", f"{lunch:.1f} L", delta_color="off")
            col3.metric("Evening", f"{evening:.1f} L", delta_color="off")
            col4.metric("Total", f"{total:.1f} L", delta=f"{total:.1f} L today", delta_color="normal")
        else:
            st.info("No milk production records for today.")

        with st.expander("📝 Record Observations", expanded=False):
            note = st.text_area("Observation / Occurrence", key="obs_text")
            if st.button("Save Observation", key="obs_btn"):
                if note.strip():
                    add_document("observations", {
                        "date": date.today().isoformat(),
                        "note": note.strip()
                    })
                    st.success("Observation saved.")
                    log_audit_event(username, "OBSERVATION", f"{note[:50]}...")
                else:
                    st.warning("Write something before saving.")

    if role == "Manager":
        st.header("Manager Dashboard")

        colA, colB = st.columns(2)
        with colA:
            with st.expander("➕ Add Cow", expanded=True):
                name = st.text_input("Cow Name", key="cow_name_input")
                cow_status_options = ["Lactating", "Dry", "Calf"]
                cow_status = st.selectbox("Status", cow_status_options, key="cow_status_select")
                gender = "Female"  # Automatically set to Female for lactating/dry
                if st.button("Add Cow", key="add_cow_btn"):
                    if not name.strip():
                        st.warning("Cow name is required.")
                    else:
                        cow_data = {"name": name.strip(), "status": cow_status, "gender": gender}
                        if cow_status == "Calf":
                            gender = st.selectbox("Gender", ["Male", "Female", "Unknown"], key="cow_gender_select")
                            cow_data["gender"] = gender
                        add_document("cows", cow_data)
                        st.success(f"Cow '{name}' added.")
                        log_audit_event(username, "COW_ADDED", f"{name} ({cow_status})")

        with colB:
            with st.expander("📦 Record Feeds Received", expanded=True):
                feeds_df = load_table("feeds_received")
                existing_feeds = feeds_df["feed_type"].unique().tolist() if not feeds_df.empty else []
                new_feed = st.checkbox("New Feed Type", key="new_feed_check")
                if new_feed:
                    fr_type = st.text_input("Enter New Feed Type", key="fr_custom_type")
                else:
                    fr_type = st.selectbox("Feed Type", existing_feeds, key="fr_type")
                fr_qty = st.number_input("Quantity (kg)", min_value=0, max_value=100000, step=1, format="%d", value=0)
                fr_cost = st.number_input("Total Cost (KES)", min_value=0, max_value=10000000, step=1, format="%d", value=0)
                if st.button("Save Feed Received", key="save_fr_btn"):
                    if fr_qty <= 0 or fr_cost < 0:
                        st.warning("Quantity must be > 0 and cost cannot be negative.")
                    elif not fr_type.strip():
                        st.warning("Feed type is required.")
                    else:
                        add_document("feeds_received", {
                            "date": date.today().isoformat(),
                            "feed_type": fr_type.strip(),
                            "quantity": fr_qty,  # Removed float() to store as integer
                            "cost": fr_cost      # Removed float() to store as integer
                        })
                        st.success("Feed receipt recorded.")
                        log_audit_event(username, "FEED_RECEIVED", f"{fr_qty}kg of {fr_type} for KES {fr_cost}")

        st.markdown("---")
        
        with st.expander("📊 Feed Inventory", expanded=True):
            inventory = get_feed_inventory()
            if inventory.empty:
                st.info("No feed inventory data available. Ensure feeds are recorded in 'Feeds Received' and 'Feeds Used'.")
                st.write("Debug: feeds_received or feeds_used is empty")  # Moved debug here
            else:
                def style_black(row):
                    return ['color: white; background-color: black'] * len(row)
                styled_inventory = inventory.style.apply(style_black, axis=1)
                st.dataframe(styled_inventory.format({"quantity_received": "{:,.1f} kg", "quantity_used": "{:,.1f} kg", "remaining": "{:,.1f} kg"}), use_container_width=True)
                critical_inventory = inventory[inventory["remaining"] < 50]
                warning_inventory = inventory[(inventory["remaining"] >= 50) & (inventory["remaining"] < 100)]
                if not critical_inventory.empty:
                    for _, row in critical_inventory.iterrows():
                        st.error(f"🚨 Critical inventory for {row['feed_type']}: only {row['remaining']:,.1f} kg remaining!")
                if not warning_inventory.empty:
                    for _, row in warning_inventory.iterrows():
                        st.warning(f"⚠️ Low inventory for {row['feed_type']}: {row['remaining']:,.1f} kg remaining")

        with st.expander("🐄 Cow List", expanded=False):
            cows = load_table("cows")
            if not cows.empty:
                cows_display = cows.drop(columns=["id"])  # Remove id
                show_table(cows_display, "Cows", search_cols=["name", "status", "gender"], page_size=15, key_prefix="cows_tbl")

        with st.expander("📦 Feeds Received", expanded=False):
            df = load_table("feeds_received")
            if not df.empty:
                df = to_date(df, "date")
                df_display = df[["date", "feed_type", "quantity", "cost"]].copy()  # Only these columns
                df_display["quantity"] = df_display["quantity"].apply(lambda x: f"{x:,.0f} kg")
                df_display["cost"] = df_display["cost"].apply(money)
                show_table(df_display, "Feeds Received", page_size=15, key_prefix="fr_tbl")
            else:
                st.info("No feed receipts yet.")

        with st.expander("🍽 Feeds Used", expanded=False):
            df = load_table("feeds_used")
            if not df.empty:
                df = to_date(df, "date")
                df_fmt = df.copy()
                df_fmt["quantity"] = df_fmt["quantity"].apply(lambda x: f"{x:,.0f} kg")
                show_table(df_fmt, "Feeds Used", search_cols=["category", "feed_type"], page_size=15, key_prefix="fu_tbl")
            else:
                st.info("No feed usage records yet.")

        with st.expander("🥛 Milk Production", expanded=False):
            df = load_table("milk_production")
            if not df.empty:
                df = to_date(df, "date")
                df_fmt = df.copy()
                df_fmt["litres_sell"] = df_fmt["litres_sell"].apply(liters)
                df_fmt["litres_calves"] = df_fmt["litres_calves"].apply(liters)
                df_display = df_fmt.drop(columns=["id"])  # Remove id
                show_table(df_display, "Milk Production", search_cols=["cow", "time_of_milking"], page_size=20, key_prefix="milk_tbl")
            else:
                st.info("No milk records yet.")

        with st.expander("📝 Observations", expanded=False):
            df = load_table("observations")
            if not df.empty:
                df = to_date(df, "date")
                df_display = df.drop(columns=["id"])  # Remove id
                show_table(df_display, "Observations", search_cols=["note"], page_size=10, key_prefix="obs_tbl")
            else:
                st.info("No observations yet.")
