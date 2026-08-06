"""
tools/scheduling.py — calendar conflict detection.

Gives Logistics a deterministic read of "what's already true about the schedule"
before it commits a write, instead of relying on the agent to independently recall
or notice conflicts. Code owns the facts (interval overlap, exact duplicates);
the agent owns judgment about what those facts mean (is this the same meeting,
is this a legitimate second meeting with the same person, does this break an
existing dependency).

Kept separate from tools/caldav.py (CalDAV protocol only) and tools/crm.py
(contacts only) so this logic — and only this logic — decides what counts as a
conflict. CalDAV querying is reused via tools.caldav._query_events rather than
reimplemented here.

Similarity scoring uses stdlib difflib rather than sentence-transformer
embeddings deliberately: this runs on every calendar write, not as an occasional
sweep (contrast tools/wisdom.py's find_duplicate_wisdom, which loads an embedding
model but is invoked on demand). A heavy model load on the hot path would undo
the latency work the rest of this system has done to keep specialist turns fast.
"""

import difflib
import json
from datetime import datetime, timedelta

from tools.caldav import _query_events
from tools.crm import search_contacts
from tools.untrusted import UNTRUSTED_CONTENT_INSTRUCTION, wrap_untrusted

# Near-duplicate candidate: title similarity at or above this is worth surfacing.
# Not a duplicate verdict — see the wisdom-dedup precedent in tools/wisdom.py,
# whose own documented testing found a fixed threshold still ranks the wrong
# partner some of the time. The agent gets the score, not just a boolean.
_TITLE_SIMILARITY_THRESHOLD = 0.6

# Window (days) searched for near-duplicate candidates and recurring-series
# matches around the requested event. Bounded deliberately — this runs on every
# write, so it stays cheap; a full week/month scan is something the agent asks
# for explicitly via this same function when it needs that reach.
_DEFAULT_CANDIDATE_WINDOW_DAYS = 3

# Two same-day events with different, non-empty locations and a gap under this
# many minutes get flagged as a tight transition. No real travel-time estimate
# exists yet (needs a maps/geocoding integration — deferred, see DEV_BACKLOG.md);
# this is a stub that only says "these two places probably aren't the same place
# and you don't have much time between them."
_TIGHT_TRANSITION_MINUTES = 30


_STOPWORDS = {"a", "an", "the", "with", "and", "or", "for", "to", "of", "in", "on", "at", "up", "is", "this", "that", "from"}


def _normalize_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def _title_similarity(a: str, b: str) -> float:
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def _significant_tokens(title: str) -> set[str]:
    """Words worth treating as a name/topic match on their own — 3+ characters,
    not a filler word. "1:1" and "with" don't count; "Jonas" does."""
    words = _normalize_title(title).replace(":", " ").replace(",", " ").split()
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def _shared_significant_tokens(a: str, b: str) -> list[str]:
    """
    Full-title similarity (_title_similarity) misses "Jonas 1:1" vs. "catch up
    with Jonas" — same person, completely different phrasing, sequence ratio
    ~0.36 and word-Jaccard ~0.2, both well under threshold. But the load-bearing
    word (the name) matches exactly, which is meaningful on its own even when
    nothing else does. Checked as a separate signal rather than folded into
    _title_similarity so the evidence returned to the agent stays legible —
    "shared word: jonas" is a clearer thing to reason about than a single
    blended score that could mean several different things.
    """
    return sorted(_significant_tokens(a) & _significant_tokens(b))


def _parse_dt(value: str) -> datetime | None:
    """Parse an ISO datetime or date string. Returns None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value + "T00:00:00")
        except ValueError:
            return None


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Strict interval overlap. Touching endpoints (a.end == b.start) are NOT an
    overlap — DTEND is exclusive per RFC 5545, so back-to-back events are normal,
    not a conflict."""
    return a_start < b_end and a_end > b_start


def _attendee_overlap(a: list[str], b: list[str]) -> list[str]:
    a_norm = {x.lower().strip() for x in (a or [])}
    b_norm = {x.lower().strip() for x in (b or [])}
    return sorted(a_norm & b_norm)


def _resolve_attendees(attendees: list[str] | None) -> list[dict]:
    """Cross-reference attendee names against CRM contacts. Best-effort — an
    attendee with no CRM match is returned as an unresolved name, not an error;
    plenty of legitimate meetings are with people who aren't in the CRM yet."""
    resolved = []
    for name in attendees or []:
        match = None
        try:
            raw = search_contacts(name)
            candidates = json.loads(raw) if raw and not raw.startswith("Error") else []
            if candidates:
                match = candidates[0].get("id")
        except Exception:
            match = None
        resolved.append({"name": name, "contact_id": match})
    return resolved


