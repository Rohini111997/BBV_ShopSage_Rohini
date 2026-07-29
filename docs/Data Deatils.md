# Apparel Retail Dataset — Semantic Schema Documentation

This document describes the five files that make up the apparel retail dataset: **`product_catalog`**, **`inventory`**, **`order_tracking`**, **`product_reviews`**, and **`shopper_profiles`**. It explains what each one represents, the meaning of every column/field, the allowed values for coded fields, and how they join together. It is written to serve both human readers and LLM/RAG systems that need schema context to answer questions or generate queries against this data.

---

## 1. Dataset Overview

The dataset models a small Indian online fashion retailer. It separates five concerns, mirroring how real e-commerce systems are designed:

| File | Grain (one row =) | Rows | Nature | Answers questions like |
|---|---|---|---|---|
| `product_catalog.jsonl` | one product | 104 | Static / descriptive | "What is this product? What does it cost?" |
| `inventory.csv` | one sellable variant (product × size × color) | 1002 | Operational snapshot, changes constantly | "Is the black tee in size M in stock? Where?" |
| `order_tracking.csv` | one order line item (one product within an order) | 496 | Transactional log | "Where is my order? What did this customer buy?" |
| `product_reviews.csv` | one review (one shopper on one purchased line item) | 243 | User-generated, append-only | "What do buyers say about this jacket? Does it run small?" |
| `shopper_profiles.json` | one shopper (keyed by `Customer_ID`) | 150 | Derived profile + live agent memory | "Who is this shopper? What's their usual budget and size?" |

**Join keys (relationships):**

- `product_catalog."ID (SKU)"` ← 1-to-many → `inventory."ID (SKU)"` (a product has many size/color variants)
- `inventory.Inventory_ID` ← 1-to-many → `order_tracking.Inventory_ID` (a variant appears in many order lines)
- `order_tracking."ID (SKU)"` also joins directly back to the catalog for convenience
- `order_tracking.Order_ID` groups multiple line-item rows into one customer order
- `order_tracking.Order_item_ID` ← 1-to-0-or-1 → `product_reviews.Order_item_ID` (a received line item may be reviewed once); `product_reviews."ID (SKU)"` also joins straight to the catalog
- `shopper_profiles` key (`CUST-NNNN`) ← 1-to-many → `order_tracking.Customer_ID` and `product_reviews.Customer_ID` (every shopper in the dataset has at least one order)

**Identifier grammar (shared conventions):**

- Product SKU: `APL-{TOP|BTM|ACC}-{M|F}-{NNN}` — e.g. `APL-TOP-M-001`. `APL` = apparel catalog, `TOP`/`BTM`/`ACC` = topwear/bottomwear/accessories, `M`/`F` = gender, `NNN` = a globally unique serial 001–104.
- Inventory (variant) ID: `{SKU}-{SIZE}-{COLOR_CODE}` — e.g. `APL-TOP-M-001-M-BLA` = that product, size M, color code `BLA` (first three letters of the color, deduplicated within the product; `FS` is used as the size segment for Free Size items).
- Order IDs: `ORD-2026-NNNNNN`; order line items: `OI-NNNNNN`; reviews: `REV-NNNNNN`; customers: `CUST-NNNN`; suppliers: `SUP-NNN`.

**Currency & locale:** all money values are Indian Rupees (INR). Dates are ISO `YYYY-MM-DD` (timestamps `YYYY-MM-DD HH:MM`, 24h). The snapshot date of the dataset is 2026-07-18.

---

## 2. Table: `product_catalog`

**Purpose.** The product master — the single source of truth for what each product *is*: its identity, branding, marketing copy, physical attributes, and selling price. This table is static; it does not track quantities, orders, or anything that changes daily. In a RAG/semantic-search setup, this is the table whose text (title, description, attributes) gets embedded, because it carries the descriptive language customers search with ("linen shirt for summer", "non-slip yoga socks").

**Grain.** One row per product (104 rows). Size and color availability are summarized here as display strings; the sellable per-size/per-color detail lives in `inventory`.

**Composition.** 72 clothing items (40 topwear, 32 bottomwear) and 32 accessories (12 sunglasses, 10 socks, 10 hats/caps); 52 male, 52 female; 10 fictional brands; prices follow fast-fashion (H&M-like) bands from ₹399 to ₹3,999. Four of the topwear items are waterproof jackets (`APL-TOP-M-101`–`APL-TOP-F-104`), added so the requirements' flagship query — a waterproof jacket for cold-weather hiking — has something real to retrieve.

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

**Grain.** One row per **variant** = product × size × color (1002 rows). A clothing product with 6 sizes and 3 colors contributes 18 rows. This is the level at which online retailers actually track stock, because customers buy variants, not products.

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
| `Stock_status` | string, enum | Derived health flag: `in_stock` (available > reorder point), `low_stock` (0 < available ≤ reorder point), `out_of_stock` (available = 0). Current mix: 773 / 157 / 72. |
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
| `Customer_ID` | string | The purchasing customer, `CUST-0001`–`CUST-0177`. Customers repeat across orders, enabling repeat-purchase analysis. |
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

