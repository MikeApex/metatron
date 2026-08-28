"""
tools/location.py — GPS coordinates in, a named zone out. `[DB-0815-12]`, first draft.

## The tier ruling this file exists to enforce (Mike, 2026-08-28)

Location is **extra-sensitive — above ordinary sensitive**. Raw coordinates never enter any
model prompt, cloud or local. A model sees only a code-derived line: *"home since 14:02"*.

That is not a prompt instruction and must never become one. The standing project rule is that
sensitive data paths are enforced in Python, never in prompts, because an instruction has
exactly the standing that the 2026-08-03 `write_agent_config` incident showed it has: being
told is not being prevented. So the coordinate→zone map is here, in code, and the coordinate
is discarded inside `record_position()` before anything else in the system can see it.

Concretely, three properties hold by construction rather than by discipline:

1. **No function in this module returns the user's coordinate.** `record_position()` takes
   lat/lon and returns a zone name; the only other coordinates handled here are a PLACE's
   public geocoded position (`append_zone`, the zone-suggestion flow), which say nothing
   about where the user is.
2. **Nothing here is registered as a model-callable tool.** The only route from this module
   into a prompt is `context_block()`, which reads the transitions log — a file that has never
   contained a coordinate — and never the ping.
3. **No raw trail is stored at all.** The transitions log holds `(zone, entered_at)`. A
   coordinate exists in memory for the duration of one `record_position()` call and is then
   gone. Debug-only raw points were left out of this build entirely rather than shipped behind
   a flag: a flag is a thing that can be left on.

## Zones are Mike's to define

`config/templates/zones.yaml` is the provisioning template and the documented shape. The live
copy is `data/personas/{persona}/zones.yaml`, owned by the VM. This module reads it, and has
exactly ONE write path ([DB-0815-12] option b, 2026-08-28): `append_zone()`, which appends a
single user-approved suggested zone through the confirm gate and nothing else — it cannot
rewrite, rename or remove anything Mike wrote by hand. A persona with no zones file is not an
error state: every coordinate maps to `AWAY`, which is a true statement about a system that
has not been told where anything is.

## Nothing here polls

`record_position()` is called only from `POST /location`, which is only reached from a
deliberate act in the app — sending a message with the ping enabled, or tapping the share
button. There is no timer, no scheduled job and no watcher in this module. Proactive scans on
zone transitions are a later build (`[DB-0815-12]` design point 4); when they arrive they fire
on a transition recorded here, never on a loop.

## What this costs to run

Nothing standing. No process, no timer, no network call, no cache with a lifetime. Per ping:
one small YAML read, one tail read of a JSONL file, and — only when the zone actually changed —
one appended line of roughly 60 bytes. A day of heavy use is a few hundred bytes; the log is
bounded by how often the user crosses a boundary, not by how often the phone reports in, which
is the point of storing transitions rather than a trail.

The zone-suggestion check adds, at most once per 15 minutes and only on an `away` ping: one
CalDAV read and up to three name-only Places geocodes (Essentials-tier field mask, per-name
in-memory cache so a repeated name is free). Without `GOOGLE_PLACES_API_KEY` the geocode
fails soft and the feature is dormant — by design, per item 5(d) of the launch ruling.
"""

from __future__ import annotations

import json
import math
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from core.persona import persona_data_dir

# The zone name for a coordinate that matches nothing. Not an error: "I do not know where this
# is" is the honest answer, and raising here would put the server in the position of failing a
# ping because the user has not finished writing their zones file.
AWAY = "away"

_LOCK = threading.Lock()

_TEMPLATE_PATH = Path(__file__).parent.parent / "config" / "templates" / "zones.yaml"

_ZONES_FILENAME = "zones.yaml"
_TRANSITIONS_FILENAME = "location_transitions.jsonl"

# Mean Earth radius. A circle-and-radius zone is a first-draft abstraction — polygons and
# dwell-time thresholds are deliberately not here — so a spherical distance is well inside the
# precision this needs. At these distances the error against a proper geodesic is centimetres.
_EARTH_RADIUS_M = 6_371_008.8


