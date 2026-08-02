"""
memory.py — read/write shopper memory for ShopSage.

Schema: DataBase/shopper_profiles.json, keyed by Customer_ID (CUST-0083).
Two preference sources, kept separate:
  - profile["preferences"]         : purchase-derived (batch script owns this)
  - profile["learned_preferences"] : chat-derived, append-only, MAX 3 KEPT

This module NEVER writes to profile["preferences"] — that block belongs to
the batch regeneration script. Chat writes only touch learned_preferences.

Run `python -m src.memory` from repo root for a write/read-back self-test.
"""

import json
from datetime import datetime
from pathlib import Path

PROFILES_PATH = Path(__file__).resolve().parent.parent / "DataBase" / "shopper_profiles.json"

MAX_LEARNED = 3   # only the 3 most recent chat-learned notes are kept on disk


# ---------------------------------------------------------------- internals

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_all() -> dict:
    if not PROFILES_PATH.exists():
        return {}
    with open(PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_all(profiles: dict) -> None:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PROFILES_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    tmp.replace(PROFILES_PATH)  # atomic — never a half-written file


# ---------------------------------------------------------------- read path

def get_profile(customer_id: str) -> dict | None:
    """Fetch one shopper's full record. None if unknown."""
    return _load_all().get(customer_id)


def profile_to_prompt(profile: dict) -> str:
    """Render a profile as system-prompt prose, with the two sources labelled
    so the LLM can apply the precedence rule (current msg > chat notes > history)."""
    pref = profile.get("preferences", {})
    loy = profile.get("loyalty", {})
    sizes = pref.get("size", {})
    lines = [
        "\n\nKNOWN SHOPPER",
        f"You are speaking with {profile['name']} "
        f"({loy.get('tier', 'new')} member). Greet her/him by name once.",
        "",
        "From purchase history (defaults, lowest priority):",
        f"- Gender: {profile.get('gender') or 'unknown'}",
        f"- Usual sizes: top {sizes.get('top', '?')}, bottom {sizes.get('bottom', '?')}",
        f"- Usual colours: {', '.join(pref.get('colour', [])) or 'unknown'}",
        f"- Shops for occasions: {', '.join(pref.get('occasion', [])) or 'unknown'}",
        f"- Typical budget: up to ₹{pref.get('budget_inr', '?')}",
        f"- Style: {pref.get('style_notes', '')}",
    ]
    notes = profile.get("learned_preferences", [])
    if notes:
        lines.append("")
        lines.append("From recent conversations (override purchase history):")
        for n in notes:
            day = n["learned_at"][:10]
            lines.append(f"- {n['note']} (noted {day})")
    lines += [
        "",
        "PRECEDENCE: what the shopper says in the current message always wins; "
        "then recent conversation notes; purchase history is only a fallback. "
        "Never contradict an explicit request using remembered preferences.",
    ]
    return "\n".join(lines)


def learned_budget(profile: dict | None) -> int | None:
    """Most recent budget the shopper stated in chat. Purchase-derived
    preferences.budget_inr is deliberately NOT used — it's a soft default and
    hard-filtering on it would silently cap searches the shopper never capped."""
    if not profile:
        return None
    for note in reversed(profile.get("learned_preferences", [])):
        if note.get("budget_inr"):
            return note["budget_inr"]
    return None


def apply_profile_defaults(slots: dict, profile: dict | None) -> dict:
    """Backfill missing extraction slots from the profile — precedence rule:
    what the shopper said this turn always wins; profile only fills gaps.
    Backfills gender (drives SKU filtering: APL-TOP-F vs -M) and the budget
    remembered from an earlier session."""
    if not profile:
        return slots
    if not slots.get("gender"):
        slots["gender"] = profile.get("gender")
    if not slots.get("customer_id"):
        slots["customer_id"] = profile.get("customer_id")
    if not slots.get("max_price_inr"):
        budget = learned_budget(profile)
        if budget:
            # Soft memory only: surfaced to the LLM to mention/ask about,
            # NEVER copied into max_price_inr — a budget from a past chat
            # must not hard-filter searches the shopper didn't cap.
            slots["remembered_budget_inr"] = budget
    return slots


# ---------------------------------------------------------------- write path

def remember_preference(customer_id: str, note: str, source: str = "chat",
                        budget_inr: int | None = None) -> dict | None:
    """Append one chat-learned note. Dedupes identical notes, keeps only the
    MAX_LEARNED most recent. Returns updated profile, None if unknown customer."""
    profiles = _load_all()
    profile = profiles.get(customer_id)
    if profile is None:
        return None
    notes = profile.setdefault("learned_preferences", [])
    if any(n["note"] == note for n in notes):      # exact duplicate → refresh, don't stack
        notes[:] = [n for n in notes if n["note"] != note]
    notes.append({"note": note, "learned_at": _now(), "source": source,
                  "budget_inr": budget_inr})
    profile["learned_preferences"] = notes[-MAX_LEARNED:]   # keep last 3 only
    _save_all(profiles)
    return profile


def note_from_slots(slots: dict) -> str | None:
    """Compose a short note from extraction slots. Returns None if the turn
    carried nothing durable (so order-tracking queries etc. write nothing)."""
    parts = []
    if slots.get("item_intent") and slots.get("item_intent_extracted", True):
        parts.append(f"interested in {slots['item_intent']}")
    if slots.get("color"):
        parts.append(f"prefers {slots['color']}")
    if slots.get("occasion"):
        parts.append(f"for {slots['occasion']}")
    if slots.get("max_price_inr"):
        parts.append(f"budget under ₹{slots['max_price_inr']}")
    return ", ".join(parts).capitalize() if parts else None


def record_session_learnings(customer_id: str, slots: dict) -> dict | None:
    """Orchestrator hook: call after every extraction. Only product-search
    turns produce notes; tracking/inventory turns are ignored."""
    if slots.get("query_type") not in ("new_search", "follow_up"):
        return None
    note = note_from_slots(slots)
    if not note:
        return None
    return remember_preference(customer_id, note,
                               budget_inr=slots.get("max_price_inr"))


def upsert_guest(customer_id: str, name: str = "Guest") -> dict:
    """Create a minimal record for an unknown customer ID (new-guest path)."""
    profiles = _load_all()
    if customer_id not in profiles:
        profiles[customer_id] = {
            "customer_id": customer_id,
            "name": name,
            "phone_no": "", "email": "", "gender": None, "age": None,
            "preferences": {"colour": [], "size": {}, "style_notes": "", "budget_inr": None},
            "learned_preferences": [],
            "loyalty": {"tier": "Bronze", "points": 0,
                        "member_since": _now()[:10], "total_orders": 0},
        }
        _save_all(profiles)
    return profiles[customer_id]


# ---------------------------------------------------------------- self-test

if __name__ == "__main__":
    import shutil
    import tempfile

    # Work on a throwaway copy — the self-test must not dirty committed data.
    _src = PROFILES_PATH
    PROFILES_PATH = Path(tempfile.mkdtemp()) / "shopper_profiles.json"
    shutil.copy(_src, PROFILES_PATH)

    print("=== memory.py self-test: write, cap at 3, read back ===\n")
    cid = "CUST-0083"
    for i, note in enumerate([
        "Interested in kurtas, budget under ₹1500",
        "Prefers pastels for office wear",
        "Interested in linen shirts, for beach trip",
        "Interested in party wear, budget under ₹2500",   # 4th → oldest must drop
    ], 1):
        remember_preference(cid, note)
        print(f"[{i}] wrote: {note}")

    profile = get_profile(cid)
    kept = [n["note"] for n in profile["learned_preferences"]]
    print(f"\nKept on disk ({len(kept)}):")
    for n in kept:
        print("  -", n)
    assert len(kept) == 3
    assert "kurtas" not in " ".join(kept)      # oldest note evicted
    assert kept[-1].startswith("Interested in party wear")
    print("\n--- rendered prompt section ---")
    print(profile_to_prompt(profile))
    print("\n✅ Cap-at-3 + read-back verified.")