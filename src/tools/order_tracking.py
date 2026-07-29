"""
Tool for the apparel retail dataset: track_order  -> queries Postgres

Each tool opens a session against the order_tracking table (src.db),
filters on the arguments provided, and returns results as JSON-safe
values, so they can be plugged directly into an agent / function-calling
setup.
"""

from mcp.server.fastmcp import FastMCP

from src.db import OrderTrackingItem, get_session

mcp = FastMCP("retail-tools")


# ─────────────────────────────────────────────────────────────────────────
# TOOL Setup -  Track Order
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def track_order(customer_id: str, order_id: str | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(OrderTrackingItem).filter(
            OrderTrackingItem.customer_id.ilike(customer_id)
        )
        if order_id:
            query = query.filter(OrderTrackingItem.order_id.ilike(order_id))

        rows = query.all()
        if not rows:
            return {"error": f"no orders found for customer '{customer_id}'"
                             + (f", order '{order_id}'" if order_id else ""),
                    "order_id": None, "order_status": None, "item_count": 0}

        latest_order = max(rows, key=lambda r: r.order_date)
        item_count = sum(1 for r in rows if r.order_id == latest_order.order_id)
    finally:
        session.close()

    return {
        "order_id": latest_order.order_id,
        "order_status": latest_order.order_status,
        "item_count": item_count,
        "expected_delivery_date": latest_order.expected_delivery,
    }
