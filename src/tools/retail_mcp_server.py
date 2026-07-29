"""
Retail MCP server: registers all retail tools (check_inventory, track_order)
on a single FastMCP instance.

Run directly to serve over stdio for Claude Desktop / MCP clients:
    export RETAIL_DATA_DIR=/path/to/csv/folder
    python retail_mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

from inventory import check_inventory, get_in_stock_sizes
from order_tracking import track_order

mcp = FastMCP("retail-tools")
mcp.add_tool(check_inventory)
mcp.add_tool(track_order)
mcp.add_tool(get_in_stock_sizes)
 

if __name__ == "__main__":
    mcp.run()
