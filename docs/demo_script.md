# ShopSage — Demo Script (Task 31)

**Persona:** Priya Kapoor, 29, Bengaluru. Active fitness enthusiast who also shops for office wear. Budget-conscious but not cheap. Loyal Gold-tier member.
**Customer ID:** `CUST-0083`
**Demo slot:** ~8 minutes | **Backend:** `uvicorn backend.main:app --port 8000` | **Frontend:** React app on `localhost:3000`

---

## 0. Setup Checklist (before audience arrives)

- [ ] `uvicorn backend.main:app --reload --port 8000` is running (confirm `[MCP] connected to retail-tools` printed)
- [ ] Frontend `npm run dev` running on port 3000
- [ ] Browser tab open on `localhost:3000`
- [ ] `.env` has `GROQ_API_KEY` set (LangSmith optional)
- [ ] Chroma DB built: `python -m src.Ingest_Embedding` (check console: `104 chunks`)
- [ ] Backup transcript ready in case of API timeout

---

## 1. Opening — Who is ShopSage? (30 sec)

> "ShopSage combines three things most chatbots miss: a grounded product catalog (no hallucinated items), live inventory and order data via MCP tools, and persistent memory so shoppers never repeat themselves."

---

## 2. Login as Priya (20 sec)

Type customer ID: **`CUST-0083`**

Expected: `Welcome back, Tanvi` (demo customer). Mention that her profile auto-loaded: Gold tier, size S/XS, prefers Black & Lilac.

---

## 3. Query 1 — RAG Search + Budget Hard-Filter (2 min)

**Type:** `I need a waterproof jacket for hiking, budget under 4000`

Show in trace panel:
- `route → new_search`
- `retrieval` span with `price_inr ≤ 4000` + `gender=female` (from memory, she didn't type it)
- `generate` span
- 3 product cards, all under ₹4000

Talking point: budget is a Chroma filter — items above ₹4000 never reach the LLM.

---

## 4. Query 2 — Follow-up Question (1 min)

**Type:** `Does the first one come in black?`

Show: `route → follow_up`, unfiltered retrieval (must see the item), reply names the jacket and lists catalog colors.

Talking point: "the first one" resolved from conversation history — no tool needed.

---

## 5. Query 3 — Live Inventory via MCP Tool (2 min)

**Type:** `Is the Summit Waterproof Trail Jacket in stock in size M?`

Show:
- `route → inventory_check`
- Retrieval resolves product name → SKU
- `tool_call: check_inventory(sku=..., size=M)` with real result

Talking point: stock data is live from the inventory table — the vector store only knows what sizes *exist*, not what is *available now*.

---

## 6. Memory Demo — Cross-Session Recall (1 min)

Re-login as `CUST-0083`, then type: `Show me some jackets`

Show: `memory_recall: {max_price_inr: 4000, budget_from_memory: true}`
Reply explicitly mentions applying the remembered budget.

---

## 7. Guardrail Demo — Age Filter (45 sec)

**Type:** `I want to buy a dress for my 8-year-old niece`

Show: `guardrail: {rule: age_filter, active: true}` in trace. Point out the Chroma filter `age_appropriate=True` was added — adult items never entered the LLM context.

---

## 8. Order Tracking (30 sec)

**Type:** `Where is my latest order?`

Show: `route → order_tracking`, `track_order(customer_id=CUST-0083)` — retrieval skipped. Reply gives order ID, status, expected delivery.

---

## 9. Scorecard (30 sec)

Show eval output: 6/6 test cases passing.
Run: `python tests/eval_suite.py`

---

## 10. Backup Plan

If network/API fails:
1. Show `docs/evidence/trace_test.log` — real multi-session trace with tool call
2. Show `docs/evidence/retrieval_test.log` — 4/4 cases with actual results
3. Run `python tests/trace_test.py` locally

---

## Timed Rehearsal

| Segment | Target |
|---|---|
| Setup + login | 0:50 |
| Query 1 (RAG) | 2:50 |
| Query 2 (follow-up) | 3:50 |
| Query 3 (inventory) | 5:50 |
| Memory demo | 6:50 |
| Guardrail + order | 8:05 |
| Scorecard | 8:35 |
| **Total** | **~8:35** |
