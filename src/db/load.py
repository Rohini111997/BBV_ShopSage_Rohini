"""
load.py — one-time/on-demand migration of DataBase/*.csv + *.jsonl into Postgres.

Creates the products / inventory / order_tracking tables (if missing) and
replaces their contents with the current CSV/JSONL snapshot. Safe to re-run:
each table is cleared and reloaded in FK-safe order (products -> inventory ->
order_tracking on delete reverses that).

Run from the repo root:
    python -m src.db.load
"""

import json
from pathlib import Path

import pandas as pd

from src.db.models import Base, InventoryItem, OrderTrackingItem, Product
from src.db.session import engine, get_session

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "DataBase"


def _records(df: pd.DataFrame) -> list[dict]:
    """Rows as dicts with NaN -> None so psycopg2 gets NULL, not float('nan')."""
    return df.where(pd.notnull(df), None).to_dict("records")


def _load_products() -> list[dict]:
    products = []
    with open(DATA_DIR / "product_catalog.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            products.append(
                {
                    "sku": item["ID (SKU)"],
                    "brand": item["brand"],
                    "title": item["title"],
                    "item_type": item["item_type"],
                    "subcategory": item["Subcategory"],
                    "gender": item["Gender"],
                    "sizes_available": item["Sizes_available"],
                    "colors_available": item["Colors_available"],
                    "num_colors": item["Number_of_Colors_available"],
                    "price_inr": item["price(INR)"],
                    "attributes": item.get("Attributes") or {},
                    "description": item["Description"],
                    "image_url": item.get("image"),
                }
            )
    return products


def _load_inventory() -> list[dict]:
    df = pd.read_csv(DATA_DIR / "inventory.csv")
    df["Last_restocked_at"] = pd.to_datetime(df["Last_restocked_at"]).dt.date
    df["Updated_at"] = pd.to_datetime(df["Updated_at"]).dt.date
    df = df.rename(
        columns={
            "Inventory_ID": "inventory_id",
            "ID (SKU)": "sku",
            "Size": "size",
            "Color": "color",
            "Qty_on_hand": "qty_on_hand",
            "Qty_reserved": "qty_reserved",
            "Qty_available": "qty_available",
            "Qty_incoming": "qty_incoming",
            "Reorder_point": "reorder_point",
            "Reorder_qty": "reorder_qty",
            "Stock_status": "stock_status",
            "Warehouse_location": "warehouse_location",
            "Cost_price(INR)": "cost_price_inr",
            "Supplier_ID": "supplier_id",
            "Last_restocked_at": "last_restocked_at",
            "Updated_at": "updated_at",
        }
    )
    return _records(df)


def _load_order_tracking() -> list[dict]:
    df = pd.read_csv(DATA_DIR / "order_tracking.csv")
    df["Order_date"] = pd.to_datetime(df["Order_date"])
    for col in ("Shipped_at", "Expected_delivery", "Delivered_at"):
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df = df.rename(
        columns={
            "Order_item_ID": "order_item_id",
            "Order_ID": "order_id",
            "Customer_ID": "customer_id",
            "Order_date": "order_date",
            "ID (SKU)": "sku",
            "Inventory_ID": "inventory_id",
            "Size": "size",
            "Color": "color",
            "Quantity": "quantity",
            "Unit_price(INR)": "unit_price_inr",
            "Line_total(INR)": "line_total_inr",
            "Payment_method": "payment_method",
            "Payment_status": "payment_status",
            "Order_status": "order_status",
            "Warehouse_shipped_from": "warehouse_shipped_from",
            "Courier_partner": "courier_partner",
            "Tracking_number": "tracking_number",
            "Shipped_at": "shipped_at",
            "Expected_delivery": "expected_delivery",
            "Delivered_at": "delivered_at",
            "Return_reason": "return_reason",
            "Shipping_city": "shipping_city",
            "Shipping_pincode": "shipping_pincode",
        }
    )
    return _records(df)


def load() -> None:
    Base.metadata.create_all(engine)

    products = _load_products()
    inventory = _load_inventory()
    order_tracking = _load_order_tracking()

    session = get_session()
    try:
        # FK-safe order: children before parents on delete, parents before children on insert.
        session.query(OrderTrackingItem).delete()
        session.query(InventoryItem).delete()
        session.query(Product).delete()

        session.bulk_insert_mappings(Product, products)
        session.bulk_insert_mappings(InventoryItem, inventory)
        session.bulk_insert_mappings(OrderTrackingItem, order_tracking)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(
        f"[load] {len(products)} products, {len(inventory)} inventory rows, "
        f"{len(order_tracking)} order_tracking rows loaded into Postgres"
    )


if __name__ == "__main__":
    load()