def _compute_conflicts(
    start: str,
    end: str,
    title: str = "",
    attendees: list[str] | None = None,
    location: str = "",
    exclude_uid: str = "",
) -> dict:
    """
    Unwrapped conflict computation — for internal callers (write_calendar_event,
    update_calendar_event) that need to programmatically branch on the result.
    See check_calendar_conflicts for the LLM-facing, wrapped version and full
    field documentation.

    On a CalDAV query failure, returns {"check_error": "..."} and nothing else —
    callers must decide how to proceed without a check.
    """
    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)
    if start_dt is None or end_dt is None:
        return {"check_error": f"Could not parse start/end for conflict check ({start!r}, {end!r})."}

    query_start = (start_dt - timedelta(days=_DEFAULT_CANDIDATE_WINDOW_DAYS)).date().isoformat()
    query_end = (end_dt + timedelta(days=_DEFAULT_CANDIDATE_WINDOW_DAYS)).date().isoformat()

    raw = _query_events(query_start, query_end)
    if "error" in raw:
        return {"check_error": raw["error"]}

    events = [e for e in raw["events"] if e.get("uid") != exclude_uid]

    norm_title = _normalize_title(title)
    overlaps = []
    exact_duplicate = None
    near_duplicate_candidates = []
    recurring_series_match = []
    location_transition_flags = []

    for ev in events:
        ev_start = _parse_dt(ev.get("start", ""))
        ev_end = _parse_dt(ev.get("end", ""))
        if ev_start is None or ev_end is None:
            continue

        is_overlap = _overlaps(start_dt, end_dt, ev_start, ev_end)
        sim = _title_similarity(title, ev.get("title", ""))
        shared_attendees = _attendee_overlap(attendees or [], ev.get("attendees", []))

        if is_overlap:
            overlaps.append({
                "uid": ev["uid"], "title": ev["title"], "start": ev["start"], "end": ev["end"],
                "location": ev.get("location", ""),
            })
            if (exact_duplicate is None and _normalize_title(ev.get("title", "")) == norm_title
                    and norm_title and ev_start == start_dt and ev_end == end_dt):
                exact_duplicate = {"uid": ev["uid"], "title": ev["title"], "start": ev["start"], "end": ev["end"]}

        # Near-duplicate candidates: close in time (overlap, or within a 2-hour
        # window of the proposed start) AND similar in title, sharing an
        # attendee, or sharing a significant word (catches reworded titles a
        # pure similarity ratio misses — see _shared_significant_tokens).
        # Time-distant same-title events (a genuinely recurring commitment) are
        # left to the recurring-series check below, not flagged here.
        shared_tokens = _shared_significant_tokens(title, ev.get("title", ""))
        time_close = is_overlap or abs((ev_start - start_dt).total_seconds()) <= 2 * 3600
        if time_close and (sim >= _TITLE_SIMILARITY_THRESHOLD or shared_attendees or shared_tokens):
            near_duplicate_candidates.append({
                "uid": ev["uid"], "title": ev["title"], "start": ev["start"], "end": ev["end"],
                "title_similarity": round(sim, 2), "shared_attendees": shared_attendees,
                "shared_words": shared_tokens,
            })

        # Recurring-series match: an existing RRULE event whose title matches
        # closely, regardless of how far away in time it falls within the query
        # window. fits_cadence is a loose heuristic (same weekday + time of day
        # within 15 minutes) — evidence for the agent to reason from, not a
        # classification it should trust blindly.
        if ev.get("recurrence") and sim >= _TITLE_SIMILARITY_THRESHOLD:
            fits_cadence = (
                ev_start.weekday() == start_dt.weekday()
                and abs((ev_start.hour * 60 + ev_start.minute) - (start_dt.hour * 60 + start_dt.minute)) <= 15
            )
            recurring_series_match.append({
                "uid": ev["uid"], "title": ev["title"], "recurrence": ev["recurrence"],
                "fits_cadence": fits_cadence,
            })

    # Location-transition tightness: only meaningful against the immediately
    # adjacent event on the same day, not every event in the window.
    if location:
        same_day = sorted(
            (e for e in events if _parse_dt(e.get("start", "")) and _parse_dt(e.get("start", "")).date() == start_dt.date()),
            key=lambda e: e["start"],
        )
        for ev in same_day:
            ev_start = _parse_dt(ev.get("start", ""))
            ev_end = _parse_dt(ev.get("end", ""))
            if ev_start is None or ev_end is None or not ev.get("location"):
                continue
            if ev.get("location", "").strip().lower() == location.strip().lower():
                continue
            # Two independent directions: the adjacent event could end right
            # before the new one starts, or start right after the new one ends.
            # Only a non-negative gap counts as "adjacent" — a negative value
            # means the events overlap in that direction, which is a scheduling
            # conflict already caught above, not a transition-time problem.
            gap_before = (start_dt - ev_end).total_seconds() / 60
            gap_after = (ev_start - end_dt).total_seconds() / 60
            gap = None
            if 0 <= gap_before < _TIGHT_TRANSITION_MINUTES:
                gap = gap_before
            elif 0 <= gap_after < _TIGHT_TRANSITION_MINUTES:
                gap = gap_after
            if gap is not None:
                location_transition_flags.append({
                    "adjacent_event_uid": ev["uid"], "adjacent_title": ev["title"],
                    "gap_minutes": round(gap, 1), "locations": [location, ev["location"]],
                })

    day_digest = sorted(
        [{"uid": e["uid"], "title": e["title"], "start": e["start"], "end": e["end"], "location": e.get("location", "")}
         for e in events
         if _parse_dt(e.get("start", "")) and _parse_dt(e.get("start", "")).date() in (start_dt.date(), end_dt.date())],
        key=lambda e: e["start"],
    )

    unverified_events = [
        {"uid": e["uid"], "title": e["title"], "start": e["start"]}
        for e in events if e.get("conflict_check_status") == "FAILED"
    ]

    resolved_attendees = _resolve_attendees(attendees)

    return {
        "overlaps": overlaps,
        "exact_duplicate": exact_duplicate,
        "near_duplicate_candidates": sorted(near_duplicate_candidates, key=lambda c: -c["title_similarity"])[:5],
        "recurring_series_match": recurring_series_match,
        "location_transition_flags": location_transition_flags,
        "day_digest": day_digest,
        "unverified_events": unverified_events,
        "attendees_resolved": resolved_attendees,
    }


