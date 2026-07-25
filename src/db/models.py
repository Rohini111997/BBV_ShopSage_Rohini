"""
models.py — SQLAlchemy models for the apparel retail dataset.

Mirrors docs/Data Deatils.md: product_catalog (1) --< inventory (1) --< order_tracking.
Column names are snake_case translations of the source CSV/JSONL headers
(e.g. "ID (SKU)" -> sku, "Cost_price(INR)" -> cost_price_inr) — see
src/db/load.py for the header mapping used when loading data in.
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String, primary_key=True)
    brand: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    item_type: Mapped[str] = mapped_column(String)
    subcategory: Mapped[str] = mapped_column(String)
    gender: Mapped[str] = mapped_column(String)
    sizes_available: Mapped[str] = mapped_column(String)
    colors_available: Mapped[str] = mapped_column(String)
    num_colors: Mapped[int] = mapped_column(Integer)
    price_inr: Mapped[int] = mapped_column(Integer)
    attributes: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[str] = mapped_column(Text)

    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="product")


class InventoryItem(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), index=True)
    size: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String)
    qty_on_hand: Mapped[int] = mapped_column(Integer)
    qty_reserved: Mapped[int] = mapped_column(Integer)
    qty_available: Mapped[int] = mapped_column(Integer)
    qty_incoming: Mapped[int] = mapped_column(Integer)
    reorder_point: Mapped[int] = mapped_column(Integer)
    reorder_qty: Mapped[int] = mapped_column(Integer)
    stock_status: Mapped[str] = mapped_column(String, index=True)
    warehouse_location: Mapped[str] = mapped_column(String)
    cost_price_inr: Mapped[int] = mapped_column(Integer)
    supplier_id: Mapped[str] = mapped_column(String)
    last_restocked_at: Mapped[Date] = mapped_column(Date)
    updated_at: Mapped[Date] = mapped_column(Date)

    product: Mapped["Product"] = relationship(back_populates="inventory_items")
    order_items: Mapped[list["OrderTrackingItem"]] = relationship(back_populates="inventory_item")


class OrderTrackingItem(Base):
    __tablename__ = "order_tracking"

    order_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    order_date: Mapped[DateTime] = mapped_column(DateTime)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    inventory_id: Mapped[str] = mapped_column(ForeignKey("inventory.inventory_id"))
    size: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_inr: Mapped[int] = mapped_column(Integer)
    line_total_inr: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String)
    payment_status: Mapped[str] = mapped_column(String)
    order_status: Mapped[str] = mapped_column(String, index=True)
    warehouse_shipped_from: Mapped[str] = mapped_column(String)
    courier_partner: Mapped[str] = mapped_column(String)
    tracking_number: Mapped[str] = mapped_column(String)
    shipped_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    expected_delivery: Mapped[Date | None] = mapped_column(Date, nullable=True)
    delivered_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    return_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    shipping_city: Mapped[str] = mapped_column(String)
    shipping_pincode: Mapped[str] = mapped_column(String)

    inventory_item: Mapped["InventoryItem"] = relationship(back_populates="order_items")
