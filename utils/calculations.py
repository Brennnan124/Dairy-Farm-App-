# dairy_farm_app/utils/calculations.py
import pandas as pd
from datetime import date, datetime
from firebase_utils import get_collection
from utils.data_loader import load_table, to_date

def get_feed_inventory():
    received = get_collection("feeds_received")
    used = get_collection("feeds_used")
    
    if received.empty and used.empty:
        return pd.DataFrame()
    
    if received.empty:
        received_grouped = pd.DataFrame(columns=["feed_type", "quantity"])
    else:
        received_grouped = received.groupby("feed_type")["quantity"].sum().reset_index()
    
    if used.empty:
        used_grouped = pd.DataFrame(columns=["feed_type", "quantity"])
    else:
        used_grouped = used.groupby("feed_type")["quantity"].sum().reset_index()
    
    inventory = pd.merge(
        received_grouped, 
        used_grouped, 
        on="feed_type", 
        how="outer",
        suffixes=("_received", "_used")
    ).fillna(0)
    
    inventory["remaining"] = inventory["quantity_received"] - inventory["quantity_used"]
    inventory["remaining"] = inventory["remaining"].clip(lower=0)
    
    return inventory

def get_available_feed_types():
    inventory = get_feed_inventory()
    if inventory.empty:
        return []
    available_feeds = inventory[inventory["remaining"] > 0]["feed_type"].tolist()
    return available_feeds

def get_all_cows():
    cows_df = load_table("cows")
    return cows_df["name"].tolist() if not cows_df.empty else []

def get_cows_by_status(status):
    cows_df = load_table("cows")
    return cows_df[cows_df["status"] == status]["name"].tolist() if not cows_df.empty else []

def calculate_feed_cost_used(start_date, end_date):
    """
    Calculate the cost of feed used based on FIFO (First-In-First-Out) method
    """
    # Load and filter feeds received
    feeds_received = load_table("feeds_received")
    if feeds_received.empty:
        return pd.DataFrame()
    
    feeds_received = to_date(feeds_received, "date")
    feeds_received = feeds_received.sort_values("date")  # Sort by date for FIFO
    
    # Load and filter feeds used
    feeds_used = load_table("feeds_used")
    if feeds_used.empty:
        return pd.DataFrame()
    
    feeds_used = to_date(feeds_used, "date")
    feeds_used = feeds_used[(feeds_used['date'] >= start_date) & (feeds_used['date'] <= end_date)]
    
    # For each feed usage, calculate cost based on available inventory at time of use
    feed_costs = []
    
    for _, usage in feeds_used.iterrows():
        usage_date = usage['date']
        feed_type = usage['feed_type']
        quantity_used = usage['quantity']
        
        # Get all receipts of this feed type before the usage date
        available_feed = feeds_received[
            (feeds_received['feed_type'] == feed_type) & 
            (feeds_received['date'] <= usage_date)
        ].copy()
        
        if available_feed.empty:
            # No feed available before usage date - use latest cost
            latest_feed = feeds_received[feeds_received['feed_type'] == feed_type]
            if not latest_feed.empty:
                latest_feed = latest_feed.sort_values('date').iloc[-1]
                cost_per_kg = latest_feed['cost'] / latest_feed['quantity']
                feed_cost = quantity_used * cost_per_kg
                feed_costs.append({
                    'date': usage_date,
                    'feed_type': feed_type,
                    'quantity': quantity_used,
                    'cost': feed_cost,
                    'method': 'latest_cost'
                })
            continue
        
        # Calculate cost using FIFO method
        remaining_quantity = quantity_used
        total_cost = 0
        
        for _, receipt in available_feed.sort_values('date').iterrows():
            if remaining_quantity <= 0:
                break
                
            receipt_quantity_available = receipt['quantity']
            receipt_cost_per_kg = receipt['cost'] / receipt['quantity']
            
            quantity_to_use = min(remaining_quantity, receipt_quantity_available)
            cost_for_this_receipt = quantity_to_use * receipt_cost_per_kg
            
            total_cost += cost_for_this_receipt
            remaining_quantity -= quantity_to_use
        
        feed_costs.append({
            'date': usage_date,
            'feed_type': feed_type,
            'quantity': quantity_used,
            'cost': total_cost,
            'method': 'fifo'
        })
    
    if not feed_costs:
        return pd.DataFrame()
    
    return pd.DataFrame(feed_costs)

def calculate_profit_per_cow(start_date, end_date):
    cows_df = load_table("cows")
    milk_df = load_table("milk_production")
    
    if not milk_df.empty and 'date' in milk_df.columns:
        milk_df = to_date(milk_df, "date")
        milk_df = milk_df[(milk_df["date"] >= start_date) & (milk_df["date"] <= end_date)]
    
    # Calculate feed cost using the improved method
    feeds_used_cost = calculate_feed_cost_used(start_date, end_date)
    if not feeds_used_cost.empty and 'cost' in feeds_used_cost.columns:
        total_feed_cost = feeds_used_cost['cost'].sum()
    else:
        total_feed_cost = 0
    
    health_df = load_table("health_records")
    if not health_df.empty and 'date' in health_df.columns:
        health_df = to_date(health_df, "date")
        health_df = health_df[(health_df["date"] >= start_date) & (health_df["date"] <= end_date)]
        total_health_cost = health_df["cost"].sum() if 'cost' in health_df.columns else 0
    else:
        total_health_cost = 0

    if not cows_df.empty and 'status' in cows_df.columns:
        lactating_cows = cows_df[cows_df["status"] == "Lactating"]
    else:
        return pd.DataFrame()
    
    if lactating_cows.empty:
        return pd.DataFrame()
    
    if milk_df.empty:
        return pd.DataFrame()
    
    # Use individual cow records (litres_sell) for profit per cow calculation
    milk_per_cow = milk_df.groupby("cow")["litres_sell"].sum().reset_index()
    milk_per_cow["revenue"] = milk_per_cow["litres_sell"] * 43
    
    # Allocate costs based on milk production rather than equally
    total_milk_produced = milk_per_cow["litres_sell"].sum()
    
    if total_milk_produced > 0:
        # Calculate cost per liter
        cost_per_liter = (total_feed_cost + total_health_cost) / total_milk_produced
        
        result = pd.merge(lactating_cows[["name"]], milk_per_cow, 
                         left_on="name", right_on="cow", how="left")
        
        result["litres_sell"] = result["litres_sell"].fillna(0)
        result["revenue"] = result["revenue"].fillna(0)
        
        # Allocate costs based on milk production
        result["feed_cost"] = result["litres_sell"] * cost_per_liter
        result["profit"] = result["revenue"] - result["feed_cost"]
        
        result = result.rename(columns={
            "name": "Cow",
            "litres_sell": "Milk Produced (L)",
            "revenue": "Revenue (KES)",
            "feed_cost": "Cost (KES)",
            "profit": "Profit (KES)"
        })
        
        return result[["Cow", "Milk Produced (L)", "Revenue (KES)", "Cost (KES)", "Profit (KES)"]]
    else:
        return pd.DataFrame()
