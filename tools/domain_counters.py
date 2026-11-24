"""
tools/domain_counters.py — the counts a specialist's flags rest on, computed by code
(instructions-to-code Stage 4, #14, M17 and the #15 evidence half).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #14, as amended
by its "Build-time amendments" 2 and 3. Thresholds and windows: config/modules/counters.yaml.

Why code: "poor sleep two nights running" is a count over dated records. A model reading five
days of logs miscounts it, and pays a turn for it; code reads the day files and knows.

Two moments, split by what this turn can change (S3):

- **Before dispatch** (`evidence_block`, handed to the specialist in its PREFETCHED block):
  completed days only, yesterday back — nothing in the current message can contradict them.
  The one exception is Physical Health's "food logged today: yes/no" (amendment 2), read from
  `health.food_logged` AND today's meals log by the same function code uses after the return.
- **After the specialist returns** (`counted_signals`, at `_run_single_agent`'s post-return hook,
  every path — amendment 3): today's thresholds from a RE-READ of today's log, so a night's
  sleep the specialist recorded this turn counts. The Diarist writes after the blocking
  specialists, so a reading it mostly writes (meals) is worded "as of before this turn's diary
  write" and is never a flag (review L7).

Rules that hold everywhere here:
- Only leaves stamped `_written_on: user` count (tools/logger._write_provenance). A log the
  system wrote during a scheduled check-in is not evidence about the user.
- Code SETS only SLEEP_POOR, SLEEP_ACUTE and ENERGY_CRASH (DECISION 4-4). Everything else is a
  "last logged N days ago" line. Code adds; it never clears, never edits a specialist's output,
  and never emits MUST_SURFACE, CLINICAL_CONCERN or MEDICATION_MISSED_CRITICAL.
- M17: a substance is reported as "last logged use: <date>"; never "N days clean", a streak or
  abstinence — no log is not evidence of not using (physical_health.md § Proposing a standing
  fact).

Never raises: every public function returns "" on any failure, so a counter can never cost a
turn.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "modules" / "counters.yaml"

_DEFAULTS: dict = {
    "window_days": 14, "last_logged_days": 30, "cessation_days": 90,
    "sleep_poor_hours": 6, "sleep_poor_run": 2, "sleep_acute_hours": 4, "energy_crash_run": 2,
    "food_cutoff": "14:00",
    "sleep_missing_days": 2, "exercise_gap_days": 5, "leisure_gap_days": 5,
    "learning_gap_days": 14,
    "owners": {
        "physical_health": ["SLEEP_POOR", "SLEEP_ACUTE", "ENERGY_CRASH", "FOOD_NOT_LOGGED",
                            "SLEEP_MISSING", "EXERCISE_GAP", "CESSATION"],
        "mental_wellbeing": ["SLEEP_CONCERN", "MOOD_LOW_DAYS", "PRACTICE_LAPSE"],
        "recreation_hobbies": ["LEISURE_GAP", "HOBBY_LAPSE"],
        "learning_growth": ["LEARNING_GAP"],
    },
}

# Code may SET these three, and only these (DECISION 4-4).
CODE_FLAGS = ("SLEEP_POOR", "SLEEP_ACUTE", "ENERGY_CRASH")

_WRITTEN_ON = "_written_on"
_SUBSTANCE_TYPES = ("alcohol", "tobacco", "nicotine", "other")

PREFETCH_HEADING = ("COUNTED EVIDENCE (computed by code from the logs of completed days — only "
                    "what was recorded on the user's own turns; weigh it, judge the flag "
                    "yourself)")
SIGNALS_HEADING = ("COUNTED SIGNALS (computed by code from the logs after the specialists' "
                   "writes this turn; the diary entry for this turn is written after this — "
                   "flags here stand even if no specialist raised them, evidence lines do not)")


def load_config() -> dict:
    cfg = {**_DEFAULTS, "owners": dict(_DEFAULTS["owners"])}
    try:
        import yaml
        raw = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                if k == "owners" and isinstance(v, dict):
                    cfg["owners"] = {str(a): list(c or []) for a, c in v.items()}
                elif v is not None:
                    cfg[k] = v
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[counters] config unreadable, using defaults: {exc}")
    return cfg


def owners() -> set[str]:
    return set(load_config()["owners"])


# --- reading the day files: the persona's day, not the server's file date ---------------------
#
# A day file is named by the SERVER's calendar (write_log's `date.today()`), but "today" for the
# user is their own: their zone and their `day_starts` boundary. Changing write_log/read_log's
# defaults is out of scope here, so the counters place each field the way
# tools/obligations._logged_entries places a dose — by its write time, converted to the persona's
# zone and day boundary, read from the same-date file and both neighbours. A field with no write
# time (written before stamps existed) keeps its file's date.

def _day_offset() -> timedelta:
    """The bound persona's `day_starts` boundary (tools.obligations), or midnight."""
    try:
        from tools.obligations import _day_starts
        return _day_starts()
    except Exception:  # noqa: BLE001
        return timedelta(0)


