"""
ShopSage — combined agent (MCP-integrated phase).

Retrieval + orchestration in ONE file. Tools are no longer local stubs:
they are called over MCP from the retail-tools server
(retail_mcp_server.py -> inventory.py / order_tracking.py).

Architecture:
    extraction routes -> retrieval grounds product knowledge (Chroma store
    built by src.Ingest_Embedding) -> MCP tools answer real-time questions
    -> agent sequences them.

Query types:
    new_search      -> RAG pipeline (filtered vector search + generation)
    follow_up       -> RAG pipeline (no hard filters, resolves references)
    order_tracking  -> MCP track_order tool, retrieval skipped entirely
    inventory_check -> retrieval resolves product name -> SKU,
                       then MCP check_inventory tool answers stock

MCP integration:
    The agent spawns retail_mcp_server.py as a stdio subprocess (the same
    transport Claude Desktop uses), keeps one persistent ClientSession on a
    background event loop, and exposes synchronous call_tool() to the
    otherwise-sync agent code.

Environment:
    RETAIL_MCP_SERVER  path to retail_mcp_server.py   (default: ./retail_mcp_server.py)
    RETAIL_DATA_DIR    folder holding inventory.csv / order_tracking.csv
                       (forwarded to the server subprocess)
"""

import asyncio
import json
import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.Ingest_Embedding import CHROMA_DIR, COLLECTION, EMBED_MODEL, ingest
from src import memory


# ======================================================================
# SECTION: MCP CLIENT  (bridge to retail_mcp_server.py)
# ======================================================================

