# dairy_farm_app/page_modules/ai.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from utils.data_loader import to_date
from utils.calculations import get_all_cows
from firebase_utils import get_collection, add_document, update_document, log_audit_event
from page_modules.staff_performance import record_staff_performance
import plotly.express as px

# ✅ Helper function to make sure required columns always exist
def ensure_ai_columns(df):
    """Make sure required columns always exist in ai_data."""
    required_cols = ["pregnancy_status", "calving_outcome", "cost"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    return df


def get_ai_records():
    return get_collection("ai_records")


def add_ai_record(cow_tag, heat_date, heat_signs, ai_date, ai_time, technician, technician_id, bull_id, bull_breed,
                 semen_batch, semen_expiry, semen_quality, expected_calving_date, success_rating, observations):
    try:
        success = add_document("ai_records", {
            "cow_tag": cow_tag,
            "heat_date": heat_date,
            "heat_signs": heat_signs,
            "ai_date": ai_date,
            "ai_time": ai_time,
            "technician": technician,
            "technician_id": technician_id,
            "bull_id": bull_id,
            "bull_breed": bull_breed,
            "semen_batch": semen_batch,
            "semen_expiry": semen_expiry,
            "semen_quality": semen_quality,
            "expected_calving_date": expected_calving_date,
            "success_rating": success_rating,
            "observations": observations,
            "cost": None,
            "pregnancy_status": None,
            "calving_outcome": None
        })

        if success:
            log_audit_event("Staff", "AI_RECORD_ADDED", f"{cow_tag}: {bull_breed}")
        return success
    except Exception as e:
        st.error(f"Error saving AI record: {e}")
        return False


def update_ai_cost(record_id, cost):
    success = update_document("ai_records", record_id, {"cost": cost})
    if success:
        log_audit_event("Manager", "AI_COST_UPDATED", f"Record ID: {record_id}, Cost: {cost}")
    return success


def staff_ai_page():
    st.title("🤰 Artificial Insemination")

    tab1, tab2, tab3 = st.tabs(["New AI Record", "AI History", "Breeding Analytics"])

    with tab1:
        with st.expander("➕ Add New AI Record", expanded=True):
            search_cow = st.text_input("Search Cow", key="ai_cow_search")
            cow_options = get_all_cows()
            filtered_cows = [c for c in cow_options if search_cow.lower() in c.lower()] if search_cow else cow_options
            cow_tag = st.selectbox("Select Cow", filtered_cows)

            col1, col2 = st.columns(2)
            with col1:
                heat_date = st.date_input("Heat Detection Date", value=date.today())
                heat_signs = st.multiselect("Heat Signs Observed", [
                    "Mounting other cows", "Standing to be mounted", "Swollen vulva",
                    "Clear mucus discharge", "Restlessness", "Decreased milk production"
                ])
            with col2:
                ai_date = st.date_input("AI Date", value=date.today())
                ai_time = st.time_input("AI Time", value=datetime.now().time())

            technician = st.text_input("Technician Name")
            technician_id = st.text_input("Technician ID (if available)")

            col3, col4 = st.columns(2)
            with col3:
                bull_id = st.text_input("Bull ID")
                bull_breed = st.text_input("Bull Breed")
            with col4:
                semen_batch = st.text_input("Semen Batch")
                semen_expiry = st.date_input("Semen Expiry Date")

            semen_quality = st.selectbox("Semen Quality", ["Poor", "Fair", "Good", "Excellent"])
            success_rating = st.slider("Procedure Rating", 1, 5, 3)

            expected_calving_date = st.date_input("Expected Calving Date",
                                               value=ai_date + timedelta(days=280))

            observations = st.text_area("Observations")

            if st.button("Submit AI Record"):
                success = add_ai_record(
                    cow_tag,
                    heat_date.isoformat(),
                    ", ".join(heat_signs),
                    ai_date.isoformat(),
                    ai_time.strftime("%H:%M"),
                    technician,
                    technician_id,
                    bull_id,
                    bull_breed,
                    semen_batch,
                    semen_expiry.isoformat() if semen_expiry else None,
                    semen_quality,
                    expected_calving_date.isoformat(),
                    success_rating,
                    observations
                )
                if success:
                    st.success("AI record added successfully!")
                    record_staff_performance("Staff", f"AI record for {cow_tag}")
                else:
                    st.error("Failed to add AI record.")

    with tab2:
        st.subheader("AI History")
        ai_data = get_ai_records()
        if not ai_data.empty:
            ai_data = ensure_ai_columns(ai_data)   # ✅ Ensure required columns
            if "ai_date" in ai_data.columns:
                ai_data = to_date(ai_data, "ai_date")
                ai_data_display = ai_data.drop(columns=["id"])
                # Use only available columns to avoid KeyError
                display_columns = [col for col in ['cow_tag', 'ai_date', 'technician', 'bull_breed', 'pregnancy_status', 'calving_outcome'] if col in ai_data_display.columns]
                st.dataframe(ai_data_display[display_columns])
            else:
                st.error("Error: 'ai_date' column not found in AI records.")
        else:
            st.info("No AI records available")

    with tab3:
        st.subheader("Breeding Analytics")
        ai_data = get_ai_records()
        if not ai_data.empty:
            ai_data = ensure_ai_columns(ai_data)   # ✅ Ensure required columns
            if "ai_date" in ai_data.columns:
                ai_data = to_date(ai_data, "ai_date")
                col1, col2 = st.columns(2)

                with col1:
                    pregnant_count = len(ai_data[ai_data['pregnancy_status'] == 'Pregnant']) if 'pregnancy_status' in ai_data.columns else 0
                    total_ai = len(ai_data)
                    conception_rate = (pregnant_count / total_ai * 100) if total_ai > 0 else 0

                    st.metric("Conception Rate", f"{conception_rate:.1f}%")

                    if 'technician' in ai_data.columns:
                        tech_success = ai_data.groupby('technician')['pregnancy_status'].apply(
                            lambda x: (x == 'Pregnant').sum() / len(x) * 100 if not x.empty else 0
                        ).reset_index()
                        tech_success.columns = ['Technician', 'Success Rate (%)']
                        st.write("**Success by Technician**")
                        st.dataframe(tech_success)

                with col2:
                    if 'bull_breed' in ai_data.columns:
                        breed_success = ai_data.groupby('bull_breed')['pregnancy_status'].apply(
                            lambda x: (x == 'Pregnant').sum() / len(x) * 100 if not x.empty else 0
                        ).reset_index()
                        breed_success.columns = ['Bull Breed', 'Success Rate (%)']
                        st.write("**Success by Bull Breed**")
                        st.dataframe(breed_success)

                        st.write("**AI Events Calendar**")
                        ai_calendar = ai_data[['ai_date', 'cow_tag', 'technician']]
                        st.dataframe(ai_calendar)
            else:
                st.error("Error: 'ai_date' column not found in AI records for analytics.")
        else:
            st.info("No AI data available for analytics")


def manager_ai_page():
    st.title("🤰 Artificial Insemination Management")

    tab1, tab2, tab3 = st.tabs(["AI Records", "Cost Management", "Advanced Analytics"])

    ai_data = get_ai_records()
    if not ai_data.empty:
        ai_data = ensure_ai_columns(ai_data)   # ✅ Ensure required columns
        if "ai_date" in ai_data.columns:
            ai_data = to_date(ai_data, "ai_date")

    with tab1:
        if not ai_data.empty:
            st.subheader("AI Records")
            ai_data_display = ai_data.drop(columns=["id"])
            st.dataframe(ai_data_display)
        else:
            st.info("No AI records available")

    with tab2:
        st.subheader("Cost Management")
        st.info("Add costs to AI records that don't have pricing yet")

        if not ai_data.empty:
            if 'cost' in ai_data.columns:
                unpriced_records = ai_data[ai_data['cost'].isna()]
            else:
                unpriced_records = ai_data
                ai_data['cost'] = None

            if unpriced_records.empty:
                st.success("All AI records have costs assigned!")
            else:
                for idx, row in unpriced_records.iterrows():
                    with st.expander(f"Unpriced: {row['cow_tag']} - {row['bull_breed']} ({row['ai_date']})"):
                        st.write(f"**Technician:** {row['technician']}")
                        st.write(f"**Bull ID:** {row['bull_id']}")
                        st.write(f"**Semen Batch:** {row['semen_batch']}")
                        if 'pregnancy_status' in row:
                            st.write(f"**Pregnancy Status:** {row['pregnancy_status']}")
                        st.write(f"**Observations:** {row['observations']}")
                        cost = st.number_input("AI Cost (KES)", min_value=0.0, step=100.0, key=f"cost_{row['id']}")
                        if st.button("Save Cost", key=f"save_{row['id']}"):
                            update_ai_cost(row['id'], cost)
                            st.success("Cost saved successfully!")
                            st.rerun()

    with tab3:
        st.subheader("Advanced Breeding Analytics")
        if not ai_data.empty:
            st.write("**Breeding Efficiency Over Time**")

            ai_data['ai_date'] = pd.to_datetime(ai_data['ai_date'])
            monthly_success = ai_data.groupby(ai_data['ai_date'].dt.to_period('M'))['pregnancy_status'].apply(
                lambda x: (x == 'Pregnant').sum() / len(x) * 100 if not x.empty else 0
            ).reset_index()
            monthly_success.columns = ['Month', 'Success Rate (%)']
            monthly_success['Month'] = monthly_success['Month'].astype(str)

            fig = px.line(monthly_success, x='Month', y='Success Rate (%)',
                         title='Monthly Conception Rate')
            st.plotly_chart(fig)

            if 'cost' in ai_data.columns and not ai_data['cost'].isna().all():
                cost_success = ai_data.groupby('bull_breed').agg({
                    'cost': 'mean',
                    'pregnancy_status': lambda x: (x == 'Pregnant').sum() / len(x) * 100 if not x.empty else 0
                }).reset_index()
                cost_success.columns = ['Bull Breed', 'Average Cost', 'Success Rate (%)']

                fig2 = px.scatter(cost_success, x='Average Cost', y='Success Rate (%)',
                                 hover_data=['Bull Breed'], title='Cost vs Success Rate by Bull Breed')
                st.plotly_chart(fig2)
            else:
                st.info("No cost data available for cost vs success rate analysis")
        else:
            st.info("No AI data available for analytics")
