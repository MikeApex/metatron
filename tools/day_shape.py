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

Plan: archive/plans/day_planner_plan_2026-10-24.md § 4.2. The planner (tools/day_plan.py) reads
`shape_for()` and `window_for()`; nothing here decides what goes in the day.
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
}

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_MODES = ("transit", "walking", "driving", "cycling")
_MEALS = ("breakfast", "lunch", "dinner")

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


def shape_for(day: date, persona: str | None = None) -> dict:
    """The effective shape of one day: the user's statements over the design.

    Returns times (not datetimes) — `window_for` anchors wake and bed on the ledger day. Every
    value says where it came from, so the planner and the plan block can tell a stated hour from
    an assumed one."""
    d = design()
    s = read_shape(persona)
    weekend_morning = day.weekday() >= 5          # Sat, Sun
    late_night = day.weekday() in (4, 5)          # Fri, Sat nights
    wake = _hhmm(s.get("wake_weekend")) if weekend_morning else None
    wake = wake or _hhmm(s.get("wake"))
    bed = _hhmm(s.get("bed_weekend")) if late_night else None
    bed = bed or _hhmm(s.get("bed"))
    wake_src = bed_src = "stated"
    qh = _quiet_hours(persona)
    if wake is None:
        wake, wake_src = (qh[1], "quiet_hours") if qh else (_hhmm(d["fallback_wake"]), "fallback")
    if bed is None:
        bed, bed_src = (qh[0], "quiet_hours") if qh else (_hhmm(d["fallback_bed"]), "fallback")

    work = None
    days = s.get("work_days")
    if isinstance(days, str):
        days = [x.strip()[:3].lower() for x in days.split(",") if x.strip()]
    ws, we = _hhmm(s.get("work_start")), _hhmm(s.get("work_end"))
    if days and ws and we and _WEEKDAYS[day.weekday()] in days:
        work = (ws, we)

    meals = []
    for name in _MEALS:
        spec = (d.get("meals") or {}).get(name) or {}
        stated = s.get(name)
        if str(stated or "").strip().lower() == "skip":
            continue
        minutes = int(spec.get("minutes") or 20)
        t = _hhmm(stated)
        if t:
            centre = datetime.combine(day, t)
            earliest = (centre - timedelta(minutes=15)).time()
            latest = (centre + timedelta(minutes=30)).time()
            src = "stated"
        else:
            earliest, latest = _offset(spec.get("earliest"), wake), _offset(spec.get("latest"), wake)
            src = "design"
        if earliest and latest:
            meals.append({"name": name, "earliest": earliest, "latest": latest,
                          "minutes": minutes, "source": src})

    mode = str(s.get("travel_mode") or d.get("travel_mode") or "transit").strip().lower()
    return {
        "day": day, "wake": wake, "bed": bed, "wake_source": wake_src, "bed_source": bed_src,
        "work": work, "focus": _windows(s.get("focus")), "personal": _windows(s.get("personal")),
        "meals": meals, "travel_mode": mode if mode in _MODES else "transit",
        "break_after_minutes": int(d.get("break_after_minutes") or 90),
        "break_minutes": int(d.get("break_minutes") or 10),
        "transition_minutes": int(d.get("transition_minutes") or 5),
        "departure_buffer_minutes": int(d.get("departure_buffer_minutes") or 10),
        "wind_down_minutes": int(d.get("wind_down_minutes") or 60),
    }


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


def set_day_shape(field: str, value, evidence: str = "") -> str:
    """Record one fact about the shape of the user's day, in their own words."""
    field = str(field or "").strip().lower()
    if field not in FIELDS:
        return (f"error: `field` must be one of {', '.join(FIELDS)}, not {field!r}. "
                f"Nothing was written.")
    turn = _turn()
    if turn is not None and not turn.get("user_turn"):
        return ("error: not recorded — the shape of the user's day changes only on their own "
                "word, and this turn has nothing from them. Nothing was changed.")
    evidence = str(evidence or "").strip()
    if not evidence:
        return ("error: `evidence` is required — quote what the user said. Nothing was written.")
    clean, why = _validate(field, value)
    if why:
        return f"error: `{field}` takes {why}. Nothing was written."
    path = _path()
    data = read_shape()
    old = data.get(field)
    data[field] = clean
    hist = data.setdefault("history", [])
    hist.append({"field": field, "value": clean, "was": old,
                 "at": datetime.now().isoformat(timespec="seconds"), "evidence": evidence[:200]})
    data["history"] = hist[-30:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    shown = ", ".join(clean) if isinstance(clean, list) else clean
    return f"recorded: {field} = {shown or 'none'}"


SET_DAY_SHAPE_SCHEMA = {
    "name": "set_day_shape",
    "description": (
        "Record one fact about the shape of the user's day, when THEY say it: when they wake and "
        "go to bed, their working days and hours, when they focus best, time that is theirs and "
        "protected, when they eat, how they get around, and whether their phone sends its place "
        "with messages. Their day is planned around these. Only on their own word — quote it as "
        "evidence. One field per call."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "field": {"type": "string", "enum": list(FIELDS),
                      "description": "; ".join(f"{k}: {v}" for k, v in FIELDS.items())},
            "value": {"type": "string", "description": "The value, in the form the field takes."},
            "evidence": {"type": "string", "description": "The user's words that say it."},
        },
        "required": ["field", "value", "evidence"],
    },
}
