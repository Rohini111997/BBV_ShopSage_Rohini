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
        if query.count() == 0:
            return f"Error: unknown SKU '{sku}'"
        if size:
            query = query.filter(InventoryItem.size.ilike(size))
        if color:
            query = query.filter(InventoryItem.color.ilike(color))

        rows = query.all()
        if not rows:
            return (f"Error: '{sku}' has no variant in size="
                    f"{size or 'any'}, color={color or 'any'}")
        has_stock = any(row.qty_available > 0 for row in rows)
    finally:
        session.close()

    return "In Stock" if has_stock else "Out of Stock"


# ─────────────────────────────────────────────────────────────────────────
# TOOL Setup -  In-Stock Sizes  (facts only — the agent applies the
# "recommendable" business rule: >=2 sizes for apparel, >=1 for accessories)
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_in_stock_size_counts(skus: list[str]) -> dict:
    """For each SKU, the number of distinct sizes currently in stock
    (qty_available > 0). One query for the whole batch. SKUs with no
    stock (or unknown SKUs) return 0."""
    session = get_session()
    try:
        rows = (
            session.query(InventoryItem.sku, InventoryItem.size)
            .filter(InventoryItem.sku.in_(skus), InventoryItem.qty_available > 0)
            .all()
        )
        sizes_by_sku: dict[str, set] = {}
        for sku, size in rows:
            sizes_by_sku.setdefault(sku, set()).add(size or "One Size")
    finally:
        session.close()

    return {"counts": {sku: len(sizes_by_sku.get(sku, set())) for sku in skus}}