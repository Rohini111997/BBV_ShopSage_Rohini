"""Per-request tracing for ShopSage.

One `Trace` per shopper message collects every event the agent produces —
routing, memory recall, retrieval, tool calls, failures — under a single
trace_id. It has two consumers:

  1. the UI, which renders it as the expandable "agent trace" panel (task 16)
  2. LangSmith, which receives the same spans for dashboards (task 24)

LangSmith is optional. With no LANGSMITH_API_KEY set, `@traceable` is a no-op
and the in-process trace still works, so nothing here is a hard dependency.
Enable it by adding to .env:

    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=ls__...
    LANGSMITH_PROJECT=shopsage
"""

import os
import time
import uuid
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()

# Tracing needs BOTH the flag and a key; the flag alone makes every LLM call
# retry against a missing endpoint.
LANGSMITH_ENABLED = bool(os.getenv("LANGSMITH_API_KEY")) and \
    os.getenv("LANGSMITH_TRACING", "").lower() in ("1", "true", "yes")

if LANGSMITH_ENABLED:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "shopsage")
else:
    # Stop LangChain auto-tracing from firing on a half-configured env.
    os.environ.pop("LANGSMITH_TRACING", None)
    os.environ.pop("LANGCHAIN_TRACING_V2", None)


def langsmith_status() -> str:
    if LANGSMITH_ENABLED:
        return f"enabled (project={os.getenv('LANGSMITH_PROJECT')})"
    return "disabled (set LANGSMITH_TRACING + LANGSMITH_API_KEY to enable)"


class Trace:
    """Events for one shopper message, sharing one trace_id."""

    def __init__(self, query: str, customer_id: str | None = None):
        self.trace_id = uuid.uuid4().hex[:12]
        self.query = query
        self.customer_id = customer_id
        self.events: list[dict] = []
        self._t0 = time.perf_counter()

    def _ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)

    def event(self, kind: str, **data) -> None:
        self.events.append({"kind": kind, "at_ms": self._ms(), **data})

    @contextmanager
    def span(self, kind: str, **data):
        """Time a block and record it, including failures.

        A raising block is recorded with ok=False and the error, then the
        exception propagates — tracing never swallows a bug.
        """
        start = time.perf_counter()
        record = {"kind": kind, "at_ms": self._ms(), **data}
        self.events.append(record)
        try:
            yield record
            record.setdefault("ok", True)   # don't clobber an ok set inside
        except Exception as exc:
            record["ok"] = False
            record["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record["ms"] = int((time.perf_counter() - start) * 1000)

    def failures(self) -> list[dict]:
        return [e for e in self.events if e.get("ok") is False]

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "customer_id": self.customer_id,
            "query": self.query,
            "total_ms": self._ms(),
            "langsmith": LANGSMITH_ENABLED,
            "events": self.events,
        }