## 5. Table: `product_reviews`

**Purpose.** The voice of the customer — what buyers actually thought of a product after wearing it. It answers the questions a shopper asks before committing ("is this true to size?", "does the colour match the photos?", "is the fabric as good as the description claims?") and gives the assistant social proof to cite instead of only marketing copy. Ratings and fit feedback also feed quality analytics: which products under-deliver, and which fits drive returns.

**Grain.** One row per review = one shopper's verdict on one purchased line item (243 rows). A shopper who bought three items in one order can leave three separate reviews, one per item.

**Derivation (why it joins cleanly).** Reviews are generated from `order_tracking`, not invented independently, so every row is a genuine verified purchase: only lines with `Order_status` of `delivered` or `returned` are eligible (you cannot review what you never received), and roughly 65% of delivered lines and 80% of returned lines carry a review — returners are more vocal than satisfied buyers, a well-documented review bias. Reviews on returned lines are written to agree with that line's `Return_reason`, so a "Size too small" return and its 2★ review tell the same story. Like the other data files, this is a static committed artifact — if `order_tracking.csv` is ever regenerated, the reviews must be re-derived against it so the `Order_item_ID` foreign keys stay valid.

**Coverage.** 83 of the 104 products have at least one review, from 111 distinct shoppers; the remaining 21 are the unreviewed long tail — including the four waterproof jackets, which are new to the catalog and so have no orders and no reviews behind them. Mean rating is 3.82 (97×5★, 56×4★, 48×3★, 33×2★, 9×1★) — positively skewed, as real review distributions are. Any recommendation logic must therefore treat "no reviews" as a normal case, not an error.

### Columns

| Column | Type | Description |
|---|---|---|
| `Review_ID` | string, **primary key** | Unique review identifier, `REV-NNNNNN`. |
| `ID (SKU)` | string, **foreign key → product_catalog** | The product being reviewed. Join here for brand, title, price, description. |
| `Customer_ID` | string, **foreign key → shopper_profiles** | The reviewing shopper, `CUST-0001`–`CUST-0177`. |
| `Order_item_ID` | string, **foreign key → order_tracking** | The exact line item purchased. Unique across reviews — one review per line item, which is what makes `Verified_purchase` true by construction. |
| `Order_ID` | string | The parent order, denormalized so review-to-order questions don't need a join. |
| `Size` / `Color` | string | The variant the reviewer actually received. Essential for reading fit complaints correctly — "runs small" is only meaningful alongside the size ordered. |
| `Rating` | integer 1–5 | Star rating. 4–5 = satisfied, 3 = lukewarm, 1–2 = dissatisfied. |
| `Review_title` | string | Short headline, e.g. "Runs at least one size small". |
| `Review_text` | string | One-to-two sentence review body in natural language, referencing the product's real attributes (fabric, fit, lens, occasion). Together with `Review_title` this is the embeddable text if reviews are added to the RAG corpus. |
| `Fit_feedback` | string, enum | `True to size`, `Too small`, `Too large`, or empty. **Empty for all Accessories** (sunglasses, caps, hats, socks are Free Size or unsized, so fit feedback is meaningless there). Aggregate this per SKU to answer "should I size up?". |
| `Verified_purchase` | string | Always `TRUE` in this dataset, since every review derives from a real delivered/returned line item. Kept as a column because production review systems mix verified and unverified. |
| `Helpful_votes` | integer 0–34 | Other shoppers who marked the review useful. Skewed low, with 1★ and 5★ reviews collecting more votes than middling ones. Use as a ranking signal when quoting reviews. |
| `Reviewed_at` | date | When the review was posted — 1–21 days after `Delivered_at`, never before it. Range 2026-06-02 to 2026-07-19. |

---

## 6. File: `shopper_profiles.json`

**Purpose.** Who the shopper is, so the assistant can personalize without re-asking. This is the memory layer's backing store: it holds identity, purchase-derived preferences (usual sizes, colours, occasions, budget), loyalty standing, and a small rolling set of preferences learned from conversation. It is what makes cross-session recall possible — a preference stated in one session is read back in the next.

**Shape.** A JSON **object keyed by `Customer_ID`** (not an array), so lookup is `profiles["CUST-0083"]`. 150 shoppers, IDs sparse in the range `CUST-0001`–`CUST-0177`. Every shopper has at least one order in `order_tracking` (1–6 orders each).

**Two preference blocks, deliberately separate.** `preferences` is **derived from purchase history** by a batch process and is owned by it — application code must never write there. `learned_preferences` is **chat-derived**, append-only, and capped at the 3 most recent notes; this is the only block the running agent writes. Precedence at answer time: what the shopper says in the current message > recent chat notes > purchase history. See [`src/memory.py`](../src/memory.py) for the read/write API (`get_profile`, `remember_preference`, `profile_to_prompt`).

### Fields

