"""
core/build/manifest.py — what exists, as IDS. Never as values.

Plan: archive/plans/build_vertical_plan_2026-09-24.md sections 3 (N4), 6.

THE CALL TABLE BELOW IS SALVAGED BY COPY (section 10, finding 8 — it was never
in probe.py). Every argument repair the D4 round bought is in its comments and
must survive: `get_log_window`'s start/end window, `search_memory`'s required
`query`, `read_archive`'s required category, `read_intake_queue`'s domain,
`read_agent_config`'s `agent_name`, `read_email`'s `count`, and the seven
`live: True` rows that are deliberately never probed. Losing one of these is
the exact defect class three review rounds were spent finding: a probe with a
wrong argument raises TypeError, records `state: error`, and every question
naming that source reaches the Librarian as "the code could not read it" — with
the richest source in the system reading as empty.

WHOSE INPUT THIS IS, AND WHY THAT CHANGED. Under v3 the manifest was INQUIRY's
input and this file was the privacy boundary for the whole vertical. Ruling 5
moved it: Inquiry now works in a vacuum and never sees this at all — the point
is to find where existing data is inadequate, which a model shown the corpus
first cannot do. The manifest is the LIBRARIAN's input, and the Librarian is
already reading the corpus through the doors.

THE CONTENT-FREE RULE SURVIVES THE MOVE, unchanged and still enforced by
tests/test_build_manifest.py's grep of every profile value. It is no longer the
privacy boundary — ruling 10 is — but it is still what makes the manifest safe
to render into a prompt, and still what makes `_SOURCES` a table of calls rather
than a table of answers.

THE RULE: the manifest names SOURCES, CAPABILITIES and POLICIES. It never
carries a value read from any of them. Every description here is a literal
written in this file — none is drawn from persona data, and none is generated.

WHERE THE PRESENCE CHECK RUNS. On the VM, behind
`GET /monitor/tool?presence=<source_id>` (phase B). It takes a SOURCE ID, not
arguments: the server runs the fixed call from this table and returns
{state, count, window}, no content. THE MODEL NAMES A SOURCE AND CODE CHOOSES
THE CALL — that is the injection answer, and it is why the arguments live here
as literals rather than anywhere a model can reach.

Three sections, three jobs:

  sources[]       what the presence check can resolve, and whether its tool is
                  live. A source whose handler is not registered is
                  `available: false`, which is how a missing-tool finding gets
                  DERIVED rather than asserted.
  capabilities[]  every specialist that already exists. `disposition: new`
                  must name one of these and say why it does not cover the
                  request, which is what stops `new` being the default answer.
  policies[]      standing decisions, with their applies_to. The Librarian
                  resolves against these when confirming a `triage` depth.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent.parent

# ---------------------------------------------------------------------------
# The source table.
#
# `tool` is the registered handler the presence check calls. `probe` is the
# FIXED call the door issues — arguments included — so that resolving a source
# never depends on anything a model wrote.
#
# Every entry is inside the read set (plan section 6). Adding a row here does
# not grant anything: the grant allowlist lives in gates.py, and a source the
# gate refuses is still refused however this table reads.
#
# `answers` (OPTIONAL) narrows which SHAPE of question a source can serve. Omit
# it and the source answers any shape.
#
# It exists because "the tool is registered" and "the tool can answer this" are
# different facts, and the gap between them is invisible. `read_journal` is
# registered and takes ONE DATE, so the journal reads as available while being
# useless for "how does Mike talk about work stress" across 61 files. Without
# this field that question probes, returns one day or nothing, and settles as
# `no_data` — "there is nothing recorded" — when the truth is "this tool cannot
# be asked that." Found 2026-09-18 by the worked Inquiry run, which named the
# journal as a source for an intent question and got no warning at all.
#
# An UNASKABLE question must not look like an UNANSWERED one: the first is a
# missing tool and the second is a missing fact. In the inventory those are
# different verdicts — `absent` against `inadequate` — and this is what tells
# them apart.
# ---------------------------------------------------------------------------

_SOURCES: tuple[dict[str, Any], ...] = (
    # `start_date`/`end_date`, NOT `days` — tools/pattern_miner.get_log_window
    # takes a window, not a length. The `{"days": 14}` this carried fitted no
    # signature, so every probe of the primary corpus raised TypeError and
    # recorded `state: error`: `data_available: False` on every question naming
    # `log`, each one reaching the Librarian as "the code could not read the
    # logs", and no log-backed single-point question ever settling by data.
    # Section 3 calls N3 the highest-value node; this made it blind to the
    # richest source in the system. `_probe_dates()` fills the window at call
    # time, because a date written into a literal goes stale overnight.
    {"id": "log", "tool": "get_log_window", "kind": "behavioural",
     "description": "daily logs — what was done, eaten, felt, logged",
     "probe": {"start_date": "", "end_date": ""},
     "probe_dates": 14},
    {"id": "journal", "tool": "read_journal", "kind": "behavioural",
     "description": "the Diarist's narrative record, one file per day",
     "probe": {"entry_date": ""},
     "answers": ["single_point"]},
    {"id": "journal_range", "tool": "read_journal_range", "kind": "behavioural",
     "description": "journal entries across a date range, condensed",
     "probe": {"start": "", "end": "", "max_entries": 40}},
    {"id": "conversations", "tool": "search_conversations", "kind": "behavioural",
     "description": "verbatim conversation turns, searchable",
     "probe": {"query": "", "k": 20}},
    # A `query` is REQUIRED by search_memory and was absent, so every probe of
    # the index raised TypeError. The probe word is code-written and deliberately
    # generic: this call asks "does the index return anything at all", not
    # anything about the question — a question-derived query here would put model
    # text into a tool call, which is the one thing section 13.3 forbids. The
    # condenser narrows it through `overrides` when a real search is wanted.
    {"id": "memory", "tool": "search_memory", "kind": "behavioural",
     "description": "the FAISS index over logs and journal entries",
     "probe": {"query": "day", "k": 8}},
    {"id": "wisdom", "tool": "read_wisdom", "kind": "single_point",
     "description": "standing facts and patterns, by domain",
     "probe": {}},
    {"id": "goals", "tool": "read_goals", "kind": "single_point",
     "description": "the goal hierarchy — tiers 1 to 3",
     "probe": {}},
    {"id": "profile", "tool": "read_profile", "kind": "single_point",
     "description": "stable biographical facts",
     "probe": {"field": ""}},
    {"id": "baselines", "tool": "read_baseline_periods", "kind": "behavioural",
     "description": "aspirational baselines and scored periods",
     "probe": {}},
    {"id": "insights", "tool": "read_recent_insights", "kind": "behavioural",
     "description": "Pattern Miner reports",
     "probe": {}},
    # read_archive(category) takes a required category and had none. "books" is
    # the category tools/diarist.py's own docstring names first; the probe only
    # has to establish whether the archive answers at all.
    {"id": "archive", "tool": "read_archive", "kind": "behavioural",
     "description": "archived records, with their merged_into pointers",
     "probe": {"category": "books"}},
    # Same defect as `log`: read_calendar takes start_date/end_date, not `days`.
    {"id": "calendar", "tool": "read_calendar", "kind": "single_point",
     "description": "calendar entries over a window",
     "probe": {"start_date": "", "end_date": ""},
     "probe_dates": 14},
    {"id": "schedules", "tool": "list_schedules", "kind": "single_point",
     "description": "scheduled prompts and their cadence",
     "probe": {}},
    {"id": "obligations", "tool": "list_obligations", "kind": "single_point",
     "description": "open obligations and what is due",
     "probe": {}},
    {"id": "contacts", "tool": "list_contacts", "kind": "single_point",
     "description": "the CRM — who the user knows",
     "probe": {}},
    # `count`, not `limit` — read_email(count, unread_only, folder).
    {"id": "email", "tool": "read_email", "kind": "behavioural",
     "description": "recent mail",
     "probe": {"count": 20}},
    {"id": "intake_queue", "tool": "read_intake_queue", "kind": "behavioural",
     "description": "classified inbound items awaiting disposition",
     # read_intake_queue(domain) requires one; "logistics" is the domain
     # every persona has, and the probe only asks whether the queue answers.
     "probe": {"domain": "logistics"}},
    {"id": "context_tracker", "tool": "read_context_tracker", "kind": "single_point",
     "description": "open threads, clinical threads, carried state",
     "probe": {}},
    # read_agent_config(agent_name) requires one; the Coordinator exists in
    # every deployment, so the probe can always be issued. (`agent` was not a
    # parameter of anything.)
    {"id": "agent_config", "tool": "read_agent_config", "kind": "single_point",
     "description": "the per-persona data store an agent reads at runtime",
     "probe": {"agent_name": "coordinator"}},

    # ---- LIVE FEEDS: `live: True`, and deliberately NOT probed -------------
    #
    # These seven are the outbound reads of section 6.3. Probing them is wrong in
    # three separate ways, and the first is the one that costs money:
    #
    #   1. A probe would make a REAL third-party API call — seven of them per
    #      job, every job, during Inquiry. Nothing in section 14 priced that, and
    #      an N3 that quietly bills an external vendor per question is the
    #      "unseen cost" class CLAUDE.md § Costs names.
    #   2. Five of them REQUIRE a real-world argument — a flight number, an
    #      origin and destination, a city, a line list, a place description.
    #      There is no honest code-written default; inventing one probes nothing
    #      and `find_places` would send the invented string outbound.
    #   3. The question a probe answers — "is there a corpus here?" — has no
    #      meaning for a live feed. There is no stored history to count. Its
    #      answer exists only at the moment the capability asks.
    #
    # So availability for these IS registration, and their evidence row says
    # exactly that: the tool is live, there is nothing to count, and the
    # Librarian adjudicates rather than settling on a row count. This is the
    # same distinction the fourth probe state was added for on 2026-09-18 —
    # "registered" and "can answer this" are different facts — one step further:
    # "registered" and "has a corpus" are different facts too.
    {"id": "weather", "tool": "get_weather", "kind": "single_point",
     "description": "live weather, including days since rain", "live": True},
    {"id": "environment", "tool": "get_environmental_snapshot", "kind": "single_point",
     "description": "ambient environmental conditions", "live": True},
    {"id": "transit_tfl", "tool": "get_tfl_status", "kind": "single_point",
     "description": "London transit status", "live": True},
    {"id": "regional_transit", "tool": "get_regional_transit_info", "kind": "single_point",
     "description": "regional transit information", "live": True},
    {"id": "flights", "tool": "get_flight_status", "kind": "single_point",
     "description": "flight status by number", "live": True},
    {"id": "travel_time", "tool": "get_travel_time", "kind": "single_point",
     "description": "door-to-door travel time between two points", "live": True},
    {"id": "places", "tool": "find_places", "kind": "single_point",
     "description": "place and venue lookup from a description", "live": True},
)

# The literal "user" is always a legal candidate source and is not a row here:
# it resolves to an interview item, never to a probe.
USER_SOURCE = "user"


class ManifestError(RuntimeError):
    """The manifest could not be assembled."""


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _registered_tools() -> set[str]:
    """
    Handler names the live register_tools() actually returns.

    This is read from the running system rather than from a list here, so a
    source whose tool has not been built yet reports `available: false` on its
    own evidence. That is what makes a missing-tool finding derived rather than
    asserted — the two section 9 tools (search_conversations,
    read_journal_range) are phase D work and are expected to be absent until
    then; that is the mechanism working, not a failure.
    """
    try:
        from core.orchestrator import register_tools
        _, handlers = register_tools()
        return set(handlers.keys())
    except Exception:
        return set()


def sources(registered: set[str] | None = None) -> list[dict]:
    live = _registered_tools() if registered is None else registered
    return [
        {**source, "available": source["tool"] in live}
        for source in _SOURCES
    ]


def source_ids() -> list[str]:
    """Every source id, available or not. What candidate_sources validates against."""
    return [source["id"] for source in _SOURCES]


def answers_shape(source_id: str, data_kind: str) -> bool:
    """
    Can this source be ASKED a question of this shape at all?

    A source with no `answers` restriction serves any shape. One that declares a
    restriction serves only the shapes it lists — so `journal` (single-date
    `read_journal`) cannot serve a `behavioural` question, and saying so is the
    difference between "there is nothing recorded" and "this cannot be asked".
    """
    entry = source(source_id)
    if entry is None:
        return False
    allowed = entry.get("answers")
    return True if not allowed else str(data_kind or "") in allowed


def unaskable(source_ids_wanted: list[str], data_kind: str) -> list[str]:
    """Named sources whose tool exists but cannot serve this question's shape."""
    return [
        s for s in source_ids_wanted
        if source(s) is not None and not answers_shape(s, data_kind)
    ]