def ledger_day(now: datetime, offset: timedelta | None = None) -> date:
    """The persona's ledger day for a persona-local moment (tools.obligations' own reckoning:
    its `day_starts` boundary applied). `offset` is that boundary, resolved once by a caller
    placing many fields. Never raises."""
    try:
        off = _day_offset() if offset is None else offset
        return (now.replace(tzinfo=None) - off).date()
    except Exception:  # noqa: BLE001
        return now.date()


def _placement(cache: dict | None) -> tuple:
    """(zone, day_starts offset) for the bound persona, resolved ONCE per block (kept in the
    block's cache), never per field."""
    if cache is not None and "_placement" in cache:
        return cache["_placement"]
    got = (_persona_zone(), _day_offset())
    if cache is not None:
        cache["_placement"] = got
    return got


def _persona_zone():
    try:
        from tools.ambient import _get_timezone
        tz = _get_timezone()
        if tz:
            from zoneinfo import ZoneInfo
            return ZoneInfo(tz)
    except Exception:  # noqa: BLE001
        pass
    return None


def _place(stamp: Any, file_day: date, zone, offset: timedelta) -> date:
    """The persona's ledger day of a field in `file_day`'s file.

    Placed by its `_written_at` stamp ONLY when the stamp's server-calendar date is the file's
    own date — a default-date write, filed under whatever day the server's clock said. A write
    whose file date differs from its stamp was given an explicit `log_date` (a backfill: "I
    slept badly on Tuesday"), and its file date is the day it is about. No stamp: the file's
    date. The stamp is the server's local time (write_log's `datetime.now()`), converted to the
    persona's zone."""
    if not stamp:
        return file_day
    try:
        dt = datetime.fromisoformat(str(stamp))
    except ValueError:
        return file_day
    if dt.date() != file_day:
        return file_day
    if dt.tzinfo is None:
        dt = dt.astimezone()                     # the server's own zone
    if zone is not None:
        dt = dt.astimezone(zone)
    return ledger_day(dt, offset)


def _read_file(d: date, cache: dict | None) -> dict:
    key = d.isoformat()
    if cache is not None and key in cache:
        return cache[key]
    try:
        from tools.logger import read_log
        entry = read_log(key)
        entry = entry if isinstance(entry, dict) else {}
    except Exception:  # noqa: BLE001
        entry = {}
    if cache is not None:
        cache[key] = entry
    return entry


