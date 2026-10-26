"""
tools/day_shape.py — the shape of the user's day: when it starts and ends, when they work and
focus, what time is theirs, when they eat, how they get around.

Two layers, deliberately apart (Mike, 2026-10-24, Q4):
  - **design** — config/modules/day_shape.yaml: meal windows, breaks, buffers, wind-down. Every
    user gets these; they are how a day is planned, not who someone is.
  - **the user's hours** — data/personas/{p}/day_shape.yaml, written only by set_day_shape on the
    user's own word. Asked in the first interview (goals_interviewer Phase 1) and, for anyone past
    it, in conversation.

Until the user has said, wake and bed come from the persona's scheduler.yaml quiet hours — the
only structured window that existed before this file — and then from the design fallback. Work
hours are never assumed.

THE VARIABLES ARE DYNAMIC (round 2, plan § 18.3 — Mike, 2026-10-26: "Not everyone has a
weekday/weekend split. Further working hours is vague"). The user's file holds SECTIONS of
entries, each scoped to any set of days:

  day            {days, wake, bed}
  windows        {activity, days, from, to, strength: protected|strong|preferred, allows?, condition?}
  routines       {what, days, from, to, place?, covers?}       — a standing block on no calendar
  meals          {name, days, at, latest?, minutes?, when?} | {name, days, from, to} | {name, days, skip}
  calendars      {id: {name, role: mine|family|feed}}          — keyed by collection id, never name
  event_rules    {match, answer: there|needs_me|someone_else|noise, duty?, load?}
  children_home  {days, from, to}                               — when a childcare duty applies
  day_overrides  {date, what, holds}                            — one day's exception
  travel_mode, location_sharing

Nothing here names any one user's hours: the structures and their defaults are universal, and a
persona's answers are data inside them (ruling 9). The flat fields of the first version (wake,
work_start, focus, personal …) are still read, as entries, so nothing written before migrates.

Plan: archive/plans/day_planner_plan_2026-10-24.md § 4.2 and § 18. The planner
(tools/day_plan.py) reads `shape_for()` and `window_for()`; nothing here decides what goes in
the day.

    python3 -m tools.day_shape --persona mike calendars     # what the account sees, with roles
    python3 -m tools.day_shape --persona mike apply FILE    # a baseline, entry by entry
    python3 -m tools.day_shape --persona mike show [DATE]   # the effective shape of one day
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml

from core.persona import persona_config_dir, persona_data_dir

logger = logging.getLogger(__name__)

_DESIGN_PATH = Path(__file__).resolve().parent.parent / "config" / "modules" / "day_shape.yaml"

_DESIGN_DEFAULTS = {
    "meals": {
        "breakfast": {"earliest": "wake", "latest": "wake+90", "minutes": 15},
        "lunch": {"earliest": "12:00", "latest": "14:00", "minutes": 30},
        "dinner": {"earliest": "18:00", "latest": "20:30", "minutes": 45},
    },
    "break_after_minutes": 90, "break_minutes": 10, "transition_minutes": 5,
    "departure_buffer_minutes": 10, "wind_down_minutes": 60, "travel_mode": "transit",
    "fallback_wake": "07:00", "fallback_bed": "23:00",
    # What a missing config file means (config/modules/day_shape.yaml is the product).
    "activities": {
        "focus": {"device": True, "concentration": "heavy"},
        "creative": {"device": True, "concentration": "heavy"},
        "admin": {"device": True, "concentration": "heavy"},
        "busy": {"device": True, "concentration": "light"},
        "entertainment": {"device": True, "concentration": "light"},
        "errands": {"device": False, "concentration": "light"},
        "household": {"device": False, "concentration": "light"},
        "personal": {"device": False, "concentration": "light"},
        "health": {"device": False, "concentration": "light"},
        "exercise": {"device": False, "concentration": "light", "solo": True},
        "family": {"device": False, "concentration": "light"},
        "social": {"device": False, "concentration": "light"},
        "rest": {"device": False, "concentration": "light"},
    },
    "default_activity": "personal",
    "domain_activity": {},
    "activity_words": {},
    "window_allows": {"family": {"device": False, "concentration": "light", "solo": False}},
    "duties": {"childcare": {"as": "family"}},
    "wind_down_excludes": ["focus", "creative", "admin", "busy"],
}

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_MODES = ("transit", "walking", "driving", "cycling")
_MEALS = ("breakfast", "lunch", "dinner")
_STRENGTHS = ("protected", "strong", "preferred")
_ROLES = ("mine", "family", "feed")
_ANSWERS = ("there", "needs_me", "someone_else", "noise")
_LOADS = ("full", "partial")
# The first version's protected "personal" windows: the user's own time, which admits nothing.
# Not an activity any task can have, so a light personal task never lands in it.
OWN_TIME = "own"
# A day-set alias is a convenience for writing, never a structure: every entry stores the days.
_DAY_ALIASES = {"all": _WEEKDAYS, "daily": _WEEKDAYS, "every day": _WEEKDAYS,
                "weekdays": _WEEKDAYS[:5], "weekends": _WEEKDAYS[5:]}
_LIST_SECTIONS = ("day", "windows", "routines", "meals", "event_rules", "children_home",
                  "day_overrides")
SECTIONS = {
    "day": "{days, wake, bed} — when the day starts and ends on those days",
    "windows": "{activity, days, from, to, strength: protected|strong|preferred, allows?, "
               "condition?} — when a kind of activity goes; protected keeps out what does not "
               "fit, strong means only there, preferred means there first",
    "routines": "{what, days, from, to, place?, covers?} — a standing block on no calendar "
                "(\"lunch with Iva at Canary Wharf, weekdays 12–1\"); covers names a meal",
    "meals": "{name, days, at, latest?, minutes?} or {name, days, from, to, when?} or "
             "{name, days, skip: true}",
    "calendars": "{id, name, role: mine|family|feed} — what one of their calendars is",
    "event_rules": "{match: [words], answer: there|needs_me|someone_else|noise, duty?, load?: "
                   "full|partial} — a standing answer for events whose title has those words",
    "children_home": "{days, from, to} — when someone in their care is home and awake",
    "day_overrides": "{date, what, holds: true|false} — one day's exception to a window "
                     "(\"I'm free of childcare today\")",
    "travel_mode": "transit, walking, driving or cycling",
    "location_sharing": "on or off",
}

# What set_day_shape accepts, and what each value means. One table so the schema, the validator
# and the error messages cannot drift apart.
FIELDS = {
    "wake": "HH:MM — when the user's day usually starts",
    "bed": "HH:MM — when they usually go to bed (after midnight is fine: 00:30)",
    "wake_weekend": "HH:MM — wake time on Saturday and Sunday, if different",
    "bed_weekend": "HH:MM — bedtime on Friday and Saturday nights, if different",
    "work_days": "weekday names (mon,tue,wed,thu,fri) or 'none'",
    "work_start": "HH:MM — when work usually starts",
    "work_end": "HH:MM — when work usually ends",
    "focus": "windows they focus best in, 'HH:MM-HH:MM' comma-separated, or 'none'",
    "personal": "windows that are theirs and protected, 'HH:MM-HH:MM' comma-separated, or 'none'",
    "breakfast": "HH:MM, or 'skip'",
    "lunch": "HH:MM, or 'skip'",
    "dinner": "HH:MM, or 'skip'",
    "travel_mode": "transit, walking, driving or cycling — how they usually get around",
    "location_sharing": "on or off — send the phone's place with each message",
}


# --- reading ---------------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text()) or {}
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 — a missing or broken file is "nothing stated"
        return {}


def design() -> dict:
    data = _read_yaml(_DESIGN_PATH)
    out = json.loads(json.dumps(_DESIGN_DEFAULTS))
    for k, v in data.items():
        if k == "meals" and isinstance(v, dict):
            for name, m in v.items():
                if isinstance(m, dict):
                    out["meals"].setdefault(name, {}).update(m)
        else:
            out[k] = v
    return out


def _path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "day_shape.yaml"


def read_shape(persona: str | None = None) -> dict:
    """What the user has stated, as stored. Empty when nothing has been."""
    return _read_yaml(_path(persona))


def _hhmm(raw) -> time | None:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(raw or ""))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    return time(int(m.group(1)), int(m.group(2)))


def _windows(raw) -> list[tuple[time, time]]:
    out = []
    for part in (raw or []) if isinstance(raw, list) else str(raw or "").split(","):
        bits = str(part).split("-")
        if len(bits) != 2:
            continue
        a, b = _hhmm(bits[0]), _hhmm(bits[1])
        if a and b and a != b:
            out.append((a, b))
    return out


def _quiet_hours(persona: str | None = None) -> tuple[time, time] | None:
    """(start, end) of the persona's quiet hours — read as (bed, wake) until the user says."""
    try:
        cfg = _read_yaml(persona_config_dir(persona) / "scheduler.yaml")
    except Exception:  # noqa: BLE001
        return None
    qh = cfg.get("quiet_hours") or {}
    a, b = _hhmm(qh.get("start")), _hhmm(qh.get("end"))
    return (a, b) if a and b else None


