"""
core/build/doors.py — the read doors. The Mac names; the VM reads; results cross.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 6 (The read doors),
ruling 11 ("the Mac searches the VM through read doors... built as the Librarian
needs them"), section 12 (the Doors row).

WHAT A DOOR IS. The Librarian subagent runs on the Mac, in Claude Code. The
persona's data is on the VM. A door is the only way the first reaches the
second: one endpoint, `GET /monitor/tool`, two modes, and nothing but the RESULT
of a read crosses the wire. No file is copied to the Mac, no corpus is mirrored,
and no tool runs on the Mac against VM data.

    mode 1   ?presence=<source_id>   "is there a corpus here?"  -> {state, count, window}
    mode 2   ?name=&args=            "read this"                -> the result

THE INJECTION ANSWER, WHICH IS THE POINT OF MODE 1 AND IS UNCHANGED. The
presence check takes a SOURCE ID, not arguments. The call it runs — tool and
every argument — comes from `manifest._SOURCES`, a table of literals written in
this repo. So a corpus carrying an injected instruction can influence what a
model NAMES; it cannot influence what is CALLED. This module is the old
`core/build/probe.py` moved to the VM behind the door: the five states, the row
counter and the fixed-call rule are carried across verbatim in substance.

WHY MODE 2 IS SAFE DESPITE TAKING ARGUMENTS. Three separate bounds, and they are
not alternatives:

  1. THE NAME IS ALLOWLISTED — `READ_SET` below. Not "not a write tool": an
     enumerated list. A deny list cannot enclose a tool surface where the
     mutators are named for what they do rather than for the verb `write`
     (`merge_contacts`, `teach_intake`, `apply_crm_proposals`,
     `record_wisdom_response` all fell through v3's "every `write_*`" rule).
  2. NO OUTBOUND TOOL SITS BEHIND A DOOR. The read set of v3.7 section 6.3
     includes seven live feeds — six `get_*` and `find_places` — that leave the
     machine. All seven are refused here with a 403, so content the Librarian
     reads can never compose a call that leaves the machine. This is a STRUCTURAL
     invariant, asserted at import (see `_assert_no_outbound_door` at the foot of
     the file): the allowlist grows by a line per run, and the line that adds an
     outbound tool must fail loudly rather than ship.
  3. THE ARGUMENTS ARE VALIDATED SERVER-SIDE against a per-tool schema with caps
     — window <= 90 days, `k` <= 50, `max_entries` <= 200, and beneath those the
     wisdom store's own `READ_CAP` (tools/wisdom.py:345), the one read tool in
     this set that defines a cap of its own. Anything outside the schema or over
     a cap is a 400 CARRYING THE SCHEMA, not a bare rejection: the caller is a
     model that has to correct itself, and a refusal it cannot act on costs a
     whole round.

What remains model-chosen is WHICH of the persona's own data to read, and how
much. Ruling 11 grants exactly that and nothing more.

PERSONA BINDING IS FROM THE QUERY AND FROM NOWHERE ELSE. Every call is wrapped
in `persona_scope(persona)`, and no per-tool schema below declares a `persona`
property — so `get_log_window`'s own `persona=` keyword, which exists for dev
testing, cannot be reached through a door. An unknown argument is a 400, which
is what makes that hold rather than merely being true today. A door bound to one
persona cannot read another's data.

BUILT AS NEEDED (ruling 11). `READ_SET` is run 1's five tools plus the two
section 9 tools phase D builds. It is not v3.7 section 6.3's list transcribed —
the rest is added a line per run, when a run needs it. A name in the set whose
tool is not registered is refused as UNREGISTERED (501, `reason: needs_tool`),
never as unauthorised and never as a 500: "you may not ask this" and "this is
not built yet" are different facts and the Librarian acts on them differently.

WHY THIS MODULE IS IMPORTED LAZILY BY core/server.py. The import-time invariant
above fails closed. Imported at module level it would take the whole server down
on a deploy; imported inside the endpoint it takes down the door and leaves the
user's sessions serving. Fail closed at the door, not at the server.

PRIVACY, STATED ONCE. Whatever crosses a door is in the build session and
therefore reaches Anthropic — ruling 10, recorded in ROADMAP.md section 0 under
the 2026-09-24 amendment. What does NOT cross is anything mode 1 touches: the
presence check returns a state, a count and a date window, and no value read
from any source. That includes the error path — see `_no_content_note`.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any, Callable

from core.build import manifest as M

# ---------------------------------------------------------------------------
# Caps (plan section 6)
#
# These sit ABOVE each tool's own limits, never instead of them. read_wisdom
# applies tools/wisdom.py's READ_CAP = 15 underneath this schema, and it stays in
# force because `uncapped` is deliberately absent from the schema below: an
# argument that is not in the schema is refused, so the one lever that would
# switch READ_CAP off cannot be reached through a door.
# ---------------------------------------------------------------------------

MAX_WINDOW_DAYS = 90
MAX_K = 50
MAX_ENTRIES = 200


class DoorRefused(Exception):
    """A refusal with an HTTP status and a JSON body the caller can act on."""

    def __init__(self, status: int, detail: dict):
        super().__init__(str(detail.get("error", "refused")))
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# The allowlist — one line per run (ruling 11)
#
# Run 1 (`home_care`) needs the first five. `search_conversations` and
# `read_journal_range` are section 9's two tools, built by phase D as ordinary
# development; they are LISTED here before they exist, deliberately, so that the
# door refuses them as unregistered rather than as unauthorised. That is the
# right behaviour and is asserted by tests/test_build_doors.py — a name Build
# will need, missing its tool, is a phase-D gap and should read as one.
#
# ADDING A LINE IS A DECISION, not a tidy-up. Every addition widens what a model
# can ask the VM to read on the strength of a corpus it has just read. The
# structural floor is `_assert_no_outbound_door`: nothing that leaves the machine
# may be added here at all.
# ---------------------------------------------------------------------------

READ_SET: frozenset[str] = frozenset({
    "get_log_window",        # run 1
    "read_wisdom",           # run 1
    "search_memory",         # run 1
    "list_schedules",        # run 1
    "read_profile",          # run 1
    "search_conversations",  # section 9 — phase D
    "read_journal_range",    # section 9 — phase D
})

def pending_tools() -> frozenset[str]:
    """
    Read-set names with no registered handler here — DERIVED, never a written list.

    This was a hardcoded frozenset naming `search_conversations` and
    `read_journal_range` while phase D was still to build them. Phase D landed
    both the same afternoon and the constant went stale in silence: nothing
    refused a working tool, because the actual gate is the `_handler(name) is
    None` lookup below, but `scripts/vm_read.py --list` went on advertising two
    live tools as unbuilt.

    A STALE LIST MATTERS MORE HERE THAN IN MOST PLACES. § 6 makes this surface
    the description of what the Librarian may read, and phase C renders it into
    that agent's prompt — so the stale version would have told the Librarian a
    tool it can use does not exist, which is the one direction the read doors are
    supposed to make impossible. Derived, it cannot drift, and it answers for the
    next tool the read set names before anyone writes it, with no edit here.
    """
    return frozenset(name for name in READ_SET if _handler(name) is None)


def live_feed_tools() -> frozenset[str]:
    """
    The outbound reads, DERIVED from manifest._SOURCES rather than listed again.

    `manifest.py` already carries the seven `live: True` rows with the reasoning
    for why they are never probed. A second copy here would be a second place to
    forget when an eighth outbound tool is added — and the one that is forgotten
    is the one that opens a door out of the machine. `sources(registered=set())`
    is used rather than the module private so this reads the public shape, and
    passing an empty set skips the register_tools() import the availability
    column would otherwise cost.
    """
    return frozenset(
        s["tool"] for s in M.sources(registered=set()) if s.get("live")
    )


# ---------------------------------------------------------------------------
# Per-tool schemas
#
# A small vocabulary on purpose. These are validated by hand rather than by
# jsonschema because the whole surface is seven tools of at most four arguments,
# and because the ERROR is the product: it has to name the offending argument,
# the cap it broke and the schema it broke it against, in a form a model can act
# on without a second round trip.
#
# Types: "string" | "integer" | "date" | "enum" | "string_list".
# Extras: "max"/"min" on integers, "values" on enum and string_list.
# "window" declares a pair of date fields and the maximum span between them.
#
# NO SCHEMA DECLARES `persona`. That is the persona binding, and it is asserted
# by the suite rather than left as a property of how these happen to be written.
# ---------------------------------------------------------------------------

_WISDOM_DOMAINS = ("food", "fitness", "health", "sleep", "work", "money",
                   "relationships", "learning", "recreation", "home",
                   "identity", "other")

_SCHEMAS: dict[str, dict] = {
    "get_log_window": {
        "summary": "daily logs over a window, newest kept when capped",
        "required": ("start_date", "end_date"),
        "properties": {
            "start_date": {"type": "date", "description": "ISO date, YYYY-MM-DD"},
            "end_date": {"type": "date", "description": "ISO date, YYYY-MM-DD"},
            "max_entries": {"type": "integer", "min": 0, "max": MAX_ENTRIES,
                            "description": "0 = no cap below the door's own"},
        },
        "window": {"start": "start_date", "end": "end_date",
                   "max_days": MAX_WINDOW_DAYS},
    },
    "read_wisdom": {
        # `uncapped` is ABSENT on purpose — see the caps note above. Passing it
        # is an unknown argument and a 400, which is what keeps READ_CAP = 15 in
        # force behind this door.
        "summary": "standing facts and patterns, newest READ_CAP per read",
        "required": (),
        "properties": {
            "key": {"type": "string", "description": "one entry by its identifier"},
            "domains": {"type": "string_list", "values": _WISDOM_DOMAINS,
                        "description": "one domain or several"},
            "provenance": {"type": "enum", "values": ("stated", "observed"),
                           "description": "limit to stated or to observed"},
        },
    },
    "search_memory": {
        "summary": "the FAISS index over logs and journal entries",
        "required": ("query",),
        "properties": {
            "query": {"type": "string", "description": "what to look for"},
            "k": {"type": "integer", "min": 1, "max": MAX_K,
                  "description": "results to return"},
        },
    },
    "list_schedules": {
        "summary": "scheduled prompts and their cadence",
        "required": (),
        "properties": {},
    },
    "read_profile": {
        "summary": "stable biographical facts",
        "required": (),
        "properties": {
            "field": {"type": "string",
                      "description": "one field; omit for the whole profile"},
        },
    },
    # ---- phase D builds these two; the schemas are written from the call
    # manifest._SOURCES already makes, so the door and the presence check agree
    # on the signature before either can run. If phase D lands a different
    # signature the mismatch surfaces as a 400 naming it (see the TypeError
    # branch in research_read), never as a 500.
    "search_conversations": {
        "summary": "verbatim conversation turns, searchable",
        "required": ("query",),
        "properties": {
            "query": {"type": "string", "description": "what to look for"},
            "k": {"type": "integer", "min": 1, "max": MAX_K,
                  "description": "results to return"},
        },
    },
    "read_journal_range": {
        "summary": "journal entries across a date range, condensed",
        "required": ("start", "end"),
        "properties": {
            "start": {"type": "date", "description": "ISO date, YYYY-MM-DD"},
            "end": {"type": "date", "description": "ISO date, YYYY-MM-DD"},
            "max_entries": {"type": "integer", "min": 1, "max": MAX_ENTRIES,
                            "description": "entries to return"},
        },
        "window": {"start": "start", "end": "end", "max_days": MAX_WINDOW_DAYS},
    },
}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def public_schema(name: str) -> dict:
    """
    The schema as the caller sees it, in a refusal body.

    Rendered rather than returned raw so that a future internal field cannot
    leak into a response by being added to `_SCHEMAS`.
    """
    spec = _SCHEMAS.get(name)
    if spec is None:
        return {}
    props: dict[str, dict] = {}
    for field, rule in spec["properties"].items():
        entry: dict[str, Any] = {"type": rule["type"]}
        if "description" in rule:
            entry["description"] = rule["description"]
        for key in ("min", "max"):
            if key in rule:
                entry[key] = rule[key]
        if "values" in rule:
            entry["values"] = list(rule["values"])
        props[field] = entry
    out: dict[str, Any] = {
        "tool": name,
        "summary": spec.get("summary", ""),
        "required": list(spec["required"]),
        "properties": props,
    }
    window = spec.get("window")
    if window:
        out["window"] = {
            "start": window["start"], "end": window["end"],
            "max_days": window["max_days"],
            "note": f"{window['end']} minus {window['start']} must be "
                    f"{window['max_days']} days or fewer",
        }
    return out


def _refuse_args(name: str, reason: str) -> DoorRefused:
    """A 400 that always carries the schema — the plan's wording, not a nicety."""
    return DoorRefused(400, {
        "error": reason,
        "reason": "schema",
        "tool": name,
        "schema": public_schema(name),
    })


