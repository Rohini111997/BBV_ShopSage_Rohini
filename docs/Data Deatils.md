# Apparel Retail Dataset — Semantic Schema Documentation

This document describes the three tables that make up the apparel retail dataset: **`product_catalog`**, **`inventory`**, and **`order_tracking`**. It explains what each table represents, the meaning of every column, the allowed values for coded fields, and how the tables join together. It is written to serve both human readers and LLM/RAG systems that need schema context to answer questions or generate queries against this data.

---

## 1. Dataset Overview

The dataset models a small Indian online fashion retailer. It separates three concerns, mirroring how real e-commerce systems are designed:

| Table | Grain (one row =) | Rows | Nature | Answers questions like |
|---|---|---|---|---|
| `product_catalog` | one product | 100 | Static / descriptive | "What is this product? What does it cost?" |
| `inventory` | one sellable variant (product × size × color) | 954 | Operational snapshot, changes constantly | "Is the black tee in size M in stock? Where?" |
| `order_tracking` | one order line item (one product within an order) | 496 | Transactional log | "Where is my order? What did this customer buy?" |

**Join keys (relationships):**

- `product_catalog."ID (SKU)"` ← 1-to-many → `inventory."ID (SKU)"` (a product has many size/color variants)
- `inventory.Inventory_ID` ← 1-to-many → `order_tracking.Inventory_ID` (a variant appears in many order lines)
- `order_tracking."ID (SKU)"` also joins directly back to the catalog for convenience
- `order_tracking.Order_ID` groups multiple line-item rows into one customer order

**Identifier grammar (shared conventions):**

- Product SKU: `APL-{TOP|BTM|ACC}-{M|F}-{NNN}` — e.g. `APL-TOP-M-001`. `APL` = apparel catalog, `TOP`/`BTM`/`ACC` = topwear/bottomwear/accessories, `M`/`F` = gender, `NNN` = a globally unique serial 001–100.
- Inventory (variant) ID: `{SKU}-{SIZE}-{COLOR_CODE}` — e.g. `APL-TOP-M-001-M-BLA` = that product, size M, color code `BLA` (first three letters of the color, deduplicated within the product; `FS` is used as the size segment for Free Size items).
- Order IDs: `ORD-2026-NNNNNN`; order line items: `OI-NNNNNN`; customers: `CUST-NNNN`; suppliers: `SUP-NNN`.

**Currency & locale:** all money values are Indian Rupees (INR). Dates are ISO `YYYY-MM-DD` (timestamps `YYYY-MM-DD HH:MM`, 24h). The snapshot date of the dataset is 2026-07-18.

---

## 2. Table: `product_catalog`

**Purpose.** The product master — the single source of truth for what each product *is*: its identity, branding, marketing copy, physical attributes, and selling price. This table is static; it does not track quantities, orders, or anything that changes daily. In a RAG/semantic-search setup, this is the table whose text (title, description, attributes) gets embedded, because it carries the descriptive language customers search with ("linen shirt for summer", "non-slip yoga socks").

**Grain.** One row per product (100 rows). Size and color availability are summarized here as display strings; the sellable per-size/per-color detail lives in `inventory`.

**Composition.** 68 clothing items (36 topwear, 32 bottomwear) and 32 accessories (12 sunglasses, 10 socks, 10 hats/caps); 50 male, 50 female; 10 fictional brands; prices follow fast-fashion (H&M-like) bands from ₹399 to ₹3,999.

### Columns

