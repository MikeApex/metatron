"""
core/build/probe.py — the model names a source; CODE chooses the call.

N3, first half. The Librarian's hardest field is *"is this data available?"* A
model asked that answers from its impression of what tools exist. This module
answers exactly: resolve the manifest id, run a FIXED code-written call, count
what came back.

With the probe, `data_available` is evidence. Without it the whole Answer
Ledger is a claim.

THREE STATES, NEVER TWO. This is core/trace.py's is_grounded() lesson one layer
up — *"we asked and nothing came back"* is a different and much more useful
state than *"this never retrieves"*, and collapsing the two is what made the
old flag unreadable. So:

    needs_tool     the handler is not registered. Nothing was asked.
    unaskable      the handler IS registered and cannot answer this SHAPE of
                   question. Nothing was asked, for a different reason.
    no_data        it ran and returned nothing. The question is answerable in
                   principle and unanswered in fact — an interview item, not a
                   build blocker.
    data           it ran and returned rows.
    error          it raised. Recorded with the exception text, never silently
                   folded into no_data, because an error means the source's
                   availability is UNKNOWN rather than false.

`unaskable` was added 2026-09-18, after the worked Inquiry run walked straight
past the gap it names. `read_journal` is registered and takes ONE DATE, so the
journal reported `available: true` against a question asking how Mike talks
about something across 61 files. That probe returns one day or nothing and
settles as `no_data` — *"there is nothing recorded"* — when the truth is *"this
tool cannot be asked that."* The first means a FACT is missing; the second
means a TOOL is, and only the second earns a `needs_tool` brief. The shape
restriction lives in manifest.py's `answers` field, so CODE decides it.

THE INJECTION ANSWER. `candidate_sources` is validated against the manifest id
list, and the probe arguments come from manifest._SOURCES, not from the model.
A corpus carrying an injected instruction can influence what a model NAMES; it
cannot influence what is CALLED.

Nothing here raises. A probe that threw would take down the node that exists to
report the failure.
"""

from __future__ import annotations

import re
from typing import Any

from core.build import manifest as M

# Tool returns in this repo are mostly prose. A short reply that opens by
# saying there is nothing is the house idiom for an empty result
# ("No profile recorded yet."), and it must count as 0 rather than 1.
#
# Bounded to short replies deliberately: a long answer beginning "No, ..." is a
# real answer. The failure direction is counting a genuinely empty result as
# one row, which reads as data_available: true and is the error worth avoiding
# — so the bound is generous rather than tight.
_EMPTY_PREFIX = re.compile(r"^\s*(no|none|nothing|empty|not\s+\w+)\b", re.I)
_EMPTY_MAX_CHARS = 120


def probe(source_id: str, persona: str | None = None,
          overrides: dict | None = None, data_kind: str = "") -> dict:
    """
    One evidence record for one manifest source.

    `overrides` is for the CONDENSER, which narrows a range probe to the window
    a question actually needs (a date range, a search term). It is merged over
    the fixed arguments and is itself code-written — settle.py and condense.py
    pass it; no model value reaches here.

    `data_kind` is the SHAPE of the question being asked (`single_point` or
    `behavioural`). Supplied, it is checked against the source's `answers`
    restriction BEFORE the call, so a tool that cannot serve this shape returns
    `unaskable` rather than being called and returning a misleading nothing.
    Omitted, the check does not run — which is the honest default for a caller
    that does not know the shape, and is why settle.py always passes it.
    """
    entry = M.source(source_id)
    if entry is None:
        return _record(source_id, "", state="error", rows=0,
                       error=f"{source_id!r} is not a manifest source")

    tool_name = entry["tool"]
    handler = _handler(tool_name)
    if handler is None:
        return _record(source_id, tool_name, state="needs_tool", rows=0,
                       error=f"{tool_name} is not registered")

    # Checked BEFORE the call, deliberately. Calling a single-date reader with a
    # behavioural question returns one day or nothing, and that answer is
    # indistinguishable from an empty corpus once it is a row count.
    if data_kind and not M.answers_shape(source_id, data_kind):
        return _record(
            source_id, tool_name, state="unaskable", rows=0,
            error=(f"{tool_name} is registered but cannot answer a "
                   f"{data_kind} question — it serves "
                   f"{entry.get('answers')} only"))

    args = {**(entry.get("probe") or {}), **(overrides or {})}
    args = {k: v for k, v in args.items() if v not in ("", None)}

    try:
        from core.persona import persona_scope
        if persona:
            with persona_scope(persona):
                raw = handler(**args)
        else:
            raw = handler(**args)
    except TypeError as exc:
        # The fixed argument set no longer matches the handler's signature —
        # a real defect in this table, reported as one rather than as no_data.
        return _record(source_id, tool_name, state="error", rows=0,
                       error=f"probe arguments do not fit {tool_name}: {exc}",
                       probe=args)
    except Exception as exc:
        return _record(source_id, tool_name, state="error", rows=0,
                       error=f"{type(exc).__name__}: {exc}", probe=args)

    rows, kind = count_rows(raw)
    return _record(
        source_id, tool_name,
        state="data" if rows > 0 else "no_data",
        rows=rows, probe=args, raw_kind=kind,
        sample_ok=rows > 0,
    )


