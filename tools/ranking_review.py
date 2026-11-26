"""
tools/ranking_review.py — ranking Part B, phase 3: the back burner, the weekly priorities
conversation's material, and the signals the monthly review reads.

Plan: archive/plans/ranking_values_plan_2026-11-23.md §§ 4.11–4.13, § 11 rows 13 and 15, § 11c.
Mike, 2026-11-22: "if not vital should have a weaker score and be relegated to back burner";
2026-11-23 (B31): "Managed or nagged is a cardinal sin for users. Same for lists running life."

Three pieces, all code, zero model tokens:

  back burner  — `daily()`, on the first tick of each day. A one-off that is trivia, whose cost of
                 delay stays below `back_burner.cod`, that nobody has mentioned for 21 days, is
                 parked: closed as moot with reason back_burner, row and history kept (archive-on-
                 merge), revived by `open_task` on a fresh mention. Never before its date; never
                 silently for a person, an obligation, health, a goal or more than trivia — those
                 are put once in the weekly conversation instead. Each parked task is said once in
                 the weekly conversation the week before. Flag `back_burner` OFF is the dry run:
                 the pass writes what it would park to the trace and closes nothing.
  weekly       — `weekly_block()`, the material for the weekly review (option 1, Mike 2026-11-23:
                 the priorities conversation rides the existing weekly review). Code chooses what
                 goes in; the model fetches nothing. Plus the one-time offer of a weekly review to
                 a user who has none.
  signals      — `daily()` appends the ledger's rows for yesterday to
                 data/personas/{p}/ranking_signals.jsonl (append-only, kept forever, deleted with
                 the persona); `record_signal` keeps what the user says, on a user turn only.

WHAT COUNTS AS A MENTION (§ 11c): the user's own words naming the task (`obligations.
note_mentioned`, every user turn), any change recorded on it — a history event other than code's
own bookkeeping, or a change to what it is, when, how long or what it costs (`news_digest`) — or
its opening. Metatron's own words do NOT count: a trivia task Metatron raises and the user lets
pass is exactly the evidence that it is back-burner material, and the weekly notice would
otherwise reset the clock it announces.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from core.persona import persona_data_dir, resolve_persona

logger = logging.getLogger(__name__)


def _O():
    import tools.obligations as O
    return O


def _D():
    import tools.day_plan as D
    return D


def _RK():
    from tools import ranking as RK
    return RK


def _flag(name: str) -> bool:
    return _D()._flag(name)


# --- the back burner (plan § 4.11, B26–B27; § 11 row 15) ---------------------------------------

# History events code writes on its own — none is a mention.
_CODE_EVENTS = frozenset({"judged", "costs_recorded", "linked_to_event", "adopted_into_plan",
                          "closed_by_prerequisite", "closed_by_later_step",
                          "closed_with_end_state", "back_burner"})
BACK_BURNER_REASON = "back_burner"
# What the user (or an agent on their word) changes about a task. Narrower than ranking.news_digest:
# the judge writes stakes, priority and the cost record on its own, and a re-judge must not start
# every clock over (Fable diff review #11). A correction of the record is a `costs_set` event,
# which `last_touched` counts.
_TOUCH_FIELDS = ("what", "due", "minutes", "note", "eligible_from", "after", "before")


def _touch_digest(t: dict) -> str:
    import hashlib
    return hashlib.sha256(json.dumps({k: t.get(k) for k in _TOUCH_FIELDS}, sort_keys=True,
                                     default=str).encode()).hexdigest()[:12]


def _day(stamp) -> date | None:
    return _O()._stamp_day(stamp) if stamp else None


def last_touched(t: dict, seen: dict | None = None) -> date | None:
    """The last day anyone but Metatron touched the task: opened, mentioned by the user, a change
    recorded on it, or (`seen["changed"]`) a change to its fields the daily pass noticed."""
    O = _O()
    days = [_day(t.get("created_at")), O._d(t.get("mentioned"))]
    for h in t.get("history") or []:
        if isinstance(h, dict) and h.get("event") not in _CODE_EVENTS:
            days.append(_day(h.get("at")))
    if seen and seen.get("changed"):
        days.append(O._d(seen["changed"]))
    days = [d for d in days if d]
    return max(days) if days else None


def _person_names(persona: str | None) -> list[re.Pattern] | None:
    """Word patterns for every person the user's contacts name (first names, nicknames, full
    names). None when the store exists and cannot be read — the pass then parks nothing
    (fail-closed: an unread name must not let a task about a person go quietly)."""
    try:
        from tools import lookup_guard as LG
        contacts = LG.load_contacts_strict()
    except Exception:  # noqa: BLE001
        return None
    out = []

    def add(v) -> None:
        v = LG.unannotated_name(str(v or "")).strip().lower()
        if len(v) >= 2:
            out.append(re.compile(r"\b" + re.escape(v) + r"\b"))

    # Read as the public-fact guard reads them (82c490e): no organisation skip — the CRM's
    # relationship_type has no organisation value, so it never matched — and each alias on
    # its own, counting as a name only when every word is capitalised ("my wife" is not one).
    for c in contacts:
        for k in ("first_name", "nickname", "name"):
            add(c.get(k))
        for alias in LG.contact_aliases(c.get("referred_to_as")):
            if LG.alias_is_name(alias):
                add(alias)
    return out


def guard_reason(t: dict, rec: dict, names: list[re.Pattern] | None) -> str | None:
    """Why this task is never parked silently, or None (B27, § 4.11). A guarded task is put once
    in the weekly conversation instead — keep it, give it a date, or drop it."""
    O, RK = _O(), _RK()
    if names is None:
        return "contacts unreadable"
    costs = rec.get("costs") or {}
    if rec.get("bears") in ("close", "others"):
        return "person"
    what = str(t.get("what") or "").lower()
    if any(p.search(what) for p in names):
        return "person"
    rank = {g: i for i, g in enumerate(RK.GRADES)}
    if any(rank.get(costs.get(d), -1) >= rank["major"] for d in ("legal", "financial")):
        return "obligation"
    if costs.get("health") in RK.GRADES or str(t.get("domain") or "").lower() == "health":
        return "health"
    if t.get("goal_id"):
        return "goal"
    grade = RK.floor_grade({k: v for k, v in costs.items() if k != "_any"}) or costs.get("_any")
    if grade != "minor" or O.stakes_of(t) == "vital":
        return "weight"
    return None


def _excluded(t: dict, today: date, by_id: dict, needed: set[str]) -> bool:
    """Never a candidate at all (§ 4.11, the prompt's guards): not an open one-off deadline, a plan
    step, a prep, a medication task, something another open task waits on, hidden until a later
    day, or blocked."""
    O = _O()
    if t.get("status") != "open" or t.get("kind") != "deadline":
        return True
    if t.get("part_of") or t.get("prep_for") or t.get("medication") or O.is_required_dose(t):
        return True
    if t["id"] in needed or t.get("_blocked"):
        return True
    try:
        until = O._d(O._deferred_until(t))
    except Exception:  # noqa: BLE001
        until = None
    if until and until > today:
        return True
    ef = O._d(t.get("eligible_from"))
    return bool(ef and ef > today)


def back_burner_pass(persona: str, today: date, st: dict) -> dict:
    """One day's reading (mutates `st["back_burner"]`): {would_archive, would_notice, guarded,
    park} — `park` is [(task id, silent days)] to close, only when parking is live and the notice
    was said. Ids, days and numbers; no task words (the trace keeps none)."""
    O, RK = _O(), _RK()
    c = RK.cfg(persona)
    bc = c.get("back_burner") or {}
    days, notice_at = int(bc.get("days", 21)), int(bc.get("notice_days", 14))
    lead, floor = int(bc.get("notice_lead_days", 7)), float(bc.get("cod", 5))
    tasks = [O._norm(t) for t in O._load(persona)]
    by_id = {t["id"]: t for t in tasks}
    needed = {n for t in tasks if t.get("status") == "open" for n in O._needs(t)}
    weekly = st.get("weekly") or {}
    try:
        from tools.profile import stated_passions
        passions = stated_passions()
    except Exception:  # noqa: BLE001
        passions = []
    bias = RK.bias_of(st, c)
    names = _person_names(persona)
    bb = st.setdefault("back_burner", {})
    seen = bb.setdefault("seen", {})
    out = {"would_archive": [], "would_notice": [], "guarded": [], "park": []}
    keep = set()
    for t in tasks:
        if _excluded(t, today, by_id, needed):
            continue
        tid = t["id"]
        keep.add(tid)
        s = seen.setdefault(tid, {})
        news = _touch_digest(t)
        if s.get("news") and s["news"] != news:
            s["changed"] = today.isoformat()
        s["news"] = news
        if tid in weekly:
            # Raised twice with nothing new: the weekly conversation already asks "keep,
            # reschedule or drop?" (§ 11 row 13) — never parked from under that question.
            continue
        rec = RK.record_of(RK.inherit(t, by_id), c)
        due = rec.get("real_due") or O._d(t.get("due"))
        if due and due >= today:
            # Never before its date (B27). Its clock starts again from the day after it.
            s.pop("low_since", None)
            s.pop("noticed", None)
            s.pop("asked", None)
            continue
        v = O._view(t, today)
        a = RK.assess(RK.inherit(t, by_id), v, today, c, bias,
                      on_list=bool(v.get("actionable") and O._on_todays_list(t, v)),
                      passions=passions)
        if float(a.get("cod") or 0.0) >= floor:
            s.pop("low_since", None)
            s.pop("noticed", None)
            s.pop("asked", None)
            continue
        touched = last_touched(t, s) or today
        if "low_since" not in s:
            # First reading: an undated or past-date trivia task has cost little since it was
            # last touched (or since its date went by) — so the dry run's first week has
            # something to show rather than starting every clock on deploy day (§ 11c).
            start = max(touched, due + timedelta(days=1)) if due else touched
            s["low_since"] = start.isoformat()
        since = max(touched, O._d(s["low_since"]) or today)
        # A notice (or a guarded question) said on or before the last touch no longer counts: the
        # user answered it, or the task changed since (Fable diff review #2 — same day included,
        # since a date cannot order a notice and a reply on the same day).
        for k in ("noticed", "asked"):
            when = O._d(s.get(k))
            if when and when <= touched:
                s.pop(k, None)
        noticed = O._d(s.get("noticed"))
        silent = (today - since).days
        if silent < notice_at:
            continue
        row = {"task_id": tid, "silent": silent, "cod": round(float(a.get("cod") or 0.0), 2),
               **({"noticed": noticed.isoformat()} if noticed else {})}
        why = guard_reason(t, rec, names)
        if why:
            # A guarded task is ASKED about, never told it will be parked — so its question is
            # kept apart from a notice, and losing the guard later needs a fresh notice
            # (Fable diff review #11, guard flip).
            row.pop("noticed", None)
            out["guarded"].append({**row, "why": why,
                                   **({"asked": s["asked"]} if s.get("asked") else {})})
            continue
        if silent >= days:
            out["would_archive"].append(row)
            if noticed and (today - noticed).days >= lead:
                out["park"].append((tid, silent))
        else:
            out["would_notice"].append(row)
    bb["seen"] = {k: v for k, v in seen.items() if k in keep}
    return out


def _park(persona: str, park: list[tuple[str, int]], today: date) -> list[str]:
    """Close each as moot, reason back_burner — the row and its history stay (archive-on-merge)."""
    O = _O()
    done: list[str] = []
    want = dict(park)

    def apply(doc: dict) -> None:
        stamp = O._stamp()
        for t in doc["tasks"]:
            if t.get("id") not in want or (t.get("status") or "open") != "open":
                continue
            n = want[t["id"]]
            t.update(status="moot", closed_at=stamp,
                     evidence=f"back burner: no mention in {n} days")
            t["back_burner"] = {"at": today.isoformat(), "silent_days": n}
            t.setdefault("history", []).append({"event": BACK_BURNER_REASON, "at": stamp,
                                                "silent_days": n})
            doc.setdefault("_history", []).append(O._one_off_row(t, "moot"))
            done.append(t["id"])

    out = O._with_store(persona, apply)
    if isinstance(out, str) and out.startswith("error"):
        logger.warning(f"[back_burner] not parked: {out}")
        return []
    return done


def is_parked(t: dict) -> bool:
    return _O()._is_parked(t)


# --- signals (plan § 4.13, B30–B32) ----------------------------------------------------------------

SIGNAL_KINDS = ("regret", "feel", "overload", "nagging", "satisfaction")
_SIGNALS = "ranking_signals.jsonl"
_TEXT_MAX = 280


def signals_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / _SIGNALS


def append_signals(rows: list[dict], persona: str | None = None) -> int:
    """Append, never rewrite (§ 4.13: kept forever). Owner-only, like every persona file."""
    if not rows:
        return 0
    import os
    path = signals_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    if new:
        os.chmod(path, 0o600)
    return len(rows)


def read_signals(persona: str | None = None) -> list[dict]:
    path = signals_path(persona)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def ledger_signals(persona: str, day: date, st: dict) -> list[dict]:
    """The ledger's rows for one finished day (§ 4.13): completion, momentum, missed obligations,
    intrusions, questions this plan's paths asked, overrides — recorded, not scored (B30). Counts
    and ids only."""
    O, RK = _O(), _RK()
    c = RK.cfg(persona)
    at = datetime.now().isoformat(timespec="seconds")
    key = day.isoformat()
    base = {"at": at, "day": key, "source": "ledger"}
    tasks = [O._norm(t) for t in O._load(persona)]
    rows: list[dict] = []
    # Completion — every occurrence that ended that day, habits included (task_history.jsonl).
    states: dict[str, int] = {}
    for h in O._history_rows(persona):
        if h.get("closed_on") == key:
            states[str(h.get("state"))] = states.get(str(h.get("state")), 0) + 1
    opened = sum(1 for t in tasks if _day(t.get("created_at")) == day)
    parked = sum(1 for t in tasks if (t.get("back_burner") or {}).get("at") == key)
    rows.append({**base, "kind": "completion", "states": states, "opened": opened,
                 "parked": parked})
    # Momentum — goal steps closed that day against those open; keep-in-touch and upkeep clocks
    # inside their wished cadence.
    steps_done = sum(1 for t in tasks if t.get("part_of") and t.get("status") == "done"
                     and _day(t.get("closed_at")) == day)
    steps_open = sum(1 for t in tasks if t.get("part_of") and t.get("status") == "open")
    within = total = 0
    for t in tasks:
        if t.get("status") != "open" or t.get("kind") != "interval":
            continue
        if RK.record_of(t, c).get("shape") != "neglect":
            continue
        total += 1
        within += O._interval_due(t, day) >= day
    rows.append({**base, "kind": "momentum", "goal_steps_done": steps_done,
                 "goal_steps_open": steps_open, "clocks_within": within, "clocks": total})
    # Missed obligations — a legal or financial cost of major or worse, past its date, open.
    rank = {g: i for i, g in enumerate(RK.GRADES)}
    missed = []
    for t in tasks:
        if t.get("status") != "open" or t.get("kind") != "deadline":
            continue
        rec = RK.record_of(t, c)
        due = rec.get("real_due") or O._d(t.get("due"))
        costs = rec.get("costs") or {}
        if due and due < day and any(rank.get(costs.get(d), -1) >= rank["major"]
                                     for d in ("legal", "financial")):
            missed.append(t["id"])
    rows.append({**base, "kind": "missed_obligations", "n": len(missed), "task_ids": missed})
    # Intrusions into protected time — what took it, by class, and what was decided (§ 4.5).
    by_class: dict[str, int] = {}
    for e in st.get("intrusions") or []:
        if isinstance(e, dict) and e.get("day") == key:
            by_class[str(e.get("class"))] = by_class.get(str(e.get("class")), 0) + 1
    decisions: dict[str, int] = {}
    for x in (((st.get("trace") or {}).get(key) or {}).get("intrusions") or {}).values():
        d = str((x or {}).get("decision"))
        decisions[d] = decisions.get(d, 0) + 1
    rows.append({**base, "kind": "intrusions", "n": sum(by_class.values()), "by_class": by_class,
                 "decisions": decisions})
    # Questions this plan's paths put (attention spent): the day's admitted prompts, the raises
    # said, the weekly items and notices said.
    prompts = len((st.get("prompts") or {}).get(key) or [])
    raises = sum(1 for r in (st.get("raises") or {}).values() if r.get("last") == key)
    weekly = sum(1 for r in (st.get("weekly") or {}).values() if r.get("said") == key)
    notices = sum(1 for r in ((st.get("back_burner") or {}).get("seen") or {}).values()
                  if r.get("noticed") == key)
    rows.append({**base, "kind": "questions", "prompts": prompts, "raises": raises,
                 "weekly_items": weekly, "notices": notices})
    # Overrides — recorded, never scored (B30): a grade the user corrected that day, and the
    # Synthesizer's request to rework the day (R9).
    corrections = sum(1 for t in tasks for h in t.get("history") or []
                      if isinstance(h, dict) and h.get("event") == "costs_set"
                      and _day(h.get("at")) == day and h.get("costs_source") == "stated")
    replans = 0
    try:
        log = _D()._log_path(persona)
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                if f'"{key}' in line and '"reshuffle_requested"' in line:
                    replans += 1
    except Exception:  # noqa: BLE001
        pass
    rows.append({**base, "kind": "overrides", "grade_corrections": corrections,
                 "replans": replans})
    return rows


def record_signal(kind: str, text: str, asked: bool = False) -> str:
    """Keep what the user said about how Metatron is going for them (§ 4.13): the regret answer,
    how things feel, an unprompted remark about overload, nagging or satisfaction. Their own
    words, on their own turn only — never a scheduled session's text, never a paraphrase."""
    if not _flag("ranking_signals"):
        return "not recorded — signals are not switched on yet. Nothing to say to the user."
    kind = str(kind or "").strip().lower()
    if kind not in SIGNAL_KINDS:
        return f"error: `kind` must be one of {', '.join(SIGNAL_KINDS)}. Nothing was written."
    text = " ".join(str(text or "").split())
    if not text:
        return "error: `text` is required — the user's own words. Nothing was written."
    try:
        from tools.turn_context import current as _turn
        turn = _turn()
    except Exception:  # noqa: BLE001
        turn = None
    if turn is None or not turn.get("user_turn"):
        return ("error: not recorded — a signal is the user's own words, on their own turn. "
                "Nothing was written.")
    persona = resolve_persona(None)
    O = _O()
    now = O._now()
    append_signals([{"at": now.isoformat(timespec="seconds"), "day": now.date().isoformat(),
                     "kind": kind, "source": "user", "asked": bool(asked),
                     "text": text[:_TEXT_MAX]}], persona)
    return "recorded. Nothing to say about it — carry on the conversation."


