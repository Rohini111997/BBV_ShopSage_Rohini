"""
Tool for the apparel retail dataset: check_inventory  -> reads inventory.csv

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
INVENTORY_CSV = DATA_DIR / "inventory.csv"

 
mcp = FastMCP("retail-tools")


# ─────────────────────────────────────────────────────────────────────────
# TOOL Setup -  Check Inventory
# ─────────────────────────────────────────────────────────────────────────
 
@mcp.tool()

def check_inventory(sku: str, size: str | None = None, color: str | None = None) -> str:
    df = pd.read_csv(INVENTORY_CSV)
    query = df[df["ID (SKU)"].str.upper() == sku.upper()]
    
    if size:
        query = query[query["Size"].str.lower() == size.lower()]
    if color:
        query = query[query["Color"].str.lower() == color.lower()]
    
    has_stock = (query["Qty_available"] > 0).any()
    return "In Stock" if has_stock else "Out of Stock"



# ─────────────────────────────────────────────────────────────────────────
# TOOL Setup -  In-Stock Sizes  (facts only — the agent applies the
# "recommendable" business rule: >=2 sizes for apparel, >=1 for accessories)
# ─────────────────────────────────────────────────────────────────────────
 
@mcp.tool()
def get_in_stock_sizes(sku: str) -> dict:
    """Return the distinct sizes of this SKU currently in stock
    (Qty_available > 0). Accessories may have blank/one-size rows,
    which still count as one available 'size'."""
    df = pd.read_csv(INVENTORY_CSV)
    rows = df[
        (df["ID (SKU)"].str.upper() == sku.upper())
        & (df["Qty_available"] > 0)
    ]
    sizes = sorted(rows["Size"].fillna("One Size").astype(str).unique().tolist())
    return {"sku": sku, "in_stock_sizes": sizes, "count": len(sizes)}
 
 
 
 