def _set_path(node: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value


def day_entry(d: date, cache: dict | None = None) -> dict:
    """The persona's day `d` as one log entry: every field from the files dated d−1, d and d+1
    that `_place` puts on `d` — a default-date write by its write time in the persona's zone and
    day boundary, a backdated write or an unstamped field by its file's date. The latest write
    of a field wins. Carries its own
    `_written_on` / `_written_at` maps, so provenance reads exactly as on a day file."""
    from tools.logger import _WRITTEN_AT_KEY, _leaf_paths
    zone, offset = _placement(cache)
    best: dict[str, tuple] = {}
    for off in (-1, 0, 1):
        file_day = d + timedelta(days=off)
        entry = _read_file(file_day, cache)
        if not entry:
            continue
        stamps = entry.get(_WRITTEN_AT_KEY) if isinstance(entry.get(_WRITTEN_AT_KEY), dict) else {}
        origins = entry.get(_WRITTEN_ON) if isinstance(entry.get(_WRITTEN_ON), dict) else {}
        for path in _leaf_paths(entry):
            stamp = stamps.get(path)
            if _place(stamp, file_day, zone, offset) != d:
                continue
            rank = (str(stamp or ""), off)
            if path not in best or rank > best[path][0]:
                best[path] = (rank, _get(entry, path), origins.get(path), stamp)
    out: dict = {}
    on: dict = {}
    at: dict = {}
    for path, (_, value, origin, stamp) in sorted(best.items()):
        _set_path(out, path, value)
        if origin:
            on[path] = origin
        if stamp:
            at[path] = stamp
    if best:
        out["date"] = d.isoformat()
    if on:
        out[_WRITTEN_ON] = on
    if at:
        out[_WRITTEN_AT_KEY] = at
    return out


def _read_day(d: date, cache: dict | None = None) -> dict:
    return day_entry(d, cache)


def _get(entry: dict, path: str) -> Any:
    cur: Any = entry
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _user(entry: dict, path: str) -> Any:
    """The value at `path` only when that leaf was written on a real user turn, else None."""
    origins = entry.get(_WRITTEN_ON) or {}
    if not isinstance(origins, dict) or origins.get(path) != "user":
        return None
    return _get(entry, path)


def _user_any(entry: dict, prefix: str) -> bool:
    """True when any leaf at or under `prefix` was written on a real user turn and holds a
    value (a block written as all-nulls says nothing happened)."""
    origins = entry.get(_WRITTEN_ON) or {}
    if not isinstance(origins, dict):
        return False
    for path, origin in origins.items():
        if origin != "user" or not (path == prefix or path.startswith(prefix + ".")):
            continue
        if _get(entry, path) not in (None, "", [], {}, "null", False):
            return True
    return False


def _stamped(entry: dict) -> bool:
    return isinstance(entry.get(_WRITTEN_ON), dict) and bool(entry.get(_WRITTEN_ON))


def _days_back(today: date, n: int, include_today: bool = False,
               cache: dict | None = None) -> list[tuple[date, dict]]:
    """[(day, entry)], newest first: today (when asked) then yesterday back n days, each the
    persona's day (day_entry)."""
    start = 0 if include_today else 1
    return [(today - timedelta(days=i), _read_day(today - timedelta(days=i), cache))
            for i in range(start, n + 1)]


def _ago_text(today: date, d: date) -> str:
    n = _ago(today, d)
    return "today" if n == 0 else f"{n} day{'s' if n != 1 else ''} ago"


def _counting_from(days: list[tuple[date, dict]]) -> str:
    """The honesty line on a window that has not filled since provenance started ("" once it
    has): logs written before the stamp shipped are not counted, so a gap may only be the
    window still filling."""
    stamped = [d for d, e in days if _stamped(e)]
    if not stamped:
        return ("counted from logs written on the user's own turns — none in this window yet, "
                "so a gap above may only mean counting has just started")
    first = min(stamped)
    oldest = min(d for d, _ in days)
    return (f"counting from {first.isoformat()} — earlier logs are not counted"
            if first > oldest else "")


def _with_note(lines: list[str], days: list[tuple[date, dict]]) -> list[str]:
    note = _counting_from(days)
    return lines + [note] if note else lines


def _last_logged(days: list[tuple[date, dict]], test) -> date | None:
    for d, e in days:              # newest first
        try:
            if test(e):
                return d
        except Exception:  # noqa: BLE001
            continue
    return None


def _ago(today: date, d: date) -> int:
    return (today - d).days


def _low(value: Any) -> bool:
    return str(value or "").strip().lower() == "low"


def _poor_night(entry: dict, hours_floor: float) -> bool | None:
    """True/False for a logged night, None for an unlogged one (which breaks a run)."""
    hours = _user(entry, "health.sleep_hours")
    quality = _user(entry, "health.sleep_quality")
    if hours in (None, "") and quality in (None, "", "null"):
        return None
    try:
        if hours not in (None, "") and float(hours) < hours_floor:
            return True
    except (TypeError, ValueError):
        pass
    return str(quality or "").strip().lower() == "poor"


def _run(days: list[tuple[date, dict]], test) -> int:
    """Consecutive days from the newest, each `test(entry)` True; None (unlogged) breaks it."""
    n = 0
    for _, e in days:
        r = test(e)
        if r is not True:
            break
        n += 1
    return n


# --- food (amendment 2: one source of truth) --------------------------------------------------

def food_logged_today(today: date, cache: dict | None = None) -> bool:
    """True when the persona's today has `health.food_logged` set on a user turn, OR the meals
    log has an entry for today. Both Physical Health's pre-dispatch line and code's post-return
    FOOD_NOT_LOGGED evidence use this one function."""
    entry = _read_day(today, cache)
    if _user(entry, "health.food_logged") not in (None, False, "", "false", "no", "null"):
        return True
    try:
        from tools import data_objects as _DO
        o = _DO.resolve("meals")
        if o is not None:
            got = _DO.read_entries(o, since=today.isoformat(), until=today.isoformat())
            if got.get("entries"):
                return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[counters] meals log unreadable: {exc}")
    return False


def _after_cutoff(now: datetime, cutoff: str) -> bool:
    try:
        hh, mm = (int(x) for x in str(cutoff).split(":", 1))
    except ValueError:
        hh, mm = 14, 0
    return (now.hour, now.minute) >= (hh, mm)


# --- M17: substance use, last logged ----------------------------------------------------------

def _substance_types(entry: dict) -> set[str]:
    rows = _user(entry, "health.substances_logged")
    out: set[str] = set()
    for r in rows if isinstance(rows, list) else []:
        t = str((r or {}).get("type") if isinstance(r, dict) else r or "").strip().lower()
        if t:
            out.add(t if t in _SUBSTANCE_TYPES else "other")
    return out


def cessation_lines(today: date, cfg: dict | None = None) -> list[str]:
    """Per substance type logged in the last `cessation_days`: its last logged use and how many
    days have a health log since. Never "clean", never a streak (M17)."""
    cfg = cfg or load_config()
    days = _days_back(today, int(cfg["cessation_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    lines: list[str] = []
    for kind in _SUBSTANCE_TYPES:
        last = _last_logged(days, lambda e, k=kind: k in _substance_types(e))
        if last is None:
            continue
        since = sum(1 for d, e in days if d > last and _user_any(e, "health"))
        lines.append(f"{kind} — last logged use: {last.isoformat()} ({_ago_text(today, last)}); "
                     f"days with a health log since: {since}")
    return lines


# --- pre-dispatch evidence ---------------------------------------------------------------------

def _ph_evidence(today: date, cfg: dict) -> list[str]:
    # "Last logged" lines include today (something logged this morning is not a gap); runs
    # and counts stay on completed days.
    span = _days_back(today, int(cfg["last_logged_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    days = span[1:]
    n = int(cfg["last_logged_days"])
    lines = []
    last = _last_logged(span, lambda e: _poor_night(e, float(cfg["sleep_poor_hours"])) is not None)
    lines.append(
        (f"SLEEP_MISSING evidence: sleep last logged {_ago_text(today, last)}"
         if last else f"SLEEP_MISSING evidence: sleep not logged in the last {n} days")
        + f" (file threshold {cfg['sleep_missing_days']})")
    run = _run(days, lambda e: _poor_night(e, float(cfg["sleep_poor_hours"])))
    if run:
        lines.append(f"nights under {cfg['sleep_poor_hours']} h or poor, consecutive to "
                     f"yesterday: {run}")
    last = _last_logged(span, lambda e: _user_any(e, "health.exercise"))
    lines.append(
        (f"EXERCISE_GAP evidence: exercise last logged {_ago_text(today, last)}"
         if last else f"EXERCISE_GAP evidence: exercise not logged in the last {n} days")
        + f" (threshold {cfg['exercise_gap_days']} if exercise is one of the user's goals — "
          f"that condition is yours to judge)")
    for c in cessation_lines(today, cfg):
        lines.append(f"CESSATION evidence: {c}")
    lines.append("food logged today: " + ("yes" if food_logged_today(today, cfg.get("_cache"))
                                          else "no")
                 + " (health.food_logged or the meals log; as of before this turn — raise "
                   "FOOD_NOT_LOGGED only when this says no and the message does not mention "
                   "eating)")
    return _with_note(lines, span)


def _mw_evidence(today: date, cfg: dict) -> list[str]:
    win = int(cfg["window_days"])
    span = _days_back(today, int(cfg["last_logged_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    days = span[1:]
    lines = []
    run = _run(days, lambda e: _poor_night(e, float(cfg["sleep_poor_hours"])))
    lines.append(f"SLEEP_CONCERN evidence: nights logged under {cfg['sleep_poor_hours']} h or "
                 f"poor, consecutive to yesterday: {run}")
    low = sum(1 for _, e in days[:win] if _low(_user(e, "wellbeing.mood")))
    logged = sum(1 for _, e in days[:win] if _user(e, "wellbeing.mood") not in (None, ""))
    lines.append(f"mood logged low on {low} of the last {win} days ({logged} with a mood "
                 f"logged; how much that weighs is yours to judge)")
    practices: dict[str, date] = {}
    for d, e in span:
        rows = _user(e, "wellbeing.practices_active")
        for p in rows if isinstance(rows, list) else []:
            name = str(p or "").strip()
            if name and name.lower() not in {k.lower() for k in practices}:
                practices[name] = d
    for name, d in sorted(practices.items(), key=lambda kv: kv[1]):
        lines.append(f"PRACTICE_LAPSE evidence: {name} last listed active "
                     f"{_ago_text(today, d)}")
    return _with_note(lines, span)


def _rec_evidence(today: date, cfg: dict) -> list[str]:
    days = _days_back(today, int(cfg["last_logged_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    n = int(cfg["last_logged_days"])
    last = _last_logged(days, lambda e: _user_any(e, "recreation"))
    lines = [(f"LEISURE_GAP evidence: leisure last logged {_ago_text(today, last)}"
              if last else f"LEISURE_GAP evidence: leisure not logged in the last {n} days")
             + f" (threshold {cfg['leisure_gap_days']}); this is recorded only when the leisure "
               f"specialist was consulted"]
    seen: dict[str, date] = {}
    for d, e in days:
        rows = _user(e, "recreation.activities")
        for a in rows if isinstance(rows, list) else []:
            if not isinstance(a, dict) or str(a.get("type") or "").lower() == "obligated":
                continue
            desc = str(a.get("description") or "").strip()[:60]
            if desc and desc.lower() not in {k.lower() for k in seen}:
                seen[desc] = d
    for desc, d in sorted(seen.items(), key=lambda kv: kv[1])[:6]:
        lines.append(f"HOBBY_LAPSE evidence: {desc} last logged {_ago_text(today, d)}")
    return _with_note(lines, days)


def _lg_evidence(today: date, cfg: dict) -> list[str]:
    days = _days_back(today, int(cfg["last_logged_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    n = int(cfg["last_logged_days"])
    last = _last_logged(days, lambda e: _user_any(e, "learning"))
    line = ((f"LEARNING_GAP evidence: learning last logged {_ago_text(today, last)}"
             if last else f"LEARNING_GAP evidence: learning not logged in the last {n} days")
            + f" (threshold {cfg['learning_gap_days']} if growth is a stated priority); this is "
              f"recorded only when you were consulted. Skill practice dates are on the skill "
              f"habits, not here")
    return _with_note([line], days)


_EVIDENCE = {"physical_health": _ph_evidence, "mental_wellbeing": _mw_evidence,
             "recreation_hobbies": _rec_evidence, "learning_growth": _lg_evidence}


def evidence_block(agent: str, today: date) -> str:
    """The pre-dispatch evidence for `agent`, or "". Runs and counts are completed days only;
    "last logged" lines include the persona's today (something logged this morning is not a
    gap), and PH's food line is today's (amendment 2). Reads under whatever persona is bound —
    the caller binds it."""
    try:
        cfg = load_config()
        fn = _EVIDENCE.get(agent)
        if fn is None or agent not in cfg["owners"]:
            return ""
        cfg["_cache"] = {}                 # one read of each day file per block
        lines = [x for x in fn(today, cfg) if x]
        return "\n".join(f"- {x}" for x in lines) if lines else ""
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[counters] evidence for {agent} failed: {exc}")
        return ""


# --- post-return signals ------------------------------------------------------------------------

def _ph_signals(today: date, now: datetime, cfg: dict) -> tuple[list[str], list[str]]:
    days = _days_back(today, int(cfg["last_logged_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    flags: list[str] = []
    evidence: list[str] = []
    floor = float(cfg["sleep_poor_hours"])
    run = _run(days, lambda e: _poor_night(e, floor))
    if run >= int(cfg["sleep_poor_run"]):
        flags.append(f"SLEEP_POOR — sleep under {cfg['sleep_poor_hours']} h or poor on {run} "
                     f"consecutive logged nights, to last night")
    hours = _user(days[0][1], "health.sleep_hours")
    try:
        if hours not in (None, "") and float(hours) < float(cfg["sleep_acute_hours"]):
            flags.append(f"SLEEP_ACUTE — {float(hours):g} h logged for last night (under "
                         f"{cfg['sleep_acute_hours']} h)")
    except (TypeError, ValueError):
        pass
    erun = _run(days, lambda e: (None if _user(e, "health.energy") in (None, "", "null")
                                 else _low(_user(e, "health.energy"))))
    if erun >= int(cfg["energy_crash_run"]):
        flags.append(f"ENERGY_CRASH — energy logged low on {erun} consecutive logged days, to "
                     f"today")
    if _after_cutoff(now, cfg["food_cutoff"]) and not food_logged_today(today,
                                                                         cfg.get("_cache")):
        evidence.append(f"FOOD_NOT_LOGGED evidence: it is past {cfg['food_cutoff']} and there is "
                        f"no meal in the meals log today and food_logged is not set — as of "
                        f"before this turn's diary write; a meal mentioned this turn is still "
                        f"being recorded")
    return flags, evidence


def _mw_signals(today: date, now: datetime, cfg: dict) -> tuple[list[str], list[str]]:
    days = _days_back(today, int(cfg["last_logged_days"]), include_today=True,
                      cache=cfg.get("_cache"))
    run = _run(days, lambda e: _poor_night(e, float(cfg["sleep_poor_hours"])))
    if run < int(cfg["sleep_poor_run"]):
        return [], []
    return [], [f"SLEEP_CONCERN evidence: sleep logged under {cfg['sleep_poor_hours']} h or poor "
                f"on {run} consecutive nights, to last night"]


_SIGNALS = {"physical_health": _ph_signals, "mental_wellbeing": _mw_signals}


def counted_signals(agent: str, now: datetime | None = None) -> str:
    """Today's thresholds for `agent`, re-read after its writes this turn: the flag lines code
    sets (SLEEP_POOR, SLEEP_ACUTE, ENERGY_CRASH) and the evidence lines, or "". `now` is the
    persona-local clock (tools.ambient._now_local()); injected by tests."""
    try:
        cfg = load_config()
        fn = _SIGNALS.get(agent)
        if fn is None or agent not in cfg["owners"]:
            return ""
        if now is None:
            from tools.ambient import _now_local
            now = _now_local()
        allowed = set(cfg["owners"].get(agent) or [])
        cfg["_cache"] = {}
        flags, evidence = fn(ledger_day(now), now, cfg)
        flags = [f for f in flags if f.split(" ", 1)[0] in allowed]
        evidence = [e for e in evidence if e.split(" ", 1)[0] in allowed]
        out = []
        if flags:
            out.append("FLAGS (set by code): " + "; ".join(flags))
        out += evidence
        return "\n".join(out)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[counters] signals for {agent} failed: {exc}")
        return ""


def signals_block(per_agent: dict[str, str]) -> str:
    """The Synthesizer's one bundle line from each owner's `counted_signals` text."""
    rows = [(a, t) for a, t in sorted(per_agent.items()) if t]
    if not rows:
        return ""
    return SIGNALS_HEADING + ":\n" + "\n".join(
        f"[{a}]\n{t}" for a, t in rows)


# --- #15: skill-practice habits, read from the ledger ------------------------------------------

def skill_habit_lines(today: date | None = None) -> str:
    """Open `habit` rows with `domain: learning`: target, done this period, last done and the
    periods missed in the last 30 days. Read only, through the ledger's own views
    (tools/obligations.py is never written from here). "" when there are none."""
    try:
        from tools import obligations as O
        today = today or O._today()
        tasks = [O._norm(t) for t in O._load()]
        habits = [t for t in tasks if t.get("kind") == "habit" and t.get("status") == "open"
                  and str(t.get("domain") or "").strip().lower() == "learning"]
        if not habits:
            return ""
        adh = {r.get("task_id"): r for r in O.adherence(days=30, as_of=today)}
        lines = []
        for t in habits[:8]:
            dates = [str(c.get("on") or c.get("at") or "")[:10]
                     for c in (t.get("completions") or []) + (t.get("recent_completions") or [])
                     if isinstance(c, dict)]
            for occ in (t.get("occurrences") or {}).values():
                if isinstance(occ, dict):
                    dates += [d.isoformat() for d in O._completion_dates(occ)]
            last = max((d for d in dates if d), default="")
            r = adh.get(t["id"]) or {}
            missed = int(r.get("missed") or 0) + int(r.get("unconfirmed") or 0)
            every = t.get("every") or "day"
            lines.append(
                f"- {t['id']} {t.get('what', '?')}: target {O._habit_target(t)} per {every}; "
                f"{O._state_line(t, today)}; last done "
                + (f"{last} ({(today - date.fromisoformat(last)).days} days ago)" if last
                   else "never recorded")
                + f"; periods missed in the last 30 days: {missed}")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[counters] skill habits unreadable: {exc}")
        return ""

