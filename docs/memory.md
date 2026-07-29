# ShopSage Memory (Task 14)

Per-shopper preferences that survive across sessions, so a budget or style stated once doesn't have to be restated.

- **Implementation:** [`src/memory.py`](../src/memory.py)
- **Store:** [`DataBase/shopper_profiles.json`](../DataBase/shopper_profiles.json) — a JSON object keyed by `Customer_ID`, 150 shoppers
- **Field-by-field reference:** [Data Deatils.md §6](Data%20Deatils.md)

The store is a file, not Postgres. Persistence across sessions means across *process restarts*, which a file gives us; the tool-backed tables (inventory, orders) are the ones that live in Neon.

## Record schema

```json
"CUST-0083": {
  "customer_id": "CUST-0083",
  "name": "Tanvi Joshi",
  "phone_no": "+91-...", "email": "...", "gender": "female", "age": 31,

  "preferences": {
    "colour": ["Black", "Lilac"],
    "size": {"top": "S", "bottom": "XS"},
    "occasion": ["Gym", "Outdoor"],
    "style_notes": "Mostly buys jackets and t-shirts for gym and outdoor occasions",
    "budget_inr": 3000
  },

  "learned_preferences": [
    {"note": "Interested in party wear, budget under ₹2500",
     "learned_at": "2026-07-28T15:20:52", "source": "chat", "budget_inr": 2500}
  ],

  "loyalty": {"tier": "Gold", "points": 1420,
              "member_since": "2024-03-11", "total_orders": 4}
}
```

## Two preference blocks, and who owns them

| Block | Derived from | Written by | Lifetime |
|---|---|---|---|
| `preferences` | purchase history | a batch process **only** | stable |
| `learned_preferences` | conversation | the running agent | last 3 notes, oldest evicted |

`src/memory.py` never writes to `preferences` — that block belongs to the batch regeneration script. Chat writes only ever touch `learned_preferences`.

**Precedence at answer time:** what the shopper says in the current message > recent chat notes > purchase history. `profile_to_prompt` renders both blocks with that rule spelled out, so the LLM can't quietly override an explicit request with a remembered one.

## API

| Function | Purpose |
|---|---|
| `get_profile(customer_id)` | Full record, or `None` if unknown |
| `upsert_guest(customer_id, name="Guest")` | Minimal record for a first-time shopper |
| `profile_to_prompt(profile)` | Render the profile as a system-prompt section |
| `apply_profile_defaults(slots, profile)` | Backfill missing extraction slots from memory |
| `learned_budget(profile)` | Most recent budget the shopper stated in chat |
| `remember_preference(customer_id, note, source="chat", budget_inr=None)` | Append one note; dedupes, keeps last 3 |
| `note_from_slots(slots)` | Compose a note from a turn, or `None` if nothing durable |
| `record_session_learnings(customer_id, slots)` | Orchestrator hook — call after every extraction |

Writes are atomic (temp file + `replace`), so a crash mid-write can't leave a half-written store.

## What actually gets remembered

`record_session_learnings` only writes on `new_search` / `follow_up` turns — order-tracking and inventory checks leave no trace. Within those, `note_from_slots` returns `None` unless the turn carried something durable (item intent, colour, occasion, budget), so greetings and filler don't become notes.

The turn's item intent is only recorded when slot extraction genuinely produced one. The agent falls back to the raw message when extraction returns nothing, and that fallback is flagged (`item_intent_extracted`) so memory skips it — without this, "hi" was being stored as `"Interested in hi"`.

## Budget recall across sessions

The behaviour sample query 5 asks for ("I usually shop for hiking gear under ₹1500; remember that" → applied unprompted in a later session):

1. Session 1 — the stated budget is saved **structurally** on the note as `budget_inr`, not just inside the note text, so it can be read back without parsing prose.
2. Session 2 — `apply_profile_defaults` fills the empty `max_price_inr` slot from `learned_budget(profile)` and sets `budget_from_memory: true`.
3. The agent's prompt rules require it to say once that it applied a remembered budget — never silently.

Two deliberate limits:

- **`preferences.budget_inr` is never applied as a filter.** It's purchase-derived and soft; hard-filtering on it would cap searches the shopper never capped, which is exactly what guardrail requirement 4 forbids.
- **A budget stated in the current message always wins.** Backfill only fills empty slots.

Ordering matters in the orchestrator: learnings are recorded from the raw extraction *before* backfill, so a recalled value doesn't get re-persisted as a fresh learning each turn.

## Verification

`python -m src.memory` runs a write / cap-at-3 / read-back self-test against a **temp copy** of the store, so it never dirties committed data. Log: [evidence/memory_test.log](evidence/memory_test.log).

```
[1] wrote: Interested in kurtas, budget under ₹1500
[2] wrote: Prefers pastels for office wear
[3] wrote: Interested in linen shirts, for beach trip
[4] wrote: Interested in party wear, budget under ₹2500

Kept on disk (3):   ← oldest evicted
  - Prefers pastels for office wear
  - Interested in linen shirts, for beach trip
  - Interested in party wear, budget under ₹2500

✅ Cap-at-3 + read-back verified.
```

Cross-session budget recall, verified separately:

```
SESSION 1  states ₹1500   → stored {'note': 'Interested in hiking jacket, budget under ₹1500', 'budget_inr': 1500}
SESSION 2  no budget      → max_price_inr: 1500, budget_from_memory: True
current message ₹800      → 800 (memory does not override)
purchase-derived ₹3000    → not backfilled
```