RECORD_SIGNAL_SCHEMA = {
    "name": "record_signal",
    "description": (
        "Keep, word for word, something the user said about how life with Metatron is going: "
        "their answer to the weekly regret question (`regret`), how things feel (`feel`), or an "
        "unprompted remark that they feel overloaded (`overload`), nagged (`nagging`) or "
        "satisfied (`satisfaction`). Only on the user's own turn, only their words. Never "
        "mention that it was kept."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": list(SIGNAL_KINDS)},
            "text": {"type": "string", "description": "The user's own words, ≤ 280 characters."},
            "asked": {"type": "boolean",
                      "description": "True when Metatron asked (the weekly questions); false "
                                     "when the user said it unprompted."},
        },
        "required": ["kind", "text"],
    },
}


# --- the daily pass ---------------------------------------------------------------------------------

def daily(persona: str | None = None, today: date | None = None) -> str:
    """The first tick of each day (`day_plan.refresh_tick`, after the ledger sweep): the back
    burner's reading — traced always, parked only when live — and yesterday's signal rows. Code
    only; best effort; returns a plain note."""
    persona = resolve_persona(persona)
    O, RK, D = _O(), _RK(), _D()
    today = today or O._today()
    notes = []
    with D._locked(persona):
        st = RK.load_state(persona)
        if _flag("ranking_signals"):
            # Every finished day since the last one written, at most a week back — a day the
            # pass missed (downtime, a failure) is caught up, never written twice (Fable #11).
            sg = st.setdefault("signals", {})
            y = today - timedelta(days=1)
            last = O._d(sg.get("last_day"))
            day = max(last + timedelta(days=1), y - timedelta(days=6)) if last else y
            try:
                n = 0
                while day <= y:
                    n += append_signals(ledger_signals(persona, day, st), persona)
                    sg["last_day"] = day.isoformat()
                    day += timedelta(days=1)
                if n:
                    notes.append(f"{n} signal row(s)")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[signals] not written: {exc}")
                notes.append(f"signals failed: {type(exc).__name__}")
        park: list[tuple[str, int]] = []
        try:
            r = back_burner_pass(persona, today, st)
            live = _flag("back_burner") and not _flag("back_burner_dry_run")
            would = r.pop("park")
            park = would if live else []
            r["mode"] = ("live" if live else "notices only" if _flag("back_burner")
                         else "dry run")
            RK.keep_trace(st, today, "back_burner", r)
            notes.append(f"back burner ({r['mode']}): {len(r['would_archive'])} would park, "
                         f"{len(r['guarded'])} guarded")
        except Exception as exc:  # noqa: BLE001 — the back burner never costs the day its plan
            logger.warning(f"[back_burner] pass failed: {exc}")
            notes.append(f"back burner failed: {type(exc).__name__}")
        RK.save_state(st, persona)
    if park:
        done = _park(persona, park, today)
        if done:
            with D._locked(persona):
                st = RK.load_state(persona)
                seen = (st.get("back_burner") or {}).get("seen") or {}
                for tid in done:
                    seen.pop(tid, None)
                RK.save_state(st, persona)
            notes.append(f"{len(done)} parked")
    return "; ".join(notes)


