"""
core/build/manifest.py — what exists, as IDS. Never as values.

N1. The manifest is what Inquiry is allowed to see of the corpus, and it is the
privacy boundary for the whole vertical: Inquiry runs before any probe, so
anything the manifest carries reaches a model that has not yet been told it
needs it.

THE RULE: the manifest names SOURCES, CAPABILITIES and POLICIES. It never
carries a value read from any of them. Every description here is a literal
written in this file — none is drawn from persona data, and none is generated.
tests/test_build_manifest.py enforces this by grepping the rendered manifest
for every string value in profile.yaml and failing on any hit.

WHY THIS IS THE RIGHT BOUNDARY. `candidate_sources` on a Question Set is
validated against `source_ids()`, and probe.py maps an id to a FIXED,
code-written call. So the model names a source and CODE CHOOSES THE CALL. That
is the answer to "the probe runs read tools with model-chosen arguments" — it
does not.

Three sections, three jobs:

  sources[]       what the probe can resolve, and whether its tool is live.
                  A source whose handler is not registered is `available:
                  false`, which is how `status: needs_tool` gets DERIVED rather
                  than asserted.
  capabilities[]  every specialist that already exists. `disposition: new`
                  must name one of these and say why it does not cover the
                  request, which is what stops `new` being the default answer.
  policies[]      standing decisions, with their applies_to. settle.py resolves
                  against these BEFORE touching data, which is the mechanism
                  behind questions arriving pre-answered.
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
# `tool` is the registered handler the probe calls. `probe` is the FIXED call
# probe.py issues — arguments included — so that resolving a source never
# depends on anything a model wrote.
#
# Every entry is inside the read set (plan section 6.3). Adding a row here does
# not grant anything: the grant allowlist lives in the writer, and a source the
# writer refuses is still refused however this table reads.
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
# This is the same class of collapse the three probe states exist to prevent,
# one level further in: an UNASKABLE question must not look like an UNANSWERED
# one, because the first is a missing tool and the second is a missing fact.
# ---------------------------------------------------------------------------

_SOURCES: tuple[dict[str, Any], ...] = (
    {"id": "log", "tool": "get_log_window", "kind": "behavioural",
     "description": "daily logs — what was done, eaten, felt, logged",
     "probe": {"days": 14}},
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
    {"id": "memory", "tool": "search_memory", "kind": "behavioural",
     "description": "the FAISS index over logs and journal entries",
     "probe": {"k": 8}},
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
    {"id": "archive", "tool": "read_archive", "kind": "behavioural",
     "description": "archived records, with their merged_into pointers",
     "probe": {}},
    {"id": "calendar", "tool": "read_calendar", "kind": "single_point",
     "description": "calendar entries over a window",
     "probe": {"days": 14}},
    {"id": "schedules", "tool": "list_schedules", "kind": "single_point",
     "description": "scheduled prompts and their cadence",
     "probe": {}},
    {"id": "obligations", "tool": "list_obligations", "kind": "single_point",
     "description": "open obligations and what is due",
     "probe": {}},
    {"id": "contacts", "tool": "list_contacts", "kind": "single_point",
     "description": "the CRM — who the user knows",
     "probe": {}},
    {"id": "email", "tool": "read_email", "kind": "behavioural",
     "description": "recent mail",
     "probe": {"limit": 20}},
    {"id": "intake_queue", "tool": "read_intake_queue", "kind": "behavioural",
     "description": "classified inbound items awaiting disposition",
     "probe": {}},
    {"id": "context_tracker", "tool": "read_context_tracker", "kind": "single_point",
     "description": "open threads, clinical threads, carried state",
     "probe": {}},
    {"id": "agent_config", "tool": "read_agent_config", "kind": "single_point",
     "description": "the per-persona data store an agent reads at runtime",
     "probe": {"agent": ""}},
    {"id": "weather", "tool": "get_weather", "kind": "single_point",
     "description": "live weather, including days since rain",
     "probe": {}},
    {"id": "environment", "tool": "get_environmental_snapshot", "kind": "single_point",
     "description": "ambient environmental conditions",
     "probe": {}},
    {"id": "transit_tfl", "tool": "get_tfl_status", "kind": "single_point",
     "description": "London transit status",
     "probe": {}},
    {"id": "regional_transit", "tool": "get_regional_transit_info", "kind": "single_point",
     "description": "regional transit information",
     "probe": {}},
    {"id": "flights", "tool": "get_flight_status", "kind": "single_point",
     "description": "flight status by number",
     "probe": {}},
    {"id": "travel_time", "tool": "get_travel_time", "kind": "single_point",
     "description": "door-to-door travel time between two points",
     "probe": {}},
    {"id": "places", "tool": "find_places", "kind": "single_point",
     "description": "place and venue lookup from a description",
     "probe": {}},
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
    own evidence. That is what makes `status: needs_tool` derived rather than
    asserted — the two section 9 briefs (search_conversations,
    read_journal_range) are expected to be absent on run 1, and that is the
    mechanism working, not a failure.
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
    content-free rule. It is here because settle.py resolves against policies
    BEFORE touching data, and it cannot do that without knowing what each
    policy claims to cover.

    A PersonaError returns [] rather than raising: the manifest's source and
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

    Expected to be non-empty on run 1: search_conversations and
    read_journal_range are section 9 briefs Mike builds on the Mac. The known
    Librarian gaps are a designed state, not a failure.
    """
    return [s["id"] for s in sources() if not s["available"]]