def _offset(spec: str, wake: time) -> time | None:
    """'wake', 'wake+90' or 'HH:MM' → a time."""
    spec = str(spec or "").strip()
    if spec.startswith("wake"):
        mins = 0
        m = re.fullmatch(r"wake\s*\+\s*(\d+)", spec)
        if m:
            mins = int(m.group(1))
        dt = datetime.combine(date(2000, 1, 1), wake) + timedelta(minutes=mins)
        return dt.time()
    return _hhmm(spec)


def _entries(s: dict, section: str) -> list[dict]:
    """A section's entries, each re-validated on read — a hand-edited file can hold anything, and
    a broken entry is "nothing stated", never a crash."""
    out = []
    items = s.get(section)
    for raw in items if isinstance(items, list) else []:
        clean, err = _validate_entry(section, raw)
        if not err and clean is not None:
            out.append(clean)
    return out


def roster(persona: str | None = None) -> dict[str, dict]:
    """{collection id: {name, role}} — the user's calendars as they classified them. Empty means
    no roster yet: every calendar is theirs (D1)."""
    raw = read_shape(persona).get("calendars")
    out = {}
    for cid, v in raw.items() if isinstance(raw, dict) else []:
        if isinstance(v, dict) and v.get("role") in _ROLES:
            out[str(cid)] = {"name": str(v.get("name") or ""), "role": v["role"]}
    return out


