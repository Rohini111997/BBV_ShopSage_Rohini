# ShopSage

**An AI shopping assistant that understands what you want, remembers who you are, and keeps you safe.**

ShopSage helps users discover and compare products from a catalog using conversational search (RAG), real-time inventory & order tracking via tools, persistent shopping preferences via memory, and guardrails that prevent recommending out-of-stock or unsafe items.

---

## Core Capabilities

### 1. **Conversational Product Search (RAG)**
Describe what you need in plain language — ShopSage retrieves matching products from the catalog and ranks them by relevance.

**Example:** *"I need a waterproof jacket under $80 for cold-weather hiking."*
→ Returns a ranked shortlist (2–3 items) with reasons why each matches.

### 2. **Ask Follow-Up Questions**
ShopSage remembers context across the conversation — ask about variants without repeating yourself.

**Example:** *"Does the second one come in green?"*
→ Knows which item you're referring to, calls the inventory tool, checks availability.

### 3. **Real-Time Inventory & Order Tracking**
- Check stock status for sizes and colors instantly (via inventory tool)
- Track orders placed days or weeks ago (via order-tracking tool)
- If an item is out of stock, ShopSage suggests in-stock alternatives instead

**Example:** *"Is it in stock in size M?"* → Live inventory check, instant answer.

### 4. **Remember Your Preferences**
ShopSage stores your budget, style, and constraints in memory — future sessions use them automatically.

**Example:** 
- Session 1: *"I usually shop for hiking gear under $100"* → ShopSage confirms & stores it
- Session 2: *"Show me jackets"* → Automatically filters to under $100 without you asking

### 5. **Age-Appropriate Guardrails**
ShopSage refuses to recommend age-restricted or unsafe items, even if they match keywords.

**Example:** *"Show me something similar but cheaper for my 10-year-old."*
→ Filters strictly to child-safe products; never surfaces adult-oriented items.

---

## Architecture & Tech Stack

### Core Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Retrieval** | LangChain + ChromaDB + HuggingFace embeddings (`all-MiniLM-L6-v2`) | RAG: semantic search over product catalog (titles, descriptions, attributes) |
| **LLM** | Llama 3.3 70B (via Groq API) | Core reasoning: context understanding, memory synthesis, guardrail logic |
| **Tools** | Inventory & Order Tracking APIs (simulated) | Real-time checks for stock, variants, order status |
| **Memory** | LangChain memory (session-based) | Persistent user preferences, conversation history |
| **UI** | Gradio | Conversational interface |
| **Observability** | LangSmith | Tracing: tool-call latency, guardrail hits, retrieval quality |

---

## How to Use This Repo

### 1. Read Requirements First
Before writing any code, the entire team reads **`docs/requirements.md`** in full. This covers the user persona, objective, sample queries, constraints, and guardrail rules.

### 2. Work Through Tasks Weekly
Follow **`docs/tasks.md`** week by week:
- Each task has a **Definition of Done** (what "complete" means)
- Collect **evidence of completion** (logs, screenshots, reports, code commits)
- The team verifies progress using the listed evidence

### 3. Hit the Weekly Demo Goal
Each week has a **Demo Goal** — a minimum working feature to demo to instructors/cohort:
- **Week 1:** A live Gradio chat UI that answers a product-search request with a RAG-grounded shortlist; no tools, memory, or guardrails yet
- **Week 2:** Add tools (inventory, order tracking) and conversational memory
- **Week 3:** Add guardrails (out-of-stock prevention, age safety, budget respect)
- **Week 4:** Add observability (LangSmith tracing) and evals; optional stretch goals

### 4. Optional Stretch Goals
If the team finishes early, stretch goals add depth (e.g., hybrid search, advanced caching, production deployment).

---

## Project Structure

This repo contains:

- **`docs/requirements.md`** — User persona and objective, sample queries with expected answers, constraints, and guardrail requirements (~1 page)
- **`docs/tasks.md`** — A 32-task, 4-week plan (Gradio UI from Week 1, tools/MCP/memory, guardrails/caching, evals/observability). Each task includes a Definition of Done and evidence of completion, plus a weekly Demo Goal and optional Stretch Goals.
- **`docs/team.md`** — Team roles, agreed tech stack, and member sign-offs on requirements.
- **`src/`** — Source code (RAG pipeline, tools, guardrails, UI, memory manager)
- **`data/`** — Sample product catalog, inventory, and order data
- **`tests/`** — Guardrail validation tests

---

## Team & Roles

See [docs/team.md](docs/team.md) for:
- Team member names and roles
- Agreed tech stack & versions
- Sign-offs on requirements reading

---


---

## Questions?

Refer to [docs/team.md](docs/team.md) for team member contacts by role, or raise an issue on GitHub.