# --- the weekly priorities conversation (plan § 4.12, B28–B29) ---------------------------------------

_WEEKLY_MARKER = "THIS WEEK'S PRIORITIES — kept by code"
_OFFER_WINDOW = timedelta(minutes=15)


def has_weekly_review(persona: str | None) -> bool:
    """Does this user already have a weekly review — a `weekly_review` job or a brief carrying it
    (`weekly_review_on`) in their scheduler.yaml, or one created through `write_schedule`?"""
    import yaml
    try:
        from core.persona import persona_config_dir
        path = persona_config_dir(persona) / "scheduler.yaml"
        cfg = yaml.safe_load(path.read_text()) if path.exists() else {}
        for key, e in ((cfg or {}).get("schedules") or {}).items():
            if key == "weekly_review" or (isinstance(e, dict) and e.get("weekly_review_on")):
                return True
    except Exception:  # noqa: BLE001 — unreadable: assume one exists (never offer twice)
        return True
    try:
        path = persona_data_dir(persona) / "schedules.yaml"
        data = yaml.safe_load(path.read_text()) if path.exists() else {}
        return any(isinstance(v, dict) and v.get("session") == "weekly_review"
                   for v in (data or {}).values())
    except Exception:  # noqa: BLE001
        return True


def _title(t: dict) -> str:
    return " ".join(str(t.get("what") or "?").split())[:80]