# ---------------------------------------------------------------------------
# Zone configuration
# ---------------------------------------------------------------------------

def _zones_path(persona: str | None = None) -> Path:
    """The live per-persona zone file. Read-only from here — the VM owns it."""
    return persona_data_dir(persona) / _ZONES_FILENAME


def load_zones(persona: str | None = None) -> list[dict[str, Any]]:
    """
    The persona's named zones, as `{name, lat, lon, radius_m}` dicts.

    Returns `[]` when the file is absent, empty, malformed, or contains no usable entry —
    never raises. A broken zones file degrades to "away", which is the safe direction: the
    alternative is a ping that 500s and a user who cannot tell why.

    Entries missing a name, a coordinate or a positive radius are skipped individually, so one
    bad line does not discard the rest of the file.
    """
    path = _zones_path(persona)
    if not path.exists():
        return []
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError):
        return []
    entries = raw.get("zones") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        return []

    zones: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        try:
            lat = float(entry["lat"])
            lon = float(entry["lon"])
            radius_m = float(entry["radius_m"])
        except (KeyError, TypeError, ValueError):
            continue
        if not name or radius_m <= 0:
            continue
        zones.append({"name": name, "lat": lat, "lon": lon, "radius_m": radius_m})
    return zones


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def zone_for(lat: float, lon: float, persona: str | None = None) -> str:
    """
    The name of the zone containing this coordinate, or `AWAY`.

    **The smallest matching zone wins.** Zones overlap in practice — "the office" sits inside
    "central London" — and the smaller circle is always the more specific statement about where
    someone is. Resolving by file order instead would make the answer depend on how the user
    happened to type the file, which is exactly the kind of invisible dependency that produces a
    wrong line in the context weeks later.

    A point exactly on the boundary is inside. A radius is the user's declared extent of a
    place; excluding its edge would make `radius_m` mean something fractionally other than what
    it says.
    """
    best_name, best_radius = AWAY, None
    for zone in load_zones(persona):
        if _haversine_m(lat, lon, zone["lat"], zone["lon"]) <= zone["radius_m"]:
            if best_radius is None or zone["radius_m"] < best_radius:
                best_name, best_radius = zone["name"], zone["radius_m"]
    return best_name


# ---------------------------------------------------------------------------
# The transitions log — zone changes only, never a trail
# ---------------------------------------------------------------------------

def _transitions_path(persona: str | None = None) -> Path:
    p = persona_data_dir(persona) / _TRANSITIONS_FILENAME
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read_transitions(persona: str | None = None) -> list[dict[str, Any]]:
    """Every recorded transition, oldest first. Unparseable lines are skipped, not fatal."""
    path = persona_data_dir(persona) / _TRANSITIONS_FILENAME
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text()
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("zone"):
            out.append(record)
    return out


def current_zone(persona: str | None = None) -> dict[str, Any] | None:
    """The most recent transition — `{"zone": ..., "entered_at": ...}` — or None."""
    records = _read_transitions(persona)
    return records[-1] if records else None


def record_transition(zone: str, entered_at: str | None = None,
                      persona: str | None = None) -> dict[str, Any]:
    """
    Append a zone change. A repeat of the zone already current is not a change and is dropped.

    The dedup is the storage rule in one line: an append per ping would be a trail with the
    coordinates stripped off — same movement history, same inference surface, and it would grow
    with how chatty the phone is rather than with what actually happened.

    Returns `{"zone", "entered_at", "changed"}`. `changed` is False when this was a repeat, and
    `entered_at` is then the *original* arrival time, not now — which is what makes "since"
    mean since arrival rather than since the last ping.
    """
    stamp = entered_at or datetime.now().isoformat(timespec="seconds")
    with _LOCK:
        latest = current_zone(persona)
        if latest and latest.get("zone") == zone:
            return {"zone": zone, "entered_at": latest.get("entered_at"), "changed": False}

        path = _transitions_path(persona)
        record = {"zone": zone, "entered_at": stamp}
        with path.open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        # `age` encryption is Phase 6; until then file permissions are the protection, and
        # this file is a movement history however abstracted it is. Set every write: an
        # append does not re-create the file, but a file restored or copied by hand might
        # arrive with the umask's permissions instead.
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return {"zone": zone, "entered_at": stamp, "changed": True}


