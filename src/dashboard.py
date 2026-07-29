"""ShopSage — Observability Dashboard (Task 29).

Aggregates the in-process traces produced during an agent session and prints
a live summary of:
  - Tool-call failure rate  (track_order / check_inventory)
  - Guardrail trigger count (age_filter / stock_filter)
  - Cache hit rate          (retrieval cache)
  - Average latency by path (new_search, follow_up, inventory_check, order_tracking)
  - Recommendation click-through (not measurable server-side; placeholder)

Usage (run from repo root after the agent has handled some requests):
    python -m src.dashboard

Or import and call from the Gradio UI:
    from src.dashboard import summarise_traces
    summary = summarise_traces(trace_list)
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import List


# ── helpers ─────────────────────────────────────────────────────────────────

def _events(trace: dict) -> list:
    return trace.get("events", [])


def _by_kind(trace: dict, kind: str) -> list:
    return [e for e in _events(trace) if e.get("kind") == kind]


# ── core aggregator ──────────────────────────────────────────────────────────

def summarise_traces(traces: List[dict]) -> dict:
    """Aggregate a list of trace dicts (as returned in result['trace']).

    Returns a plain dict ready to print or serialise.
    """
    if not traces:
        return {"error": "no traces provided"}

    # Tool calls
    tool_total = tool_failures = 0
    tool_failure_detail: list[dict] = []
    for t in traces:
        for e in _by_kind(t, "tool_call"):
            tool_total += 1
            if e.get("ok") is False:
                tool_failures += 1
                tool_failure_detail.append({
                    "trace_id": t.get("trace_id"),
                    "tool": e.get("tool"),
                    "error": e.get("error"),
                })

    # Guardrails
    guardrail_counts: dict[str, int] = defaultdict(int)
    for t in traces:
        for e in _by_kind(t, "guardrail"):
            guardrail_counts[e.get("rule", "unknown")] += 1

    # Cache
    cache_hits = cache_misses = 0
    for t in traces:
        cache_hits   += len(_by_kind(t, "cache_hit"))
        cache_misses += len(_by_kind(t, "cache_miss"))
    cache_total = cache_hits + cache_misses
    cache_hit_rate = round(cache_hits / cache_total * 100, 1) if cache_total else 0.0

    # Latency by path
    latency_by_path: dict[str, list[int]] = defaultdict(list)
    for t in traces:
        for e in _by_kind(t, "generate"):
            path = e.get("path", "unknown")
            ms = e.get("ms")
            if ms is not None:
                latency_by_path[path].append(ms)

    avg_latency = {
        path: round(sum(vals) / len(vals))
        for path, vals in latency_by_path.items()
    }

    # Total turn latency
    turn_latencies = [t.get("total_ms", 0) for t in traces]
    avg_turn_ms = round(sum(turn_latencies) / len(turn_latencies)) if turn_latencies else 0

    return {
        "num_turns": len(traces),
        "tool_calls": {
            "total": tool_total,
            "failures": tool_failures,
            "failure_rate_pct": round(tool_failures / tool_total * 100, 1) if tool_total else 0.0,
            "failures_detail": tool_failure_detail,
        },
        "guardrails": {
            "total_triggers": sum(guardrail_counts.values()),
            "by_rule": dict(guardrail_counts),
        },
        "cache": {
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_rate_pct": cache_hit_rate,
        },
        "latency": {
            "avg_turn_ms": avg_turn_ms,
            "avg_generate_ms_by_path": avg_latency,
        },
        "click_through": {
            "note": "Click-through is tracked client-side; not available server-side."
        },
    }


# ── pretty printer ───────────────────────────────────────────────────────────

def print_dashboard(summary: dict) -> None:
    print("\n" + "=" * 65)
    print("        SHOPSAGE OBSERVABILITY DASHBOARD")
    print("=" * 65)

    n = summary.get("num_turns", 0)
    print(f"\n  Turns analysed : {n}")

    tc = summary.get("tool_calls", {})
    print(f"\n  Tool Calls")
    print(f"    Total        : {tc.get('total', 0)}")
    print(f"    Failures     : {tc.get('failures', 0)}  "
          f"({tc.get('failure_rate_pct', 0):.1f}% failure rate)")
    for fd in tc.get("failures_detail", []):
        print(f"      ↳ [{fd['trace_id']}] {fd['tool']}: {fd['error']}")

    gr = summary.get("guardrails", {})
    print(f"\n  Guardrails")
    print(f"    Total triggers: {gr.get('total_triggers', 0)}")
    for rule, count in gr.get("by_rule", {}).items():
        print(f"      {rule:<20} {count}x")

    ca = summary.get("cache", {})
    print(f"\n  Retrieval Cache")
    print(f"    Hits         : {ca.get('hits', 0)}")
    print(f"    Misses       : {ca.get('misses', 0)}")
    print(f"    Hit rate     : {ca.get('hit_rate_pct', 0):.1f}%")

    la = summary.get("latency", {})
    print(f"\n  Latency")
    print(f"    Avg turn     : {la.get('avg_turn_ms', 0)} ms")
    for path, ms in la.get("avg_generate_ms_by_path", {}).items():
        print(f"      generate/{path:<18} {ms} ms")

    print("\n" + "=" * 65 + "\n")


# ── standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Drive a few turns through the live agent and summarise their traces.
    import os, sys
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from src.Agent_3 import rag_agent
    except Exception as exc:
        print(f"Could not import Agent_3: {exc}")
        sys.exit(1)

    DEMO_QUERIES = [
        ("CUST-0083", "waterproof jacket for hiking under 4000"),
        ("CUST-0083", "does the first one come in black"),
        ("CUST-0083", "is the Summit Waterproof Trail Jacket in stock in size M?"),
        ("CUST-0083", "show me jackets"),   # cache hit expected on second session
        ("CUST-EVAL-06", "show me a dress for my 10-year-old daughter"),  # age guardrail
        ("CUST-0028", "where is my order ORD-1042?"),
    ]

    traces: list[dict] = []
    prev_cust: str | None = None

    for cust_id, query in DEMO_QUERIES:
        if cust_id != prev_cust:
            rag_agent.set_shopper(cust_id)
            prev_cust = cust_id
        result = rag_agent.get_rag_product_recommendation(query)
        trace = result.get("trace", {})
        if trace:
            traces.append(trace)
        print(f"  [{trace.get('trace_id', '?')}] {query[:55]!r:<57} "
              f"→ {len(result.get('products', []))} products  "
              f"{trace.get('total_ms', 0)}ms")

    summary = summarise_traces(traces)
    print_dashboard(summary)

    # Save for the evidence folder
    out_path = "docs/evidence/dashboard_run.json"
    import os as _os
    _os.makedirs("docs/evidence", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved dashboard summary → {out_path}")


# ── session trace store ───────────────────────────────────────────────────────

class SessionTraceStore:
    """Thread-safe accumulator for traces produced during a live Gradio session.

    Typical usage in the Gradio app::

        from src.dashboard import session_store
        ...
        result = rag_agent.get_rag_product_recommendation(query)
        session_store.push(result.get("trace", {}))
        summary = session_store.summarise()
        html    = render_html_dashboard(summary)
    """

    def __init__(self) -> None:
        import threading
        self._lock   = threading.Lock()
        self._traces: list[dict] = []

    def push(self, trace: dict) -> None:
        """Append one trace dict (as returned in result['trace'])."""
        if not trace:
            return
        with self._lock:
            self._traces.append(trace)

    def clear(self) -> None:
        with self._lock:
            self._traces.clear()

    def snapshot(self) -> list[dict]:
        """Return a shallow copy of collected traces (safe to iterate)."""
        with self._lock:
            return list(self._traces)

    def summarise(self) -> dict:
        """Return the current aggregated summary dict."""
        return summarise_traces(self.snapshot())

    def __len__(self) -> int:
        with self._lock:
            return len(self._traces)


#: Module-level singleton — import and use in the Gradio app directly.
session_store = SessionTraceStore()


# ── edge-case analyser ────────────────────────────────────────────────────────

def analyse_edge_cases(traces: list[dict]) -> dict:
    """Detect the three edge-case categories from Task 30.

    Scans trace events for signals that indicate:
      - **inventory_timeout**  : tool_call events where ok=False and the error
        mentions "timeout" or "timed out".
      - **no_catalog_match**   : retrieval events marked no_match=True or
        returning 0 results.
      - **ambiguous_reference**: routing events where path="follow_up" AND
        the agent emitted a clarification_needed flag.

    Returns a dict ready to merge into the dashboard summary.
    """
    timeouts:   list[dict] = []
    no_matches: list[dict] = []
    ambiguous:  list[dict] = []

    for t in traces:
        tid = t.get("trace_id", "?")
        for e in _events(t):
            kind = e.get("kind", "")

            # ── inventory / order-tracking API timeout ────────────────────
            if kind == "tool_call" and e.get("ok") is False:
                err = str(e.get("error", "")).lower()
                if "timeout" in err or "timed out" in err:
                    timeouts.append({
                        "trace_id": tid,
                        "tool":     e.get("tool"),
                        "error":    e.get("error"),
                    })

            # ── no catalog match (retrieval returned nothing useful) ───────
            if kind == "retrieval":
                if e.get("no_match") is True or e.get("n_results", 1) == 0:
                    no_matches.append({
                        "trace_id": tid,
                        "query":    e.get("query", t.get("query")),
                    })

            # ── ambiguous "the second one" / pronoun reference ────────────
            if kind in ("route", "generate"):
                if e.get("clarification_needed") or e.get("path") == "follow_up" and e.get("ambiguous"):
                    ambiguous.append({
                        "trace_id":    tid,
                        "query":       t.get("query"),
                        "explanation": e.get("clarification_needed", "ambiguous follow-up"),
                    })

    return {
        "edge_cases": {
            "inventory_timeouts": {
                "count":   len(timeouts),
                "details": timeouts,
            },
            "no_catalog_match": {
                "count":   len(no_matches),
                "details": no_matches,
            },
            "ambiguous_references": {
                "count":   len(ambiguous),
                "details": ambiguous,
            },
        }
    }


# ── eval report integration ───────────────────────────────────────────────────

def load_eval_report(path: str = "docs/evidence/eval_report.json") -> dict | None:
    """Load a saved eval report produced by the eval harness (Task 25-28).

    Expected schema (flexible — only reads what exists)::

        {
          "baseline_score": 0.67,
          "improved_score": 0.83,
          "cases": [
            {"query": "...", "passed": true, "category": "retrieval_miss"}
          ]
        }

    Returns None if the file does not exist.
    """
    import pathlib
    p = pathlib.Path(path)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def eval_summary(report: dict | None) -> dict:
    """Condense a full eval report into dashboard-ready numbers."""
    if report is None:
        return {"available": False, "note": "Run the eval harness to populate scores."}

    cases     = report.get("cases", [])
    total     = len(cases)
    passed    = sum(1 for c in cases if c.get("passed"))
    fail_cats: dict[str, int] = {}
    for c in cases:
        if not c.get("passed"):
            cat = c.get("category", "unknown")
            fail_cats[cat] = fail_cats.get(cat, 0) + 1

    return {
        "available":       True,
        "baseline_score":  report.get("baseline_score"),
        "improved_score":  report.get("improved_score"),
        "delta":           (
            round(report["improved_score"] - report["baseline_score"], 3)
            if "improved_score" in report and "baseline_score" in report
            else None
        ),
        "total_cases":     total,
        "passed":          passed,
        "failed":          total - passed,
        "pass_rate_pct":   round(passed / total * 100, 1) if total else 0.0,
        "failure_by_category": fail_cats,
    }


# ── full enriched summary ─────────────────────────────────────────────────────

def full_summary(
    traces: list[dict],
    eval_report_path: str = "docs/evidence/eval_report.json",
) -> dict:
    """Return summarise_traces + edge-case analysis + eval scores in one dict."""
    base  = summarise_traces(traces)
    edges = analyse_edge_cases(traces)
    evals = eval_summary(load_eval_report(eval_report_path))
    return {**base, **edges, "eval": evals}


# ── HTML renderer (Gradio / Streamlit) ───────────────────────────────────────

def render_html_dashboard(summary: dict) -> str:
    """Produce a self-contained HTML snippet that Gradio can display via
    ``gr.HTML(render_html_dashboard(summary))``.

    The snippet is styled with inline CSS so it renders correctly inside
    Gradio's iframe-less HTML component without any external dependencies.
    """
    n   = summary.get("num_turns", 0)
    tc  = summary.get("tool_calls",  {})
    gr_ = summary.get("guardrails",  {})
    ca  = summary.get("cache",       {})
    la  = summary.get("latency",     {})
    ec  = summary.get("edge_cases",  {})
    ev  = summary.get("eval",        {})

    def _badge(label: str, value, color: str = "#4f8ef7") -> str:
        return (
            f'<span style="display:inline-block;background:{color};color:#fff;'
            f'border-radius:6px;padding:2px 10px;margin:2px;font-size:13px;">'
            f'{label}: <b>{value}</b></span>'
        )

    def _section(title: str, body: str) -> str:
        return (
            f'<div style="margin:10px 0;padding:10px 14px;border-left:4px solid #4f8ef7;'
            f'background:#1e2230;border-radius:4px;">'
            f'<h4 style="margin:0 0 6px;color:#4f8ef7;">{title}</h4>{body}</div>'
        )

    tool_color  = "#e74c3c" if tc.get("failure_rate_pct", 0) > 10 else "#2ecc71"
    cache_color = "#2ecc71" if ca.get("hit_rate_pct", 0)    > 50 else "#e67e22"

    # ── Tool calls ────────────────────────────────────────────────────────────
    tool_body = (
        _badge("Total", tc.get("total", 0))
        + _badge("Failures", tc.get("failures", 0), tool_color)
        + _badge("Failure rate", f"{tc.get('failure_rate_pct', 0):.1f}%", tool_color)
    )
    fail_rows = "".join(
        f'<div style="font-size:12px;color:#e74c3c;padding-left:8px;">↳ [{d["trace_id"]}]'
        f' {d["tool"]}: {d["error"]}</div>'
        for d in tc.get("failures_detail", [])
    )
    tool_body += fail_rows

    # ── Guardrails ────────────────────────────────────────────────────────────
    gr_body = _badge("Total triggers", gr_.get("total_triggers", 0), "#9b59b6")
    for rule, cnt in gr_.get("by_rule", {}).items():
        gr_body += _badge(rule, f"{cnt}×", "#8e44ad")

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_body = (
        _badge("Hits",     ca.get("hits",   0), cache_color)
        + _badge("Misses", ca.get("misses", 0), "#e67e22")
        + _badge("Hit rate", f"{ca.get('hit_rate_pct', 0):.1f}%", cache_color)
    )

    # ── Latency ───────────────────────────────────────────────────────────────
    lat_body = _badge("Avg turn", f"{la.get('avg_turn_ms', 0)} ms")
    for path, ms in la.get("avg_generate_ms_by_path", {}).items():
        lat_body += _badge(f"generate/{path}", f"{ms} ms", "#16a085")

    # ── Edge cases ────────────────────────────────────────────────────────────
    ec_body = ""
    if ec:
        ec_body = (
            _badge("API timeouts",    ec.get("inventory_timeouts",   {}).get("count", 0), "#e74c3c")
            + _badge("No-match",      ec.get("no_catalog_match",     {}).get("count", 0), "#e67e22")
            + _badge("Ambiguous ref", ec.get("ambiguous_references", {}).get("count", 0), "#8e44ad")
        )

    # ── Eval ─────────────────────────────────────────────────────────────────
    ev_body = ""
    if ev.get("available"):
        delta_str = (
            f'+{ev["delta"]:.3f}' if ev.get("delta") and ev["delta"] > 0 else str(ev.get("delta", "—"))
        )
        ev_color = "#2ecc71" if ev.get("delta", 0) and ev["delta"] > 0 else "#e74c3c"
        ev_body = (
            _badge("Baseline", ev.get("baseline_score", "—"))
            + _badge("Improved", ev.get("improved_score", "—"), "#2ecc71")
            + _badge("Delta",  delta_str, ev_color)
            + _badge("Pass rate", f"{ev.get('pass_rate_pct', 0):.1f}%",
                     "#2ecc71" if ev.get("pass_rate_pct", 0) >= 70 else "#e74c3c")
        )
        for cat, cnt in ev.get("failure_by_category", {}).items():
            ev_body += _badge(cat, f"{cnt} failures", "#7f8c8d")
    else:
        ev_body = f'<span style="color:#7f8c8d;font-size:13px;">{ev.get("note", "")}</span>'

    html = f"""
