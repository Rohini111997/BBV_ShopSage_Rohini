"""
Tool for the apparel retail dataset: check_inventory  -> queries Postgres

Each tool opens a session against the inventory table (src.db), filters
on the arguments provided, and returns results as JSON-safe values, so
they can be plugged directly into an agent / function-calling setup.
"""

from mcp.server.fastmcp import FastMCP

from src.db import InventoryItem, get_session

mcp = FastMCP("retail-tools")


# ─────────────────────────────────────────────────────────────────────────
# TOOL Setup -  Check Inventory
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def check_inventory(sku: str, size: str | None = None, color: str | None = None) -> str:
    session = get_session()
    try:
        query = session.query(InventoryItem).filter(InventoryItem.sku.ilike(sku))
        if size:
            query = query.filter(InventoryItem.size.ilike(size))
        if color:
            query = query.filter(InventoryItem.color.ilike(color))

        has_stock = any(row.qty_available > 0 for row in query.all())
    finally:
        session.close()

    return "In Stock" if has_stock else "Out of Stock"
