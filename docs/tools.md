# ShopSage Tool Specs (Task 10)

Two tools give the agent live data the RAG index can't provide: **stock right now** and **where an order is**. Both are exposed over MCP and read from Neon Postgres.

- **Definitions:** [`src/tools/inventory.py`](../src/tools/inventory.py), [`src/tools/order_tracking.py`](../src/tools/order_tracking.py)
- **Server:** [`src/tools/retail_mcp_server.py`](../src/tools/retail_mcp_server.py) registers both on one `FastMCP("retail-tools")` instance and serves over **stdio**
- **Client:** `RetailMCPClient` in [`src/Agent_2.py`](../src/Agent_2.py) spawns the server as a subprocess and holds one session for the process lifetime
- **Data:** the `inventory` and `order_tracking` tables in Neon, loaded by [`src/db/load.py`](../src/db/load.py). Requires `DATABASE_URL` — see `.env.example`

## Deviation from the task brief

tasks.md specifies `check_inventory(product_id, variant)` and `track_order(order_id)`. The implemented signatures differ, deliberately:

| Brief | Implemented | Why |
|---|---|---|
| `product_id` | `sku` | The catalog's primary key is `ID (SKU)`; "product_id" doesn't exist in this dataset. |
| `variant` | `size`, `color` | `inventory` is keyed by product × size × color, so a single opaque `variant` would have to be parsed apart anyway. Splitting it also allows partial checks ("any size in Black"). |
| `track_order(order_id)` | `track_order(customer_id, order_id=None)` | Shoppers ask "where's my order?" without knowing the ID. `customer_id` is required and `order_id` optional; with no ID the tool returns the **latest** order. |

---

## `check_inventory(sku, size=None, color=None) -> str`

Live stock for a product, optionally narrowed to a size and/or colour. Omitted arguments widen the check: with neither, it answers "is *any* variant of this product buyable?"

### Inputs

| Arg | Type | Required | Notes |
|---|---|---|---|
| `sku` | string | yes | e.g. `APL-TOP-M-001`. Matched case-insensitively. |
| `size` | string | no | `XS`–`XXL`, `S`/`M`/`L` for socks, `Free Size` for eyewear/headwear. |
| `color` | string | no | Must be one of the product's `Colors_available`, e.g. `Black`. |

### Output

A plain string, one of:

- `"In Stock"` — at least one matching variant has `Qty_available > 0`
- `"Out of Stock"` — matching variants exist but all are at zero
- `"Error: ..."` — see below

Stock is judged on `Qty_available` (on-hand minus reserved), never `Qty_on_hand`.

### Error cases

| Condition | Return |
|---|---|
| SKU not in the catalog | `Error: unknown SKU 'APL-XXX-X-999'` |
| SKU exists, but no variant in that size/colour | `Error: 'APL-TOP-M-001' has no variant in size=any, color=Neon Pink` |
| DB unreachable / MCP failure | Surfaces through the client as `{"ok": false, ...}` → agent returns `error: "tool_error"` |

"Unknown product" is deliberately **not** reported as "Out of Stock" — the agent must be able to say "we don't carry that" rather than implying we're merely sold out.

### Examples (verified against Neon)

```
check_inventory(sku="APL-TOP-M-001")                      → "In Stock"
check_inventory(sku="APL-TOP-M-001", size="M")            → "In Stock"
check_inventory(sku="APL-XXX-X-999")                      → "Error: unknown SKU 'APL-XXX-X-999'"
check_inventory(sku="APL-TOP-M-001", color="Neon Pink")   → "Error: 'APL-TOP-M-001' has no variant in size=any, color=Neon Pink"
```

---

## `track_order(customer_id, order_id=None) -> dict`

Status of a customer's order. Without `order_id`, returns their most recent order by `order_date`.

### Inputs

| Arg | Type | Required | Notes |
|---|---|---|---|
| `customer_id` | string | yes | e.g. `CUST-0083`. Matched case-insensitively. |
| `order_id` | string | no | e.g. `ORD-2026-000001`. Omit for the latest order. |

### Output

```json
{
  "order_id": "ORD-2026-000001",
  "order_status": "delivered",
  "item_count": 2,
  "expected_delivery_date": "2026-07-03"
}
```

`item_count` is the number of line items in that order (orders hold 1–4). `order_status` is one of `pending`, `confirmed`, `packed`, `shipped`, `out_for_delivery`, `delivered`, `cancelled`, `returned`.

### Error cases

| Condition | Return |
|---|---|
| Customer has no orders | `{"error": "no orders found for customer 'CUST-9999'", "order_id": null, "order_status": null, "item_count": 0}` |
| Order ID doesn't belong to that customer | `{"error": "no orders found for customer 'CUST-0083', order 'ORD-2026-999999'", "order_id": null, ...}` |
| No `customer_id` supplied | Short-circuited by the agent before the call — it asks the shopper for their ID |

### Examples (verified against Neon)

```
track_order(customer_id="CUST-0083")
  → {'order_id': 'ORD-2026-000001', 'order_status': 'delivered', 'item_count': 2,
     'expected_delivery_date': datetime.date(2026, 7, 3)}

track_order(customer_id="CUST-9999")
  → {'error': "no orders found for customer 'CUST-9999'", 'order_id': None, ...}

track_order(customer_id="CUST-0083", order_id="ORD-2026-999999")
  → {'error': "no orders found for customer 'CUST-0083', order 'ORD-2026-999999'", ...}
```

---

## Agent-side wrappers

`RAG_Reco_Agent` wraps each MCP call so the generation rules read a stable shape regardless of transport outcome. These dicts — not the raw tool returns — are what get injected into the prompt as `TOOL RESULT`.

**`check_inventory`**

| Case | Wrapper returns |
|---|---|
| Success | `{"checked": true, "sku", "size", "color", "stock_status": "In Stock", "in_stock": true}` |
| Unknown SKU/variant | `{"checked": false, "error": "not_found", "detail": "Error: unknown SKU ..."}` |
| Transport/DB failure | `{"checked": false, "error": "tool_error", "detail": ...}` |
| No SKU resolved from retrieval | `{"checked": false, "error": "no_sku"}` |

**`track_order`**

| Case | Wrapper returns |
|---|---|
| Success | `{"found": true, "order": {...}}` |
| No such order | `{"found": false, "error": "order_not_found", "detail": ...}` |
| Transport/DB failure | `{"found": false, "error": "tool_error", "detail": ...}` |
| No customer ID | `{"found": false, "error": "no_customer_id"}` |

`checked: false` / `found: false` is what stops the agent inventing a stock level: the prompt rules require it to say it couldn't confirm rather than guess from the catalog description.

## How the agent decides to call them

Slot extraction routes each message before any tool runs:

- `inventory_check` → retrieval first (resolves a product **name** to a SKU), then `check_inventory`
- `order_tracking` → `track_order` directly, retrieval skipped entirely
- `new_search` / `follow_up` → no tool call; RAG only

## Testing

[`tests/tool_test.py`](../tests/tool_test.py) calls both functions directly, bypassing MCP transport, covering known and unknown inputs for each.