def record_position(lat: float, lon: float, accuracy: float | None = None,
                    ts: str | None = None, persona: str | None = None) -> dict[str, Any]:
    """
    The one entry point for a coordinate, and the boundary the tier ruling is enforced on.

    A coordinate goes in; a zone name comes out. Nothing between here and the caller retains
    the coordinate, writes it, or logs it — `lat`, `lon` and `accuracy` are consumed by
    `zone_for()` and then fall out of scope with the frame. The zone-suggestion check below
    runs inside this same frame for exactly that reason: the comparison against an expected
    place needs the live coordinate, and this is the only place one legitimately exists.

    `accuracy` is accepted because the client has it and dropping a field the client sends
    invites it being smuggled somewhere else later; it is not stored, and it is not used to
    reject a ping. A first draft that silently discards imprecise readings would be a feature
    nobody can debug from the outside.

    `ts` is the client's reading time, used as the arrival time when this is a real transition,
    so a ping delivered late does not date the arrival to when the server got round to it.

    Returns `{"zone", "entered_at", "changed"}` — safe to hand back to the app and safe to
    log — plus `"suggestion"` when an away ping matched an expected place and a confirm card
    was raised.
    """
    zone = zone_for(lat, lon, persona)
    result = record_transition(zone, entered_at=ts, persona=persona)
    if zone == AWAY:
        # Never let the suggestion path break a ping — it is a nicety on top of a
        # working record, and it degrades to nothing on any failure.
        try:
            suggestion = _maybe_suggest_zone(lat, lon, persona)
            if suggestion:
                result["suggestion"] = suggestion
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Zone suggestion — an away ping near an EXPECTED place ([DB-0815-12] option b)
# ---------------------------------------------------------------------------
#
# THE RULING (Mike, 2026-08-28, second same-day ruling — supersedes the reverse-geocode
# note): the vendor never receives the user's position. When a place is expected — named
# in an upcoming calendar event — code asks Google Places where that PLACE is, by name
# only (tools/places.py geocode_place_name, per-name cache, fail-soft without the key).
# The returned public coordinate is compared LOCALLY against the ping; a match while the
# ping resolves `away` raises the existing confirm card ("lock this in as a zone?"), and
# approval has Python append to zones.yaml — the one write path granted to that file.
# Rejected in the same ruling, do not build: randomised nearby coordinates.
#
# CANDIDATES COME FROM STRUCTURED SOURCES IN CODE, never from asking a model where the
# user might be. Today that means the `location` field of calendar events around now,
# read via the CalDAV layer's structured query (not the untrusted-wrapped tool return —
# this is code reading code's own data). A place named only in the current turn has no
# structured source yet; when one exists it plugs in as a second candidate list here.
#
# NOTHING POLLS. This runs only inside a ping the user caused, at most once per
# _SUGGEST_MIN_INTERVAL_S, and only when the ping resolved `away`.

# How close the ping must be to the geocoded place to count as "you are there".
# Wider than a zone's default 150 m radius on purpose: a geocode point is the venue's
# pin, not its extent, and GPS in a building drifts. The zone written on approval gets
# the normal default radius; this threshold only decides whether to ASK.
_SUGGEST_MATCH_M = 300.0

# The default radius for a suggested zone — matches config/templates/zones.yaml.
_SUGGEST_RADIUS_M = 150.0

# At most one suggestion attempt per this interval, process-wide. The away state is the
# common state, and every attempt may cost a CalDAV read; a suggestion is not worth a
# per-ping network call.
_SUGGEST_MIN_INTERVAL_S = 900.0
_last_suggest_attempt = 0.0

# How far around now an event counts as "the place the user is expected to be".
_SUGGEST_EVENT_WINDOW_H = 3