def source(source_id: str) -> dict | None:
    for entry in _SOURCES:
        if entry["id"] == source_id:
            return dict(entry)
    return None


def capabilities() -> list[dict]:
    """
    Every specialist that already exists — NAMES ONLY.

    Read from config/agents/*.md stems rather than from the routing files,
    because the routing files are not the complete set: time_director has an
    agent file and no routing entry. A `new` disposition must be checked
    against what exists, and a capability missing from this list would let
    `new` pass by omission.
    """
    agents_dir = _ROOT / "config" / "agents"
    found: list[dict] = []
    if agents_dir.is_dir():
        for path in sorted(agents_dir.glob("*.md")):
            found.append({"id": path.stem, "origin": "tracked"})
    return found


def capability_names() -> set[str]:
    return {entry["id"] for entry in capabilities()}


def policies(persona: str | None = None) -> list[dict]:
    """
    Standing policies, as id + domain + applies_to.

    `applies_to` is a policy's own scope statement, authored with the user at
    build time — not persona data read from the corpus — so it is inside the
    content-free rule. It is here because the Librarian resolves against
    policies before deciding a question needs data, and it cannot do that
    without knowing what each policy claims to cover.

    Read from config/build/policies/{persona}/ — tracked, in the diff (section 4).
    Any failure returns [] rather than raising: the manifest's source and
    capability sections are static and useful with no persona bound, and a
    caller that needs policies is one that already resolved a persona.
    """
    try:
        from core.build.policy import list_policies
        return [
            {"id": p.get("id", ""), "domain": p.get("domain", ""),
             "applies_to": p.get("applies_to", ""),
             "retires_question_classes": p.get("retires_question_classes", [])}
            for p in list_policies(persona)
        ]
    except Exception:
        return []


def build(persona: str | None = None) -> dict:
    """The whole manifest. Content-free by construction."""
    resolved = sources()
    payload = {
        "schema": "manifest/1",
        "sources": resolved,
        "capabilities": capabilities(),
        "policies": policies(persona),
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload


def fingerprint(payload: dict) -> str:
    """
    Identifies the substrate a Question Set was written against.

    Covers source ids AND their availability, plus capability and policy ids —
    so a tool landing, a capability being added, or a policy being written all
    invalidate a stale question set. It deliberately does NOT cover
    descriptions: rewording one does not change what can be answered.
    """
    material = {
        "sources": sorted(
            (s["id"], bool(s.get("available"))) for s in payload.get("sources", [])
        ),
        "capabilities": sorted(c["id"] for c in payload.get("capabilities", [])),
        "policies": sorted(p["id"] for p in payload.get("policies", [])),
    }
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def unavailable(persona: str | None = None) -> list[str]:
    """
    Source ids whose tool is not registered — the `needs_tool` candidates.

    Expected to be non-empty until phase D: search_conversations and
    read_journal_range are ordinary development (`/fix`). The known Librarian
    gaps are a designed state, not a failure.
    """
    return [s["id"] for s in sources() if not s["available"]]
