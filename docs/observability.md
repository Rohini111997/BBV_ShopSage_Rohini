# ShopSage Observability

Every shopper message produces one `Trace` — routing, memory, retrieval, tool calls, guardrail decisions, cache hits, failures — sharing a single `trace_id`.

- **Implementation:** [`src/observability.py`](../src/observability.py)
- **Collected in:** [`src/Agent_3.py`](../src/Agent_3.py) (`get_rag_product_recommendation` → `_run_turn`)
- **Evidence:** [evidence/trace_test.log](evidence/trace_test.log)

Instrument once, consume twice:

| Consumer | How it gets the trace | Task |
|---|---|---|
| Agent-trace panel in the chat UI | returned as `trace` on the `/api/chat` response | 16 |
| LangSmith dashboard | the same spans, when tracing is enabled | 24, 29 |

The panel deliberately reads the in-process record rather than querying LangSmith's API — the data is produced in the same request, so fetching it back over the network would add latency and a hard dependency on a third-party service being reachable mid-demo.

## Event kinds

| Kind | Recorded fields |
|---|---|
| `extract_slots` | duration of the routing LLM call |
| `route` | chosen `query_type` and the full extracted slots |
| `memory_write` | the note persisted this turn |
| `memory_recall` | which slots were backfilled, `budget_from_memory`, current learned notes |
| `retrieval` | search query, `k`, metadata filters, and each hit (SKU, title, price) |
| `retrieval_relaxed` | the budget-dropped retry used for "nothing under your budget" |
| `cache_hit` | kind_detail=`retrieval`, cumulative hits/misses, query text |
| `cache_miss` | kind_detail=`retrieval`, cumulative hits/misses, query text |
| `guardrail` | rule name (`age_filter` / `stock_filter`), counts of retrieved/blocked SKUs |
| `tool_call` | tool name, arguments, result, `ok`, duration |
| `generate` | which path generated the reply, and its duration |
| `unhandled_error` | exception type and message if the turn dies |

Every event carries `at_ms` (offset from the start of the turn) and spans also carry `ms` (their own duration), so a slow turn can be attributed without a profiler.

**Failures are recorded, not swallowed.** `Trace.span` marks a failing block `ok: false` with the error text and then re-raises — tracing never hides a bug. `trace.failures()` returns them, which is what the Week 4 tool-call failure rate will count.

## Shape

```json
{
  "trace_id": "61b04eebcf78",
  "customer_id": "CUST-0002",
  "query": "is the Summit Waterproof Trail Jacket in stock in size M in Forest Green?",
  "total_ms": 1970,
  "langsmith": false,
  "events": [
    {"kind": "route", "at_ms": 365, "query_type": "inventory_check", "slots": {...}},
    {"kind": "retrieval", "at_ms": 365, "ms": 50, "filters": {...}, "hits": [...]},
    {"kind": "tool_call", "at_ms": 416, "ms": 1134, "tool": "check_inventory",
     "args": {"sku": "APL-TOP-M-102", "size": "M", "color": "Forest Green"},
     "result": "Out of Stock", "ok": true},
    {"kind": "generate", "at_ms": 1550, "ms": 419, "path": "inventory_check", "ok": true}
  ]
}
```

## LangSmith

**Optional and off by default.** With no key set, `@traceable` is a no-op and the in-process trace still works, so no one needs a LangSmith account to run the project.

Enable by adding both to `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls__...        # smith.langchain.com -> Settings -> API Keys
LANGSMITH_PROJECT=shopsage
```

Startup prints which mode it's in:

```
[observability] LangSmith tracing disabled (set LANGSMITH_TRACING + LANGSMITH_API_KEY to enable)
```

Both variables are required. A key without the flag does nothing; the flag without a key makes LangChain retry against an unauthenticated endpoint on every LLM call, which is why `observability.py` clears the flag unless both are present.

When enabled you get two layers:

- **Automatic** — `ChatGroq` calls and the Chroma retriever are LangChain components, so LangSmith captures them with no extra code
- **Explicit** — `@traceable` on `get_rag_product_recommendation` (the parent span, `run_type="chain"`) and on both MCP tool wrappers (`run_type="tool"`). The tool calls need this because MCP sits outside LangChain and would otherwise be invisible

> **Not yet verified against the live service.** The disabled path is tested end-to-end; the enabled path is wired per the LangSmith SDK but nobody has run it with a real key. First person to add one should confirm traces land in the project and that the tool spans nest under the turn.

## What's still missing for Week 4

- **Dashboard** (task 29) — tool-call failure rate and guardrail counts, aggregated across traces. `trace.failures()` is the hook; guardrail triggers now appear in every trace via `kind="guardrail"` events.
- **Persistence** — traces are per-request and in-memory; nothing is stored server-side yet, so aggregate metrics need either LangSmith or a local sink.

> **Guardrail events are now wired** (tasks 18, 24). Both `age_filter` and `stock_filter` emit a `guardrail` event on the trace, visible in the agent-trace panel and in LangSmith when enabled.
