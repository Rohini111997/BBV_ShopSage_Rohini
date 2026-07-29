# ShopSage — Error Analysis (Task 27)

Baseline eval run: 2026-07-29 | Agent: Agent_3 | Score: see `docs/evidence/eval_baseline.json`

---

## Failure Categories

| Category | Description | Tasks Affected |
|---|---|---|
| **Retrieval miss** | Correct product type not in top-k results | TC-01, TC-02 |
| **Tool error** | MCP tool called with wrong args or tool unavailable | TC-03, TC-04 |
| **Guardrail miss** | Age/stock guardrail not triggered when it should be | TC-06 |
| **Fabricated attribute** | LLM invents price, color, or stock not in context | All |
| **Routing error** | Query misclassified (e.g., follow_up routed as new_search) | TC-05 |

---

## Per-Case Analysis

### TC-01 — Breathable gym socks for women under ₹600
- **Expected:** `new_search`, ≥1 product, all ≤ ₹600, keywords: sock/gym/breathable
- **Root cause (if failing):** `item_type` metadata on socks may be indexed as `"socks"` but query semantic may score t-shirts higher if Chroma k=6 is too broad
- **Fix applied:** Retrieval k=6 with `gender=female` + `price_inr ≤ 600` filter; catalog verified to have 3 qualifying socks items

### TC-02 — Formal shirt for office wear, men, under ₹1500
- **Expected:** `new_search`, ≥1 product ≤ ₹1500, keywords: shirt/formal/office
- **Root cause (if failing):** "Boardroom Oxford Shirt" at ₹1499 is right at the edge; filter must be `$lte` not `$lt`
- **Fix applied:** Chroma `$lte` used in `_build_where`; confirmed by retrieval_test.log (item [2] at INR 1499 returned)

### TC-03 — Inventory check: Everyday Crew Tee, size M
- **Expected:** `inventory_check` route, `check_inventory` tool called, `ok=true`
- **Root cause (if failing):** Slot extractor may route as `follow_up` if "in stock" phrasing is ambiguous
- **Fix applied:** Routing hint in `_extract_slots` prompt: `"Is it in stock?" / "do you have this in M?" → inventory_check`; `get_in_stock_sizes` MCP tool used for stock guardrail separately

### TC-04 — Order tracking: ORD-1042
- **Expected:** `order_tracking` route, `track_order` tool called
- **Root cause (if failing):** Customer ID `CUST-0028` must be set via `set_shopper()` before the query; if not logged in, agent asks for customer ID instead
- **Fix applied:** `evaluate_case` calls `rag_agent.set_shopper(cust_id)` before each query

### TC-05 — Memory: budget recalled across sessions
- **Expected:** `budget_from_memory=True` in session 2 `memory_recall` event
- **Root cause (if failing):** `record_session_learnings` writes only for `new_search`/`follow_up`; greeting turns do not persist. `budget_inr` must be set structurally on the note (not just in text).
- **Fix applied:** `note_from_slots` stores `budget_inr` as a dedicated key; `learned_budget()` reads it back without string parsing; `item_intent_extracted` flag prevents "hi" from being stored

### TC-06 — Age filter guardrail: "dress for my 8-year-old niece"
- **Expected:** `for_child=True` extracted, `guardrail: {rule: age_filter}` event in trace
- **Root cause (if failing):** LLM may return `for_child=null` instead of `true` if phrasing is indirect. Normalization: `str(c.get("for_child")).strip().lower() == "true"` handles LLM variation
- **Fix applied:** Strict bool normalization in `_extract_slots`; `age_appropriate=True` Chroma filter added when `for_child=True`; `trace.event("guardrail", rule="age_filter", ...)` now emitted

---

## Top 3 Fixes Applied (for T28)

| Priority | Fix | Where |
|---|---|---|
| 1 | **Bug: `set_shopper` null-dereference on new guests** — `first_name` accessed before `profile is None` check | `Agent_3.py` `set_shopper()` — fixed 2026-07-29 |
| 2 | **Guardrail events not traced** — `age_filter` and `stock_filter` guardrails ran silently; the trace panel showed no evidence of guardrail activity | `Agent_3.py` `_run_turn()` — fixed 2026-07-29, both guardrails now emit `trace.event("guardrail", ...)` |
| 3 | **Cache hits invisible in traces** — `_retrieval_cache` hit/miss was only logged to console, not to the agent-trace panel; the UI and eval suite could not count cache efficiency | `Agent_3.py` `retrieve_relevant_knowledge()` — fixed 2026-07-29, now emits `cache_hit`/`cache_miss` trace events |

---

## Remaining Known Issues

| Issue | Severity | Status |
|---|---|---|
| `get_in_stock_sizes` MCP tool must exist on the server for `_is_recommendable()` to work; if absent, fail-open behaviour returns True (product shown) | Medium | Fail-open is intentional — tool error ≠ product blocked |
| `age_appropriate` field must be present in catalog JSONL; items without it default to `False` in `Ingest_Embedding.py` | Medium | Catalog v2 includes this field |
| LangSmith tracing not validated against a live key | Low | Documented in `docs/observability.md` |
