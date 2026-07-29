# ShopSage: 4-Week Task Plan
*Core path: 32 one-hour tasks; this is the safe, required build every team should be able to finish. Stretch Goals (bottom) are optional add-ons for teams with extra time.*

## Week 1: Foundations, RAG & UI (9 tasks)
**Demo Goal:** A live Gradio chat UI that answers a product-search request with a RAG-grounded shortlist; no tools, memory, or guardrails yet, but it's clickable and shareable.

| # | Task (~1 hr) | Definition of Done | Evidence of Completion |
|---|---|---|---|
| 1 | Kickoff: assign roles, review requirements.md and Priya Kapoor's persona/objective, agree on tech stack | Roles assigned (prompt/RAG, tools/MCP, memory, guardrails/caching, observability/UI owners); requirements.md read by everyone; stack agreed | A `docs/team.md` listing roles and stack, with each member confirming they've read requirements.md |
| 2 | Set up the git repository: initialize repo, agree on branch strategy, add .gitignore, write a README | Repo exists remotely with main + feature branches; README lets a fresh clone run the project | A teammate clones the repo and runs it successfully from README alone |
| 3 | Draft the system prompt: shopping-assistant tone, budget-aware recommendation rules | Prompt file committed; 2 manual test prompts respect the stated budget | Prompt file in repo + pasted transcript of the 2 test runs |
| 4 | Generate a synthetic dataset of shopper preference histories, past orders, and product reviews | Dataset file committed with several shopper profiles and order histories | Dataset file in repo + a summary count of profiles/orders |
| 5 | Prepare a sample product catalog (titles, descriptions, attributes) for the RAG corpus | Catalog covers all 6 sample queries in requirements.md, especially the jacket search | Catalog file committed with item count |
| 6 | Build the ingestion pipeline: chunk and embed the catalog into a vector store | Pipeline runs with no errors; vector store has the expected chunk count | Console log showing chunk/embedding count |
| 7 | Implement retrieval and test against "waterproof jacket under $80" | Relevant product chunk(s) appear in the top-3 retrieved results | Logged query + retrieved chunks with a correct/incorrect judgment |
| 8 | Wire a minimal prototype: query → ranked shortlist (no tools yet) | Full query→shortlist round trip runs without crashing and reflects catalog data | Terminal/notebook transcript of one successful run |
| 9 | Build a Gradio chat UI for the prototype and deploy it locally with a shareable link | Gradio app launches and returns a grounded shortlist for a real query | Screenshot of the running UI + shareable link posted to the team channel |

## Week 2: Tools, MCP & Memory (7 tasks)
**Demo Goal:** The same Gradio UI now checks live inventory/variant availability and order status, and remembers the shopper's budget preference across two visits; visible live in the chat.

| # | Task (~1 hr) | Definition of Done | Evidence of Completion |
|---|---|---|---|
| 10 | Design tool specs: `check_inventory(product_id, variant)` and `track_order(order_id)` | Written spec for both tools: inputs, outputs, error cases | `docs/tools.md` with both signatures and example input/output |
| 11 | Implement the inventory/variant-check tool | Returns correct stock status for a known product/variant and a clear error for an unknown one | Test log showing both cases |
| 12 | Implement the order-tracking tool | Returns correct status for a known order and a clear error for an unknown one | Test log showing both cases |
| 13 | Set up MCP to expose both tools to the agent; test a full round trip | Agent calls both tools via MCP and uses their results in a live response | Trace/log of one query showing the response built from tool output |
| 14 | Design the memory schema: style/budget preferences and purchase history | Schema documented; a record can be written and read back correctly | Schema doc + log of one record written and retrieved |
| 15 | Integrate memory; test preference recall (e.g., "hiking gear under $100") across 2 sessions | Preference stated in session 1 is correctly recalled, unprompted, in session 2 | Transcripts of both sessions showing the preference and its recall |
| 16 | Wire tools and memory into the Gradio UI via an expandable "agent trace" panel | Panel lists each tool call and the recalled preferences for the response | Screenshot of the panel expanded on a real query |