# Reasons code writes on a move it made itself (tools/obligations.py, tools/day_plan.py). A user's
# own reschedule carries their words as its reason and is not "what Metatron moved" (Fable #5).
_CODE_MOVE_REASONS = frozenset({"fitted into its plan", "its event moved", "its event is today"})


def weekly_material(persona: str, today: date, st: dict) -> dict:
    """What the weekly conversation may draw on, chosen by code (§ 4.12): {moved, clash,
    slipping, clock} — lines, and for slipping (kind, task id, line)."""
    O, RK = _O(), _RK()
    c = RK.cfg(persona)
    wc = c.get("weekly") or {}
    since = today - timedelta(days=int(wc.get("moved_days", 7)))
    tasks = [O._norm(t) for t in O._load(persona)]
    by_id = {t["id"]: t for t in tasks}
    trace = st.get("trace") or {}
    # (1) What Metatron moved and why — code's own moves only, newest first.
    moved: list[tuple[str, str]] = []
    for t in tasks:
        bb = t.get("back_burner") or {}
        if O._is_parked(t) and (O._d(bb.get("at")) or today) >= since:
            moved.append((bb["at"], f"parked \"{_title(t)}\" — nobody had mentioned it in "
                                     f"{bb.get('silent_days')} days (kept; a mention brings it back)"))
        for h in t.get("history") or []:
            if (isinstance(h, dict) and h.get("event") == "rescheduled"
                    and h.get("reason") in _CODE_MOVE_REASONS
                    and (_day(h.get("at")) or today) >= since):
                moved.append((str(h.get("at")), f"moved \"{_title(t)}\" to {h.get('to')} — "
                                                 f"{h.get('reason')}"))
    for k, day in sorted(trace.items()):
        if (O._d(k) or today) < since:
            continue
        for x in ((day or {}).get("intrusions") or {}).values():
            t = by_id.get(str((x or {}).get("task_id")))
            if t and x.get("decision") == "granted":
                moved.append((k, f"\"{_title(t)}\" took {x.get('class')} time on {k} — "
                                 f"the user said yes"))
    moved.sort(reverse=True)
    # (2) A clash held — a protected-time question kept out or unanswered this week, its task
    # still open: one question with a recommendation (B29).
    clash = None
    answered = set(st.get("asks") or {})
    for k, day in sorted(trace.items(), reverse=True):
        if (O._d(k) or today) < since:
            continue
        for x in ((day or {}).get("intrusions") or {}).values():
            t = by_id.get(str((x or {}).get("task_id")))
            if not t or t.get("status") != "open" or x.get("id") in answered:
                continue
            if x.get("decision") not in ("ask", "kept_out"):
                continue
            a = RK.assess(t, O._view(t, today), today, c)
            rec, when = RK.intrusion_advice(a, today)
            clash = (f"\"{_title(t)}\" wanted {x.get('class')} time this week and was kept out — "
                     + ("recommend letting it in once, on their yes" if rec == "yes"
                        else f"recommend doing it by {when} outside that time"))
            break
        if clash:
            break
    # (3) What is slipping or about to be parked — guarded first, then "keep, reschedule or
    # drop?" (§ 11 row 13), then the small things about to be parked.
    slipping: list[tuple[str, str, str]] = []
    bt = (trace.get(today.isoformat()) or {}).get("back_burner") or {}
    if not bt:
        bt = next(((d or {}).get("back_burner") for _, d in sorted(trace.items(), reverse=True)
                   if (d or {}).get("back_burner")), {}) or {}
    live = _flag("back_burner") and not _flag("back_burner_dry_run")
    # A goal asked about again (goal network phase 3 § 17, Mike 2026-11-24: it lands here, at
    # most one goal a week). First among the questions — there is at most one, and it is about a
    # whole goal — and it takes the place of a guarded question about one of that goal's own
    # tasks, so the look back never asks about the same thing twice.
    try:
        from tools.goal_network import weekly_revet
        revets = weekly_revet(persona, today)
    except Exception:  # noqa: BLE001 — a fault here never costs the look back
        revets = []
    revet_goals = {gid for gid, _ in revets}
    for gid, line in revets:
        slipping.append(("revet", gid, line))
    if _flag("back_burner"):
        why_words = {"person": "it concerns someone", "obligation": "it is a money or legal matter",
                     "health": "it is about health", "goal": "it serves a goal",
                     "weight": "it matters more than a small thing",
                     "contacts unreadable": "it may concern someone"}
        for r in bt.get("guarded") or []:
            t = by_id.get(r["task_id"])
            if t and (t.get("goal_id") in revet_goals or t.get("part_of") in revet_goals):
                continue
            if t and t.get("status") == "open" and not r.get("asked"):
                slipping.append(("guarded", t["id"],
                                 f"\"{_title(t)}\" — not mentioned in {r['silent']} days, and "
                                 f"{why_words.get(r.get('why'), 'it matters')}: keep it, give it "
                                 f"a date, or drop it?"))
    for tid, w in sorted((st.get("weekly") or {}).items(), key=lambda kv: kv[1].get("since", "")):
        t = by_id.get(tid)
        if t and t.get("status") == "open" and not w.get("said"):
            slipping.append(("weekly", tid, f"\"{_title(t)}\" — raised twice with nothing new: "
                                            f"keep, reschedule or drop?"))
    if _flag("back_burner"):
        for r in (bt.get("would_archive") or []) + (bt.get("would_notice") or []):
            t = by_id.get(r["task_id"])
            if t and t.get("status") == "open" and not r.get("noticed"):
                # Said only as true: live, it goes next week; in notices-only mode nothing is
                # parked, so the line asks instead of announcing (Fable diff review #10).
                tail = ("unless they want it kept, it goes on the back burner next week (kept, "
                        "and a mention brings it back)" if live else
                        "ask whether they still want it or it can go on the back burner")
                slipping.append(("notice", t["id"], f"\"{_title(t)}\" — not mentioned in "
                                                    f"{r['silent']} days; {tail}"))
    # (4) One relationship or upkeep clock — the one furthest through its wished cadence.
    clock = None
    best = None
    for t in tasks:
        if t.get("status") != "open" or t.get("kind") != "interval":
            continue
        n = max(1, int(t.get("interval_days") or 1))
        ratio = 1.0 + (today - O._interval_due(t, today)).days / n
        if ratio >= float(wc.get("clock_min_ratio", 0.8)) and (best is None or ratio > best[0]):
            best = (ratio, t)
    if best:
        t = best[1]
        clock = (f"\"{_title(t)}\" — wished about every {t.get('interval_days')} days, last "
                 f"{t.get('last_done') or 'never on record'}")
    return {"moved": [m for _, m in moved[:int(wc.get("moved_max", 3))]], "clash": clash,
            "slipping": slipping, "clock": clock}


