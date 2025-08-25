# dairy_farm_app/utils/data_loader.py
import pandas as pd
from datetime import date
from ..firebase_utils import get_collection  # Relative import from parent (root) directory

def load_table(table_name: str) -> pd.DataFrame:
    return get_collection(table_name)

def to_date(df, col):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df
