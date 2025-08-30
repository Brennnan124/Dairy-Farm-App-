import streamlit as st
from firebase_utils import add_document, log_audit_event, get_collection, update_document
from utils.calculations import get_available_feed_types, get_cows_by_status, get_all_cows, get_feed_inventory
from page_modules.staff_performance import record_staff_performance
from datetime import date
import pandas as pd

def feed_records_page(username):
    st.title("🍽 Feed Records")
    
    # Section 1: Cow Categorization and Feed Allocation
    st.subheader("Cow Categorization & Feed Allocation")
    
    # Get all lactating cows
    lactating_cows = get_cows_by_status("Lactating")
    
    if not lactating_cows:
        st.warning("No lactating cows found. Please add lactating cows in the Manager Dashboard.")
        return
    
    # Load or initialize cow categories
    cow_categories = load_cow_categories()
    
    # Create two columns for high and low yielders
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**High Yielders**")
        high_yielders = st.multiselect(
            "Select high yielding cows",
            lactating_cows,
            default=cow_categories.get("high_yielders", []),
            key="high_yielders_select"
        )
    
    with col2:
        st.write("**Low Yielders**")
        low_yielders = st.multiselect(
            "Select low yielding cows",
            lactating_cows,
            default=cow_categories.get("low_yielders", []),
            key="low_yielders_select"
        )
    
    # Check for duplicates
    duplicates = set(high_yielders) & set(low_yielders)
    if duplicates:
        st.error(f"Error: The following cows are in both categories: {', '.join(duplicates)}")
        return
    
    # Calculate total dairy meal requirement
    total_dairy_meal = (len(high_yielders) * 7) + (len(low_yielders) * 4)
    
    st.write(f"**Daily Dairy Meal Requirement:** {total_dairy_meal}kg")
    st.write(f"- {len(high_yielders)} high yielders × 7kg = {len(high_yielders) * 7}kg")
    st.write(f"- {len(low_yielders)} low yielders × 4kg = {len(low_yielders) * 4}kg")
    
    # Custom feed amounts
    st.subheader("Custom Feed Amounts")
    col3, col4 = st.columns(2)
    with col3:
        high_yielder_amount = st.number_input("High yielder amount (kg)", min_value=0.0, max_value=20.0, 
                                            value=7.0, step=0.5, key="high_amount")
    with col4:
        low_yielder_amount = st.number_input("Low yielder amount (kg)", min_value=0.0, max_value=20.0, 
                                           value=4.0, step=0.5, key="low_amount")
    
    # Recalculate with custom amounts
    custom_total = (len(high_yielders) * high_yielder_amount) + (len(low_yielders) * low_yielder_amount)
    st.write(f"**Custom Daily Requirement:** {custom_total}kg")
    
    # Check inventory
    inventory = get_feed_inventory()
    dairy_meal_inventory = 0
    if not inventory.empty and "Dairy Meal" in inventory["feed_type"].values:
        dairy_meal_row = inventory[inventory["feed_type"] == "Dairy Meal"]
        dairy_meal_inventory = dairy_meal_row["remaining"].values[0]
    
    st.write(f"**Current Dairy Meal Inventory:** {dairy_meal_inventory}kg")
    
    if dairy_meal_inventory < custom_total:
        st.error(f"⚠️ Not enough Dairy Meal in inventory! Need {custom_total}kg, but only {dairy_meal_inventory}kg available.")
    
    # Save categories and deduct feed
    col5, col6 = st.columns(2)
    with col5:
        if st.button("Save Categories Only", key="save_categories"):
            save_cow_categories(high_yielders, low_yielders)
            st.success("Cow categories saved!")
            log_audit_event(username, "COW_CATEGORIES_SAVED", 
                          f"High: {len(high_yielders)}, Low: {len(low_yielders)}")
    
    with col6:
        if st.button("Save & Deduct Dairy Meal", type="primary", key="deduct_feed"):
            if dairy_meal_inventory < custom_total:
                st.error("Cannot deduct - insufficient inventory")
            else:
                # Save categories
                save_cow_categories(high_yielders, low_yielders)
                
                # Record the dairy meal usage
                add_document("feeds_used", {
                    "date": date.today().isoformat(),
                    "category": "Lactating Cows",
                    "feed_type": "Dairy Meal",
                    "quantity": float(custom_total),
                    "automated": True,
                    "note": f"Auto-deducted: {len(high_yielders)} high yielders @{high_yielder_amount}kg, {len(low_yielders)} low yielders @{low_yielder_amount}kg"
                })
                
                # Record individual allocations for profit analysis
                for cow in high_yielders:
                    add_document("feed_allocations", {
                        "date": date.today().isoformat(),
                        "cow": cow,
                        "feed_type": "Dairy Meal",
                        "amount": float(high_yielder_amount),
                        "yield_category": "High",
                        "recorded_by": username
                    })
                
                for cow in low_yielders:
                    add_document("feed_allocations", {
                        "date": date.today().isoformat(),
                        "cow": cow,
                        "feed_type": "Dairy Meal",
                        "amount": float(low_yielder_amount),
                        "yield_category": "Low",
                        "recorded_by": username
                    })
                
                st.success(f"Saved categories and deducted {custom_total}kg of Dairy Meal!")
                record_staff_performance(username, f"Auto-deducted {custom_total}kg Dairy Meal")
                log_audit_event(username, "FEED_AUTO_DEDUCT", 
                              f"Dairy Meal: {custom_total}kg, High: {len(high_yielders)}, Low: {len(low_yielders)}")
    
    st.markdown("---")
    
    # Manual Feed Recording (existing code)
    st.subheader("Manual Feed Recording")
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
            quantity = st.number_input("Quantity Used (kg)", min_value=0.0, max_value=100000.0, step=None, format="%f", key="feed_qty")
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
                    "quantity": float(quantity)
                })
                st.success("Feed usage recorded!")
                record_staff_performance(username, f"Feed usage recorded for {feed_type}")
                log_audit_event(username, "FEED_USED", f"{quantity}kg of {feed_type} for {category}")