def _shown_slipping(slipping: list[tuple[str, str, str]], wc: dict) -> tuple[list, str]:
    """What the block shows, and how it words the rest (Fable diff review #7): at most
    `questions_max` questions a week (guarded, then keep-reschedule-drop) — the rest wait for
    next week, said as a count — and the small things about to be parked up to `slipping_max`
    in all."""
    qmax, total = int(wc.get("questions_max", 5)), int(wc.get("slipping_max", 5))
    qs = [x for x in slipping if x[0] in ("revet", "guarded", "weekly")]
    notes = [x for x in slipping if x[0] == "notice"]
    shown = qs[:qmax]
    shown += notes[:max(0, total - len(shown))]
    rest_q = len(qs) - len(qs[:qmax])
    rest_n = len(notes) - len([x for x in shown if x[0] == "notice"])
    extra = []
    if rest_q:
        extra.append(f"{rest_q} more to ask about another week — not this one")
    if rest_n:
        extra.append(f"{rest_n} more small thing(s), next week")
    return shown, "; ".join(extra)


def weekly_block(persona: str | None, session: str | None, weekly: bool = False,
                 user_turn: bool = False) -> str:
    """The weekly review's look back (option 1: it rides the existing weekly review — `weekly` is
    the orchestrator's `carries_weekly_review` for this turn), or — on a user's own turn, when
    they have no weekly review — the one-time offer of one. "" otherwise. Recorded as offered
    here; stamped as said by `note_said` once a reply says it. Conduct lives in
    synthesizer_scheduled_sessions.md § Weekly review and synthesizer.md; this is material."""
    if not _flag("weekly_priorities"):
        return ""
    persona = resolve_persona(persona)
    O, RK, D = _O(), _RK(), _D()
    today = O._today()
    now = O._now()
    wc = RK.cfg(persona).get("weekly") or {}
    if weekly:
        with D._locked(persona):
            st = RK.load_state(persona)
            m = weekly_material(persona, today, st)
            shown, extra = _shown_slipping(m["slipping"], wc)
            st["weekly_offered"] = [e for e in st.get("weekly_offered") or []
                                    if isinstance(e, dict) and (D._dt(e.get("at")) or now)
                                    > now - _OFFER_WINDOW] + [{
                "at": now.isoformat(timespec="seconds"),
                "items": [[k, tid] for k, tid, _ in shown]}]
            RK.save_state(st, persona)
        lines = [f"[{_WEEKLY_MARKER}. The week behind, before the week ahead.]"]
        lines.append("MOVED: " + ("; ".join(m["moved"]) if m["moved"] else "nothing this week"))
        if m["clash"]:
            lines.append("CLASH HELD: " + m["clash"])
        goal_checks = [x for k, _, x in shown if k == "revet"]
        if goal_checks:
            lines.append("GOAL CHECK (one question, never a verdict): " + "; ".join(goal_checks))
        slip_lines = [x for k, _, x in shown if k != "revet"]
        if slip_lines:
            lines.append("SLIPPING (guarded first; name each one): "
                         + "; ".join(slip_lines) + (f"; {extra}" if extra else ""))
        if m["clock"]:
            lines.append("ONE CLOCK: " + m["clock"])
        if goal_checks:
            from tools.goal_network import mark_shown
            mark_shown([tid for k, tid, _ in shown if k == "revet"], persona)
        return "\n".join(lines)
    # The offer: a user turn, no weekly review yet, not said, at most once a day (Fable #8).
    if not user_turn or session is not None or has_weekly_review(persona):
        return ""
    cap = int(wc.get("offer_max_shows", 3))
    with D._locked(persona):
        st = RK.load_state(persona)
        wo = st.setdefault("weekly_offer", {})
        if (wo.get("said") or int(wo.get("shown") or 0) >= cap
                or str(wo.get("at") or "")[:10] == today.isoformat()):
            return ""
        wo["shown"] = int(wo.get("shown") or 0) + 1
        wo["at"] = now.isoformat(timespec="seconds")
        RK.save_state(st, persona)
    return ("[WEEKLY CONVERSATION — the user has no weekly review. To set one up on their yes: "
            "write_schedule with name \"weekly_review\", session \"weekly_review\", day (a full "
            "weekday name), time (HH:MM), agent \"coordinator\", a prompt of at least four words, "
            "and a reason.]")


