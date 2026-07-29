"""Retrieval checks against the Chroma store (task 7).

Runs the sample queries through the same filtered vector search the agent uses
and judges each top-3 result set. Needs the store built:
    python -m src.Ingest_Embedding
Run from the repo root:
    python tests/retrieval_test.py
"""

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.Ingest_Embedding import CHROMA_DIR, COLLECTION, EMBED_MODEL

CASES = [
    {
        "name": "sample query 1 — waterproof jacket, cold-weather hiking",
        "query": "waterproof jacket for cold-weather hiking",
        "gender": "male", "budget": 7000,
        "expect_item_type": "jacket",
        "expect_keyword": "waterproof",
    },
    {
        "name": "formal shirt for office wear, men, under INR 1500",
        "query": "crisp formal shirt for office wear",
        "gender": "male", "budget": 1500,
        "expect_item_type": "shirt",
    },
    {
        "name": "breathable gym socks for women under INR 600",
        "query": "breathable gym socks",
        "gender": "female", "budget": 600,
        "expect_item_type": "socks",
    },
    {
        "name": "budget filter — no formal shirt exists under INR 500",
        "query": "crisp formal shirt for office wear",
        "gender": "male", "budget": 500,
        "expect_absent_item_type": "shirt",
        "note": ("filter holds, but note the retriever returns the nearest surviving "
                 "items rather than nothing — relevance is not enforced, only price. "
                 "Agent_2's 'nothing under your budget' path only fires when the "
                 "filter eliminates every product."),
    },
]


def build_filter(gender, budget):
    conds = [{"doc_type": {"$eq": "product_catalog"}}]
    if gender:
        conds.append({"gender": {"$eq": gender}})
    if budget:
        conds.append({"price_inr": {"$lte": budget}})
    return {"$and": conds}


def run_case(store, case):
    docs = store.as_retriever(
        search_kwargs={"k": 3, "filter": build_filter(case.get("gender"), case.get("budget"))}
    ).invoke(case["query"])

    print(f"\nQUERY   : {case['query']}")
    print(f"FILTERS : gender={case.get('gender')}, price_inr <= {case.get('budget')}")
    if not docs:
        print("TOP 3   : (no results)")
    for i, d in enumerate(docs, 1):
        m = d.metadata
        print(f"  [{i}] {m['sku']}  INR {int(m['price_inr']):<5} {m['brand']} {m['title']}"
              f"  ({m['item_type']})")
        print(f"      {d.page_content[:110]}...")

    problems = []
    if not docs:
        problems.append("no results returned")
    if case.get("budget") and any(d.metadata["price_inr"] > case["budget"] for d in docs):
        problems.append("a result breaks the budget filter")
    want = case.get("expect_item_type")
    if want and not any(d.metadata["item_type"] == want for d in docs):
        problems.append(f"no '{want}' in top 3")
    absent = case.get("expect_absent_item_type")
    if absent and any(d.metadata["item_type"] == absent for d in docs):
        problems.append(f"'{absent}' surfaced despite nothing qualifying")
    kw = case.get("expect_keyword")
    if kw and not any(kw in d.page_content.lower() for d in docs):
        problems.append(f"no result mentions '{kw}' — the catalog has no such item")

    verdict = "CORRECT" if not problems else "INCORRECT: " + "; ".join(problems)
    print(f"VERDICT : {verdict}")
    if case.get("note"):
        print(f"NOTE    : {case['note']}")
    return not problems


if __name__ == "__main__":
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=HuggingFaceEmbeddings(model_name=EMBED_MODEL),
        persist_directory=CHROMA_DIR,
    )
    print(f"chroma store: {store._collection.count()} chunks in '{COLLECTION}'")

    results = []
    for case in CASES:
        print("\n" + "=" * 78)
        print(case["name"])
        print("=" * 78)
        results.append(run_case(store, case))

    print("\n" + "=" * 78)
    print(f"{sum(results)}/{len(results)} cases correct")
