"""FastAPI wrapper around ShopSage's Agent_2 (../src/Agent_2.py) for the React frontend.

Importing src.Agent_2 runs its bootstrap: loads/builds the Chroma vector store
and spawns the retail-tools MCP server as a subprocess. Run this from the repo
root so the relative chroma_db/ path resolves consistently:

    uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src import memory
from src.Agent_2 import rag_agent

app = FastAPI(title="ShopSage API")


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
    return ChatResponse(reply=result["reply"], products=result["products"],
                        trace=result.get("trace", {}))


@app.get("/api/memory/{customer_id}")
def get_memory(customer_id: str):
    profile = memory.get_profile(customer_id.strip())
    if profile is None:
        raise HTTPException(status_code=404, detail="unknown customer_id")
    return profile


@app.get("/api/health")
def health():
    return {"status": "ok"}
