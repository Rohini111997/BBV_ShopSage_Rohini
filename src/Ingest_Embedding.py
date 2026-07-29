"""ShopSage — Task - ingestion pipeline.

Loads the apparel catalog (JSONL), converts each product into one
LangChain Document (content for embedding + metadata for filtering),
embeds with MiniLM, and persists to a local Chroma vector store.

Run from the repo root:
    python -m src.ingestion
"""
import json
from pathlib import Path
from typing import List
import shutil


from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings



CATALOG_PATH = Path(__file__).resolve().parent.parent / "DataBase" / "product_catalog_v2.jsonl"
CHROMA_DIR = "chroma_db"
COLLECTION = "shopsage_catalog"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ------------------------- Helpers ----------------------------------- #


def _as_text(value) -> str:
    """Render lists as 'a, b, c' and everything else as a plain string."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _as_number(value) -> float:
    """Coerce price to a number so Chroma range filters ($lte) work."""
    if isinstance(value, (int, float)):
        return value
    return float(str(value).replace(",", "").replace("₹", "").strip())


def load_catalog(path: Path = CATALOG_PATH) -> List[dict]:
    """Read the product catalog from a JSONL file (one JSON object per line)."""
    products = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                products.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[ingest] skipping malformed line {line_num}: {e}")
    return products


# ------------------------- Document Creation -------------------------- #

def create_item_documents(product_catalog: List[dict]) -> List[Document]:
    documents = []
    for item in product_catalog:
        attributes = item.get("Attributes") or {}
        attrs = "; ".join(f"{k.capitalize()}: {v}" for k, v in attributes.items())

        content = (
            f"Product catalog entry for {item['brand']} {item['title']} "
            f"({item['Subcategory']} > {item['item_type']}, {item['Gender']}): "
            f"{item['Description']} "
            f"Available sizes: {_as_text(item['Sizes_available'])}. "
            f"Available colors: {_as_text(item['Colors_available'])} "
            f"({item['Number_of_Colors_available']} colors). "
            f"{attrs}. "
            f"Price: INR {item['price(INR)']}."
        )

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "doc_type": "product_catalog",
                    "sku": str(item["ID (SKU)"]),
                    "brand": item["brand"],
                    "title": item["title"],
                    # lowercased so slot-extraction filters match reliably
                    "subcategory": str(item["Subcategory"]).lower(),
                    "item_type": str(item["item_type"]).lower(),
                    "gender": str(item["Gender"]).lower(),
                    # numeric so {"price_inr": {"$lte": budget}} works
                    "price_inr": _as_number(item["price(INR)"]),
                    "num_colors": int(item["Number_of_Colors_available"]),
                    "sizes": _as_text(item["Sizes_available"]).lower(),
                    "occasion": str(attributes.get("occasion", "")).lower(),
                    "age_appropriate": bool(item.get("age_appropriate", False)),
                    "image": str(item.get("image") or f"images/{item['ID (SKU)']}.png"),
                },
            )
        )
    return documents


# ------------------------- Ingest -------------------------- #

def ingest() -> Chroma:
    # Wipe any stale vector store first — ingestion is a batch job, so a
    # fresh build avoids duplicate collections and zombie-client errors.
    chroma_path = Path(CHROMA_DIR)
    if chroma_path.exists():
        try:
            shutil.rmtree(chroma_path)
            print(f"[ingest] deleted stale vector store at {CHROMA_DIR}/")
        except Exception as e:
            print(f"[ingest] notice: could not rmtree {CHROMA_DIR} ({e}), clearing collection via API instead")

    catalog = load_catalog()
    print(f"[ingest] loaded {len(catalog)} products from {CATALOG_PATH}")

    documents = create_item_documents(catalog)
    print(f"[ingest] built {len(documents)} documents (1 per product)")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    try:
        existing_vs = Chroma(
            collection_name=COLLECTION,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
        existing_vs.delete_collection()
    except Exception:
        pass

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
    )

    stored = vector_store._collection.count()
    print(f"[ingest] embedded + stored {stored} chunks in '{COLLECTION}' at {CHROMA_DIR}/")
    assert stored == len(documents), "chunk count mismatch — re-run after deleting chroma_db/"
    return vector_store


if __name__ == "__main__":
    ingest()



