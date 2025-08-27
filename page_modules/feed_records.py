import streamlit as st
from firebase_utils import add_document, log_audit_event
from utils.calculations import get_available_feed_types
from page_modules.staff_performance import record_staff_performance
from datetime import date

def feed_records_page(username):
    st.title("🍽 Feed Records")
    
    st.subheader("Record Feed Usage")
    available_feeds = get_available_feed_types()
    if not available_feeds:
        st.warning("No feed available. Manager needs to add feed receipts.")
    else:
        search_feed = st.text_input("Search Feed", key="feed_search")
        filtered_feeds = [f for f in available_feeds if search_feed.lower() in f.lower()] if search_feed else available_feeds
        feed_type = st.selectbox("Feed Type", filtered_feeds, key="feed_type")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Cow Category", ["Grown Cow", "Calf"], key="feed_category")
            quantity = st.number_input("Quantity Used (kg)", min_value=0.0, max_value=100000.0, key="feed_qty")
        with col2:
            date_used = st.date_input("Date", value=date.today(), key="feed_date")
        
        if st.button("Record Feed Usage"):
            if quantity <= 0 or not feed_type:
                st.warning("Quantity must be positive and feed type is required.")
            else:
                add_document("feeds_used", {
                    "date": date_used.isoformat(),
                    "category": category,
                    "feed_type": feed_type,
                    "quantity": float(quantity)  # Store as float
                })
                st.success("Feed usage recorded!")
                record_staff_performance(username, f"Feed usage recorded for {feed_type}")
                log_audit_event(username, "FEED_USED", f"{quantity}kg of {feed_type} for {category}")
