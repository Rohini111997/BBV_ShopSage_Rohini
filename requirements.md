# ShopSage: Requirements

**Industry:** Retail / E-commerce

## 1. Objective
Build a shopping assistant that helps users discover and compare products from a sample catalog using RAG, checks live cart/inventory status and order tracking via tools, and remembers a shopper's style and budget preferences across visits; while never recommending out-of-stock or age-restricted items.

## 2. User Persona
**Priya Kapoor**, a 26-year-old marketing professional, shops online frequently but finds product search frustrating; filters are clunky and reviews take too long to sift through. She wants to describe what she needs in plain language ("a waterproof jacket under $80 for hiking in cold weather") and get a short, well-reasoned shortlist, plus the ability to ask follow-up questions ("does it come in green?") without starting over. She also wants to track an order she placed last week without digging through email. Her objective: find the right product faster and trust that recommendations respect her stated budget and preferences.

## 3. Sample Queries & Expected Answers

| # | Input / Query | Expected Agent Behavior |
|---|---|---|
| 1 | "I need a waterproof jacket under $80 for cold-weather hiking." | Retrieves matching products from the catalog RAG index, filters by price and attributes, returns a ranked shortlist (2-3 items) with reasons. |
| 2 | "Does the second one come in green?" | Uses conversational context to identify "the second one," calls inventory tool to check variant/color availability, answers accurately. |
| 3 | "Is it in stock in size M?" | Calls the inventory tool, returns real-time stock status; if out of stock, does not recommend it further and suggests an in-stock alternative. |
| 4 | "Where's my order from last Tuesday?" | Calls the order-tracking tool, returns current shipment status and expected delivery date. |
| 5 | "I usually shop for hiking gear under $100; remember that." | Stores the preference in memory and confirms; a later session should apply this budget/context automatically without being restated. |
| 6 | "Show me something similar but cheaper for my 10-year-old." | Declines to surface age-restricted or clearly adult-oriented catalog items even if keyword-similar; filters strictly to age-appropriate products. |

## 4. Constraints
- Product catalog, inventory, and order data are a static or lightly simulated dataset (no live e-commerce platform integration required).
- RAG index built over product titles, descriptions, and attributes from the sample catalog.
- Cart/checkout is simulated; no real payment processing.
- Must demonstrate memory persistence across at least two separate sessions with the same user.

## 5. Guardrail Requirements
- Must never recommend an item confirmed out-of-stock by the inventory tool; must proactively suggest in-stock alternatives.
- Must filter out age-restricted, unsafe, or clearly inappropriate items regardless of keyword match relevance.
- Must not fabricate product attributes (color, price, size availability); all such claims must come from a live tool call, not assumed from the RAG description alone.
- Must respect and never silently override a user's stated budget constraint from memory.
- Observability must track and expose tool-call failure rate (e.g., inventory API timeouts) and how the agent degraded gracefully (e.g., "I couldn't confirm stock right now").
