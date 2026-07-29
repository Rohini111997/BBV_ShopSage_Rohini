"""
Retail MCP server: registers all retail tools (check_inventory, track_order)
on a single FastMCP instance.

Run directly to serve over stdio for Claude Desktop / MCP clients:
    # DATABASE_URL must be set (.env at repo root, or exported) — see .env.example
    python retail_mcp_server.py
"""

import sys
from pathlib import Path

# inventory/order_tracking import `src.db` (Postgres session/models) — put the
# repo root on sys.path so that resolves even when this file is launched
# directly as a subprocess (`python retail_mcp_server.py`), not via `-m`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mcp.server.fastmcp import FastMCP

from inventory import check_inventory, get_in_stock_sizes
from order_tracking import track_order

mcp = FastMCP("retail-tools")
mcp.add_tool(check_inventory)
mcp.add_tool(track_order)
mcp.add_tool(get_in_stock_sizes)
 

if __name__ == "__main__":
    mcp.run()
