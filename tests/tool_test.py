
#!/usr/bin/env python3
"""
Test script: call the 2 retail tools locally without MCP transport.

This is for quick testing of the tool logic before registering with Claude Desktop.
It imports the functions directly and calls them.

Usage:
    export RETAIL_DATA_DIR=/path/to/csv/folder
    python test_tools.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src/tools to path so we can import the server
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tools"))

# Load RETAIL_DATA_DIR (and any other vars) from a .env file at the repo root
load_dotenv(Path(__file__).parent.parent / ".env")

# Set up environment
if "RETAIL_DATA_DIR" not in os.environ:
    print("❌ Error: RETAIL_DATA_DIR env var not set")
    print("   export RETAIL_DATA_DIR=/path/to/csv/folder")
    sys.exit(1)

# Import tool functions (these are the @mcp.tool() decorated functions)
from inventory import check_inventory
from order_tracking import track_order
import json


def pp(obj):
    """Pretty-print JSON."""
    print(json.dumps(obj, indent=2, default=str))


print("\n[Test 1] Latest order for customer 'CUST-0083'?")

result = track_order(customer_id="CUST-0151")
print(result)
result = track_order(customer_id="CUST-0083", order_id="ORD-2026-000001")
print(result)

def test_check_inventory():
    """Test the inventory tool with various queries."""
    print("\n" + "="*70)
    print("TOOL 1: check_inventory")
    print("="*70)

    # Test 1: Only SKU (check if ANY variant of that product is available)
    print("\n[Test 1] Is SKU 'APL-TOP-M-001' in stock (any size/color)?")
    result = check_inventory(sku="APL-TOP-M-001")
    print(f"  → {result}")

    # Test 2: SKU + Size (check if that product in that size is available)
    print("\n[Test 2] Is SKU 'APL-TOP-M-001' in stock, size M (any color)?")
    result = check_inventory(sku="APL-TOP-M-001", size="M")
    print(f"  → {result}")

    # Test 3: SKU + Color (check if that product in that color is available)
    print("\n[Test 3] Is SKU 'APL-TOP-M-001' in stock, color Black (any size)?")
    result = check_inventory(sku="APL-TOP-M-001", color="Black")
    print(f"  → {result}")

    # Test 4: SKU + Size + Color (check if that exact variant is available)
    print("\n[Test 4] Is SKU 'APL-TOP-M-001' in stock, size M, color Black (exact match)?")
    result = check_inventory(sku="APL-TOP-M-001", size="M", color="Black")
    print(f"  → {result}")

    # Test 5: Non-existent SKU
    print("\n[Test 5] Is non-existent SKU 'APL-XXX-X-999' in stock?")
    result = check_inventory(sku="APL-XXX-X-999")
    print(f"  → {result}")


def test_track_order():
    """Test the order tracking tool."""
    print("\n" + "="*70)
    print("TOOL 2: track_order")
    print("="*70)

    # Test 1: Known customer, latest order
    print("\n[Test 1] Latest order for customer 'CUST-0083'?")
    result = track_order(customer_id="CUST-0083")
    pp(result)

    # Test 2: Known customer + specific order ID
    print("\n[Test 2] Customer 'CUST-0083', order 'ORD-2026-000001'?")
    result = track_order(customer_id="CUST-0083", order_id="ORD-2026-000001")
    pp(result)

    # Test 3: Non-existent customer
    print("\n[Test 3] Latest order for non-existent customer 'CUST-9999'?")
    result = track_order(customer_id="CUST-9999")
    pp(result)


if __name__ == "__main__":
    test_check_inventory()
    test_track_order()
