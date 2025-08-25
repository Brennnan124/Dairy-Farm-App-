# dairy_farm_app/utils/helpers.py
import streamlit as st
import pandas as pd
import numpy as np
import re

def show_table(df: pd.DataFrame, title: str, search_cols=None, page_size=15, key_prefix=""):
    st.subheader(title)
    if df.empty:
        st.info("No records yet.")
        return

    df_disp = df.copy()

    q = st.text_input("Search", key=f"{key_prefix}_search").strip()
    if q and search_cols:
        mask = np.zeros(len(df_disp), dtype=bool)
        for col in search_cols:
            if col in df_disp.columns:
                mask |= df_disp[col].astype(str).str.contains(q, case=False, na=False)
        df_disp = df_disp[mask]

    total = len(df_disp)
    pages = max(1, (total + page_size - 1) // page_size)
    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        current_page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1, key=f"{key_prefix}_page")
    with col2:
        st.write(f"Showing {page_size} per page — {total} rows total.")
    start = (current_page - 1) * page_size
    end = start + page_size
    st.dataframe(df_disp.iloc[start:end])

def money(x):
    try:
        return f"KES {x:,.0f}"
    except Exception:
        return x

def parse_money(money_str):
    try:
        if isinstance(money_str, (int, float)):
            return float(money_str)
        return float(re.sub(r'[^\d.]', '', str(money_str)))
    except:
        return 0.0

def liters(x):
    try:
        return f"{x:,.2f} L"
    except Exception:
        return x

def format_with_commas(x):
    try:
        return f"{x:,.0f}"
    except:
        return x

def clamp(val, vmin, vmax):
    return max(vmin, min(vmax, val))