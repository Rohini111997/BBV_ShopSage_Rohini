"""FastAPI wrapper around ShopSage's Agent_3 (../src/Agent_3.py) for the React frontend.

Importing src.Agent_3 runs its bootstrap: loads/builds the Chroma vector store
and spawns the retail-tools MCP server as a subprocess. Run this from the repo
root so the relative chroma_db/ path resolves consistently:

    uvicorn backend.main:app --reload --port 8000
"""

import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import memory
from src.Agent_3 import rag_agent
from src.dashboard import session_store, full_summary

app = FastAPI(title="ShopSage API")

# Allow the Vite dev server, plus the deployed frontend origin(s) — comma-
# separated in DEPLOYED_FRONTEND_ORIGINS, e.g. https://shopsage.vercel.app
_default_origins = ["http://localhost:5173", "http://localhost:3000"]
_deployed_origins = [o.strip() for o in
                      os.environ.get("DEPLOYED_FRONTEND_ORIGINS", "").split(",")
                      if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _deployed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Per-IP rate limit on /api/chat ──────────────────────────────────────────
# A public deployment shares one Groq quota across every visitor; this caps
# how much of it any single visitor can burn. In-memory only — fine for a
# single free-tier instance, not meant to survive a restart or scale out.
_CHAT_LIMIT = int(os.environ.get("CHAT_RATE_LIMIT_PER_HOUR", "30"))
_chat_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_chat(request: Request, call_next):
    if request.url.path == "/api/chat" and request.method == "POST":
        client_ip = request.headers.get("x-forwarded-for", "")
        client_ip = client_ip.split(",")[0].strip() or (
            request.client.host if request.client else "unknown")
        now = time.monotonic()
        hits = _chat_hits[client_ip]
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= _CHAT_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit: max {_CHAT_LIMIT} messages/hour per visitor. Please try again later."},
            )
        hits.append(now)
    return await call_next(request)


class LoginRequest(BaseModel):
    customer_id: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class Product(BaseModel):
    sku: str
    brand: str
    title: str
    price_inr: float | None = None
    image: str | None = None
    item_type: str | None = None
    description: str | None = None
    sizes_available: str | None = None
    colors_available: str | None = None
    attributes: dict = {}


class ChatResponse(BaseModel):
    reply: str
    products: list[Product] = []
    trace: dict = {}


@app.post("/api/login")
def login(req: LoginRequest):
    customer_id = req.customer_id.strip()
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id must not be empty")
    status = rag_agent.set_shopper(customer_id)
    return {"status": status, "profile": rag_agent.profile}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    history = [m.model_dump() for m in req.history]
    result = rag_agent.get_rag_product_recommendation(req.message, history=history)

    # ── Push trace into the live dashboard store ──────────────────────────────
    trace = result.get("trace", {})
    if trace:
        session_store.push(trace)

    return ChatResponse(reply=result["reply"], products=result["products"], trace=trace)


@app.get("/api/memory/{customer_id}")
def get_memory(customer_id: str):
    profile = memory.get_profile(customer_id.strip())
    if profile is None:
        raise HTTPException(status_code=404, detail="unknown customer_id")
    return profile


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard():
    """Return live observability summary (tool calls, guardrails, cache, latency, edge cases, eval).

    The React frontend polls this every 10 s to refresh the dashboard panel.
    Returns an empty-state dict when no turns have been processed yet.
    """
    traces = session_store.snapshot()
    if not traces:
        return {
            "num_turns": 0,
            "tool_calls": {"total": 0, "failures": 0, "failure_rate_pct": 0.0, "failures_detail": []},
            "guardrails": {"total_triggers": 0, "by_rule": {}},
            "cache": {"hits": 0, "misses": 0, "hit_rate_pct": 0.0},
            "latency": {"avg_turn_ms": 0, "avg_generate_ms_by_path": {}},
            "edge_cases": {
                "inventory_timeouts":   {"count": 0, "details": []},
                "no_catalog_match":     {"count": 0, "details": []},
                "ambiguous_references": {"count": 0, "details": []},
            },
            "eval": {"available": False, "note": "Run the eval harness to populate scores."},
        }
    return full_summary(traces)


@app.post("/api/dashboard/reset")
def reset_dashboard():
    """Clear all accumulated traces (e.g. when the user starts a new session)."""
    session_store.clear()
    return {"status": "reset", "num_turns": 0}
