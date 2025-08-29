# dairy_farm_app/utils/calculations.py
import pandas as pd
from datetime import date
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
    Calculate the cost of feed used based on the average cost of each feed type
    from the feeds_received records.
    """
    # Load feeds received to calculate average cost per feed type
    feeds_received = load_table("feeds_received")
    if feeds_received.empty:
        return pd.DataFrame()
    
    feeds_received = to_date(feeds_received, "date")
    
    # Calculate average cost per kg for each feed type
    feed_costs = {}
    for feed_type in feeds_received['feed_type'].unique():
        feed_data = feeds_received[feeds_received['feed_type'] == feed_type]
        total_cost = feed_data['cost'].sum()
        total_quantity = feed_data['quantity'].sum()
        if total_quantity > 0:
            feed_costs[feed_type] = total_cost / total_quantity
        else:
            feed_costs[feed_type] = 0
    
    # Load feeds used
    feeds_used = load_table("feeds_used")
    if feeds_used.empty:
        return pd.DataFrame()
    
    feeds_used = to_date(feeds_used, "date")
    feeds_used = feeds_used[(feeds_used['date'] >= start_date) & (feeds_used['date'] <= end_date)]
    
    # Calculate cost for each feed usage
    feeds_used['cost'] = feeds_used.apply(
        lambda row: row['quantity'] * feed_costs.get(row['feed_type'], 0), 
        axis=1
    )
    
    return feeds_used

def calculate_profit_per_cow(start_date, end_date):
    cows_df = load_table("cows")
    milk_df = load_table("milk_production")  # Use individual cow records, not totals
    
    if not milk_df.empty and 'date' in milk_df.columns:
        milk_df = to_date(milk_df, "date")
        milk_df = milk_df[(milk_df["date"] >= start_date) & (milk_df["date"] <= end_date)]
    
    # Calculate feed cost used (based on actual consumption)
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
    
    if 'status' in cows_df.columns:
        num_grown_cows = len(cows_df[cows_df["status"].isin(["Lactating", "Dry"])])
    else:
        num_grown_cows = 0
    
    cost_per_cow = (total_feed_cost + total_health_cost) / num_grown_cows if num_grown_cows > 0 else 0
    
    result = pd.merge(lactating_cows[["name"]], milk_per_cow, 
                     left_on="name", right_on="cow", how="left")
    
    result["litres_sell"] = result["litres_sell"].fillna(0)
    result["revenue"] = result["revenue"].fillna(0)
    
    result["feed_cost"] = cost_per_cow
    result["profit"] = result["revenue"] - result["feed_cost"]
    
    result = result.rename(columns={
        "name": "Cow",
        "litres_sell": "Milk Produced (L)",
        "revenue": "Revenue (KES)",
        "feed_cost": "Cost (KES)",
        "profit": "Profit (KES)"
    })
    
    return result[["Cow", "Milk Produced (L)", "Revenue (KES)", "Cost (KES)", "Profit (KES)"]]