## Week 3: Guardrails & Caching (7 tasks)
**Demo Goal:** In the live UI, show the agent refuse to recommend an out-of-stock or age-restricted item, and show a visible speed-up (cache hit badge) on a repeated catalog query.

| # | Task (~1 hr) | Definition of Done | Evidence of Completion |
|---|---|---|---|
| 17 | Codify guardrail rules: no out-of-stock recommendations, no age-restricted items, no fabricated attributes | Rules written as a checklist mapped to requirements.md's guardrail section | `docs/guardrails.md` listing each rule with its requirements.md reference |
| 18 | Implement guardrail checks verified against live inventory tool output | Every recommendation passes through the guardrail check before reaching the user | Log entry showing a recommendation being filtered by the guardrail layer |
| 19 | Test guardrails against the out-of-stock item and "gift for my 10-year-old" | Both are correctly filtered/refused; a benign query is not falsely blocked | Transcripts of all 3 test runs |
| 20 | Implement caching for product embeddings and frequent queries | Repeated identical queries hit the cache instead of re-querying | Log showing a cache miss then a cache hit on the repeat |
| 21 | Measure cache hit rate and latency improvement | Latency compared for cached vs. uncached calls with documented improvement | Before/after latency numbers committed to the repo |
| 22 | Run all 6 sample queries from requirements.md end-to-end; fix bugs | All 6 run and are compared against the expected-answers table | Filled-in expected-answers table with actual output and pass/fail per row |
| 23 | Surface guardrail status and cache hit/miss as visible badges in the Gradio UI | UI visibly shows guardrail blocks and cache hits | Screenshots showing both badge states |

## Week 4: Observability, Evals & Demo Readiness (9 tasks)
**Demo Goal:** Full live walkthrough: Gradio UI + observability dashboard, an eval score shown before/after your error-analysis fixes, and a guardrail refusal on demand.

| # | Task (~1 hr) | Definition of Done | Evidence of Completion |
|---|---|---|---|
| 24 | Instrument observability: log retrievals, tool calls, guardrail triggers, and tool failures | Every event for one request shares a single trace ID | Exported trace for one request showing all event types tied together |
| 25 | Build an eval harness from the expected-answers table with pass/fail scoring | Each of the 6 rows is an automated test case with a scorer | Eval script committed, runnable with one command |
| 26 | Run the eval suite against the synthetic shopper data; record baseline scores | Suite runs successfully and produces a baseline score | Saved baseline report (score, timestamp, per-case pass/fail) |
| 27 | Do error analysis: categorize failures, find root causes, pick top 3 fixes | Every failing case is categorized (retrieval miss, tool error, guardrail miss, fabricated attribute, latency) with a root cause and prioritized fix | Error-analysis table committed |
| 28 | Apply the top fixes and re-run the eval suite; record the improvement | Score improves measurably over baseline after the fixes | Before/after eval report showing the score delta |
| 29 | Build a dashboard: tool-call failure rate, recommendation click-through, guardrail trigger count | Dashboard shows real data and is reachable from the UI | Screenshot/link of the live dashboard with real run data |
| 30 | Handle edge cases: inventory API timeout, ambiguous "the second one" references, no catalog match | Each edge case produces a graceful fallback instead of a crash | Log/transcript of each edge case being triggered and handled |
| 31 | Prepare the demo script: Priya persona, 2-3 live queries, a memory demo, the scorecard | Script covers all elements and is timed to the demo slot | Script document + timed rehearsal note |
| 32 | Final rehearsal, deploy the demo build, record a backup demo video | Live demo runs end-to-end without failure; build deployed and reachable; backup video exists | Deployment link + backup video link, both in README |

## Stretch Goals (optional; the core path above is the safe, required build)
- Baseline comparison: run the same requests through a vanilla LLM with no RAG/tools/guardrails, and show side-by-side why grounded, budget-aware search matters.
- Red-team your own agent: try to get it to recommend an out-of-stock or age-restricted item anyway (misleading phrasing, indirect requests), then harden the guardrail against what worked.
- Add image-based product search (upload a photo, find similar catalog items).
- Set and hit a latency/cost budget (e.g., under 3s and under $0.01/query) and show the before/after numbers.
- (Add your own ideas here as the team comes up with them.)