| Column | Type | Description |
|---|---|---|
| `ID (SKU)` | string, **primary key** | Unique product identifier in the `APL-CAT-G-NNN` grammar described above. Encodes subcategory and gender, so the ID alone tells you `APL-BTM-F-027` is women's bottomwear. |
| `brand` | string | Brand label. One of 10 fictional brands, each with a personality: UrbanThread (streetwear basics), Aster & Co. (tailored/formal), NovaFit (activewear), DenimWorks (denim), Drift & Dune (outdoor/casual), Rangrez (ethnic wear), Lumière (women's contemporary), Fleur Studio (feminine/occasion), Rayzr (eyewear), SoleMate (socks). |
| `title` | string | Short marketing name of the product, e.g. "Everyday Crew Tee". Unique across the catalog. |
| `item_type` | string | The specific garment/accessory type, finer than subcategory: T-Shirt, Shirt, Hoodie, Sweater, Jacket, Blazer, Kurta, Nehru Jacket, Tank Top, Blouse, Bodysuit, Camisole, Dress, Cardigan, Top, Jeans, Chinos, Trousers, Formal Trousers, Track Pants, Joggers, Cargo Pants, Shorts, Pyjamas, Leggings, Jeggings, Palazzos, Culottes, Skirt, Yoga Pants, Sunglasses, Cap, Hat, Socks. |
| `Subcategory` | string, enum | High-level grouping: `Topwear`, `Bottomwear`, or `Accessories`. Note: dresses are classified under Topwear in this taxonomy. |
| `Gender` | string, enum | Target gender of the product line: `Male` or `Female`. |
| `Sizes_available` | string (comma-separated list) | Sizes the product is offered in. Clothing: `"XS, S, M, L, XL, XXL"`. Socks: `"S, M, L"`. Sunglasses, caps, hats: `"Free Size"`. This is the offered size range; actual per-size stock is in `inventory`. |
| `Colors_available` | string (comma-separated list) | Colorways offered, always 1–3 per product, e.g. `"White, Black, Navy"`. Each color becomes separate variant rows in `inventory`. |
| `Number_of_Colors_available` | integer (1–3) | Count of colorways; equals the number of items in `Colors_available`. Useful as a filter without string parsing. |
| `price(INR)` | integer | Current selling price (MRP) per unit in rupees. All prices end in 99 (₹399–₹3,999). This is the price customers pay; the retailer's cost is `inventory.Cost_price(INR)`. |
| `Attributes` | object (nested key-value) | Structured product specs. **Keys vary by item type**: garments use keys like `fabric`, `fit`, `sleeve`, `neck`, `collar`, `rise`, `wash`, `waist`, `length`, `closure`, `pattern`, `occasion`; sunglasses use `frame`, `lens`, `lens_color`; hats/socks use `material`, `brim`, `pack`, `feature`. `occasion` (Casual, Formal, Festive, Gym, etc.) appears on nearly all items and is valuable for intent-based search. If storing in a system that requires flat metadata, flatten or serialize this object. |
| `Description` | string | One-to-two sentence marketing description in natural language. Together with `title` and `Attributes`, this is the primary text for semantic embedding. |

---

## 3. Table: `inventory`

**Purpose.** The stock ledger — how many units of each sellable variant the retailer physically holds, where they sit, what they cost, and when to reorder. This table answers availability ("can a customer buy size L in Navy right now?") and operations questions (what to reorder, stock value). It is a point-in-time snapshot dated 2026-07-18 and would be updated continuously in a live system.

**Grain.** One row per **variant** = product × size × color (954 rows). A clothing product with 6 sizes and 3 colors contributes 18 rows. This is the level at which online retailers actually track stock, because customers buy variants, not products.

**Simplification to note.** Each product is stocked in exactly one primary fulfillment center here; a full multi-warehouse system would repeat variants per location.

### Columns

| Column | Type | Description |
|---|---|---|
| `Inventory_ID` | string, **primary key** | Unique variant identifier: `{SKU}-{SIZE}-{COLOR_CODE}`, e.g. `APL-TOP-M-001-XS-WHI`. |
| `ID (SKU)` | string, **foreign key → product_catalog** | Parent product. Join here to get brand, title, price, description. |
| `Size` | string | The specific size of this variant: `XS`–`XXL` for clothing, `S`/`M`/`L` for socks, `Free Size` for eyewear and headwear. |
| `Color` | string | The specific colorway of this variant, matching one entry of the product's `Colors_available`. |
| `Qty_on_hand` | integer ≥ 0 | Physical units currently in the warehouse, including units promised to unshipped orders. |
| `Qty_reserved` | integer ≥ 0 | Units locked against placed-but-unshipped orders (up to ~15% of on-hand). These cannot be sold again. |
| `Qty_available` | integer ≥ 0 | **The sellable number** shown to customers: `Qty_on_hand − Qty_reserved`. Use this, not on-hand, for "is it in stock" questions. |
| `Qty_incoming` | integer ≥ 0 | Units already ordered from the supplier (on open purchase order) but not yet received. Usually non-zero when a variant is low or out of stock. |
| `Reorder_point` | integer | Threshold: when `Qty_available` falls to or below this, replenishment should be triggered. Scales with the variant's expected demand. |
| `Reorder_qty` | integer | Standard replenishment quantity ordered when the reorder point is hit. |
| `Stock_status` | string, enum | Derived health flag: `in_stock` (available > reorder point), `low_stock` (0 < available ≤ reorder point), `out_of_stock` (available = 0). Current mix: 729 / 154 / 71. |
| `Warehouse_location` | string | Full bin address `{FC}-{Aisle}{Shelf}-R{Rack}`, e.g. `BLR-FC1-A12-R3`. The first 7 characters identify the fulfillment center: `BLR-FC1` (Bengaluru), `DEL-FC1` (Delhi), `MUM-FC1` (Mumbai). |
| `Cost_price(INR)` | integer | What the retailer pays the supplier per unit — 38–55% of the catalog selling price (typical apparel margins). Margin per unit = `price(INR) − Cost_price(INR)`; stock value = `Qty_on_hand × Cost_price(INR)`. |
| `Supplier_ID` | string | Replenishment supplier, `SUP-001`…`SUP-010`. Suppliers map 1-to-1 to brands (all UrbanThread products share one supplier). |
| `Last_restocked_at` | date | When this variant last received stock (within the 90 days before the snapshot). |
| `Updated_at` | date | When this row was last modified by any stock movement. Always ≥ `Last_restocked_at`. |

---

## 4. Table: `order_tracking`

**Purpose.** The transaction log — who bought what, when, for how much, how it was paid, and where each shipment currently is in its lifecycle. This single flat table combines what larger systems split into `orders` and `order_items`: order-level fields (customer, payment, status, shipping) are **repeated on every line row of the same order**. It answers customer-service questions ("where is my order?"), sales analytics ("GMV last month, return rate"), and links demand back to inventory.

**Grain.** One row per **order line item** (496 rows across 300 orders). Rows sharing an `Order_ID` are one checkout; to count *orders* rather than items, use `COUNT(DISTINCT Order_ID)`, and de-duplicate order-level fields before summing anything per-order.

**Status semantics.** `Order_status` stores only the **latest** state (a snapshot), not the history of transitions. The tracking timeline can be partially reconstructed from the date columns (`Order_date` → `Shipped_at` → `Delivered_at`); a full append-only event log is a separate table not included in this dataset.

**Window.** Orders span the 60 days up to 2026-07-18, so older orders are mostly delivered while the most recent ones are still pending/confirmed/packed.

### Columns

| Column | Type | Description |
|---|---|---|
| `Order_item_ID` | string, **primary key** | Unique line-item identifier, `OI-NNNNNN`. |
| `Order_ID` | string | The parent order, `ORD-2026-NNNNNN`. Repeats across rows for multi-item orders (1–4 items per order). |
| `Customer_ID` | string | The purchasing customer, `CUST-0001`–`CUST-0180`. Customers repeat across orders, enabling repeat-purchase analysis. |
| `Order_date` | timestamp | When the order was placed (checkout time). Identical on all rows of an order. |
| `ID (SKU)` | string, **foreign key → product_catalog** | The product purchased on this line. |
| `Inventory_ID` | string, **foreign key → inventory** | The exact size/color variant purchased. Guaranteed to exist in the inventory table. |
| `Size` / `Color` | string | Denormalized copies of the variant's size and color, so common questions don't require a join. |
| `Quantity` | integer (1–3) | Units of this variant on this line. |
| `Unit_price(INR)` | integer | Selling price per unit at time of sale; matches the catalog `price(INR)`. |
| `Line_total(INR)` | integer | `Quantity × Unit_price(INR)`. Sum per `Order_ID` for order value; sum overall for GMV. |
| `Payment_method` | string, enum | `UPI`, `COD` (cash on delivery), `Credit/Debit Card`, `Netbanking`, `Wallet`. COD + UPI dominate, reflecting Indian e-commerce. |
| `Payment_status` | string, enum | `paid`, `pending` (COD not yet delivered), `refunded` (returned orders, or cancelled prepaid orders), `not_charged` (cancelled COD orders). |
| `Order_status` | string, enum | Latest lifecycle state. Forward flow: `pending` → `confirmed` → `packed` → `shipped` → `out_for_delivery` → `delivered`. Terminal branches: `cancelled` (before shipping) and `returned` (after delivery). Stored per line; in this dataset all lines of an order share one status. |
| `Warehouse_shipped_from` | string | Fulfillment center for the whole order: `BLR-FC1`, `DEL-FC1`, or `MUM-FC1`. All items of one order ship from the same FC, and each item is stocked there per the inventory table. |
| `Courier_partner` | string | Last-mile carrier: Delhivery, Bluedart, Ekart, XpressBees, or DTDC. Empty until the order ships. |
| `Tracking_number` | string | Courier AWB (air waybill) number, `AWB` + 10 digits. Empty until shipped. |
| `Shipped_at` | date | Handover to courier (0–2 days after order date). Empty for unshipped/cancelled orders. |
| `Expected_delivery` | date | Courier's promised delivery date (2–6 days after shipping). Empty until shipped. |
| `Delivered_at` | date | Actual delivery. Populated only for `delivered` and `returned` (a return implies it was delivered first). |
| `Return_reason` | string | Populated only for `returned` rows. Values: "Size too small", "Size too large", "Different from images", "Quality not as expected", "Received damaged", "Changed mind", "Color mismatch" — size issues dominate, as is typical for apparel. |
| `Shipping_city` / `Shipping_pincode` | string | Destination city and PIN code (city-level only; 12 Indian metros). Identical across an order's rows. |

---

## 5. Cross-Table Enumerations (quick reference)

- **Subcategory:** Topwear · Bottomwear · Accessories
- **Gender:** Male · Female
- **Clothing sizes:** XS S M L XL XXL · **Sock sizes:** S M L · **Eyewear/headwear:** Free Size
- **Stock_status:** in_stock · low_stock · out_of_stock
- **Order_status:** pending · confirmed · packed · shipped · out_for_delivery · delivered · cancelled · returned
- **Payment_method:** UPI · COD · Credit/Debit Card · Netbanking · Wallet
- **Payment_status:** paid · pending · refunded · not_charged
- **Fulfillment centers:** BLR-FC1 · DEL-FC1 · MUM-FC1
- **Couriers:** Delhivery · Bluedart · Ekart · XpressBees · DTDC
- **Brands:** UrbanThread · Aster & Co. · NovaFit · DenimWorks · Drift & Dune · Rangrez · Lumière · Fleur Studio · Rayzr · SoleMate

---

## 6. How the Tables Work Together (worked examples)

**"Is the Everyday Crew Tee available in M, Black?"**
Catalog: find `title = "Everyday Crew Tee"` → `ID (SKU) = APL-TOP-M-001`. Inventory: find `ID (SKU) = APL-TOP-M-001 AND Size = "M" AND Color = "Black"` → read `Qty_available` and `Stock_status`.

**"Where is order ORD-2026-000123?"**
Order tracking: filter `Order_ID`, read `Order_status`; if shipped, quote `Courier_partner`, `Tracking_number`, `Expected_delivery`.

**"Which products should we restock first?"**
Inventory: `Stock_status IN (low_stock, out_of_stock) AND Qty_incoming = 0`, join catalog for names; prioritize by how far below `Reorder_point` the variant sits.

**"What's our return rate and why do people return?"**
Order tracking: `COUNT(DISTINCT Order_ID WHERE Order_status='returned') / COUNT(DISTINCT Order_ID delivered-or-returned)`; group `Return_reason` for the why; join `ID (SKU)` → catalog to see whether specific products or fits drive returns.

**Note for vector-DB usage.** Embed the catalog's text fields for semantic retrieval; keep inventory and order data in structured storage (SQL/dataframe) and route quantitative questions there. If this document itself is embedded for schema-RAG, chunk it by section (one chunk per table, plus one for the overview and enumerations).
