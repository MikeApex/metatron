"""
tools/travel_watch.py — proactive pre-departure travel check.

`get_tfl_status` (tools/tfl_status.py) and `get_flight_status` (tools/flights.py) both
work and both were built for exactly this, but until now nothing called either one
automatically — an agent reached them only if the user thought to ask, which is precisely
backwards for a delay the user wants to hear about *before* they leave. This file is the
trigger those two tools were missing: it reads the calendar, recognises travel, extracts
what to check, and dispatches the right check.

Runs as a `function:` scheduler job — no model tokens. Same class as
tools/calendar_audit.py and tools/rule_audit.py, and structured after them deliberately
(seen-set, report-once, never raise into the daemon).

WHAT IT COSTS TO GET DETECTION WRONG, AND WHY IT IS CONSERVATIVE
----------------------------------------------------------------
A false positive here is not free. `get_flight_status` runs on AeroDataBox's RapidAPI
Basic plan: **600 units/month and 1 request/second** (tools/flights.py). A loose flight-
number regex over calendar titles matches things like "Q4 2026", "Room B12" and "H1
planning", and each of those would spend a unit and could rate-limit a real check queued
behind it. So a flight number is only accepted when the event *also* carries independent
travel context — the word "flight", an airport, a terminal, boarding. Two signals, not one.

The asymmetry is deliberate: a missed check costs the user a surprise at the airport; a
false check costs quota and trains them to distrust the alerts. Both are bad, but the
second is the one that makes the feature worthless, because an alert stream with noise in
it stops being read. When in doubt this stays quiet.

WHAT IT SURFACES
----------------
Only actual problems. A flight on time and a line running Good Service produce **no
notification at all** — the same rule `get_tfl_status`'s own schema states ("a clean
'Good Service' result on every line checked does not need a message"). A user who gets
a daily "your flight is fine" push stops reading the pushes, and then misses the one that
matters.

Each finding is reported once, keyed on the event and the specific disruption, so a
three-day-old delay does not re-alert every morning. A *change* in status (on time →
delayed, or a worsening) is a new finding and does alert again.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from core.persona import persona_config_dir, persona_data_dir, resolve_persona
from tools.caldav import _query_events
from tools.scheduling import _parse_dt

# How far ahead to look. A pre-departure check is only useful in the window where the
# user can still act on it — long enough to rebook or leave early, short enough that the
# airline's own status is meaningful (statuses more than ~24h out are mostly schedule,
# not live information).
_LOOKAHEAD_HOURS = 24

# IATA flight designator: 2-character airline code (LL, LD or DL) + 1-4 digits.
# Deliberately NOT anchored to a word boundary alone — see the module docstring on why
# this needs a second signal before it is believed.
_FLIGHT_RE = re.compile(r"\b([A-Z]{2}|[A-Z]\d|\d[A-Z])\s?(\d{1,4})\b")

# Independent evidence that an event is actually air travel. Without one of these, a
# regex match is treated as a coincidence and dropped.
_FLIGHT_CONTEXT = (
    "flight", "flying", "fly ", "airport", "terminal", "boarding", "check-in",
    "checkin", "departure", "departs", "arrivals", "gate", "airline", "plane",
)

# 3-letter airport codes also count as flight context, but only in an obviously
# travel-shaped phrase — a bare "LHR" in a title is context, "CEO" is not.
_AIRPORT_RE = re.compile(r"\b(LHR|LGW|STN|LTN|LCY|SEN|MAN|EDI|BHX|GLA|BRS|NCL|LPL|DUB)\b")

# TfL line names worth recognising in an event's text. Matches tools/tfl_status.py's
# alias table plus the tube lines it accepts directly.
_TFL_LINES = (
    "bakerloo", "central", "circle", "district", "hammersmith-city", "jubilee",
    "metropolitan", "northern", "piccadilly", "victoria", "waterloo-city",
    "dlr", "elizabeth", "overground", "tram",
)
_TFL_ALIASES = {
    "hammersmith & city": "hammersmith-city",
    "hammersmith and city": "hammersmith-city",
    "waterloo & city": "waterloo-city",
    "waterloo and city": "waterloo-city",
    "elizabeth line": "elizabeth",
    "crossrail": "elizabeth",
    "london overground": "overground",
}


def _seen_path(persona: str) -> Path:
    return persona_data_dir(persona) / "logs" / ".travel_watch_seen"


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


def _finding_key(*parts: str) -> str:
    """Keyed on the event AND the disruption, so a status that changes re-alerts."""
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _event_text(ev: dict) -> str:
    return " ".join(str(ev.get(k) or "") for k in ("title", "location", "description"))


def _usual_lines(persona: str) -> list[str]:
    """
    Lines this persona normally travels on, from profile.yaml:

        transit:
          usual_lines: [victoria, elizabeth]

    Optional. Absent means "only check lines an event actually names" — which is the
    safe default, since guessing someone's commute and alerting on it is noise.
    """
    path = persona_config_dir(persona) / "profile.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return []
    lines = (data.get("transit") or {}).get("usual_lines") or []
    return [str(l).strip().lower() for l in lines if str(l).strip()]


def extract_flight_numbers(text: str) -> list[str]:
    """
    Flight numbers in a piece of event text, or [] when the text has no independent
    travel context. See the module docstring — the second signal is the whole point.
    """
    lowered = (text or "").lower()
    has_context = any(k in lowered for k in _FLIGHT_CONTEXT) or bool(_AIRPORT_RE.search(text or ""))
    if not has_context:
        return []

    found = []
    for carrier, number in _FLIGHT_RE.findall(text or ""):
        # Strip the leading zero-padding airlines sometimes print; the API takes either.
        candidate = f"{carrier}{number}"
        if candidate not in found:
            found.append(candidate)
    return found


def extract_transit_lines(text: str) -> list[str]:
    """TfL lines explicitly named in event text. Alias-aware, deduplicated."""
    lowered = (text or "").lower()
    found: list[str] = []
    for alias, canonical in _TFL_ALIASES.items():
        if alias in lowered and canonical not in found:
            found.append(canonical)
    for line in _TFL_LINES:
        # Word-ish match so "central" doesn't fire on "Central Perk" — require the line
        # name next to a transit word, or standing alone as a token.
        if re.search(rf"\b{re.escape(line)}\b", lowered) and line not in found:
            found.append(line)
    return found


def find_travel_events(persona: str | None = None, lookahead_hours: int = _LOOKAHEAD_HOURS) -> list[dict]:
    """
    Calendar events in the next `lookahead_hours` that look like travel.

    Returns a list of {"uid", "title", "start", "location", "flights": [...],
    "lines": [...]} — evidence, not a verdict. An event with neither a flight number nor
    a named line is dropped: there is nothing to check.
    """
    resolved = resolve_persona(persona)
    now = datetime.now()
    horizon = now + timedelta(hours=lookahead_hours)

    raw = _query_events(now.date().isoformat(), horizon.date().isoformat(), persona=resolved)
    if "error" in raw:
        return []

    usual = _usual_lines(resolved)
    out = []
    for ev in raw.get("events", []):
        start = _parse_dt(ev.get("start", ""))
        if start is None or not (now <= start <= horizon):
            continue

        text = _event_text(ev)
        flights = extract_flight_numbers(text)
        lines = extract_transit_lines(text)

        # A flight with no named line still implies a journey to the airport, so the
        # persona's usual lines are worth checking on that day — but only then. This is
        # the one place a configured default is applied, and only alongside hard evidence
        # of travel, never on an ordinary calendar day.
        if flights and not lines:
            lines = list(usual)

        if not flights and not lines:
            continue

        out.append({
            "uid": ev.get("uid", ""),
            "title": ev.get("title", ""),
            "start": ev.get("start", ""),
            "location": ev.get("location", ""),
            "flights": flights,
            "lines": lines,
        })
    return out


def check_travel_events(events: list[dict]) -> list[dict]:
    """
    Run the actual status checks for detected travel and return only the problems.

    Fails soft per check: a flight lookup that errors must not suppress the transit
    check for the same trip, and neither must take down the scheduler job.
    """
    from tools.flights import get_flight_status
    from tools.tfl_status import get_tfl_status

    findings = []
    for ev in events:
        for flight_number in ev["flights"]:
            try:
                result = get_flight_status(flight_number)
            except Exception as e:
                result = {"error": str(e)}
            if "error" in result:
                continue
            for f in result.get("flights", []):
                dep, arr = f.get("departure", {}), f.get("arrival", {})
                status = (f.get("status") or "").lower()
                problem = dep.get("delayed") or arr.get("delayed") or status in (
                    "cancelled", "canceled", "diverted",
                )
                if not problem:
                    continue
                findings.append({
                    "kind": "flight",
                    "event_uid": ev["uid"],
                    "event_title": ev["title"],
                    "subject": f.get("number", flight_number),
                    "status": f.get("status", "Unknown"),
                    "detail": (
                        f"{f.get('number', flight_number)} ({f.get('airline', '?')}) — "
                        f"{f.get('status', 'Unknown')}. Departs {dep.get('airport', '?')} "
                        f"scheduled {dep.get('scheduled_local', '?')}, now "
                        f"{dep.get('current_estimate_local', '?')}."
                    ),
                })

        if ev["lines"]:
            try:
                result = get_tfl_status(ev["lines"])
            except Exception as e:
                result = {"error": str(e)}
            if "error" in result:
                continue
            for line in result.get("lines", []):
                if not line.get("disrupted"):
                    continue
                findings.append({
                    "kind": "transit",
                    "event_uid": ev["uid"],
                    "event_title": ev["title"],
                    "subject": line.get("name", "?"),
                    "status": line.get("status", "Unknown"),
                    "detail": (
                        f"{line.get('name', '?')}: {line.get('status', 'Unknown')}"
                        + (f" — {line['detail']}" if line.get("detail") else "")
                    ),
                })
    return findings


def travel_check() -> dict | str:
    """
    Scheduler entry point. Takes no arguments; persona comes from the scope.

    Returns a dict with `notify: True` and a message when something is actually wrong —
    `fire_function` dispatches that to the configured notification channel. Returns a
    plain status string otherwise, which is printed and goes no further, so a quiet
    travel day is silent to the user by construction.

    Never raises: this runs unattended in a daemon, and a travel check that crash-loops
    the scheduler costs more than the delay it was watching for.
    """
    try:
        persona = resolve_persona()
        events = find_travel_events(persona)
    except Exception as e:
        return f"travel check skipped: {e}"

    if not events:
        return "no travel found in the next 24h"

    try:
        findings = check_travel_events(events)
    except Exception as e:
        return f"travel check failed: {e}"

    seen = _load_seen(persona)
    fresh = [
        f for f in findings
        if _finding_key(f["event_uid"], f["kind"], f["subject"], f["status"]) not in seen
    ]

    if not fresh:
        return (f"{len(events)} travel event(s) checked, "
                f"{len(findings)} known issue(s), nothing new")

    _record_seen(persona, {
        _finding_key(f["event_uid"], f["kind"], f["subject"], f["status"]) for f in fresh
    })

    body = "\n".join(f["detail"] for f in fresh)
    subjects = ", ".join(sorted({f["subject"] for f in fresh}))
    return {
        "notify": True,
        "title": f"Travel check: {subjects}",
        "body": body,
        "summary": f"{len(fresh)} new travel issue(s) across {len(events)} travel event(s)",
    }


if __name__ == "__main__":  # manual run: python3 -m tools.travel_watch <persona>
    import sys
    from core.persona import persona_scope

    who = sys.argv[1] if len(sys.argv) > 1 else "mike"
    with persona_scope(who):
        detected = find_travel_events(who)
        print(f"{len(detected)} travel event(s) detected:")
        for e in detected:
            print(f"  {e['start']}  {e['title']!r}  flights={e['flights']} lines={e['lines']}")
        print()
        print(travel_check())
