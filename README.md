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

### 3. **Real-Time Inventory & Tracking**
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

### Guardrail Enforcement

ShopSage enforces four critical safety rules:

1. **Out-of-Stock Prevention:** Never recommend an item marked out-of-stock by the inventory tool; proactively suggest alternatives.
2. **Age Safety:** Filter out age-restricted or clearly inappropriate items regardless of keyword relevance.
3. **Accuracy:** Never fabricate product attributes (color, price, size); all claims backed by RAG data or live tool calls.
4. **Budget Respect:** Never silently override a user's stated budget constraint from memory.

---

## Quick Start

### Prerequisites
- Python 3.9+
- A Groq API key (free tier at [console.groq.com](https://console.groq.com))

### Setup

1. **Clone the repo:**
```bash
   git clone https://github.com/Rohini111997/ShopSage_BuildwithBeyondVector.git
   cd ShopSage_BuildwithBeyondVector
```

2. **Create a virtual environment:**
```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
   pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
```

5. **Run the app:**
```bash
   python src/app.py
```
   
   The Gradio UI opens at `http://127.0.0.1:7860`

---

## Project Structure

ShopSage_BuildwithBeyondVector/
├── docs/
│   └── team.md                  # Team roles, stack, sign-offs
├── src/
│   ├── app.py                   # Gradio UI entry point
│   ├── rag_pipeline.py          # ChromaDB indexing & retrieval
│   ├── prompt_engineering.py    # System prompt, context formatting
│   ├── tools.py                 # Inventory & order-tracking tool definitions
│   ├── guardrails.py            # Age-safety, budget, stock validation
│   └── memory_manager.py        # User preference persistence
├── data/
│   ├── products.json            # Sample product catalog
│   ├── inventory.json           # Stock status (simulated)
│   └── orders.json              # Sample order history (simulated)
├── tests/
│   └── test_guardrails.py       # Guardrail validation tests
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file


---

## Development Workflow

### Branch Strategy

- **`main`** — production-ready; protected; all work via feature branches + PR.
- **Feature branches** — `feature/<owner>-<area>`, e.g. `feature/rohini-rag-pipeline`, `feature/guardrails`.
  - Branch from: `main`
  - Submit PR, ≥1 review, merge.

### Creating a Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/<your-name>-<area>
# ... make changes ...
git add .
git commit -m "Add <feature> to <area>"
git push origin feature/<your-name>-<area>
# Open PR on GitHub
```

### Running Tests Locally

```bash
pytest tests/
```

---

## Constraints & Assumptions

- **Catalog & Inventory:** Static or lightly simulated; no live e-commerce platform needed.
- **RAG Index:** Built over product titles, descriptions, and attributes only.
- **Cart & Checkout:** Simulated; no real payment processing.
- **Memory Persistence:** Demonstrated across at least two separate sessions with the same user ID.
- **Tool Failures:** Agent degrades gracefully (e.g., *"I couldn't confirm stock right now; here's what I found"*) and exposes latency via LangSmith.

---

## Troubleshooting

**"Module not found" error:**
```bash
which python  # Verify venv is active (should show venv path)
pip install -r requirements.txt  # Reinstall
```

**Gradio UI won't open:**
- Check terminal for the URL (usually `http://127.0.0.1:7860`).
- If port 7860 is in use, Gradio auto-increments (7861, 7862, ...). Check the terminal.

**Groq API errors:**
- Verify `.env` has `GROQ_API_KEY=sk-...` (no extra spaces).
- Get a free key at [console.groq.com](https://console.groq.com).

**ChromaDB "readonly" errors in Colab:**
- Close all other Colab tabs using the same ChromaDB directory.
- Or reset: `rm -rf chroma_db/` and restart.

**Tool-call failures / timeouts:**
- Check LangSmith tracing for latency and fallback behavior.
- Verify inventory & order-tracking simulators are running (if using external services).

---

## Running on Google Colab

```python
!pip install -r requirements.txt
!python src/app.py
```

Gradio provides a public shareable link. Set `share=True` in `.launch()` for live demos.

---

## Contributing

1. Create a feature branch (see Branch Strategy).
2. Make changes; keep commits atomic and descriptive.
3. Push and open a PR.
4. At least one teammate reviews and approves.
5. Merge via GitHub UI (keep history linear).
6. Delete the branch after merge.

---

## Team & Roles

See [docs/team.md](docs/team.md) for:
- Team member names and roles
- Agreed tech stack & versions
- Sign-offs on requirements reading

---

## References

- **Functional Requirements:** See `docs/requirements.md`
- **Guardrail Specifications:** See `docs/requirements.md` Section 4
- **LangChain Docs:** https://python.langchain.com
- **ChromaDB Docs:** https://docs.trychroma.com
- **Groq API:** https://console.groq.com

---

## Questions?

Refer to [docs/team.md](docs/team.md) for team member contacts by role, or raise an issue on GitHub.

