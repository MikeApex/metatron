"""
tools/calendar_audit.py — periodic sweep for calendar entries duplicated without purpose.

Runs as a `function:` scheduler job — no model tokens, interval/string arithmetic
over calendar data, same class as tools/rule_audit.py and tools/ambient.py's
refresh job.

WHY A SWEEP ON TOP OF THE WRITE-TIME CHECK
-------------------------------------------
The write-time check (check_calendar_conflicts, wired into write_calendar_event
and update_calendar_event — tools/scheduling.py) only ever sees one write at a
time, compared against what already existed at that moment. It cannot catch:
  - duplicates already on the calendar before this build shipped (2026-08-05,
    including the original Jonas triplication itself — the write-time check
    guards against a fourth, it never removes the first three);
  - anything written through a path that bypasses the check (a direct CalDAV
    client, a future integration that doesn't route through write_calendar_event);
  - drift that accumulates for reasons the write-time check has no view of —
    an event edited outside this system, or a recurring series whose pattern
    changed underneath an old one-off that no longer matches it.

Same relationship as tools/rule_audit.py to the write-time check in
core/rule_classes.py: the write-time check catches the same-second case, the
sweep catches everything else, because it's the only one of the two that ever
looks at the whole picture at once.

WHAT COUNTS AS A DUPLICATE HERE, AND WHAT DOESN'T
---------------------------------------------------
Reuses the exact matching logic from tools/scheduling.py (title similarity,
shared significant words, shared attendees) rather than reimplementing it —
applied pairwise across a date window instead of one candidate against history.
Two occurrences of the *same* identified recurring series are explicitly
excluded: that repetition is what the user asked for, not the failure this
audit exists to catch. "Duplicates without purpose" means two entries that look
like the same commitment got created independently, not a series doing what a
series does.

Findings go into the quality-event stream as CALENDAR_DUPLICATE, reaching
DEV_BACKLOG.md through the existing sync path (scripts/sync_dev_backlog.py) —
same route as RULE_CONFLICT. Each pair is reported once (seen-set keyed on the
sorted uid pair) and never re-reported daily — a daily repeat of the same
finding trains the reader to ignore it, which is the exact failure the
"raise a thing once" rule exists to prevent.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path

from core.persona import persona_data_dir, resolve_persona
from tools.caldav import _query_events
from tools.logger import write_quality_event
from tools.scheduling import (
    _TITLE_SIMILARITY_THRESHOLD,
    _attendee_overlap,
    _overlaps,
    _parse_dt,
    _shared_significant_tokens,
    _title_similarity,
)

# How far back and ahead the sweep looks. Bounded deliberately — this runs
# daily, and an unbounded full-history scan gets slower every day the calendar
# grows. Lookback catches a just-passed duplicate before it's forgotten;
# lookahead covers the horizon a user actually reasons about.
_LOOKBACK_DAYS = 7
_LOOKAHEAD_DAYS = 60


def _seen_path(persona: str) -> Path:
    return persona_data_dir(persona) / "logs" / ".calendar_dedup_seen"


def _load_seen(persona: str) -> set[str]:
    p = _seen_path(persona)
    if not p.exists():
        return set()
    return {ln.strip() for ln in p.read_text().splitlines() if ln.strip()}


def _record_seen(persona: str, keys: set[str]) -> None:
    p = _seen_path(persona)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        for k in sorted(keys):
            f.write(k + "\n")
    p.chmod(0o600)


def _pair_key(uid_a: str, uid_b: str) -> str:
    # Keyed on the pair, not either uid alone — an event can legitimately be
    # near-duplicate-adjacent to more than one other event without every such
    # pair being the same finding.
    return hashlib.sha256("|".join(sorted([uid_a, uid_b])).encode()).hexdigest()[:16]


def find_calendar_duplicates(persona: str | None = None) -> list[dict]:
    """
    Sweep the near-term calendar for pairs of events that look like accidental
    duplicates rather than intentional recurrence.

    A pair is flagged when both are time-close (overlapping, or within 2 hours
    of each other) AND share enough identity signal (title similarity, a
    significant word, or an attendee) — the same evidence rules as the
    real-time check, just run pairwise across a window instead of one
    candidate against history. Pairs sharing an identical, matching RRULE are
    excluded outright: that's a recurring series working as intended.

    Returns a list of finding dicts. Evidence, not a verdict — same caveat as
    check_calendar_conflicts: a human/agent still decides whether a flagged
    pair is actually the same commitment before merging or deleting either one.
    """
    resolved = resolve_persona(persona)
    start = (date.today() - timedelta(days=_LOOKBACK_DAYS)).isoformat()
    end = (date.today() + timedelta(days=_LOOKAHEAD_DAYS)).isoformat()

    raw = _query_events(start, end, persona=resolved)
    if "error" in raw:
        return []

    events = raw["events"]
    findings = []

    for i, a in enumerate(events):
        a_start, a_end = _parse_dt(a.get("start", "")), _parse_dt(a.get("end", ""))
        if a_start is None or a_end is None:
            continue
        for b in events[i + 1:]:
            if a.get("recurrence") and a.get("recurrence") == b.get("recurrence"):
                continue
            b_start, b_end = _parse_dt(b.get("start", "")), _parse_dt(b.get("end", ""))
            if b_start is None or b_end is None:
                continue

            is_overlap = _overlaps(a_start, a_end, b_start, b_end)
            time_close = is_overlap or abs((b_start - a_start).total_seconds()) <= 2 * 3600
            if not time_close:
                continue

            sim = _title_similarity(a["title"], b["title"])
            shared_attendees = _attendee_overlap(a.get("attendees", []), b.get("attendees", []))
            shared_tokens = _shared_significant_tokens(a["title"], b["title"])
            if not (sim >= _TITLE_SIMILARITY_THRESHOLD or shared_attendees or shared_tokens):
                continue

            findings.append({
                "uids": [a["uid"], b["uid"]],
                "titles": [a["title"], b["title"]],
                "starts": [a["start"], b["start"]],
                "title_similarity": round(sim, 2),
                "shared_attendees": shared_attendees,
                "shared_words": shared_tokens,
            })

    return findings


def _detail(f: dict) -> str:
    return (
        f"Possible duplicate calendar entries: '{f['titles'][0]}' ({f['starts'][0]}, "
        f"uid={f['uids'][0]}) and '{f['titles'][1]}' ({f['starts'][1]}, uid={f['uids'][1]}). "
        f"title_similarity={f['title_similarity']}, shared_attendees={f['shared_attendees']}, "
        f"shared_words={f['shared_words']}. Resolve with update_calendar_event (keep one, "
        f"correct it) or delete_calendar_event (remove the extra) once confirmed — this is "
        f"evidence, not a verdict; check both events before acting."
    )


def audit_calendar_duplicates() -> str:
    """
    Scheduler entry point. Takes no arguments; persona comes from the scope.

    Never raises on a calendar/config problem: this runs unattended in a
    daemon, and a tidiness check that crash-loops the scheduler would cost far
    more than the duplication it's looking for (see tools/rule_audit.py for
    the same reasoning).
    """
    try:
        persona = resolve_persona()
        findings = find_calendar_duplicates(persona)
    except Exception as e:
        return f"calendar dedup audit skipped: {e}"

    seen = _load_seen(persona)
    fresh = [f for f in findings if _pair_key(*f["uids"]) not in seen]

    for f in fresh:
        write_quality_event(
            event_type="CALENDAR_DUPLICATE",
            source_agent="calendar_audit",
            detail=_detail(f),
            session_id="calendar_audit",
        )
    if fresh:
        _record_seen(persona, {_pair_key(*f["uids"]) for f in fresh})

    return (f"{len(findings)} possible duplicate pair(s) present, {len(fresh)} newly reported"
            if findings else "no calendar duplicates found")


if __name__ == "__main__":  # manual run: python3 -m tools.calendar_audit <persona>
    import sys
    from core.persona import persona_scope

    who = sys.argv[1] if len(sys.argv) > 1 else "mike"
    with persona_scope(who):
        found = find_calendar_duplicates(who)
        for f in found:
            print(_detail(f) + "\n")
        print(f"{len(found)} finding(s).")