def _calendar_place_candidates(persona: str | None = None) -> list[str]:
    """Location strings of calendar events around now — the structured source.

    Only the `location` field is used: an event title ("Meeting with John") is not a
    place. Fail-soft: any CalDAV error means no candidates, never an exception.
    """
    try:
        from datetime import timedelta
        from tools.caldav import _query_events
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        raw = _query_events(today, tomorrow)
        if not isinstance(raw, dict) or "error" in raw:
            return []
        now = datetime.now()
        names: list[str] = []
        for event in raw.get("events") or []:
            if not isinstance(event, dict):
                continue
            place = str(event.get("location") or "").strip()
            if not place:
                continue
            try:
                start = datetime.fromisoformat(str(event.get("start"))).replace(tzinfo=None)
            except (TypeError, ValueError):
                continue
            if abs((start - now).total_seconds()) > _SUGGEST_EVENT_WINDOW_H * 3600:
                continue
            if place not in names:
                names.append(place)
        return names[:3]
    except Exception:
        return []


def _maybe_suggest_zone(lat: float, lon: float,
                        persona: str | None = None) -> dict[str, Any] | None:
    """Raise a "lock this in as a zone?" card when an away ping sits at an expected place.

    Returns a small safe-to-return dict when a card was raised, else None. The card's
    args carry the PLACE's public geocoded coordinate — the user's ping is compared here
    and discarded with the frame, per the module's tier ruling.
    """
    global _last_suggest_attempt
    import time as _time
    now_mono = _time.monotonic()
    if _last_suggest_attempt and now_mono - _last_suggest_attempt < _SUGGEST_MIN_INTERVAL_S:
        return None
    _last_suggest_attempt = now_mono

    candidates = _calendar_place_candidates(persona)
    if not candidates:
        return None

    from tools import confirm as _confirm
    from tools.places import geocode_place_name
    existing = {z["name"].casefold() for z in load_zones(persona)}
    pending_zone_cards = {p.get("action") for p in _confirm.pending(persona)}

    for place_name in candidates:
        # The zone's name is the human half of the place string — "Luigi's" from
        # "Luigi's, 12 High St" — because zones.yaml names are spoken back in context.
        zone_name = place_name.split(",", 1)[0].strip()[:60]
        if not zone_name or zone_name.casefold() in existing:
            continue
        if "add_zone" in pending_zone_cards:
            # One zone question at a time — a stack of cards is how approvals stop
            # being read before they are tapped.
            return None
        geo = geocode_place_name(place_name)
        if "error" in geo:
            continue                      # incl. no API key: dormant by design
        if _haversine_m(lat, lon, geo["lat"], geo["lon"]) > _SUGGEST_MATCH_M:
            continue
        args = {"name": zone_name, "lat": geo["lat"], "lon": geo["lon"],
                "radius_m": _SUGGEST_RADIUS_M}
        card = _confirm.request(
            "add_zone", args,
            f"Lock “{zone_name}” in as a place Metatron knows? Your last "
            f"shared location matches it ({geo.get('address') or place_name}). "
            "Approving stores the place's own coordinates, never your position.",
            persona=persona,
        )
        if card.get("status") == "PENDING_CONFIRMATION":
            return {"zone_suggested": zone_name}
        return None
    return None


