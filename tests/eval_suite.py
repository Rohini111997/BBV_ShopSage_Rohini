"""ShopSage Evaluation Suite (Week 4 / Evals).

Runs automated test cases covering RAG retrieval, tool execution, budget compliance,
guardrail enforcement, and memory recall against the live agent. Calculates accuracy
scores and generates an evaluation report.

If LANGSMITH_TRACING=true and LANGSMITH_API_KEY are configured in .env, traces and
evaluations are automatically sent to your LangSmith project dashboard.

Writes to a temp copy of the shopper store, so committed data stays clean.

Run from repo root:
    python tests/eval_suite.py
"""

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

# Ensure dependencies are present
try:
    from src import memory
except Exception as e:
    print(f"Error importing ShopSage agent modules: {e}")
    sys.exit(1)

# Redirect the shopper store to a temp copy BEFORE the agent loads it — the
# eval cases write learned preferences, and those must not land in the
# committed DataBase/shopper_profiles.json.
_src = memory.PROFILES_PATH
memory.PROFILES_PATH = Path(tempfile.mkdtemp()) / "shopper_profiles.json"
shutil.copy(_src, memory.PROFILES_PATH)

try:
    from src.Agent_3 import rag_agent  # noqa: E402  (import after the store swap)
    from src.observability import LANGSMITH_ENABLED, langsmith_status  # noqa: E402
except Exception as e:
    print(f"Error importing ShopSage agent modules: {e}")
    sys.exit(1)

# Comprehensive test suite covering catalog queries, budget limits, tools, and memory
EVAL_CASES = [
    {
        "id": "TC-01",
        "category": "RAG Product Search",
        "query": "Breathable gym socks for women under 600",
        "customer_id": "CUST-EVAL-01",
        "history": [],
        "expected": {
            "query_type": "new_search",
            "max_price": 600,
            "min_products": 1,
            "keywords": ["sock", "gym", "breathable"],
        },
    },
    {
        "id": "TC-02",
        "category": "RAG Product Search",
        "query": "A crisp formal shirt for office wear, men, under 1500",
        "customer_id": "CUST-EVAL-02",
        "history": [],
        "expected": {
            "query_type": "new_search",
            "max_price": 1500,
            "min_products": 1,
            "keywords": ["shirt", "formal", "office"],
        },
    },
    {
        "id": "TC-03",
        "category": "Inventory Check (Tool Call)",
        "query": "Is the Everyday Crew Tee in stock in size M?",
        "customer_id": "CUST-EVAL-03",
        "history": [],
        "expected": {
            "query_type": "inventory_check",
            "tool_called": "check_inventory",
            "require_stock_info": True,
        },
    },
    {
        "id": "TC-04",
        "category": "Order Tracking (Tool Call)",
        "query": "Where is my order ORD-1042?",
        "customer_id": "CUST-0028",
        "history": [],
        "expected": {
            "query_type": "order_tracking",
            "tool_called": "track_order",
            "require_order_info": True,
        },
    },
    {
        "id": "TC-05",
        "category": "Memory & Personalization",
        "step_1": {
            "query": "I am looking for formal trousers under 2000",
            "customer_id": "CUST-EVAL-MEM",
        },
        "step_2": {
            "query": "Show me formal trousers",
            "customer_id": "CUST-EVAL-MEM",
            "expected_recall_budget": 2000,
        },
    },
    {
        "id": "TC-06",
        "category": "Guardrail — Age Filter",
        "query": "Show me a dress for my 10-year-old daughter",
        "customer_id": "CUST-EVAL-06",
        "history": [],
        "expected": {
            "query_type": "new_search",
            "guardrail_rule": "age_filter",
        },
    },
]