<div style="font-family:\'Segoe UI\',Arial,sans-serif;background:#13161f;
            color:#dde3f0;padding:16px;border-radius:10px;max-width:780px;">
  <h3 style="margin:0 0 12px;color:#fff;letter-spacing:1px;">
    🛍️ ShopSage — Observability Dashboard
  </h3>
  <p style="margin:0 0 10px;font-size:13px;color:#7f8c8d;">
    Turns analysed: <b style="color:#fff;">{n}</b>
  </p>
  {_section("🔧 Tool Calls", tool_body)}
  {_section("🛡️ Guardrails", gr_body)}
  {_section("⚡ Retrieval Cache", cache_body)}
  {_section("⏱️ Latency", lat_body)}
  {(_section("⚠️ Edge Cases", ec_body) if ec else "")}
  {(_section("📊 Eval Scores", ev_body) if ev else "")}
  <p style="margin:12px 0 0;font-size:11px;color:#444;">
    Click-through tracking is client-side only and not reflected here.
  </p>
</div>
"""
    return html


# ── live-refresh dashboard server ─────────────────────────────────────────────

class DashboardServer:
    """Polling-based live dashboard that re-renders every N seconds.

    Designed for use in a Gradio ``gr.Blocks`` app::

        from src.dashboard import DashboardServer, session_store
        ds = DashboardServer(store=session_store, interval_s=10)

        with gr.Blocks() as demo:
            panel = gr.HTML(ds.render())
            timer = gr.Timer(value=10)
            timer.tick(fn=ds.render, outputs=panel)

    Also callable from Streamlit with ``st.components.v1.html(ds.render())``.
    """

    def __init__(
        self,
        store: SessionTraceStore | None = None,
        interval_s: float = 10.0,
        eval_report_path: str = "docs/evidence/eval_report.json",
    ) -> None:
        self._store            = store or session_store
        self._interval         = interval_s
        self._eval_report_path = eval_report_path

    def render(self) -> str:
        """Compute and return the current HTML dashboard (called by Gradio timer)."""
        traces  = self._store.snapshot()
        summary = full_summary(traces, self._eval_report_path)
        return render_html_dashboard(summary)

    def print_console(self) -> None:
        """Print the text dashboard to stdout (convenience for CLI use)."""
        traces  = self._store.snapshot()
        summary = full_summary(traces, self._eval_report_path)
        print_dashboard(summary)
        ec = summary.get("edge_cases", {})
        if ec:
            print("  Edge Cases")
            to = ec.get("inventory_timeouts", {})
            nm = ec.get("no_catalog_match", {})
            ar = ec.get("ambiguous_references", {})
            print(f"    API timeouts    : {to.get('count', 0)}")
            print(f"    No-catalog match: {nm.get('count', 0)}")
            print(f"    Ambiguous refs  : {ar.get('count', 0)}")
            print("=" * 65 + "\n")

        ev = summary.get("eval", {})
        if ev.get("available"):
            print("  Eval Scores")
            print(f"    Baseline : {ev.get('baseline_score')}")
            print(f"    Improved : {ev.get('improved_score')}")
            print(f"    Delta    : {ev.get('delta')}")
            print(f"    Pass rate: {ev.get('pass_rate_pct'):.1f}%")
            print("=" * 65 + "\n")