def _allows_for(activities: list[str], strength: str, allows, d: dict):
    """What a window admits besides meals and its own activities. Only protected windows close
    anything, so only they need a filter; the design supplies one per activity (family time —
    Mike's rule) until the user says otherwise. None admits nothing."""
    if strength != "protected":
        return None
    if allows == "none":
        return None
    if isinstance(allows, dict):
        return allows
    return (d.get("window_allows") or {}).get(activities[0])


def admits(window_allows, attrs: dict) -> bool:
    """Whether an activity with these attributes may share a protected window with this filter."""
    if not isinstance(window_allows, dict):
        return False
    for key, want in window_allows.items():
        have = attrs.get(key, False if isinstance(want, bool) else None)
        if have != want:
            return False
    return True


def _legacy_windows(s: dict, wd: str) -> list[dict]:
    """The first version's flat fields as entries: work hours and focus windows are preferred
    time for focused work (others keep out of them first); `personal` is protected own time."""
    out = []
    days = s.get("work_days")
    if isinstance(days, str):
        days = [x.strip()[:3].lower() for x in days.split(",") if x.strip()]
    ws, we = _hhmm(s.get("work_start")), _hhmm(s.get("work_end"))
    if days and ws and we and wd in days:
        out.append({"activities": ["focus"], "start": ws, "end": we, "strength": "preferred",
                    "allows": None, "condition": None, "source": "stated"})
    for a, b in _windows(s.get("focus")):
        out.append({"activities": ["focus"], "start": a, "end": b, "strength": "preferred",
                    "allows": None, "condition": None, "source": "stated"})
    for a, b in _windows(s.get("personal")):
        out.append({"activities": [OWN_TIME], "start": a, "end": b, "strength": "protected",
                    "allows": None, "condition": None, "source": "stated"})
    return out