| Field | Type | Description |
|---|---|---|
| `customer_id` | string, **key** | Matches the object's key and `order_tracking.Customer_ID`. |
| `name` | string | Shopper's full name (Indian names, matching the dataset's locale). Used to greet by first name. |
| `phone_no` | string | `+91-NNNNNN-NNNNN`. Synthetic; populated for all 150 shoppers. |
| `email` | string | `first.lastNN@example.com`. Synthetic, non-routable domain by design. |
| `gender` | string, enum | `male` / `female` — **lowercase here**, whereas `product_catalog.Gender` is `Male` / `Female`. Normalize case before using it as a catalog filter. Split: 82 female, 68 male. |
| `age` | integer | 18–64. Note the whole dataset is adult shoppers; there is no minors' segment. |
| `preferences` | object | Purchase-derived defaults. **Batch-owned — do not write from app code.** Sub-fields below. |
| `preferences.colour` | array of strings | Colours this shopper actually buys, drawn from catalog colourways (71 distinct values across the dataset). |
| `preferences.size` | object | `{"top": <size>, "bottom": <size>}` — present for all shoppers. Clothing sizes `XS`–`XXL`. |
| `preferences.occasion` | array of strings | Occasions they shop for: Casual (most common), Smart Casual, Formal, Everyday, Gym, Evening, Lounge, Yoga, Festive, Winter, Sports, Resort, and others. |
| `preferences.style_notes` | string | One-sentence prose summary of buying pattern, e.g. "Mostly buys jackets for outdoor occasions; favours performance/polyester fabrics, usually regular fit". Written to be dropped straight into a prompt. |
| `preferences.budget_inr` | integer | Typical per-item ceiling, banded: 500, 1000, 1500, 2000, 2500, 3000, 4000. Treat as a soft default, never as an override of a budget the shopper states in the conversation. |
| `learned_preferences` | array of objects | Chat-derived notes, **oldest evicted past 3**. Each: `{"note": <short phrase>, "learned_at": <ISO timestamp>, "source": "chat"}`. Empty for 147 of 150 shoppers — this block fills up only as the assistant is used. |
| `loyalty.tier` | string, enum | `Bronze` (54), `Silver` (60), `Gold` (26), `Platinum` (10). |
| `loyalty.points` | integer | 0–2558, roughly tracking cumulative spend. |
| `loyalty.member_since` | date | Signup date, 2023-01-03 to 2025-12-22. |
| `loyalty.total_orders` | integer 1–6 | Lifetime order count. Should agree with `COUNT(DISTINCT Order_ID)` for that customer in `order_tracking`. |

---

## 7. Cross-Table Enumerations (quick reference)

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
- **Rating:** 1 · 2 · 3 · 4 · 5 · **Fit_feedback:** True to size · Too small · Too large · (empty for Accessories)
- **Loyalty tiers:** Bronze · Silver · Gold · Platinum
- **Gender casing:** `Male`/`Female` in the catalog · `male`/`female` in shopper profiles — normalize before filtering

---

## 8. How the Tables Work Together (worked examples)

**"Is the Everyday Crew Tee available in M, Black?"**
Catalog: find `title = "Everyday Crew Tee"` → `ID (SKU) = APL-TOP-M-001`. Inventory: find `ID (SKU) = APL-TOP-M-001 AND Size = "M" AND Color = "Black"` → read `Qty_available` and `Stock_status`.

**"Where is order ORD-2026-000123?"**
Order tracking: filter `Order_ID`, read `Order_status`; if shipped, quote `Courier_partner`, `Tracking_number`, `Expected_delivery`.

**"Which products should we restock first?"**
Inventory: `Stock_status IN (low_stock, out_of_stock) AND Qty_incoming = 0`, join catalog for names; prioritize by how far below `Reorder_point` the variant sits.

**"What's our return rate and why do people return?"**
Order tracking: `COUNT(DISTINCT Order_ID WHERE Order_status='returned') / COUNT(DISTINCT Order_ID delivered-or-returned)`; group `Return_reason` for the why; join `ID (SKU)` → catalog to see whether specific products or fits drive returns.

**"Does this jacket run small?"**
Catalog: title → `ID (SKU)`. Reviews: filter that SKU, aggregate `Fit_feedback` — if `Too small` dominates, advise sizing up and quote the highest-`Helpful_votes` review saying so. Remember 17 products have no reviews at all; say so rather than implying consensus.

**"Show me something like last time, within my usual budget."**
Shopper profiles: `profiles[customer_id]` → `preferences.budget_inr`, `preferences.size`, `preferences.colour`, plus any `learned_preferences` notes (which outrank purchase history). Filter the catalog on those, then confirm stock in `inventory` before recommending.

**"Which products are quietly hurting us?"**
Reviews: mean `Rating` per SKU where review count ≥ 2; cross-reference `order_tracking.Return_reason` for the same SKUs. A low rating plus size-related returns points at a fit/size-chart problem rather than a quality one.

**Note for vector-DB usage.** Embed the catalog's text fields for semantic retrieval; optionally embed `Review_title` + `Review_text` as a second document type (keep `ID (SKU)` and `Rating` in metadata so reviews can be filtered and attributed back to a product). Keep inventory, order, and profile data in structured storage (SQL/dataframe/JSON) and route quantitative and per-shopper questions there. If this document itself is embedded for schema-RAG, chunk it by section (one chunk per table, plus one for the overview and enumerations).
