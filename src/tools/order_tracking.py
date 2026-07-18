"""
Tool for the apparel retail dataset: track_order  -> reads order_tracking.csv

Each tool loads its CSV into a pandas DataFrame, filters on the
arguments provided, and returns results as a list of dicts (JSON-safe),
so they can be plugged directly into an agent / function-calling setup.
"""


import os
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────

load_dotenv()
DATA_DIR = Path(os.environ.get("RETAIL_DATA_DIR", "."))
ORDER_TRACKING_CSV = DATA_DIR / "order_tracking.csv"

 
mcp = FastMCP("retail-tools")


# ─────────────────────────────────────────────────────────────────────────
# TOOL Setup -  Track Order
# ─────────────────────────────────────────────────────────────────────────
 

 
@mcp.tool()
def track_order(customer_id: str, order_id: str | None = None) -> dict:
    df = pd.read_csv(ORDER_TRACKING_CSV)
    query = df[df["Customer_ID"].str.upper() == customer_id.upper()]
    
    if order_id:
        query = query[query["Order_ID"].str.upper() == order_id.upper()]
    
    if query.empty:
        return {"order_id": None, "order_status": None, "item_count": 0}
    
    latest_order = query.sort_values("Order_date", ascending=False).iloc[0]
    order_id_val = latest_order["Order_ID"]
    item_count = len(query[query["Order_ID"] == order_id_val])
    exp_del_date = latest_order["Expected_delivery"]
    
    return {
        "order_id": order_id_val,
        "order_status": latest_order["Order_status"],
        "item_count": item_count,
        "expected_delivery_date": exp_del_date,
    }