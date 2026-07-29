"""Call the two retail tools directly, bypassing MCP transport.

Covers the known-input and unknown-input cases for each (tasks 11, 12).
Needs DATABASE_URL in .env. Run from the repo root:
    python tests/tool_test.py
"""

from src.tools.inventory import check_inventory
from src.tools.order_tracking import track_order


def test_check_inventory():
    print("\n" + "=" * 70)
    print("TOOL 1: check_inventory")
    print("=" * 70)

    cases = [
        ("any variant of a known SKU", {"sku": "APL-TOP-M-001"}),
        ("known SKU, size M", {"sku": "APL-TOP-M-001", "size": "M"}),
        ("known SKU, color Black", {"sku": "APL-TOP-M-001", "color": "Black"}),
        ("known SKU, size M + Black", {"sku": "APL-TOP-M-001", "size": "M", "color": "Black"}),
        ("unknown SKU", {"sku": "APL-XXX-X-999"}),
        ("known SKU, colour we don't carry", {"sku": "APL-TOP-M-001", "color": "Neon Pink"}),
    ]
    for label, kwargs in cases:
        result = check_inventory(**kwargs)
        print(f"  {label:<34} → {result}")

    assert check_inventory(sku="APL-TOP-M-001") in ("In Stock", "Out of Stock")
    assert check_inventory(sku="APL-XXX-X-999").startswith("Error: unknown SKU")
    assert check_inventory(sku="APL-TOP-M-001", color="Neon Pink").startswith("Error:")


def test_track_order():
    print("\n" + "=" * 70)
    print("TOOL 2: track_order")
    print("=" * 70)

    cases = [
        ("known customer, latest order", {"customer_id": "CUST-0083"}),
        ("known customer + order ID", {"customer_id": "CUST-0083", "order_id": "ORD-2026-000001"}),
        ("unknown customer", {"customer_id": "CUST-9999"}),
        ("known customer, unknown order", {"customer_id": "CUST-0083", "order_id": "ORD-2026-999999"}),
    ]
    for label, kwargs in cases:
        result = track_order(**kwargs)
        print(f"  {label:<34} → {result}")

    assert track_order(customer_id="CUST-0083")["order_id"]
    assert "error" in track_order(customer_id="CUST-9999")
    assert "error" in track_order(customer_id="CUST-0083", order_id="ORD-2026-999999")


if __name__ == "__main__":
    test_check_inventory()
    test_track_order()
    print("\n✅ all tool cases passed")