def validate_args(name: str, args: dict | None) -> dict:
    """
    Check `args` against the tool's schema and return the cleaned call.

    Raises DoorRefused(400) carrying the schema on anything the schema does not
    admit: an unknown argument, a missing required one, a wrong type, a value
    over a cap, or a window wider than MAX_WINDOW_DAYS.
    """
    spec = _SCHEMAS.get(name)
    if spec is None:
        # Unreachable through research_read, which checks the read set first.
        # Kept because a direct caller is a caller, and silently accepting a
        # tool with no schema is exactly the hole the schemas exist to close.
        raise DoorRefused(500, {
            "error": f"{name!r} is in the read set with no schema — refusing",
            "reason": "no_schema", "tool": name,
        })

    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise _refuse_args(name, "args must be a JSON object")

    unknown = sorted(set(args) - set(spec["properties"]))
    if unknown:
        raise _refuse_args(
            name,
            f"unknown argument(s) {unknown} — this door admits only "
            f"{sorted(spec['properties']) or 'no arguments'}")

    missing = [f for f in spec["required"] if f not in args or args[f] in ("", None)]
    if missing:
        raise _refuse_args(name, f"missing required argument(s) {sorted(missing)}")

    cleaned: dict[str, Any] = {}
    for field, value in args.items():
        if value in ("", None) and field not in spec["required"]:
            continue
        cleaned[field] = _coerce(name, field, spec["properties"][field], value)

    window = spec.get("window")
    if window and window["start"] in cleaned and window["end"] in cleaned:
        _check_window(name, cleaned[window["start"]], cleaned[window["end"]],
                      window["max_days"])
    return cleaned