def shape_for(day: date, persona: str | None = None) -> dict:
    """The effective shape of one day: the user's entries for this weekday over the design.

    Returns times (not datetimes) — `window_for` anchors wake and bed on the ledger day. Every
    value says where it came from, so the planner and the plan block can tell a stated hour from
    an assumed one. Later entries win where two cover the same day."""
    d = design()
    s = read_shape(persona)
    wd = _WEEKDAYS[day.weekday()]

    wake = bed = None
    for e in _entries(s, "day"):
        if wd in e["days"]:
            wake = _hhmm(e.get("wake")) or wake
            bed = _hhmm(e.get("bed")) or bed
    if wake is None:
        wake = (_hhmm(s.get("wake_weekend")) if day.weekday() >= 5 else None) or _hhmm(s.get("wake"))
    if bed is None:
        bed = (_hhmm(s.get("bed_weekend")) if day.weekday() in (4, 5) else None) or _hhmm(s.get("bed"))
    wake_src = bed_src = "stated"
    qh = _quiet_hours(persona)
    if wake is None:
        wake, wake_src = (qh[1], "quiet_hours") if qh else (_hhmm(d["fallback_wake"]), "fallback")
    if bed is None:
        bed, bed_src = (qh[0], "quiet_hours") if qh else (_hhmm(d["fallback_bed"]), "fallback")

    windows = _legacy_windows(s, wd)
    for e in _entries(s, "windows"):
        if wd in e["days"]:
            windows.append({"activities": e["activities"], "start": _hhmm(e["from"]),
                            "end": _hhmm(e["to"]), "strength": e["strength"],
                            "allows": _allows_for(e["activities"], e["strength"],
                                                  e.get("allows"), d),
                            "condition": e.get("condition"), "source": "stated"})
    # One day's exceptions (review F8): "I'm free of childcare today" clears a condition;
    # "working tonight" lifts a window for that day only.
    for o in _entries(s, "day_overrides"):
        if o["date"] != day.isoformat():
            continue
        for w in windows:
            if o["what"] == "all" or o["what"] in w["activities"]:
                if o["holds"]:
                    w["condition"] = None
                else:
                    w["dropped"] = True
    windows = [w for w in windows if not w.get("dropped")]

    routines = [{"what": e["what"], "start": _hhmm(e["from"]), "end": _hhmm(e["to"]),
                 "place": e.get("place") or "", "covers": e.get("covers") or ""}
                for e in _entries(s, "routines") if wd in e["days"] and e.get("active", True)]

    stated: dict[str, dict] = {}
    for name in _MEALS:                                   # the first version's flat meal times
        raw = str(s.get(name) or "").strip().lower()
        if raw == "skip":
            stated[name] = {"name": name, "skip": True}
        elif _hhmm(raw):
            stated[name] = {"name": name, "at": raw}
    for e in _entries(s, "meals"):
        if wd in e["days"]:
            stated[e["name"]] = e
    design_meals = d.get("meals") or {}
    meals = []
    for name in list(design_meals) + [n for n in stated if n not in design_meals]:
        e, spec = stated.get(name), design_meals.get(name) or {}
        if e and e.get("skip"):
            continue
        minutes = int((e or {}).get("minutes") or spec.get("minutes") or 20)
        target = None
        if e and e.get("at"):
            target = _hhmm(e["at"])
            centre = datetime.combine(day, target)
            earliest = (centre - timedelta(minutes=15)).time()
            latest = _hhmm(e.get("latest")) or (centre + timedelta(minutes=30)).time()
            src = "stated"
        elif e and e.get("from"):
            earliest, latest, src = _hhmm(e["from"]), _hhmm(e["to"]), "stated"
        else:
            earliest, latest = _offset(spec.get("earliest"), wake), _offset(spec.get("latest"), wake)
            src = "design"
        if earliest and latest:
            meals.append({"name": name, "earliest": earliest, "latest": latest, "target": target,
                          "minutes": minutes, "when": (e or {}).get("when"), "source": src})
    meals.sort(key=lambda m: bool(m["when"]))         # a conditional meal is decided last

    children = [(_hhmm(e["from"]), _hhmm(e["to"])) for e in _entries(s, "children_home")
                if wd in e["days"]]

    mode = str(s.get("travel_mode") or d.get("travel_mode") or "transit").strip().lower()
    return {
        "day": day, "wake": wake, "bed": bed, "wake_source": wake_src, "bed_source": bed_src,
        "windows": windows, "routines": routines, "meals": meals, "children_home": children,
        "calendars": roster(persona), "event_rules": _entries(s, "event_rules"),
        "travel_mode": mode if mode in _MODES else "transit",
        "activities": d.get("activities") or {}, "default_activity": d.get("default_activity"),
        "domain_activity": d.get("domain_activity") or {},
        "activity_words": d.get("activity_words") or {},
        "window_allows": d.get("window_allows") or {}, "duties": d.get("duties") or {},
        "wind_down_excludes": list(d.get("wind_down_excludes") or []),
        "break_after_minutes": int(d.get("break_after_minutes") or 90),
        "break_minutes": int(d.get("break_minutes") or 10),
        "transition_minutes": int(d.get("transition_minutes") or 5),
        "departure_buffer_minutes": int(d.get("departure_buffer_minutes") or 10),
        "wind_down_minutes": int(d.get("wind_down_minutes") or 60),
    }


def activity_of(task: dict, shape: dict) -> tuple[str, dict]:
    """A task's activity and its attributes: stated on the task, else a word in its title the
    design names, else its domain's, else the design default (plan § 18.3)."""
    acts = shape.get("activities") or {}
    act = str(task.get("activity") or "").strip().lower()
    if act not in acts:
        low = str(task.get("what") or "").lower()
        act = next((a for a, words in (shape.get("activity_words") or {}).items()
                    if a in acts and any(re.search(r"\b" + re.escape(str(w).lower()) + r"\b", low)
                                         for w in words or [])), "")
    if act not in acts:
        dom = str(task.get("domain") or "").strip().lower()
        act = (shape.get("domain_activity") or {}).get(dom) or shape.get("default_activity") or "personal"
    return act, dict(acts.get(act) or {})


def anchor(day: date, t: time, wake: time) -> datetime:
    """A time of the ledger day `day` as a datetime. A time earlier than wake belongs to the night
    after the day, so it lands on the next date (plan § 5.3, review R1-7)."""
    dt = datetime.combine(day, t)
    if t < wake:
        dt += timedelta(days=1)
    return dt


def window_for(day: date, persona: str | None = None, shape: dict | None = None
               ) -> tuple[datetime, datetime]:
    """(wake, bed) of ledger day `day` as datetimes. A bedtime at or before wake is on the next
    date — 01:30, or the 22:00–07:00 quiet-hours fallback read the other way round."""
    sh = shape or shape_for(day, persona)
    wake_dt = datetime.combine(day, sh["wake"])
    bed_dt = datetime.combine(day, sh["bed"])
    if bed_dt <= wake_dt:
        bed_dt += timedelta(days=1)
    return wake_dt, bed_dt