# A reply has made the offer when it says "weekly" (or "each/every week") AND asks or offers.
_OFFER_SAID = re.compile(r"\b(weekly|each week|every week|once a week)\b", re.I)
_OFFER_ASK = re.compile(r"\?|\b(would you like|want me to|shall i|should i|happy to)\b", re.I)
# A sentence that tells the user a task is going: the notice (§ 4.11).
_PARK_WORDS = re.compile(r"\b(park\w*|back[- ]burner|set (it |that |them )?aside|let (it|that|"
                         r"them) go|put (it|that|them) away)\b", re.I)
# A sentence that asks about a task: keep, date, drop, reschedule.
_ASK_WORDS = re.compile(r"\?|\b(keep\w*|drop\w*|resched\w*|date|still want)\b", re.I)


def _sentences(text: str) -> list[str]:
    return [x for x in re.split(r"(?<=[.!?;])\s+|\n+", text or "") if x.strip()]


def note_said(reply_text: str, persona: str | None = None) -> int:
    """After a delivered reply: stamp each weekly item a recent render offered that the reply
    SAYS — one sentence naming the task (two of its words, as `_tokens_match`) and carrying the
    item's own signal: a parking word for a notice, a question or keep/drop word for a guarded or
    keep-reschedule-drop item (Fable diff review #3 — a long weekly reply is noun-rich, and
    "library books" must not count as telling the user "Renew library card" is going). The
    weekly offer counts once a sentence says "weekly" and asks. A notice said is what lets a task
    be parked a week later; an item said is not repeated. Best effort."""
    reply = (reply_text or "").strip()
    if not reply or not _flag("weekly_priorities"):
        return 0
    persona = resolve_persona(persona)
    O, RK, D = _O(), _RK(), _D()
    now = O._now()
    today = now.date().isoformat()
    sents = [(x, O._task_tokens(x)) for x in _sentences(reply)]
    n = 0
    revet_said: list[str] = []
    with D._locked(persona):
        st = RK.load_state(persona)
        wo = st.get("weekly_offer") or {}
        if (wo.get("at") and not wo.get("said")
                and (D._dt(wo.get("at")) or now) > now - _OFFER_WINDOW
                and any(_OFFER_SAID.search(x) and _OFFER_ASK.search(x) for x, _ in sents)):
            wo["said"] = today
            n += 1
        pending = [e for e in st.get("weekly_offered") or [] if isinstance(e, dict)
                   and (D._dt(e.get("at")) or now) > now - _OFFER_WINDOW]
        if pending:
            tasks = {t["id"]: O._norm(t) for t in O._load(persona)}
            seen = (st.get("back_burner") or {}).get("seen") or {}
            weekly = st.get("weekly") or {}
            said = set()
            goals = None
            for e in pending:
                for kind, tid in e.get("items") or []:
                    if kind == "revet":
                        # A goal, not a task: named by its title, asked as a question.
                        if goals is None:
                            goals = O._goal_index()
                        gtoks = O._task_tokens(str((goals.get(tid) or {}).get("title") or ""))
                        # One shared word is enough: at most one goal check is on offer a
                        # week, and "how's the Bulgarian going?" names it with one.
                        if any(toks & gtoks and _ASK_WORDS.search(x) for x, toks in sents):
                            said.add(tid)
                            revet_said.append(tid)
                        continue
                    t = tasks.get(tid)
                    if not t:
                        continue
                    ttoks = O._task_tokens(t["what"])
                    signal = _PARK_WORDS if kind == "notice" else _ASK_WORDS
                    if not any(O._tokens_match(toks, ttoks) and signal.search(x)
                               for x, toks in sents):
                        continue
                    said.add(tid)
                    if kind == "weekly" and tid in weekly:
                        weekly[tid]["said"] = today
                    elif kind == "notice" and tid in seen:
                        seen[tid]["noticed"] = today
                    elif kind == "guarded" and tid in seen:
                        seen[tid]["asked"] = today
            n += len(said)
            st["weekly_offered"] = [{**e, "items": [i for i in e.get("items") or []
                                                    if i[1] not in said]} for e in pending]
        RK.save_state(st, persona)
    if revet_said:
        # After the lock: the re-vet's own record and its `revet_asked` signal row.
        from tools.goal_network import mark_said
        mark_said(revet_said, persona)
    return n