def evaluate_case(test_case: Dict) -> Dict:
    tc_id = test_case["id"]
    category = test_case["category"]

    # Special handling for multi-turn memory test case
    if tc_id == "TC-05":
        cust_id = test_case["step_1"]["customer_id"]
        rag_agent.set_shopper(cust_id)
        start_time = time.time()
        # Turn 1: establish preference
        r1 = rag_agent.get_rag_product_recommendation(test_case["step_1"]["query"])
        # Turn 2: fresh login, budget not mentioned — it must come back from memory
        rag_agent.set_shopper(cust_id)
        r2 = rag_agent.get_rag_product_recommendation(test_case["step_2"]["query"])
        elapsed_ms = int((time.time() - start_time) * 1000)

        events = r2.get("trace", {}).get("events", [])
        recall_event = next((e for e in events if e.get("kind") == "memory_recall"), {})

        # Assert on the recalled VALUE, not just the derived flag — a renamed
        # slot silently zeroed this check once already.
        recalled_budget = recall_event.get("recalled", {}).get("remembered_budget_inr")
        expected_budget = test_case["step_2"]["expected_recall_budget"]

        passed = True
        reasons = []
        if not recall_event.get("budget_from_memory"):
            passed = False
            reasons.append("trace did not flag budget_from_memory on turn 2")
        if recalled_budget != expected_budget:
            passed = False
            reasons.append(
                f"Recalled budget mismatch: expected INR {expected_budget}, "
                f"got {recalled_budget}"
            )

        return {
            "id": tc_id,
            "category": category,
            "passed": passed,
            "latency_ms": elapsed_ms,
            "details": (f"Memory recalled budget: INR {recalled_budget}"
                        if passed else " | ".join(reasons)),
            "trace_id": r2.get("trace", {}).get("trace_id"),
        }

    # Standard single-turn test cases
    cust_id = test_case["customer_id"]
    rag_agent.set_shopper(cust_id)
    start_time = time.time()
    res = rag_agent.get_rag_product_recommendation(
        test_case["query"], history=test_case["history"]
    )
    elapsed_ms = int((time.time() - start_time) * 1000)

    trace = res.get("trace", {})
    events = trace.get("events", [])
    products = res.get("products", [])
    reply = res.get("reply", "")

    expected = test_case["expected"]
    passed = True
    reasons = []

    # Check query type routing
    route_event = next((e for e in events if e.get("kind") == "route"), {})
    actual_qt = route_event.get("query_type")
    if expected.get("query_type") and actual_qt != expected["query_type"]:
        passed = False
        reasons.append(f"Routing mismatch: expected '{expected['query_type']}', got '{actual_qt}'")

    # Check price budget constraint
    max_price = expected.get("max_price")
    if max_price is not None:
        overpriced = [p for p in products if p.get("price_inr") and p["price_inr"] > max_price]
        if overpriced:
            passed = False
            reasons.append(f"{len(overpriced)} products exceed max price INR {max_price}")

    # Check minimum product count
    min_prods = expected.get("min_products", 0)
    if len(products) < min_prods:
        passed = False
        reasons.append(f"Expected at least {min_prods} products, got {len(products)}")

    # Check tool calls
    expected_tool = expected.get("tool_called")
    if expected_tool:
        tool_events = [e for e in events if e.get("kind") == "tool_call" and e.get("tool") == expected_tool]
        if not tool_events:
            passed = False
            reasons.append(f"Expected tool call '{expected_tool}' was not logged in trace")
        else:
            if not tool_events[0].get("ok"):
                passed = False
                reasons.append(f"Tool call '{expected_tool}' failed: {tool_events[0].get('error')}")

    # Check guardrail rules
    expected_guardrail = expected.get("guardrail_rule")
    if expected_guardrail:
        guardrail_events = [
            e for e in events
            if e.get("kind") == "guardrail" and e.get("rule") == expected_guardrail
        ]
        if not guardrail_events:
            passed = False
            reasons.append(
                f"Expected guardrail rule '{expected_guardrail}' was not logged in trace"
            )

    details = "PASSED" if passed else " | ".join(reasons)
    return {
        "id": tc_id,
        "category": category,
        "passed": passed,
        "latency_ms": elapsed_ms,
        "num_products": len(products),
        "details": details,
        "trace_id": trace.get("trace_id"),
    }


def run_evals():
    print("\n" + "=" * 70)
    print("           SHOPSAGE EVALUATION SUITE & SCORECARD")
    print("=" * 70)
    print(f"LangSmith Status: {langsmith_status()}")
    print("-" * 70)

    results = []
    for tc in EVAL_CASES:
        res = evaluate_case(tc)
        results.append(res)
        status = "[PASS]" if res["passed"] else "[FAIL]"
        print(f"[{res['id']}] {res['category']:<28} {status} ({res.get('latency_ms', 0)}ms)")
        if not res["passed"]:
            print(f"      Reason: {res['details']}")

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    accuracy = (passed_count / total) * 100

    print("=" * 70)
    print(f"SUMMARY: {passed_count}/{total} Test Cases Passed ({accuracy:.1f}% Accuracy)")
    print("=" * 70)

    if LANGSMITH_ENABLED:
        print("\nTraces for this evaluation run have been logged to LangSmith.")
        print(f"   Dashboard: https://smith.langchain.com (Project: {os.getenv('LANGSMITH_PROJECT', 'shopsage')})")
    else:
        print("\nTip: To send traces to LangSmith, set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in .env")

    return results


if __name__ == "__main__":
    run_evals()