# Helper functions for cow categories
def load_cow_categories():
    """Load saved cow categories from Firebase"""
    categories = {"high_yielders": [], "low_yielders": []}
    
    # Try to load from a dedicated collection
    try:
        saved_categories = get_collection("cow_categories")
        if not saved_categories.empty and len(saved_categories) > 0:
            latest = saved_categories.iloc[-1]  # Get the most recent
            categories["high_yielders"] = latest.get("high_yielders", [])
            categories["low_yielders"] = latest.get("low_yielders", [])
    except Exception as e:
        st.error(f"Error loading cow categories: {str(e)}")
    
    return categories

def save_cow_categories(high_yielders, low_yielders):
    """Save cow categories to Firebase using correct document IDs"""
    # Save the category definitions
    add_document("cow_categories", {
        "date": date.today().isoformat(),
        "high_yielders": high_yielders,
        "low_yielders": low_yielders,
        "total_high": len(high_yielders),
        "total_low": len(low_yielders)
    })
    
    # Get all cows with their document IDs
    cows_data = get_collection("cows")
    if not cows_data.empty:
        # Create a mapping from cow name to document ID
        name_to_id = {}
        for idx, row in cows_data.iterrows():
            # The document ID is stored in the 'id' column
            name_to_id[row["name"]] = row["id"]
        
        # Update cow documents with their category
        for cow_name in high_yielders:
            if cow_name in name_to_id:
                update_document("cows", name_to_id[cow_name], {"yield_category": "High"})
            else:
                st.error(f"Warning: Cow '{cow_name}' not found in database")
        
        for cow_name in low_yielders:
            if cow_name in name_to_id:
                update_document("cows", name_to_id[cow_name], {"yield_category": "Low"})
            else:
                st.error(f"Warning: Cow '{cow_name}' not found in database")
        
        # Mark lactating cows that aren't categorized as "Uncategorized"
        for idx, row in cows_data.iterrows():
            if (row["status"] == "Lactating" and 
                row["name"] not in high_yielders and 
                row["name"] not in low_yielders):
                update_document("cows", row["id"], {"yield_category": "Uncategorized"})