def _coerce(name: str, field: str, rule: dict, value: Any) -> Any:
    kind = rule["type"]

    if kind == "date":
        if not isinstance(value, str) or not _ISO_DATE.match(value):
            raise _refuse_args(name, f"{field!r} must be an ISO date (YYYY-MM-DD)")
        try:
            date.fromisoformat(value)
        except ValueError:
            raise _refuse_args(name, f"{field!r} is not a real date: {value!r}")
        return value

    if kind == "integer":
        # bool is an int in Python and True would silently become 1 — a cap
        # comparison that passes on a value the caller did not mean.
        if isinstance(value, bool) or not isinstance(value, int):
            raise _refuse_args(name, f"{field!r} must be an integer")
        if "min" in rule and value < rule["min"]:
            raise _refuse_args(
                name, f"{field!r} must be at least {rule['min']} (got {value})")
        if "max" in rule and value > rule["max"]:
            raise _refuse_args(
                name, f"{field!r} is capped at {rule['max']} (got {value})")
        return value

    if kind == "string":
        if not isinstance(value, str):
            raise _refuse_args(name, f"{field!r} must be a string")
        return value

    if kind == "enum":
        if value not in rule["values"]:
            raise _refuse_args(
                name, f"{field!r} must be one of {list(rule['values'])}")
        return value

    if kind == "string_list":
        items = [value] if isinstance(value, str) else value
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            raise _refuse_args(
                name, f"{field!r} must be a string or a list of strings")
        allowed = rule.get("values")
        if allowed:
            bad = sorted(set(items) - set(allowed))
            if bad:
                raise _refuse_args(
                    name, f"{field!r} has unknown value(s) {bad} — allowed: "
                          f"{list(allowed)}")
        return items

    raise DoorRefused(500, {  # pragma: no cover — a typo in _SCHEMAS
        "error": f"schema for {name!r} declares unknown type {kind!r}",
        "reason": "no_schema", "tool": name,
    })


