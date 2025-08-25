# dairy_farm_app/utils/calculations.py
import pandas as pd
from datetime import date
from firebase_utils import get_collection
from utils.data_loader import load_table, to_date

def get_feed_inventory():
    received = get_collection("feeds_received")
    used = get_collection("feeds_used")
    
    # Debug: Check data availability and structure
    if received is not None:
        print(f"Debug: feeds_received shape: {received.shape}, columns: {received.columns.tolist()}")
    else:
        print("Debug: feeds_received is None")
    if used is not None:
        print(f"Debug: feeds_used shape: {used.shape}, columns: {used.columns.tolist()}")
    else:
        print("Debug: feeds_used is None")
    
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

# Rest of the functions remain unchanged...
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

def calculate_profit_per_cow(start_date, end_date):
    cows_df = load_table("cows")
    milk_df = load_table("milk_production")
    
    if not milk_df.empty and 'date' in milk_df.columns:
        milk_df = to_date(milk_df, "date")
        milk_df = milk_df[(milk_df["date"] >= start_date) & (milk_df["date"] <= end_date)]
    
    feeds_used_df = load_table("feeds_used")
    if not feeds_used_df.empty and 'date' in feeds_used_df.columns:
        feeds_used_df = to_date(feeds_used_df, "date")
        feeds_used_df = feeds_used_df[(feeds_used_df["date"] >= start_date) & (feeds_used_df["date"] <= end_date)]
    
    health_df = load_table("health_records")
    if not health_df.empty and 'date' in health_df.columns:
        health_df = to_date(health_df, "date")
        health_df = health_df[(health_df["date"] >= start_date) & (health_df["date"] <= end_date)]

    if not cows_df.empty and 'status' in cows_df.columns:
        lactating_cows = cows_df[cows_df["status"] == "Lactating"]
    else:
        return pd.DataFrame()
    
    if lactating_cows.empty:
        return pd.DataFrame()
    
    if milk_df.empty or 'litres_sell' not in milk_df.columns:
        return pd.DataFrame()
    
    milk_per_cow = milk_df.groupby("cow")["litres_sell"].sum().reset_index()
    milk_per_cow["revenue"] = milk_per_cow["litres_sell"] * 43
    
    if not feeds_used_df.empty and 'quantity' in feeds_used_df.columns:
        feeds_used_df = feeds_used_df[feeds_used_df["category"] == "Grown Cow"]
        total_feed_cost = feeds_used_df["quantity"].sum()
    else:
        total_feed_cost = 0
    
    if not health_df.empty and 'cost' in health_df.columns:
        total_health_cost = health_df["cost"].sum()
    else:
        total_health_cost = 0
    
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