# ShopSage

**An AI shopping assistant that understands what you want, remembers who you are, and keeps you safe.**

ShopSage helps shoppers discover and compare products from a catalog using conversational search (RAG), checks live inventory and order status via MCP tools, and remembers style and budget preferences across visits.

---

## Core Capabilities

### 1. Conversational product search (RAG)
Describe what you need in plain language — ShopSage retrieves matching products from the catalog and ranks them.

*"A crisp formal shirt for office wear, men, size L"* → a ranked shortlist with reasons, each item grounded in a real catalog entry.

### 2. Follow-up questions
Context carries across the conversation, so you can ask about an item you've already been shown.

*"Does the second one come in green?"* → resolves the reference and answers from the catalog's colour list.

### 3. Live inventory & order tracking
Stock and order status come from **tool calls against Postgres**, not from the product description — so the assistant can't guess at availability.

*"Is it in stock in size M?"* · *"Where's my order?"*

### 4. Remembered preferences
A budget stated in one session is applied in the next, unprompted — and the assistant says so rather than filtering silently.

Session 1: *"hiking gear under ₹1500"* → Session 2: *"show me jackets"* filters to ₹1500.

### 5. Guardrails *(Week 3 — not built yet)*
Refusing out-of-stock and age-restricted items is the next milestone.

---

## Architecture

| Layer | Component | Notes |
|---|---|---|
| Retrieval | LangChain + ChromaDB + HuggingFace `all-MiniLM-L6-v2` | One document per product, embedded from `product_catalog.jsonl` |
| LLM | Llama 3.3 70B via Groq | Slot extraction (routing) + grounded generation |
| Tools | `check_inventory`, `track_order` over **MCP** (stdio) | Back onto Neon Postgres — see [docs/tools.md](docs/tools.md) |
| Memory | JSON store, per shopper | See [docs/memory.md](docs/memory.md) |
| Observability | Per-request trace + optional LangSmith | See [docs/observability.md](docs/observability.md) |
| API | FastAPI | `backend/main.py` |
| UI | React + Vite (primary) · Gradio (demo) | |

Query flow: **extract slots → route** → `new_search`/`follow_up` take the RAG path, `inventory_check` resolves a product name to a SKU then calls the inventory tool, `order_tracking` calls the order tool and skips retrieval entirely.

---

## Setup

**Prerequisites:** Python 3.11+, Node 18+, a [Groq API key](https://console.groq.com/keys), and a Postgres database ([Neon](https://neon.tech) free tier is what we use).

### 1. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` includes `-e .`, which installs the project itself so `src.*` and `DataBase.*` import correctly from anywhere.

### 2. Configure secrets

Copy `.env.example` to `.env` and fill in both values:

```bash
DATABASE_URL=postgresql://user:password@ep-xxxx-pooler.region.aws.neon.tech/dbname?sslmode=require
GROQ_API_KEY=your_key_here
```

Both are required — the app raises on startup without them. `.env` is gitignored; never commit it.

LangSmith tracing is optional and off 1

### 3. Load the dataset into Postgres

```bash
python -m src.db.load
```

Creates the `products` / `inventory` / `order_tracking` tables and loads them from `DataBase/`. Safe to re-run — it clears and reloads in FK-safe order. The inventory and order tools query these tables.

### 4. Build the vector store

```bash
python -m src.Ingest_Embedding
```

Embeds the 104-product catalog into `chroma_db/`. Only needed once, and re-run when the catalog changes; the agent auto-ingests if it finds the store empty.

> **Run every command from the repo root.** `chroma_db/` is a relative path, so running from inside `src/` creates a second, empty store.

### 5. Run it

**React UI (primary)** — two terminals:

```bash
uvicorn backend.main:app --reload --port 8000    # terminal 1
cd frontend && npm install && npm run dev        # terminal 2
```

Open the Vite URL (default `http://localhost:5173`). It proxies `/api` to port 8000. Log in with a customer ID — e.g. `CUST-0083` — to see personalization; any unknown ID creates a guest.

**Gradio demo** — single process, prompts for a customer ID in the terminal before launching:

```bash
python -m src.Shopsage_RAG_Demo2
```

---

## Tests

```bash
python tests/tool_test.py      # both MCP tools, known + unknown inputs (needs DATABASE_URL)
python tests/retrieval_test.py # sample queries against the vector store
python tests/trace_test.py     # agent trace: routing, memory recall, tool calls
python -m src.memory           # memory write / cap-at-3 / read-back, on a temp copy
python tests/test_prompts.py   # budget-aware system prompt (needs GROQ_API_KEY)
```

Captured runs live in [docs/evidence/](docs/evidence/).

---

## Project Structure

```
DataBase/          product_catalog.jsonl · inventory.csv · order_tracking.csv
                   shopper_profiles.json · product_reviews.csv
src/
  Ingest_Embedding.py    catalog → Chroma
  Agent_1.py             prototype agent (RAG only)
  Agent_2.py             current agent: routing, RAG, MCP client, memory
  memory.py              shopper preference store
  observability.py       per-request trace + LangSmith wiring
  system_prompt.py       standalone budget-aware prompt (used by tests/test_prompts.py)
  tools/                 check_inventory · track_order · retail_mcp_server
  db/                    SQLAlchemy models, session, CSV → Postgres loader
  Shopsage_RAG_Demo1.py  Gradio UI over Agent_1
  Shopsage_RAG_Demo2.py  Gradio UI over Agent_2
backend/main.py    FastAPI: /api/login, /api/chat, /api/memory, /api/health
frontend/          React + Vite chat UI
docs/              team · data · tools · memory · observability · evidence
tests/             tool · retrieval · trace · prompt tests
```

Product images are served from `frontend/public/images/` and referenced by SKU.

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/Data Deatils.md](docs/Data%20Deatils.md) | All five data files: schema, columns, joins, worked examples |
| [docs/tools.md](docs/tools.md) | Tool signatures, inputs, outputs, error cases |
| [docs/memory.md](docs/memory.md) | Memory schema, precedence rules, cross-session recall |
| [docs/observability.md](docs/observability.md) | Trace shape, event kinds, LangSmith setup |
| [docs/team.md](docs/team.md) | Team roles, stack, sign-offs |

## Team

Team 2 — see [docs/team.md](docs/team.md) for roles and contacts.