def append_zone(name: str, lat: float, lon: float, radius_m: float = _SUGGEST_RADIUS_M,
                persona: str | None = None, confirm_token: str = "") -> dict[str, Any]:
    """
    THE one write path to `data/personas/{p}/zones.yaml`, and it only opens on the
    user's own approval: every call must spend a confirm token issued by
    `_maybe_suggest_zone`'s card. Called by `tools/confirm.execute()` from
    `POST /confirm` — nothing model-reachable calls this, and there is no ungated
    variant. The module docstring's "reads it and never creates or writes it" holds
    for everything except this function, by the same ruling that created it.

    Appends, never rewrites: existing entries survive byte-for-byte in spirit (the
    file is re-serialised) and a name collision is refused rather than merged — the
    file is Mike's to edit, and a suggestion must not restructure it.
    """
    from tools.confirm import consume

    args = {"name": name, "lat": lat, "lon": lon, "radius_m": radius_m}
    ok, reason = consume(confirm_token, "add_zone", args, persona=persona)
    if not ok:
        return {"error": f"Zone not added: {reason}"}

    name = str(name or "").strip()
    try:
        lat, lon, radius_m = float(lat), float(lon), float(radius_m)
    except (TypeError, ValueError):
        return {"error": "Zone not added: coordinates were not numbers."}
    if not name or radius_m <= 0:
        return {"error": "Zone not added: a name and a positive radius are required."}

    with _LOCK:
        path = _zones_path(persona)
        entries: list[dict[str, Any]] = []
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text()) or {}
                loaded = raw.get("zones") if isinstance(raw, dict) else raw
                if isinstance(loaded, list):
                    entries = [e for e in loaded if isinstance(e, dict)]
            except (yaml.YAMLError, OSError):
                return {"error": "Zone not added: the zones file could not be read. "
                                 "It was left untouched."}
        if any(str(e.get("name", "")).strip().casefold() == name.casefold()
               for e in entries):
            return {"status": "exists", "zone": name,
                    "message": f"'{name}' is already a defined zone — nothing changed."}

        entries.append({"name": name, "lat": lat, "lon": lon, "radius_m": radius_m})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump({"zones": entries}, default_flow_style=False,
                                  sort_keys=False, allow_unicode=True))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return {"status": "added", "zone": name, "radius_m": radius_m}


# ---------------------------------------------------------------------------
# The context line — the only route from this module into a prompt
# ---------------------------------------------------------------------------

def _relative_age(days_ago: int) -> str:
    """"today" / "yesterday" / "N days ago" — the phrasing used across the context."""
    if days_ago <= 0:
        return "today"
    if days_ago == 1:
        return "yesterday"
    return f"{days_ago} days ago"


def context_line(persona: str | None = None) -> str:
    """
    *"home since 14:02"* — where the user is, as a named place and an arrival time.

    Returns "" when nothing has ever been recorded, so a user who never enables the ping pays
    nothing for this feature in either tokens or noise.

    **Age is annotated, never filtered** — the `[DB-0822-06]` pattern, for the same reason it
    was adopted there. Stored state read back as current is how a Teams link resolved at 07:14
    was still "still missing" at 10:00; a zone entered on Tuesday reads as "where they are"
    unless the line says when. So an arrival from an earlier day carries its age
    (*"home since 14:02, 3 days ago"*) and nothing here decides that it has gone stale. The
    only thing that changes a zone is another ping.
    """
    latest = current_zone(persona)
    if not latest:
        return ""
    zone = str(latest.get("zone") or "").strip()
    if not zone:
        return ""

    raw = str(latest.get("entered_at") or "")
    try:
        entered = datetime.fromisoformat(raw)
    except ValueError:
        # A record with no usable time still says where they are, which is most of the value.
        return zone

    clock = entered.strftime("%H:%M")
    days = (date.today() - entered.date()).days
    if days <= 0:
        return f"{zone} since {clock}"
    return f"{zone} since {clock}, {_relative_age(days)}"


def context_block(persona: str | None = None) -> str:
    """
    The location section for `load_recent_context`, or "" when there is nothing to say.

    Same contract as the obligations, reconcile, intake and confirm blocks: empty means the
    section does not appear at all.

    The framing is deliberate and is the user-facing half of the tier ruling. The line names a
    **place the user named** and states that it is a report, not a live fix — a model told
    "the user is at home" will reason as though it knows that now, and the last thing this
    system should manufacture is confident belief about where somebody physically is. There is
    no coordinate in this string and no way to obtain one from it.
    """
    line = context_line(persona)
    if not line:
        return ""
    return (
        "## Where the user was\n"
        f"{line} — a place they named, reported by their phone when they last used the app. "
        "It is not a live position and says nothing about where they are now."
    )