class RetailMCPClient:
    """Synchronous facade over the MCP stdio client.

    Spawns `python retail_mcp_server.py` once, keeps the ClientSession
    alive on a dedicated background event loop, and lets the (sync) agent
    call tools with plain method calls.
    """

    _DEFAULT_SERVER_SCRIPT = Path(__file__).parent / "tools" / "retail_mcp_server.py"

    def __init__(self, server_script: str | None = None,
                 data_dir: str | None = None, startup_timeout: float = 30.0):
        self.server_script = str(Path(
            server_script
            or os.environ.get("RETAIL_MCP_SERVER")
            or self._DEFAULT_SERVER_SCRIPT
        ).resolve())

        # Forward env so the server finds its CSVs
        self.server_env = dict(os.environ)
        if data_dir:
            self.server_env["RETAIL_DATA_DIR"] = str(data_dir)

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="mcp-client-loop", daemon=True
        )
        self._thread.start()

        self._session: ClientSession | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None

        asyncio.run_coroutine_threadsafe(self._run(), self._loop)
        if not self._ready.wait(timeout=startup_timeout):
            raise TimeoutError(
                f"MCP server at {self.server_script} did not start "
                f"within {startup_timeout}s"
            )
        if self._startup_error:
            raise RuntimeError(
                f"Failed to start MCP server: {self._startup_error}"
            ) from self._startup_error

        self.tool_names = self._list_tool_names()
        print(f"[MCP] connected to retail-tools — tools: {self.tool_names}")

    # ---- background-loop coroutines ----------------------------------

    async def _run(self):
        """Owns the stdio transport + session for the client's lifetime.

        Everything must be entered and exited inside this ONE task —
        anyio cancel scopes forbid crossing tasks.
        """
        try:
            params = StdioServerParameters(
                command=sys.executable,
                args=[self.server_script],
                env=self.server_env,
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    self._shutdown_event = asyncio.Event()
                    self._ready.set()
                    await self._shutdown_event.wait()   # park until close()
        except BaseException as exc:                     # startup failure
            self._startup_error = exc
            self._ready.set()
        finally:
            self._session = None

    # ---- sync facade ---------------------------------------------------

    def _submit(self, coro, timeout: float = 30.0):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def _list_tool_names(self) -> list[str]:
        result = self._submit(self._session.list_tools())
        return [t.name for t in result.tools]

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call an MCP tool; normalize the result into a plain dict.

        Returns {"ok": bool, "data": <parsed content>, "raw_text": str}.
        """
        # MCP arguments must not carry nulls for optional params
        arguments = {k: v for k, v in arguments.items() if v is not None}
        try:
            result = self._submit(self._session.call_tool(name, arguments))
        except Exception as exc:
            return {"ok": False, "data": None, "raw_text": str(exc)}

        texts = [c.text for c in result.content
                 if getattr(c, "type", None) == "text"]
        raw_text = "\n".join(texts).strip()

        if getattr(result, "isError", False):
            return {"ok": False, "data": None, "raw_text": raw_text}

        # FastMCP serializes dict returns as JSON text; strings stay strings
        try:
            data = json.loads(raw_text)
        except (json.JSONDecodeError, ValueError):
            data = raw_text
        return {"ok": True, "data": data, "raw_text": raw_text}

    def close(self):
        if self._shutdown_event is not None:
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


# ======================================================================
# SECTION: AGENT
# ======================================================================

class RAG_Reco_Agent:

    def __init__(self, vectorstore, embeddings, mcp_client: RetailMCPClient):

        # Initialize the LLM
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,  # low temp: recommendations need consistency, not creativity
            max_tokens=1024   # Caps the response length
        )

        # RAG components (Chroma store built by src.Ingest_Embedding)
        self.vectorstore = vectorstore
        self.embeddings = embeddings

        # MCP bridge to retail-tools (check_inventory, track_order)
        self.mcp = mcp_client

        # Retrieval cache (Task 20): repeated identical searches hit this
        # instead of re-embedding + re-querying Chroma
        self._retrieval_cache: dict = {}
        self._CACHE_MAX = 128
        self._cache_hits = 0
        self._cache_misses = 0

        # System message for RAG-enhanced agent
        self.system_message = SystemMessage(
            content="""You are ShopSage, a conversational shopping assistant for a curated apparel catalog. You help shoppers discover products, answer questions about them, compare options, check stock, and track orders. The catalog contains:
- Product entries with brand, title, item type, subcategory, and gender
- Available sizes and colors for each item
- Prices in INR
- Detailed attributes (fabric, fit, sleeve, neck, pattern, material, occasion)
- Short product descriptions
 
You handle four kinds of requests:
A. RECOMMENDATIONS — "I need a waterproof jacket under Rs800 for hiking"
B. FOLLOW-UP QUESTIONS about items already discussed — "Does the second one come in green?", "What fabric is it?"
C. INVENTORY CHECKS — "Is it in stock in size M?" (answered from live TOOL RESULTS when provided)
D. ORDER TRACKING — "Where is my order ORD-1042?" (answered from live TOOL RESULTS when provided)
 
Grounding rules (apply to everything you say):
1. Base every answer ONLY on the retrieved catalog context, tool results, and the conversation so far — never invent products, brands, prices, colors, sizes, stock levels, or order details
2. For recommendations, treat stated constraints (gender, size, color, occasion, budget) as hard filters; rank the qualifying items and present up to 3 DISTINCT products — never list the same product twice, even if it appears in multiple context entries. If fewer than 3 distinct products qualify, show only those; do not pad the list
3. For follow-up questions, resolve references like "the second one" or "it" from your own previous answers in the conversation; if the reference is ambiguous, ask which item they mean
4. Answer color and size questions from the item's Available colors and Available sizes lists — quote what the catalog actually lists. If the requested color/size is not listed, say it isn't available and name what is
5. For STOCK questions: if a TOOL RESULT with live inventory is provided, answer from it exactly. If no tool result is provided, state what sizes/colors the catalog offers and say you could not check live stock
6. For ORDER questions: answer only from the TOOL RESULT. If the tool reports the order was not found, say so and ask the shopper to double-check the order ID
7. If nothing in the retrieved context matches a request, say so plainly and suggest the closest available alternative, clearly labeled as an alternative — do not force a bad match
8. If the query is ambiguous (no gender or budget given), answer with the best matches and note the assumption you made
9. Never mention internal fields such as SKU, document type, or metadata
10. Answer only shopping, order, and product questions; politely decline anything unrelated
11. When the shopper is shopping for a child or anyone under 18, recommend only from the retrieved context (it is pre-filtered to age-appropriate items) and never suggest adult-styled items such as bodysuits, camisoles, or evening/party wear
 
Output formats:
- Start the conversation with a greeting
- For recommendations, numbered list each item as:
  - **{brand} {title}** — INR {price}
    {One-sentence description drawn from the catalog entry, mentioning why it fits the query}
- For follow-up, stock, and order answers: 1-3 plain sentences, always naming the specific product or order ID
- End each recommendation with ONE short, warm closing line inviting the shopper to continue. Vary the phrasing naturally between responses.
Keep responses concise. Do not add disclaimers."""
        )

        # Shopper memory (src/memory.py). The base prompt is kept so
        # set_shopper() can rebuild cleanly when the customer changes.
        self._base_system_content = self.system_message.content
        self.customer_id: str | None = None
        self.profile: dict | None = None

    # ==================================================================
    # SECTION: SHOPPER MEMORY  (login + personalization)
    # ==================================================================

    def set_shopper(self, customer_id: str) -> str:
        """Load (or create) a shopper profile and personalize the system
        prompt. Called by the UI at login. Returns a status line."""
        customer_id = customer_id.strip().upper()
        profile = memory.get_profile(customer_id)
        first_name = profile["name"].split()[0]
        if profile is None:
            profile = memory.upsert_guest(customer_id)
            status = f"New guest {customer_id} — I'll ask their name in chat."
        else:
            status = (f"Welcome back, {first_name} ")
        self.customer_id = customer_id
        self.profile = profile
        # Rebuild from BASE every time — switching shoppers never stacks
        self.system_message = SystemMessage(
            content=self._base_system_content + memory.profile_to_prompt(profile)
        )
        return status

    # ==================================================================
    # SECTION: RETRIEVAL  (Chroma store from src.Ingest_Embedding)
    # ==================================================================

    @staticmethod
    def _build_where(metadata_filter: dict):
        """Chroma requires multiple conditions wrapped in $and."""
        conds = []
        for key, val in metadata_filter.items():
            if isinstance(val, dict):        # already an operator, e.g. {"$lte": 800}
                conds.append({key: val})
            else:
                conds.append({key: {"$eq": val}})
        if not conds:
            return None
        return conds[0] if len(conds) == 1 else {"$and": conds}

    def retrieve_relevant_knowledge(self, query: str, k: int = 3,
                                    metadata_filter: dict = None):
        """Filtered nearest-neighbour search against Chroma, with an
        in-memory cache (Task 20): repeated identical queries skip
        re-embedding + re-searching entirely. Keyed on the normalized
        query text + k + the exact metadata filter. Safe to cache because
        the catalog/vector store is static for the life of the process —
        LIVE data (stock, orders) is never served from this cache; those
        MCP tools run fresh on every request."""
        cache_key = (
            query.strip().lower(), k,
            json.dumps(metadata_filter, sort_keys=True, default=str),
        )
        if cache_key in self._retrieval_cache:
            self._cache_hits += 1
            print(f"[cache] HIT  retrieval (hits={self._cache_hits}, "
                  f"misses={self._cache_misses}) query={query[:60]!r}")
            return self._retrieval_cache[cache_key]

        self._cache_misses += 1
        print(f"[cache] MISS retrieval (hits={self._cache_hits}, "
              f"misses={self._cache_misses}) query={query[:60]!r}")
        search_kwargs = {"k": k}
        if metadata_filter:
            search_kwargs["filter"] = self._build_where(metadata_filter)
        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        docs = retriever.invoke(query)

        if len(self._retrieval_cache) >= self._CACHE_MAX:   # simple FIFO cap
            self._retrieval_cache.pop(next(iter(self._retrieval_cache)))
        self._retrieval_cache[cache_key] = docs
        return docs

    def format_retrieved_context(self, docs):
        """Document objects -> plain string for the LLM."""
        context_parts = []
        for i, doc in enumerate(docs, 1):
            doc_type = doc.metadata.get("doc_type", "unknown").replace("_", " ").title()
            context_parts.append(f"[{i}] ({doc_type})\n{doc.page_content}")
        return "\n\n".join(context_parts)

    # ==================================================================
    # SECTION: MCP TOOL WRAPPERS
    # The orchestrator contract (dict in, dict out) is unchanged — only
    # the bodies now delegate to the retail-tools MCP server.
    # ==================================================================

    def track_order(self, customer_id: str, order_id: str | None = None) -> dict:
        """TOOL (MCP): order tracking via retail-tools `track_order`.

        The MCP tool filters order_tracking.csv by Customer_ID (and
        optionally Order_ID) and returns
        {order_id, order_status, item_count, expected_delivery_date}.
        """
        if not customer_id:
            return {"found": False, "error": "no_customer_id"}

        res = self.mcp.call_tool(
            "track_order",
            {"customer_id": customer_id, "order_id": order_id},
        )
        if not res["ok"]:
            return {"found": False, "error": "tool_error",
                    "detail": res["raw_text"]}

        data = res["data"] if isinstance(res["data"], dict) else {}
        if not data.get("order_id"):
            return {"found": False, "error": "order_not_found",
                    "customer_id": customer_id, "order_id": order_id}
        return {"found": True, "order": data}

    def check_inventory(self, sku: str, size: str = None,
                        color: str = None) -> dict:
        """TOOL (MCP): live inventory via retail-tools `check_inventory`.

        The MCP tool reads inventory.csv and returns the string
        "In Stock" / "Out of Stock"; we wrap it so the generation rules
        (checked=true/false) keep working.
        """
        if not sku:
            return {"checked": False, "error": "no_sku"}

        res = self.mcp.call_tool(
            "check_inventory",
            {"sku": sku, "size": size, "color": color},
        )
        if not res["ok"]:
            return {"checked": False, "sku": sku, "size": size, "color": color,
                    "error": "tool_error", "detail": res["raw_text"]}

        status = res["data"] if isinstance(res["data"], str) else res["raw_text"]
        return {
            "checked": True,
            "sku": sku,
            "size": size,
            "color": color,
            "stock_status": status,          # "In Stock" | "Out of Stock"
            "in_stock": status.strip().lower() == "in stock",
        }

    @staticmethod
    def _resolve_sku(docs):
        """Pull the SKU off the top retrieved catalog entry, if present.
        (Retrieval resolves product NAME -> catalog entry -> SKU; the
        inventory tool needs the SKU.)"""
        for doc in docs:
            sku = doc.metadata.get("sku")
            if sku:
                return sku, doc
        return None, (docs[0] if docs else None)

    def _is_recommendable(self, doc) -> bool:
        """GUARDRAIL (stock): a product may be recommended only if it has
        live stock — apparel needs >= 2 sizes in stock, accessories >= 1
        (size doesn't matter for them). The MCP tool returns facts
        (in-stock sizes); this business rule lives here in the agent.
        Fail-open on tool errors so a flaky tool doesn't blank the demo."""
        sku = doc.metadata.get("sku")
        if not sku:
            return False
        res = self.mcp.call_tool("get_in_stock_sizes", {"sku": sku})
        if not res["ok"] or not isinstance(res["data"], dict):
            return True   # tool error -> don't silently hide the product
        count = res["data"].get("count", 0)
        if doc.metadata.get("subcategory") == "accessories":
            return count >= 1
        return count >= 2

    # ==================================================================
    # SECTION: ORCHESTRATOR
    # ==================================================================

    @staticmethod
    def _format_history(history, last_n=6):
        lines = []
        for item in history[-last_n:]:
            if isinstance(item, dict):
                role = "Shopper" if item.get("role") == "user" else "ShopSage"
                content = item.get("content", "")
                if isinstance(content, list):   # some versions nest content blocks
                    content = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )
                lines.append(f"{role}: {content}")
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                u, a = item
                lines.append(f"Shopper: {u}")
                lines.append(f"ShopSage: {a}")
        return "\n".join(lines)

    def _extract_slots(self, shopper_query: str, history_text: str) -> dict:
        """Stage 1: query understanding — also the ROUTER between the
        RAG path and the MCP tool paths."""
        extraction_prompt = f"""Analyze this shopper message in the context of the conversation.
Return ONLY a JSON object, no other text, with these keys:
- "query_type": one of:
    "new_search"      (looking for / asking to recommend products)
    "follow_up"       (asking about attributes of items already discussed, e.g. colors, sizes, fabric, price, "the second one")
    "inventory_check" (asking whether an item is in stock / available RIGHT NOW, possibly in a size or color)
    "order_tracking"  (asking about the status, location, or delivery of an order they placed)
- "item_intent": short phrase for the product they want or are asking about (resolve references like "it" or "the second one" into the actual product name from the conversation); null for order_tracking
- "customer_id": the customer identifier if mentioned (e.g. "CUST-001"), else null
- "order_id": the order identifier if mentioned (e.g. "ORD-1042"), else null
- "gender": "Male" | "Female" | null
- "size": string or null
- "color": string or null
- "max_price_inr": number or null
- "occasion": string or null (e.g. "Sports", "Casual", "Festive", "Winter")
- "for_child": true or false — true ONLY if the shopper is clearly shopping for a child, kid, teen, or anyone under 18 (e.g. "for my 10 year old", "for my son", "gift for my niece, she's 12", "for a teenager"). Also look back through the CONVERSATION: once the shopper says they are shopping for a child, keep for_child=true for related follow-up searches. Otherwise false.

Routing hints:
- "Is it in stock?" / "do you have this in M?" -> inventory_check
- "does it COME in green?" (catalog attribute, not live stock) -> follow_up
- "where is my order" / "has it shipped" / an order ID -> order_tracking
- Also look back through the CONVERSATION for a customer ID the shopper gave earlier

CONVERSATION SO FAR:
{history_text if history_text else "(none — this is the first message)"}

SHOPPER MESSAGE: "{shopper_query}" """

        raw = self.llm.invoke([HumanMessage(content=extraction_prompt)]).content
        raw = raw.replace("```json", "").replace("```", "").strip()
        try:
            c = json.loads(raw)
        except json.JSONDecodeError:
            c = {}
        keys = ["query_type", "item_intent", "customer_id", "order_id",
                "gender", "size", "color", "max_price_inr", "occasion",
                "for_child"]
        c = {k: c.get(k) for k in keys}
        # normalize to a strict bool (LLM may return null / "true" / etc.)
        c["for_child"] = str(c.get("for_child")).strip().lower() == "true"
        if not c["item_intent"] and c["query_type"] != "order_tracking":
            c["item_intent"] = shopper_query
        if c["query_type"] not in ("new_search", "follow_up",
                                   "inventory_check", "order_tracking"):
            c["query_type"] = "new_search"
        return c

    def _generate(self, shopper_query, history_text, slots,
                  context="", tool_result=None, rules=""):
        """Final grounded LLM call, shared by all paths."""
        prompt = f"""Continue this shopping conversation.

CONVERSATION SO FAR:
{history_text if history_text else "(none — this is the first message)"}

SHOPPER'S NEW MESSAGE: "{shopper_query}"

PARSED UNDERSTANDING:
{json.dumps(slots, indent=2)}
"""
        if context:
            prompt += f"\nRETRIEVED CATALOG CONTEXT:\n{context}\n"
        if tool_result is not None:
            prompt += f"\nTOOL RESULT:\n{json.dumps(tool_result, indent=2)}\n"
        prompt += f"\nRules:\n{rules}"

        messages = [self.system_message, HumanMessage(content=prompt)]
        return self.llm.invoke(messages).content

    def get_rag_product_recommendation(self, shopper_query, history=None):
        """Main entry point. Routes each message to the right path:
        RAG (new_search / follow_up), MCP order tool, or MCP inventory tool."""

        history = history or []
        history_text = self._format_history(history)

        # ---- Stage 1: extract + ROUTE --------------------------------
        c = self._extract_slots(shopper_query, history_text)

        # ---- Memory: read then write ---------------------------------
        # Backfill missing slots from the logged-in profile (gender drives
        # SKU filtering; customer_id lets order tracking skip the ID ask).
        # Precedence: what the shopper typed this turn always wins.
        c = memory.apply_profile_defaults(c, self.profile)
        # Persist durable preferences (product-search turns only; deduped;
        # capped at the 3 most recent notes on disk).
        if self.customer_id:
            memory.record_session_learnings(self.customer_id, c)

        # ---- PATH: order tracking (MCP tool, retrieval skipped) ------
        if c["query_type"] == "order_tracking":
            if not c["customer_id"]:
                return ("I can check that for you — could you share your "
                        "customer ID (e.g. CUST-001)? An order ID helps too "
                        "if you have it.")
            result = self.track_order(c["customer_id"], c["order_id"])
            return self._generate(
                shopper_query, history_text, c, tool_result=result,
                rules=("- Answer ONLY from the TOOL RESULT\n"
                       "- If found, summarize order_status, item_count and "
                       "expected_delivery_date in 1-3 sentences, naming the "
                       "order ID\n"
                       "- If not found, say so and ask the shopper to "
                       "double-check their customer ID / order ID"))

        # ---- Build search inputs (all remaining paths use retrieval) --
        query_parts = [c["item_intent"]]
        if c["gender"]:
            query_parts.append(f"for {c['gender']}")
        if c["occasion"]:
            query_parts.append(f"{c['occasion']} occasion")
        if c["color"]:
            query_parts.append(f"{c['color']} color")
        search_query = ", ".join(query_parts)

        # Hard filters apply only to NEW searches — for follow-ups and
        # inventory checks we must be able to SEE the item being asked about
        metadata_filter = {"doc_type": "product_catalog"}
        if c["query_type"] == "new_search":
            if c["gender"]:
                # ingestion lowercases gender metadata — match it
                metadata_filter["gender"] = str(c["gender"]).lower()
            if c["max_price_inr"]:
                metadata_filter["price_inr"] = {"$lte": c["max_price_inr"]}
            if c["for_child"]:
                # GUARDRAIL: shopping for a minor — only age-appropriate
                # items can ever reach the recommendation LLM
                metadata_filter["age_appropriate"] = True
                print("[guardrail] age filter ACTIVE — retrieval limited "
                      "to age_appropriate=True items")

        relevant_docs = self.retrieve_relevant_knowledge(
            search_query, k=6, metadata_filter=metadata_filter
        )

        # ---- GUARDRAIL (stock): filter new-search candidates ---------
        # Recommendations must be backed by live stock (>= 2 sizes for
        # apparel, >= 1 for accessories). Applied ONLY to new_search:
        # follow_up / inventory_check must still SEE the item asked about.
        if c["query_type"] == "new_search" and relevant_docs:
            in_stock_docs = []
            for d in relevant_docs:
                if self._is_recommendable(d):
                    in_stock_docs.append(d)
                else:
                    print(f"[guardrail] BLOCKED "
                          f"{d.metadata.get('sku')} "
                          f"'{d.metadata.get('title')}' — fails stock rule "
                          f"(needs >=2 in-stock sizes; accessories >=1)")
            print(f"[guardrail] stock check: {len(relevant_docs)} retrieved "
                  f"-> {len(in_stock_docs)} recommendable")
            if not in_stock_docs:
                return ("The items matching your request are currently out "
                        "of stock or very low on sizes. Would you like me "
                        "to look at similar alternatives?")
            relevant_docs = in_stock_docs

        # ---- PATH: inventory check (retrieval resolves SKU -> MCP tool)
        if c["query_type"] == "inventory_check":
            if not relevant_docs:
                return ("I'm not sure which item you'd like me to check — "
                        "could you mention the product name?")
            sku, top_doc = self._resolve_sku(relevant_docs)
            result = self.check_inventory(sku, size=c["size"], color=c["color"])
            context = self.format_retrieved_context([top_doc] if top_doc else [])
            return self._generate(
                shopper_query, history_text, c,
                context=context, tool_result=result,
                rules=("- If the TOOL RESULT has checked=true, answer stock "
                       "from stock_status exactly ('In Stock' / 'Out of "
                       "Stock'), naming the product and any size/color "
                       "checked\n"
                       "- If checked=false, state which sizes/colors the "
                       "catalog offers for this product and say you could "
                       "not confirm live stock\n"
                       "- 1-3 plain sentences"))

        # ---- PATH: RAG (new_search / follow_up) ----------------------
        # Empty-retrieval guard — only meaningful for new searches
        if not relevant_docs:
            if c["query_type"] == "follow_up":
                return ("I'm not sure which item you're referring to — could you "
                        "mention the product name from the list I shared?")
            if c["max_price_inr"] is not None:
                relaxed = {k: v for k, v in metadata_filter.items()
                           if k != "price_inr"}
                alt_docs = self.retrieve_relevant_knowledge(
                    search_query, k=3, metadata_filter=relaxed
                )
                if alt_docs:
                    cheapest = min(d.metadata["price_inr"] for d in alt_docs)
                    return (f"I couldn't find anything matching your request under "
                            f"INR {c['max_price_inr']}. The closest options start at "
                            f"INR {cheapest}. Would you like to see those, or adjust "
                            f"your budget?")
            return ("I couldn't find anything in the catalog matching that request. "
                    "Could you tell me a bit more about what you're looking for?")

        context = self.format_retrieved_context(relevant_docs)
        rag_rules = ("- For a new search: recommend ONLY items in the retrieved "
                     "context; treat size and budget as hard constraints; rank "
                     "by fit and return up to 3, in the standard recommendation "
                     "format\n"
                     "- For a follow-up question: answer about the specific "
                     "item(s) from the conversation, using the retrieved context "
                     "as the source of truth for colors, sizes, fabric, and "
                     "price; answer in 1-3 plain sentences and name the product\n"
                     "- If the retrieved context doesn't contain the item being "
                     "asked about, say so rather than guessing")
        if c["for_child"]:
            rag_rules += ("\n- The shopper is shopping for someone under 18: "
                          "the retrieved context is already limited to "
                          "age-appropriate items; mention that these are adult "
                          "sizes (XS runs closest for kids) and never suggest "
                          "items outside the retrieved context")
        return self._generate(
            shopper_query, history_text, c, context=context, rules=rag_rules)

    # Mental Model:
    # shopper query -> extract slots + ROUTE
    #   order_tracking  -> MCP track_order (customer_id [, order_id]) -> answer
    #   inventory_check -> retrieve (resolve SKU) -> MCP check_inventory -> answer
    #   new_search      -> filtered retrieve (Chroma / Ingest_Embedding) -> reco
    #   follow_up       -> unfiltered retrieve -> grounded answer
    #   for_child=true  -> new_search adds {"age_appropriate": True} filter


# ======================================================================
# SECTION: BOOTSTRAP
# ======================================================================

class CachedEmbeddings:
    """Task 20 (embeddings half): caching wrapper around the MiniLM
    embedder.

    - DOCUMENT embeddings are computed once at ingestion and persisted
      inside the Chroma store — never recomputed at query time.
    - QUERY embeddings are cached here: embedding the same query text
      twice returns the cached 384-dim vector instead of re-running the
      model. Logs [cache] HIT/MISS embedding as evidence.
    """

    def __init__(self, inner, max_size: int = 256):
        self.inner = inner
        self._cache: dict = {}
        self._max = max_size
        self.hits = 0
        self.misses = 0

    def embed_query(self, text: str):
        key = text.strip().lower()
        if key in self._cache:
            self.hits += 1
            print(f"[cache] HIT  embedding (hits={self.hits}, "
                  f"misses={self.misses}) text={text[:60]!r}")
            return self._cache[key]
        self.misses += 1
        print(f"[cache] MISS embedding (hits={self.hits}, "
              f"misses={self.misses}) text={text[:60]!r}")
        vec = self.inner.embed_query(text)
        if len(self._cache) >= self._max:          # simple FIFO cap
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = vec
        return vec

    def embed_documents(self, texts):
        # ingestion path — pass through untouched (batch job, runs once)
        return self.inner.embed_documents(texts)


def _load_vectorstore():
    """Reopen the persisted Chroma store built by Ingest_Embedding.ingest().
    If it hasn't been built yet (empty/missing), run ingestion now."""
    embeddings = CachedEmbeddings(HuggingFaceEmbeddings(model_name=EMBED_MODEL))
    vector_store = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
    if vector_store._collection.count() == 0:
        print("[Agent_2] chroma_db is empty — running ingestion...")
        vector_store = ingest()
    return vector_store, embeddings


# Initialize the RAG recommendation agent
print("Initializing RAG Recommendation Agent...")
vectorstore, embeddings = _load_vectorstore()
mcp_client = RetailMCPClient(
    server_script=os.environ.get("RETAIL_MCP_SERVER"),
    data_dir=os.environ.get("RETAIL_DATA_DIR"),
)
rag_agent = RAG_Reco_Agent(vectorstore, embeddings, mcp_client)
print("RAG Recommendation Agent Ready!")