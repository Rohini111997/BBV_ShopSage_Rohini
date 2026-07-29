"""Agent trace check (tasks 13, 15, 24).

Drives three turns through the live agent and prints the trace each one
produces: routing, memory recall, retrieval hits, MCP tool calls, failures.
Writes to a temp copy of the shopper store, so committed data stays clean.

Needs DATABASE_URL + GROQ_API_KEY. Run from the repo root:
    python tests/trace_test.py
"""

import json
import shutil
import tempfile
from pathlib import Path

from src import memory

_src = memory.PROFILES_PATH
memory.PROFILES_PATH = Path(tempfile.mkdtemp()) / "shopper_profiles.json"
shutil.copy(_src, memory.PROFILES_PATH)

from src.Agent_3 import rag_agent  # noqa: E402  (import after the store swap)

CUSTOMER = "CUST-0002"


def show(trace):
    print(f"  trace_id : {trace['trace_id']}   total {trace['total_ms']}ms   "
          f"langsmith={trace['langsmith']}")
    for e in trace["events"]:
        head = f"  {e['at_ms']:>5}ms  {e['kind']}"
        if e.get("ms") is not None:
            head += f" ({e['ms']}ms)"
        print(head)
        if e["kind"] == "route":
            print(f"           -> {e['query_type']}")
        if e["kind"] == "memory_recall" and e["recalled"]:
            print(f"           -> recalled {json.dumps(e['recalled'])}")
        if e["kind"] == "memory_write":
            print(f"           -> stored {e['note']!r}")
        if e["kind"] == "retrieval":
            print(f"           -> filters {json.dumps(e['filters'])}")
            for h in e["hits"][:3]:
                print(f"           -> hit {h['sku']} {h['title']} INR {h['price_inr']}")
        if e["kind"] == "tool_call":
            print(f"           -> {e['tool']}({json.dumps(e['args'])}) = {e.get('result')!r}")
    fails = [e for e in trace["events"] if e.get("ok") is False]
    print(f"  failures : {fails or 'none'}")


if __name__ == "__main__":
    print(f"\n{'=' * 78}\nSESSION 1 — shopper states a budget\n{'=' * 78}")
    rag_agent.set_shopper(CUSTOMER)
    r1 = rag_agent.get_rag_product_recommendation("waterproof jacket for hiking under 4000")
    show(r1["trace"])

    print(f"\n{'=' * 78}\nSESSION 2 — fresh login, no budget mentioned\n{'=' * 78}")
    rag_agent.set_shopper(CUSTOMER)
    r2 = rag_agent.get_rag_product_recommendation("show me jackets")
    show(r2["trace"])

    print(f"\n{'=' * 78}\nINVENTORY CHECK — MCP tool round trip\n{'=' * 78}")
    hist = [{"role": "user", "content": "show me jackets"},
            {"role": "assistant", "content": r2["reply"]}]
    r3 = rag_agent.get_rag_product_recommendation(
        "is the Summit Waterproof Trail Jacket in stock in size M in Forest Green?",
        history=hist)
    show(r3["trace"])
    print(f"\n  reply: {r3['reply'][:200]}")

    recall = next(e for e in r2["trace"]["events"] if e["kind"] == "memory_recall")
    assert recall["budget_from_memory"], "session 2 did not recall the budget"
    assert any(e["kind"] == "tool_call" for e in r3["trace"]["events"]), "no tool call traced"
    print("\n✅ trace captures routing, cross-session recall, and MCP tool calls")