def digest(persona: str | None = None) -> str:
    """For the planner's gate: has anything in the shape changed?"""
    raw = json.dumps({"s": read_shape(persona), "d": design()}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def location_sharing(persona: str | None = None) -> bool | None:
    """The user's interview answer on sending their place with messages: True, False, or None
    when never asked. The app uses it only to set a default it has not stored (plan § 8.2)."""
    raw = str(read_shape(persona).get("location_sharing") or "").strip().lower()
    return {"on": True, "off": False}.get(raw)


# --- writing ---------------------------------------------------------------------------------

def _turn() -> dict | None:
    try:
        from tools.turn_context import current
        return current()
    except Exception:  # noqa: BLE001
        return None


def _validate(field: str, value) -> tuple[object | None, str | None]:
    raw = value if isinstance(value, list) else str(value or "").strip()
    if field in ("wake", "bed", "wake_weekend", "bed_weekend", "work_start", "work_end"):
        t = _hhmm(raw)
        return (f"{t.hour:02d}:{t.minute:02d}", None) if t else (None, "a time in HH:MM form")
    if field in _MEALS:
        if str(raw).lower() == "skip":
            return "skip", None
        t = _hhmm(raw)
        return (f"{t.hour:02d}:{t.minute:02d}", None) if t else (None, "HH:MM, or 'skip'")
    if field == "work_days":
        if str(raw).lower() == "none":
            return [], None
        parts = raw if isinstance(raw, list) else [p for p in re.split(r"[,\s/]+", raw) if p]
        out = []
        for p in parts:
            d = str(p).strip().lower()[:3]
            if d not in _WEEKDAYS:
                return None, f"weekday names (mon … sun), not {p!r}"
            if d not in out:
                out.append(d)
        return (out, None) if out else (None, "at least one weekday, or 'none'")
    if field in ("focus", "personal"):
        if str(raw).lower() == "none":
            return [], None
        wins = _windows(raw)
        if not wins:
            return None, "windows like 09:00-11:30, comma-separated, or 'none'"
        return [f"{a.hour:02d}:{a.minute:02d}-{b.hour:02d}:{b.minute:02d}" for a, b in wins], None
    if field == "travel_mode":
        m = str(raw).lower()
        return (m, None) if m in _MODES else (None, ", ".join(_MODES))
    if field == "location_sharing":
        v = str(raw).lower()
        return (v, None) if v in ("on", "off") else (None, "on or off")
    return None, "a known field"


def _day_set(raw) -> tuple[list[str] | None, str | None]:
    """Any set of days — names, ranges (mon-fri), or a convenience alias. Absent means all."""
    if raw in (None, "", []):
        return list(_WEEKDAYS), None
    parts = raw if isinstance(raw, list) else [p for p in re.split(r"[,/]+|\s+and\s+", str(raw)) if p]
    out: list[str] = []
    for p in parts:
        text = str(p).strip().lower()
        if text in _DAY_ALIASES:
            days = list(_DAY_ALIASES[text])
        elif "-" in text:
            a, _, b = text.partition("-")
            a, b = a.strip()[:3], b.strip()[:3]
            if a not in _WEEKDAYS or b not in _WEEKDAYS:
                return None, f"weekday names or ranges (mon-fri), not {p!r}"
            i, j = _WEEKDAYS.index(a), _WEEKDAYS.index(b)
            days = list(_WEEKDAYS[i:j + 1]) if i <= j else list(_WEEKDAYS[i:] + _WEEKDAYS[:j + 1])
        elif text[:3] in _WEEKDAYS:
            days = [text[:3]]
        else:
            return None, f"weekday names (mon … sun), ranges (mon-fri) or 'all', not {p!r}"
        out += [d for d in days if d not in out]
    return [d for d in _WEEKDAYS if d in out], None


def _hm_text(raw) -> str | None:
    t = _hhmm(raw)
    return f"{t.hour:02d}:{t.minute:02d}" if t else None


def _text(raw, limit: int) -> str:
    return re.sub(r"\s+", " ", str(raw or "")).strip()[:limit]


def _validate_entry(section: str, raw) -> tuple[dict | None, str | None]:
    """One entry of a section, cleaned. (clean, None) or (None, what the section takes)."""
    if not isinstance(raw, dict):
        return None, f"an object — {SECTIONS.get(section, 'a known section')}"
    days, err = _day_set(raw.get("days"))
    if err:
        return None, err
    acts = design().get("activities") or {}
    if section == "day":
        wake, bed = _hm_text(raw.get("wake")), _hm_text(raw.get("bed"))
        if not (wake or bed):
            return None, "a wake and/or bed time in HH:MM form"
        return {"days": days, **({"wake": wake} if wake else {}), **({"bed": bed} if bed else {})}, None
    if section in ("windows", "children_home", "routines"):
        a, b = _hm_text(raw.get("from")), _hm_text(raw.get("to"))
        if not a or not b or a == b:
            return None, "`from` and `to` as HH:MM"
        if section == "children_home":
            return {"days": days, "from": a, "to": b}, None
        if section == "routines":
            what = _text(raw.get("what"), 80)
            if not what:
                return None, "`what` — what the routine is"
            covers = _text(raw.get("covers"), 30).lower()
            out = {"what": what, "days": days, "from": a, "to": b}
            if raw.get("place"):
                out["place"] = _text(raw["place"], 200)
            if covers:
                out["covers"] = covers
            if raw.get("active") is False:
                out["active"] = False
            return out, None
        names = raw.get("activity") or raw.get("activities")
        names = [names] if isinstance(names, str) else list(names or [])
        names = [str(n).strip().lower() for n in names if str(n).strip()]
        bad = [n for n in names if n not in acts and n != OWN_TIME]
        if not names or bad:
            return None, f"`activity` — one or more of {', '.join(acts)}"
        strength = str(raw.get("strength") or "preferred").strip().lower()
        if strength not in _STRENGTHS:
            return None, f"`strength` — {', '.join(_STRENGTHS)}"
        out = {"activities": names, "days": days, "from": a, "to": b, "strength": strength}
        allows = raw.get("allows")
        if isinstance(allows, str) and allows.strip().lower() == "none":
            out["allows"] = "none"
        elif isinstance(allows, dict):
            flt = {}
            if "device" in allows:
                flt["device"] = bool(allows["device"])
            if allows.get("concentration") in ("light", "heavy"):
                flt["concentration"] = allows["concentration"]
            if "solo" in allows:
                flt["solo"] = bool(allows["solo"])
            out["allows"] = flt
        if raw.get("condition"):
            out["condition"] = _text(raw["condition"], 120)
        return out, None
    if section == "meals":
        name = _text(raw.get("name"), 30).lower()
        if not name:
            return None, "`name` — breakfast, lunch, dinner, or the user's own (snack)"
        if raw.get("skip") is True or str(raw.get("skip")).lower() == "true":
            return {"name": name, "days": days, "skip": True}, None
        out: dict = {"name": name, "days": days}
        at, frm, to = _hm_text(raw.get("at")), _hm_text(raw.get("from")), _hm_text(raw.get("to"))
        if at:
            out["at"] = at
            if _hm_text(raw.get("latest")):
                out["latest"] = _hm_text(raw.get("latest"))
        elif frm and to:
            out.update({"from": frm, "to": to})
        else:
            return None, "`at` (HH:MM, with an optional `latest`), or `from` and `to`, or skip"
        if raw.get("minutes") is not None:
            try:
                out["minutes"] = max(5, min(180, int(raw["minutes"])))
            except (TypeError, ValueError):
                return None, "`minutes` as a number"
        when = raw.get("when")
        if isinstance(when, dict) and when.get("meal") and _hm_text(when.get("ends_by")):
            out["when"] = {"meal": _text(when["meal"], 30).lower(),
                           "ends_by": _hm_text(when["ends_by"])}
        elif when:
            return None, "`when` as {meal, ends_by: HH:MM} — eaten only if that meal ends by then"
        return out, None
    if section == "event_rules":
        words = raw.get("match")
        words = [words] if isinstance(words, str) else list(words or [])
        words = [_text(w, 40) for w in words if _text(w, 40)]
        answer = str(raw.get("answer") or "").strip().lower()
        if not words or answer not in _ANSWERS:
            return None, f"`match` (words in the title) and `answer` — {', '.join(_ANSWERS)}"
        out = {"match": words, "answer": answer}
        if raw.get("duty"):
            out["duty"] = _text(raw["duty"], 40).lower()
        load = str(raw.get("load") or "full").strip().lower()
        out["load"] = load if load in _LOADS else "full"
        return out, None
    if section == "day_overrides":
        try:
            when = date.fromisoformat(str(raw.get("date") or "")).isoformat()
        except ValueError:
            return None, "`date` as YYYY-MM-DD"
        what = str(raw.get("what") or "").strip().lower()
        if what != "all" and what not in acts:
            return None, f"`what` — 'all' or one of {', '.join(acts)}"
        holds = raw.get("holds")
        if not isinstance(holds, bool):
            holds = str(holds).strip().lower() in ("true", "yes", "1")
        return {"date": when, "what": what, "holds": holds}, None
    if section == "calendars":
        role = str(raw.get("role") or "").strip().lower()
        cid = _text(raw.get("id"), 300)
        if not cid or role not in _ROLES:
            return None, f"`id` (the calendar's, as the plan names it) and `role` — {', '.join(_ROLES)}"
        return {"id": cid, "name": _text(raw.get("name"), 80), "role": role}, None
    return None, "a known section"


def _entry_key(section: str, e: dict):
    """Which stored entry a new one replaces."""
    return {
        "day": lambda: tuple(e["days"]),
        # Strength is part of what a window IS: "admin preferred 10–3" and "admin only 10–5:30"
        # both start at 10 and are two entries.
        "windows": lambda: (tuple(e["activities"]), tuple(e["days"]), e["from"], e["strength"]),
        "routines": lambda: e["what"].lower(),
        "meals": lambda: (e["name"], tuple(e["days"])),
        "event_rules": lambda: tuple(sorted(w.lower() for w in e["match"])),
        "children_home": lambda: (tuple(e["days"]), e["from"]),
        "day_overrides": lambda: (e["date"], e["what"]),
    }[section]()


def _write(data: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def set_day_shape(section: str | None = None, entry=None, evidence: str = "",
                  date: str | None = None, remove: bool = False,
                  field: str | None = None, value=None) -> str:
    """Record one fact about the shape of the user's day, in their own words: one entry of one
    section, replacing the entry it matches. `date` makes a one-day override (review F8);
    `remove` deletes the matching entry. The first version's `field`/`value` still work."""
    section = str(section or field or "").strip().lower()
    entry = value if entry is None else entry
    if section not in SECTIONS and section not in FIELDS:
        return (f"error: `section` must be one of {', '.join(SECTIONS)}, not {section!r}. "
                f"Nothing was written.")
    turn = _turn()
    if turn is not None and not turn.get("user_turn"):
        return ("error: not recorded — the shape of the user's day changes only on their own "
                "word, and this turn has nothing from them. Nothing was changed.")
    evidence = str(evidence or "").strip()
    if not evidence:
        return ("error: `evidence` is required — quote what the user said. Nothing was written.")
    data = read_shape()
    stamp = datetime.now().isoformat(timespec="seconds")

    if section in _LIST_SECTIONS or section == "calendars":
        if isinstance(entry, str):
            try:
                entry = json.loads(entry)
            except ValueError:
                return f"error: `entry` for {section} is {SECTIONS[section]}. Nothing was written."
        if date:
            entry = {**(entry or {}), "date": date}
            if section != "day_overrides":
                return ("error: `date` makes a one-day override — use section day_overrides. "
                        "Nothing was written.")
        clean, why = _validate_entry(section, entry)
        if why:
            return f"error: `{section}` takes {why}. Nothing was written."
        if section == "calendars":
            cals = data.get("calendars") if isinstance(data.get("calendars"), dict) else {}
            old = cals.get(clean["id"])
            if remove:
                cals.pop(clean["id"], None)
            else:
                cals[clean["id"]] = {"name": clean["name"], "role": clean["role"]}
            data["calendars"] = cals
            shown = f"{clean['name'] or clean['id']} → {'removed' if remove else clean['role']}"
        else:
            items = [x for x in (data.get(section) or []) if isinstance(x, dict)]
            key = _entry_key(section, clean)
            kept, old = [], None
            for x in items:
                cx, _ = _validate_entry(section, x)
                if cx is not None and _entry_key(section, cx) == key:
                    old = x
                    continue
                kept.append(x)
            if not remove:
                kept.append(clean)
            if section == "day_overrides":          # a past day's exception is history
                cutoff = (datetime.now().date() - timedelta(days=7)).isoformat()
                kept = [x for x in kept if str(x.get("date") or "") >= cutoff]
            data[section] = kept
            shown = ("removed " if remove else "") + json.dumps(clean, ensure_ascii=False)
    else:
        clean, why = _validate(section, entry)
        if why:
            return f"error: `{section}` takes {why}. Nothing was written."
        old = data.get(section)
        data[section] = clean
        shown = ", ".join(clean) if isinstance(clean, list) else clean
    hist = data.setdefault("history", [])
    hist.append({"section": section, "value": None if remove else clean, "was": old,
                 "at": stamp, "evidence": evidence[:200]})
    data["history"] = hist[-30:]
    _write(data)
    return f"recorded: {section} — {shown or 'none'}"


SET_DAY_SHAPE_SCHEMA = {
    "name": "set_day_shape",
    "description": (
        "Record one fact about the shape of the user's day, when THEY say it: when it starts and "
        "ends, when each kind of activity goes (focus, creative, admin, busy, errands, household, "
        "personal, health, family, social, entertainment, rest — protected, strong or "
        "preferred), standing routines, meals, what each of their calendars is, standing answers "
        "for kinds of event, when someone in their care is home, how they get around, whether "
        "their phone sends its place. Every entry names its days — any set, no weekday/weekend "
        "assumption. A one-day exception (\"I'm free of childcare today\") is a day_overrides "
        "entry with `date`. Only on their own word — quote it as evidence. One entry per call; "
        "it replaces the entry it matches."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {"type": "string", "enum": list(SECTIONS),
                        "description": "; ".join(f"{k}: {v}" for k, v in SECTIONS.items())},
            "entry": {"description": "The entry: an object for every section but travel_mode "
                                     "and location_sharing, which take a string."},
            "evidence": {"type": "string", "description": "The user's words that say it."},
            "date": {"type": "string", "description": "YYYY-MM-DD — only for day_overrides."},
            "remove": {"type": "boolean", "description": "Delete the entry this one matches."},
        },
        "required": ["section", "entry", "evidence"],
    },
}


# --- setup: a baseline, from the command line (plan § 18.4, R2-2) -----------------------------

SETUP_EVIDENCE = "stated by the user in setup"


def list_calendars(persona: str | None = None) -> tuple[list[dict], str]:
    """Every calendar the account exposes: id, name, whether it is the one Metatron writes. One
    CalDAV discovery — never on a reply path."""
    from tools.caldav import _calendar_set, _collection_key, _load_config
    cfg = _load_config(persona)
    auth_cfg = cfg.get("auth", {})
    cals, status = _calendar_set(cfg, (auth_cfg.get("username", ""), auth_cfg.get("password", "")))
    return [{"id": _collection_key(c["url"]), "name": c["name"], "writable": c["writable"]}
            for c in cals], status


def apply_baseline(doc: dict, calendars: list[dict] | None = None, dry_run: bool = False
                   ) -> tuple[list[str], list[str]]:
    """Write a baseline file's entries through the same validator a model's writes go through.
    Everything is checked before anything is written. `calendars` in the file is {name: role};
    names resolve to ids against `calendars` (the account's), and every calendar the file does
    not name is recorded as the user's — D1: all calendars default to the user. Returns
    (written, errors)."""
    plan: list[tuple[str, object]] = []
    errors: list[str] = []
    for section in SECTIONS:
        if section not in doc:
            continue
        val = doc[section]
        if section == "calendars":
            continue
        if section in _LIST_SECTIONS:
            for raw in val or []:
                clean, why = _validate_entry(section, raw)
                if why:
                    errors.append(f"{section}: {why} — {raw!r}")
                else:
                    plan.append((section, raw))
        else:
            clean, why = _validate(section, val)
            if why:
                errors.append(f"{section}: {why}")
            else:
                plan.append((section, val))
    unknown = [k for k in doc if k not in SECTIONS]
    errors += [f"unknown section {k!r}" for k in unknown]
    if "calendars" in doc or calendars:
        named = {str(k).strip().lower(): str(v).strip().lower()
                 for k, v in (doc.get("calendars") or {}).items()}
        by_name = {c["name"].strip().lower(): c for c in calendars or []}
        for name, role in named.items():
            if name not in by_name:
                errors.append(f"calendars: no calendar named {name!r} — the account has "
                              f"{', '.join(c['name'] for c in calendars or []) or 'none listed'}")
            elif role not in _ROLES:
                errors.append(f"calendars: {name!r} → {role!r}; a role is {', '.join(_ROLES)}")
        for c in calendars or []:
            role = "mine" if c["writable"] else named.get(c["name"].strip().lower(), "mine")
            plan.append(("calendars", {"id": c["id"], "name": c["name"], "role": role}))
    if errors or dry_run:
        return [f"{s}: {json.dumps(e, ensure_ascii=False)}" for s, e in plan], errors
    written = [set_day_shape(s, e, evidence=SETUP_EVIDENCE) for s, e in plan]
    return written, [w for w in written if w.startswith("error")]


def _main(argv: list[str]) -> int:
    import argparse
    from core.persona import persona_scope
    ap = argparse.ArgumentParser(prog="python3 -m tools.day_shape")
    ap.add_argument("--persona", required=True)
    ap.add_argument("command", choices=("calendars", "apply", "show"))
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    with persona_scope(a.persona):
        if a.command == "calendars":
            cals, status = list_calendars()
            known = roster()
            print(f"discovery: {status}")
            for c in cals:
                role = "mine (writable)" if c["writable"] else (known.get(c["id"]) or {}).get("role", "—")
                print(f"  {c['name']!r:40} {role:16} {c['id']}")
            return 0
        if a.command == "apply":
            if not a.arg:
                print("apply needs a baseline file")
                return 2
            doc = yaml.safe_load(Path(a.arg).read_text()) or {}
            cals = None
            if "calendars" in doc:
                cals, status = list_calendars()
                if status != "ok":
                    print(f"calendar discovery {status} — not applying a roster built on it")
                    return 1
            written, errors = apply_baseline(doc, cals, dry_run=a.dry_run)
            for line in written:
                print(("  would write " if a.dry_run else "  ") + line)
            for e in errors:
                print(f"  ERROR {e}")
            return 1 if errors else 0
        day = date.fromisoformat(a.arg) if a.arg else date.today()
        print(json.dumps(shape_for(day), indent=1, default=str))
        return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