def _handler(tool_name: str):
    try:
        from core.orchestrator import register_tools
        _, handlers = register_tools()
        return handlers.get(tool_name)
    except Exception:
        return None


def _record(source_id: str, tool: str, state: str, rows: int,
            error: str = "", probe: dict | None = None,
            raw_kind: str = "", sample_ok: bool = False) -> dict:
    return {
        "source": source_id,
        "tool": tool,
        "probe": probe or {},
        "state": state,
        "rows": rows,
        "data_available": state == "data",
        "sample_ok": sample_ok,
        "raw_kind": raw_kind,
        "error": error,
    }


def count_rows(raw: Any) -> tuple[int, str]:
    """
    (count, kind). The count's only job is to separate "something" from
    "nothing" — precision beyond that is the condenser's problem, not this one.
    """
    if raw is None:
        return 0, "none"
    if isinstance(raw, (list, tuple)):
        return len(raw), "list"
    if isinstance(raw, dict):
        return len(raw), "dict"
    if isinstance(raw, (int, float, bool)):
        return 1, "scalar"

    text = str(raw).strip()
    if not text:
        return 0, "text"
    if len(text) <= _EMPTY_MAX_CHARS and _EMPTY_PREFIX.match(text):
        return 0, "text"
    return len([line for line in text.splitlines() if line.strip()]), "text"


def probe_all(source_ids: list[str], persona: str | None = None,
              data_kind: str = "") -> list[dict]:
    """Evidence for each named source, in order, deduplicated."""
    seen: set[str] = set()
    out: list[dict] = []
    for source_id in source_ids:
        if source_id in seen or source_id == M.USER_SOURCE:
            continue
        seen.add(source_id)
        out.append(probe(source_id, persona, data_kind=data_kind))
    return out


def summarise(records: list[dict]) -> dict:
    """
    What the ledger row's code-written block needs, derived from the evidence.

    `data_available` is true when ANY probed source returned rows. A question
    with three sources of which one answers is answerable; requiring all three
    would park work on the absence of a source nobody needed.

    `needs_tool` collects BOTH kinds of missing tool — the unregistered one and
    the registered one that cannot be asked this shape — because both resolve
    the same way: a brief Mike builds on the Mac. `unaskable` is reported
    separately alongside it so the brief can say WHICH of the two it is, since
    "write this tool" and "widen this tool" are different pieces of work.
    """
    return {
        "data_available": any(r.get("data_available") for r in records),
        "evidence": records,
        "needs_tool": sorted({
            r["tool"] for r in records
            if r.get("state") in ("needs_tool", "unaskable")
        }),
        "unaskable": sorted({
            r["tool"] for r in records if r.get("state") == "unaskable"
        }),
        "errors": [r["error"] for r in records if r.get("state") == "error"],
        "rows_total": sum(int(r.get("rows") or 0) for r in records),
    }