def _check_window(name: str, start: str, end: str, max_days: int) -> None:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise _refuse_args(name, f"the window ends before it starts ({start} to {end})")
    span = (last - first).days
    if span > max_days:
        raise _refuse_args(
            name,
            f"the window is {span} days ({start} to {end}) and this door caps it "
            f"at {max_days}")


# ---------------------------------------------------------------------------
# Mode 1 — the presence check
# ---------------------------------------------------------------------------

# Tool returns in this repo are mostly prose, and a short reply that opens by
# saying there is nothing is the house idiom for an empty result ("No profile
# recorded yet."). It must count as 0 rather than 1. Bounded to short replies
# deliberately: a long answer beginning "No, ..." is a real answer, and the
# failure direction worth avoiding is counting a genuinely empty result as one
# row — which reads as a corpus that exists. (Salvaged from probe.py.)
_EMPTY_PREFIX = re.compile(r"^\s*(no|none|nothing|empty|not\s+\w+)\b", re.I)
_EMPTY_MAX_CHARS = 120


def count_rows(raw: Any) -> tuple[int, str]:
    """
    (count, kind). The count's only job is to separate "something" from
    "nothing" — precision beyond that is the Librarian's problem, not this one.
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


def _probe_dates(entry: dict) -> dict:
    """
    A window ending today, for a source declaring `probe_dates: N`.

    Computed at call time and never written into the manifest literal — the
    standing "do not record a value with a short half-life" rule applied to a
    probe argument: a date in the table is correct on the day it is typed and
    silently wrong the next. (Salvaged from probe.py.)
    """
    days = entry.get("probe_dates")
    if not days:
        return {}
    today = date.today()
    return {"start_date": (today - timedelta(days=int(days))).isoformat(),
            "end_date": today.isoformat()}


def _no_content_note(tool: str, exc: BaseException) -> str:
    """
    What a failed probe is allowed to say.

    A TypeError from a fixed call is a SIGNATURE report — it names parameters,
    not values — and it is the one diagnosis this table cannot do without: the
    D4 round existed because wrong probe arguments made the richest source in
    the system read as empty. So its text is kept.

    Every other exception gets its TYPE and nothing else. `str(exc)` on a YAML
    or JSON error quotes the document that failed to parse, and a document that
    failed to parse is persona data. Mode 1's contract is {state, count, window}
    and NO CONTENT; an exception string is the one place content can cross it
    without anybody deciding that it should.
    """
    if isinstance(exc, TypeError):
        return f"probe arguments do not fit {tool}: {exc}"
    return (f"{tool} raised {type(exc).__name__} — the detail is withheld "
            f"because this door returns no content")


def _handler(tool_name: str) -> Callable | None:
    try:
        from core.orchestrator import register_tools
        _, handlers = register_tools()
        return handlers.get(tool_name)
    except Exception:
        return None


def _presence_record(source_id: str, tool: str, state: str, count: int = 0,
                     window: dict | None = None, note: str = "") -> dict:
    return {
        "mode": "presence",
        "source": source_id,
        "tool": tool,
        "state": state,
        "count": count,
        "window": window,
        "note": note,
    }


def presence(source_id: str, persona: str) -> dict:
    """
    Resolve one manifest source to {state, count, window}. No content, ever.

    FIVE STATES, NEVER TWO — core/trace.py's is_grounded() lesson one layer up.
    "We asked and nothing came back" is a different and far more useful fact than
    "this never retrieves", and collapsing them is what made the old flag
    unreadable:

        needs_tool  the handler is not registered. Nothing was asked.
        live        an outbound feed: registered, answerable at runtime, and
                    with no stored history to count. Never called from here.
        no_data     it ran and returned nothing — a missing FACT.
        data        it ran and returned rows.
        error       it raised. Never folded into no_data, because an error means
                    availability is UNKNOWN rather than false.

    There is no `unaskable` state here and that is not an omission: it needed the
    question's SHAPE as a second argument, and this door takes a source id and
    nothing else. The shape restriction is a manifest property
    (`manifest.answers_shape`) the Librarian already holds, so it is adjudicated
    where the question is, not where the data is.
    """
    entry = M.source(source_id)
    if entry is None:
        raise DoorRefused(400, {
            "error": f"{source_id!r} is not a manifest source",
            "reason": "unknown_source",
            "sources": M.source_ids(),
        })

    tool = entry["tool"]

    # A LIVE FEED IS NOT PROBED. Its availability IS its registration: there is
    # no stored history to count, five of the seven need a real-world argument no
    # code-written default can honestly supply, and a probe would make a real
    # third-party call per question that nothing in section 14 priced.
    if entry.get("live"):
        return _presence_record(
            source_id, tool, state="live",
            note=f"{tool} is a live feed: registered and answerable at runtime, "
                 f"with no stored history to probe. It is not readable through "
                 f"mode 2 — no outbound tool sits behind a door.")

    handler = _handler(tool)
    if handler is None:
        return _presence_record(
            source_id, tool, state="needs_tool",
            note=f"{tool} is not registered on this server")

    args = {**(entry.get("probe") or {}), **_probe_dates(entry)}
    args = {k: v for k, v in args.items() if v not in ("", None)}
    window = None
    if entry.get("probe_dates"):
        window = {"start": args.get("start_date"), "end": args.get("end_date"),
                  "days": int(entry["probe_dates"])}

    try:
        from core.persona import persona_scope
        with persona_scope(persona):
            raw = handler(**args)
    except Exception as exc:
        return _presence_record(source_id, tool, state="error", window=window,
                                note=_no_content_note(tool, exc))

    count, _kind = count_rows(raw)
    return _presence_record(
        source_id, tool,
        state="data" if count > 0 else "no_data",
        count=count, window=window)


# ---------------------------------------------------------------------------
# Mode 2 — a research read
# ---------------------------------------------------------------------------

def _jsonable(raw: Any) -> Any:
    """Whatever the handler returned, in a form the response can carry."""
    try:
        json.dumps(raw)
        return raw
    except (TypeError, ValueError):
        return str(raw)


def research_read(name: str, args: dict | None, persona: str) -> dict:
    """
    Run an allowlisted read tool for one persona and return its result.

    The order of the checks is load-bearing. A live feed is refused BEFORE the
    read-set check so the refusal can say which rule it broke — "this leaves the
    machine" and "this is not a read tool you may call" are different findings,
    and a Librarian that cannot tell them apart will re-try the first as if it
    were the second.
    """
    if not isinstance(name, str) or not name:
        raise DoorRefused(400, {"error": "name is required", "reason": "no_name"})

    outbound = live_feed_tools()
    if name in outbound:
        raise DoorRefused(403, {
            "error": f"{name!r} is a live feed — no outbound tool sits behind a "
                     f"door, so content read here can never compose a call that "
                     f"leaves the machine",
            "reason": "live_feed",
            "live_feeds": sorted(outbound),
        })

    if name not in READ_SET:
        raise DoorRefused(403, {
            "error": f"{name!r} is not in the Librarian's read set",
            "reason": "not_in_read_set",
            "read_set": sorted(READ_SET),
        })

    cleaned = validate_args(name, args)

    handler = _handler(name)
    if handler is None:
        # NOT a 403 and NOT a 500. The name is allowed; the tool does not exist
        # here yet. The read set is deliberately written ahead of the tools
        # (section 6: "once built"), so this refusal is the mechanism working
        # rather than a fault — and `pending_tools()` derives the current list
        # from exactly this lookup.
        raise DoorRefused(501, {
            "error": f"{name!r} is in the read set but is not registered on this "
                     f"server",
            "reason": "needs_tool",
            "tool": name,
            # True by construction — reaching this branch IS the handler being
            # absent. It used to read `name in PENDING_TOOLS`, a hardcoded list
            # that could disagree with the lookup three lines above it, and did
            # the afternoon phase D landed the two tools on it.
            "pending_build": True,
        })

    try:
        from core.persona import persona_scope
        with persona_scope(persona):
            raw = handler(**cleaned)
    except TypeError as exc:
        # The schema and the handler's signature have drifted apart. Reported as
        # the defect it is rather than as a 500, which is the D4 lesson: a call
        # with a wrong argument must never read as "the source is empty".
        raise DoorRefused(400, {
            "error": f"arguments do not fit {name}: {exc}",
            "reason": "signature_mismatch",
            "tool": name,
            "schema": public_schema(name),
        })

    return {
        "mode": "read",
        "name": name,
        "persona": persona,
        "args": cleaned,
        "result": _jsonable(raw),
    }


# ---------------------------------------------------------------------------
# The structural invariant
# ---------------------------------------------------------------------------

def _assert_no_outbound_door() -> None:
    """
    No outbound tool may sit behind a door, and no name may sit in the allowlist
    without a schema.

    Checked at import, so the failure is a module that will not load rather than
    a door that quietly serves an outbound tool. core/server.py imports this
    module inside the endpoint precisely so that this fails the DOOR and not the
    server — a user's session does not stop because Build's allowlist is wrong.
    """
    outbound = READ_SET & live_feed_tools()
    if outbound:
        raise RuntimeError(
            f"core/build/doors.py: {sorted(outbound)} are outbound tools and are "
            f"in READ_SET. No outbound tool sits behind a door (plan section 6) "
            f"— remove the line rather than relaxing this check.")
    unschemad = READ_SET - set(_SCHEMAS)
    if unschemad:
        raise RuntimeError(
            f"core/build/doors.py: {sorted(unschemad)} are in READ_SET with no "
            f"schema. Arguments are validated server-side against a per-tool "
            f"schema; a name without one has no validation at all.")


_assert_no_outbound_door()
