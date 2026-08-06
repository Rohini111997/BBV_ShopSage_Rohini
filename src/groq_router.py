"""
Rotates across multiple Groq API keys so a public deployment isn't capped by
a single account's daily token quota (Groq's TPD limit is scoped to the
account/organization, not the request) — see docs in the setup guide for why
this only helps when each key belongs to a *separate* Groq account.

GroqKeyRouter exposes the same .invoke() surface as langchain_groq's ChatGroq,
so it's a drop-in replacement: RAG_Reco_Agent calls self.llm.invoke(...) and
does not need to know rotation is happening underneath.

Configuration:
    GROQ_API_KEYS   comma-separated keys (preferred for multi-key setups)
    GROQ_API_KEY    single key, used if GROQ_API_KEYS is unset
"""

import os
import re
import threading
import time

from groq import RateLimitError
from langchain_groq import ChatGroq

_WAIT_RE = re.compile(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s")
_DEFAULT_COOLDOWN_S = 3600.0  # used only if the error message can't be parsed


def _load_keys() -> list[str]:
    multi = os.environ.get("GROQ_API_KEYS", "")
    keys = [k.strip() for k in multi.split(",") if k.strip()]
    if keys:
        return keys
    single = os.environ.get("GROQ_API_KEY", "").strip()
    if not single:
        raise RuntimeError("Set GROQ_API_KEY or GROQ_API_KEYS")
    return [single]


class GroqKeyRouter:
    """Sticky key selection: stays on one key until it 429s, then rotates to
    the next key that isn't on cooldown. Thread-safe for FastAPI's threadpool."""

    def __init__(self, keys: list[str] | None = None, **llm_kwargs):
        self._keys = keys or _load_keys()
        self._clients = [ChatGroq(api_key=k, **llm_kwargs) for k in self._keys]
        self._cooldown_until = [0.0] * len(self._clients)
        self._current = 0
        self._lock = threading.Lock()

    def _mark_exhausted(self, index: int, error: Exception) -> None:
        wait_s = _DEFAULT_COOLDOWN_S
        match = _WAIT_RE.search(str(error))
        if match:
            minutes = float(match.group(1) or 0)
            seconds = float(match.group(2))
            wait_s = minutes * 60 + seconds
        self._cooldown_until[index] = time.monotonic() + wait_s

    def invoke(self, messages, config=None, **kwargs):
        n = len(self._clients)
        with self._lock:
            start = self._current
        last_error: Exception | None = None
        for offset in range(n):
            index = (start + offset) % n
            if self._cooldown_until[index] > time.monotonic():
                continue
            try:
                result = self._clients[index].invoke(messages, config=config, **kwargs)
            except RateLimitError as exc:
                self._mark_exhausted(index, exc)
                last_error = exc
                continue
            with self._lock:
                self._current = index
            return result
        raise last_error or RuntimeError("No Groq API keys configured")