def check_calendar_conflicts(
    start: str,
    end: str,
    title: str = "",
    attendees: list[str] | None = None,
    location: str = "",
    exclude_uid: str = "",
) -> dict:
    """
    Report what's already on the calendar around a proposed event.

    This is evidence, not a verdict — it tells you what exists and how closely
    it resembles the proposed event; deciding whether that's a real conflict
    (same meeting, legitimate second meeting, a series it does or doesn't
    belong to) is your judgment to make with context this function doesn't have.

    Args:
        start:       Proposed start, same format as write_calendar_event.
        end:         Proposed end.
        title:       Proposed title — used for duplicate/similarity matching.
        attendees:   Optional list of attendee names.
        location:    Optional location — used for the transition-tightness check.
        exclude_uid: Event uid to exclude from all comparisons (pass the event's
                     own uid when re-checking during an update).

    Returns:
        Dict with a wrapped conflict_report (overlaps, exact_duplicate,
        near_duplicate_candidates, recurring_series_match,
        location_transition_flags, day_digest, unverified_events,
        attendees_resolved), or {"error": "..."} if the calendar couldn't be read.
    """
    result = _compute_conflicts(start, end, title, attendees, location, exclude_uid)
    if "check_error" in result:
        return {"error": result["check_error"]}

    # Evidence drawn from other calendar events is the same untrusted class
    # read_calendar already wraps — titles/locations here are free text some
    # of it written by whoever sent the original invite, not the user.
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    return {
        "security_note": UNTRUSTED_CONTENT_INSTRUCTION,
        "conflict_report": wrap_untrusted(rendered, source="calendar conflict check"),
    }


CHECK_CALENDAR_CONFLICTS_SCHEMA = {
    "name": "check_calendar_conflicts",
    "description": (
        "Check what's already on the calendar around a proposed time before "
        "scheduling — or at any point you need a wider read of the schedule to "
        "reason about ordering or dependencies between meetings. write_calendar_event "
        "already calls this automatically before every write; call it directly "
        "yourself when you need a broader look (a whole day, or pass a wide "
        "start/end range for a week/month view) or want to check a hypothetical "
        "time before committing to it. Returns overlaps, exact/near-duplicate "
        "candidates, whether this fits an existing recurring series, tight "
        "back-to-back location transitions, and a same-day digest of other "
        "events — evidence to reason from, not a verdict."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "Proposed/query start, same datetime format as write_calendar_event."},
            "end": {"type": "string", "description": "Proposed/query end."},
            "title": {"type": "string", "description": "Event title, for duplicate/similarity matching. Omit for a general schedule check."},
            "attendees": {"type": "array", "items": {"type": "string"}, "description": "Optional attendee names."},
            "location": {"type": "string", "description": "Optional location, for the tight-transition check."},
        },
        "required": ["start", "end"],
    },
}
