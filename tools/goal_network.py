"""
tools/goal_network.py — goal–task network phase 3, part A: a goal's likely finish, watched; and a
goal asked about again when it stalls or reaches a checkpoint. Code only — no model call here.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md § 4.2 (re-vetting triggers 1–2), § 4.5
(projected finish), § 10 (governs), § 17 (this build). Rolling wave is in tools/project_plan.py.

PROJECTED FINISH (`projected_finish`). Daily, for each planned goal or obligation: its open steps
in prerequisite order, then (rolling wave) its later milestone outlines, worked through one at a
time at the pace the user keeps — the weekly time they gave (else `default_weekly_minutes`),
replaced by the pace ACTUALLY kept (estimated minutes of done steps per week since the plan
began) once `pace_min_steps` steps are done. A step's waiting gap (`eligible_from`) and its
prerequisites are respected. That is the "remaining critical path from step minutes and weekly
time" of § 4.5, for one person whose time is the constraint. When the result passes the goal's
own date — or, for a goal with no date, slips later than the date last said by more than
`finish_margin_days` — it is said ONCE as Important with the new date and one fix. The alert is
state on the plan record: a second tick finds it pending or said and does nothing (§ 6).

RE-VET (`revet`). Trigger 1 (non-compliance): a goal's steps slipped (the day planner's slip
record), were skipped or dismissed, or got "not yet" (the tap log), or a matching intention was
judged unfulfilled by the Accountability Index — on `noncompliance_days` distinct days within
`window_days` — or a rolling-wave milestone stalled. Trigger 2 (time): an L goal at
`checkpoints_days` after it was vetted, then every `every_days`. Each fires once per checkpoint.
Where it lands is Mike's ruling (2026-11-24): ONE line in the weekly look back, at most `per_week`
goals a week, inside the look back's question cap — as a question, never a verdict. An
obligation is never asked whether it is wanted (§ 4.2) — only whether its date works and what
would help — and never gets trigger 2. The answer is `update_goal vet`'s existing verdicts.
`revet_asked` and `revet_answer` rows go to ranking_signals.jsonl (`source: goal_network`), the
one signals file the ranking's monthly review reads (ranking plan § 4.13) — ids and counts only.

THE BACK BURNER. It never parks a plan step (tools/ranking_review.py `_excluded`), and a goal
being re-vetted this week takes the place of a guarded question about one of its own tasks, so
the two never ask about the same thing in one look back.

State lives on the project planner's record (`projects.json`: `finish` on each request, `revet`
at the top), under the day-plan lock — never nested: `weekly_block` and `note_said` hold that
lock while they read, so this module only reads there and stamps after.

Costs. Run: zero model tokens. A re-vet line adds ~60–100 tokens to a weekly-review turn the
user already has; a finish alert ~60 to a brief. Ancillary: a few hundred bytes per plan on the
plan record, rewritten daily; a few signal rows a month. Unseen: a false "late" costs the user's
attention — bounded by the margin, by one alert per crossing, and by the pace correcting itself.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import date, datetime, timedelta

from core.persona import resolve_persona

logger = logging.getLogger(__name__)


def _O():
    import tools.obligations as O
    return O


def _D():
    import tools.day_plan as D
    return D


def _PP():
    import tools.project_plan as PP
    return PP


def _cfg() -> dict:
    try:
        from tools import day_plan_config as C
        return C.goal_network()
    except Exception:  # noqa: BLE001
        return {}


def _flag(name: str) -> bool:
    return _D()._flag(name)


def _r15(minutes: float) -> int:
    return max(15, int(math.ceil(minutes / 15.0)) * 15)


# =============================================================================================
# Projected finish (§ 4.5)
# =============================================================================================

def _plan_rows(rid: str, tasks: list[dict]) -> list[dict]:
    return [t for t in tasks if t.get("part_of") == rid]


def pace(req: dict, rows: list[dict], today: date, cfg: dict | None = None) -> tuple[float, str, int]:
    """(minutes a week, source, done steps used). `actual` once enough steps are done: their
    estimated minutes over the weeks since the plan began (at least one week, so two quick closes
    on day one do not read as a heroic pace); else the weekly time `stated`, else `default`."""
    O = _O()
    cfg = cfg if cfg is not None else _cfg()
    done = [t for t in rows if t.get("status") == "done" and O._stamp_day(t.get("closed_at"))]
    # Not for L (Fable S1): an L milestone's minutes include the recurring practice, which is no
    # step, so a pace measured from step minutes alone reads a user doing everything right as
    # months behind. An L plan runs at the weekly time the user gave it.
    if str(req.get("size") or "") != "L" and len(done) >= int(cfg.get("pace_min_steps") or 2):
        starts = [O._stamp_day(w.get("at")) for w in req.get("waves") or []]
        start = min([d for d in starts if d] or [O._stamp_day(req.get("outcome_at")) or today])
        last = max(O._stamp_day(t["closed_at"]) for t in done)
        weeks = max(7, (max(last, today) - start).days) / 7.0
        mins = sum(int(t.get("minutes") or 0) for t in done)
        if mins > 0:
            return mins / weeks, "actual", len(done)
    if req.get("weekly_minutes"):
        return float(req["weekly_minutes"]), "stated", 0
    return float(cfg.get("default_weekly_minutes") or 150), "default", 0


def _topo(rows: list[dict]) -> list[dict]:
    """Open rows in prerequisite order, earliest window first among the ready ones."""
    O = _O()
    ids = {t["id"] for t in rows}
    left = {t["id"]: t for t in rows}
    out: list[dict] = []
    while left:
        ready = [t for t in left.values()
                 if not any(n in left for n in t.get("needs") or [] if n in ids)]
        if not ready:                               # a cycle the validator should have refused
            ready = list(left.values())
        ready.sort(key=lambda t: (str(t.get("eligible_from") or ""), str(t.get("due") or "")))
        out.append(ready[0])
        left.pop(ready[0]["id"])
    return out


def _simulate(rows: list[dict], milestones: list[dict], today: date, per_day: float) -> float:
    """Days from today until the last piece of work is done, one piece at a time."""
    O = _O()
    default = 30
    try:
        default = int(_D()._limit("default_task_minutes") or 30)
    except Exception:  # noqa: BLE001
        pass
    cursor = 0.0
    fin: dict[str, float] = {}
    for t in _topo(rows):
        ef = O._d(t.get("eligible_from"))
        start = max(cursor, float(max(0, (ef - today).days)) if ef else 0.0,
                    max((fin[n] for n in t.get("needs") or [] if n in fin), default=0.0))
        end = start + int(t.get("minutes") or default) / per_day
        fin[t["id"]] = cursor = end
    for m in milestones:
        ef = O._d(m.get("eligible_from"))
        start = max(cursor, float(max(0, (ef - today).days)) if ef else 0.0)
        cursor = start + int(m.get("minutes") or 0) / per_day
    return cursor


def live_deadline(req: dict, persona: str | None = None) -> str | None:
    """The end state's date NOW — the goal's or the end task's — not the snapshot taken when it
    was queued (Fable S3: moving the date, the alert's own advice, must stop the alert). Falls
    back to the snapshot when the end state cannot be read."""
    try:
        end = _PP()._end(req.get("id") or "", persona)
    except Exception:  # noqa: BLE001
        end = None
    return (end or {}).get("deadline") if end else req.get("deadline")


def project(req: dict, tasks: list[dict], today: date, cfg: dict | None = None) -> dict | None:
    """The likely finish of one planned goal or obligation, or None when nothing is left."""
    O = _O()
    cfg = cfg if cfg is not None else _cfg()
    rows = _plan_rows(req.get("id") or "", tasks)
    open_rows = [O._norm(t) for t in rows if t.get("status") == "open"]
    later = sorted((m for m in req.get("milestones") or []
                    if m.get("status") in ("pending", "stalled")),
                   key=lambda m: str(m.get("due") or ""))
    if not open_rows and not later:
        return None
    rate, source, n = pace(req, rows, today, cfg)
    rate = max(rate, 10.0)
    days = _simulate(open_rows, later, today, rate / 7.0)
    # Waiting alone (prerequisites and windows at an unlimited pace): what no amount of time
    # given can beat — the floor that decides between "more time a week" and "a later date".
    floor = _simulate(open_rows, later, today, 1e9)
    remaining = sum(int(t.get("minutes") or 30) for t in open_rows) + sum(
        int(m.get("minutes") or 0) for m in later)
    target = O._d(req.get("deadline"))
    return {"projected": (today + timedelta(days=math.ceil(days))).isoformat(),
            "floor": (today + timedelta(days=math.ceil(floor))).isoformat(),
            "target": target.isoformat() if target else None,
            "remaining_minutes": remaining, "pace": round(rate), "pace_source": source,
            "pace_steps": n, "size": req.get("size") or "M", "at": today.isoformat()}


def _fix(p: dict, today: date, baseline: str | None) -> str:
    """One concrete fix, in minutes a week or a date — code's arithmetic, Synth's words. A date
    when waiting alone runs past it, when no extra time is needed, or when the time it would take
    is implausible (more than three times the pace, or over ten hours a week — Fable S4/L2)."""
    O = _O()
    goal = O._d(p.get("target") or baseline)
    if not goal or goal <= today:
        return f"moving the date to {p['projected']}"
    if O._d(p["floor"]) > goal:
        # Waiting (a document in the post, a step's window) alone runs past it: no amount of
        # time a week fixes that, so the fix is the date.
        return f"moving the date to {p['projected']} — the waiting alone runs past {goal.isoformat()}"
    need = p["remaining_minutes"] * 7.0 / max(1, (goal - today).days)
    extra = need - p["pace"]
    if extra <= 0 or need > max(3 * p["pace"], 600):
        return f"moving the date to {p['projected']}"
    tail = {"actual": f" (it has been getting about {_r15(p['pace'])})",
            "stated": f" (about {_r15(p['pace'])} a week was the plan)"}.get(p.get("pace_source"), "")
    return f"about {_r15(extra)} more minutes a week on it would keep {goal.isoformat()}{tail}"


# A slip is said again at most this many times per crossing (Fable S4).
_MOVED_MAX = 2


def _worse(p: dict, f: dict) -> bool:
    """Did the work grow, or the pace fall, since the date last said? A projection that slides
    only because days pass with the same work left is not news (Fable S4)."""
    return (int(p["remaining_minutes"]) > int(f.get("base_remaining") or 0)
            or float(p["pace"]) < 0.9 * float(f.get("base_pace") or 0))


def _rebase(f: dict, p: dict, when: str | None = None) -> None:
    f["baseline"] = when or p["projected"]
    f["base_remaining"] = p["remaining_minutes"]
    f["base_pace"] = p["pace"]


def finish_daily(persona: str | None = None, today: date | None = None) -> int:
    """Once a day (refresh_tick, first tick): re-project every planned item and raise an alert on
    a crossing. Returns how many alerts were raised.

    Said once per crossing of the goal's date. Said again only when, since the date last said, the
    work grew or the pace fell AND the finish moved later by more than the size's margin — at most
    `_MOVED_MAX` times a crossing. No alert on a `default` pace: with no time given and nothing
    done there is no evidence of lateness, only the planner's own windows (Fable L2). Back on time,
    or nothing left: a pending alert is withdrawn and the next crossing is said afresh (L1)."""
    if not _flag("projected_finish"):
        return 0
    persona = resolve_persona(persona)
    O, D, PP = _O(), _D(), _PP()
    today = today or D._today()
    cfg = _cfg()
    margins = cfg.get("finish_margin_days") or {}
    tasks = [O._norm(t) for t in O._load(persona)]
    raised = 0
    with D._locked(persona):
        st = PP._load(persona)
        for rid, r in st["requests"].items():
            if r.get("status") != "planned":
                continue
            r["deadline"] = live_deadline(r, persona)     # the date now (Fable S3)
            p = project(r, tasks, today, cfg)
            f = dict(r.get("finish") or {})
            if p is None:
                if f:
                    f["done"] = today.isoformat()
                    if not (f.get("alert") or {}).get("said"):
                        f.pop("alert", None)
                    r["finish"] = f
                continue
            margin = int(margins.get(str(p["size"]), margins.get("M", 3)) or 0)
            proj = O._d(p["projected"])
            target = O._d(p["target"])
            base = O._d(f.get("baseline"))
            late = bool(target and proj > target)
            kind = None
            if not f.get("baseline"):
                _rebase(f, p)
                kind = "crossed" if late else None
            elif target and late and not f.get("late"):
                kind = "crossed"
            elif target and not late:
                if f.get("late") or (f.get("alert") and not f["alert"].get("said")):
                    _rebase(f, p)                          # back on time: silent, re-armed
                    if not (f.get("alert") or {}).get("said"):
                        f.pop("alert", None)
                    f["moved_count"] = 0
            elif (base and (proj - base).days > margin and _worse(p, f)
                  and int(f.get("moved_count") or 0) < _MOVED_MAX):
                kind = "moved"                             # late, or no date of its own
            if p["pace_source"] == "default":
                # No weekly time given and nothing done: the pace is invented, so a projection
                # past the date is no evidence (L2). Only hard facts count — the waiting alone runs
                # past the date, the date itself has passed, or a step is past its own date — said
                # once, with a new date as the fix and no pace claim (verify pass N1).
                kind = None
                hard = None
                if target:
                    floor = O._d(p["floor"])
                    overdue = any(O._d(t.get("due")) and O._d(t["due"]) < today
                                  for t in _plan_rows(rid, tasks) if t.get("status") == "open")
                    hard = ("the waiting alone runs past its date" if floor > target else
                            "its date has passed" if today > target else
                            "a step is past its own date" if overdue else None)
                if hard and not f.get("hard_late"):
                    kind = "crossed"
                    p = {**p, "projected": max(p["floor"], (today + timedelta(days=1)).isoformat())}
                f["hard_late"] = bool(hard)
            f.update(late=late, last=p)
            if kind:
                al = f.get("alert") or {}
                if kind == "crossed":
                    f["moved_count"] = 0
                    offers = 0                             # a new crossing is said afresh (L1)
                else:
                    f["moved_count"] = int(f.get("moved_count") or 0) + 1
                    offers = int(al.get("offers") or 0) if al and not al.get("said") else 0
                fix = (f"setting a new date with them — {hard}" if p["pace_source"] == "default"
                       else _fix(p, today, f.get("baseline")))
                f["alert"] = {"kind": kind, "projected": p["projected"], "target": p["target"],
                              "baseline": f.get("baseline"), "fix": fix,
                              "at": today.isoformat(), "offers": offers, "said": None}
                raised += 1
                D._log("finish_alert", persona, end=rid, kind=kind, projected=p["projected"])
            r["finish"] = f
        PP._save(st, persona)
    return raised


_MAX_ALERT_OFFERS = 3


def finish_notices(st: dict) -> list[dict]:
    """Pending finish alerts as project notices (`status: late`) — for `project_plan.notices`."""
    out = []
    for rid, r in (st.get("requests") or {}).items():
        al = (r.get("finish") or {}).get("alert") or {}
        if not al or al.get("said") or int(al.get("offers") or 0) >= _MAX_ALERT_OFFERS:
            continue
        if r.get("status") != "planned":
            continue
        out.append({"id": f"late:{rid}", "status": "late", "title": r.get("title") or rid,
                    "projected": al.get("projected"), "target": al.get("target"),
                    "baseline": al.get("baseline"), "kind": al.get("kind"), "fix": al.get("fix")})
    return out


def render_late(n: dict) -> str:
    O = _O()

    def day(s):
        d = O._d(s)
        return f"{d:%a} {d.day} {d:%b}" if d else str(s)

    if n.get("target"):
        head = (f"\"{n['title']}\" now looks likely to be finished {day(n['projected'])}, after "
                f"its date of {day(n['target'])}")
    else:
        head = (f"\"{n['title']}\" now looks likely to reach its next stages around "
                f"{day(n['projected'])}, later than {day(n.get('baseline'))}")
    return (f"{head}. Say it once, plainly, naming it, with the new date and this fix: {n['fix']} "
            f"— and never how it was worked out.")


# The fix's own words (Fable S2, verify N2): more time a week, or a new date.
_FIX_SAID = re.compile(r"\b(minutes?|hours?|an? (hour|evening)|evenings?) (a|each|per|every) week\b|"
                       r"\b(new|later|different) (date|deadline)\b|\b(move|moving|push|pushing|"
                       r"change|changing|shift|shifting) (the |its )?(date|deadline)\b", re.I)
_MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
           "september", "october", "november", "december")


def _date_said(reply: str, day: date | None) -> bool:
    """The alert's OWN new date: its weekday named in full, or its day number with its month
    (full name or the three-letter form, as a whole word) — never "maybe", "decide" or "mark"."""
    if not day:
        return False
    low = (reply or "").lower()
    if re.search(rf"\b{day.strftime('%A').lower()}\b", low):
        return True
    month = _MONTHS[day.month - 1]
    has_month = re.search(rf"\b({month}|{month[:3]})\b", low)
    has_day = re.search(rf"(?<!\d){day.day}(st|nd|rd|th)?\b", low)
    return bool(has_month and has_day)


def late_said(r: dict, reply: str, now: datetime, window: timedelta) -> bool:
    """Only within `window` of being offered, and only a reply that names it AND carries the
    news: the alert's own new date, or the fix's words."""
    O = _O()
    al = (r.get("finish") or {}).get("alert") or {}
    at = _D()._dt(al.get("offered_at"))
    if not at or now - at > window:
        return False
    if not (O._task_tokens(reply) & O._task_tokens(r.get("title") or "")):
        return False
    return _date_said(reply, O._d(al.get("projected"))) or bool(_FIX_SAID.search(reply or ""))


def mark_late_offered(r: dict, stamp: str | None = None) -> None:
    al = (r.get("finish") or {}).get("alert")
    if al and not al.get("said"):
        al["offers"] = int(al.get("offers") or 0) + 1
        al["offered_at"] = stamp or _D()._now().isoformat(timespec="seconds")


def mark_late_said(r: dict, stamp: str) -> None:
    f = r.get("finish") or {}
    al = f.get("alert")
    if al and not al.get("said"):
        al["said"] = stamp
        if f.get("last"):
            _rebase(f, f["last"], al.get("projected") or f.get("baseline"))
        else:
            f["baseline"] = al.get("projected") or f.get("baseline")


# =============================================================================================
# Re-vet (§ 4.2, triggers 1 and 2)
# =============================================================================================

def _steps_of(gid: str, tasks: list[dict]) -> list[dict]:
    O = _O()
    return [t for t in tasks if t.get("kind") in O._ONE_OFF
            and (t.get("part_of") == gid or t.get("goal_id") == gid)]


def _slip_days(s: dict) -> set[date]:
    """The days a task slipped. The day planner keeps `recent` (its last slip dates, since § 17);
    an older record has only {first, days, last} — a count. That is a run ending on `last` only
    when the days fill first..last exactly; otherwise only `last` is known (Fable L5: one slip
    this week and three six weeks ago is not "4 of the last 7 days")."""
    O = _O()
    if s.get("recent"):
        return {d for d in (O._d(x) for x in s["recent"]) if d}
    last, first = O._d(s.get("last")), O._d(s.get("first"))
    if not last:
        return set()
    n = int(s.get("days") or 0)
    if first and n == (last - first).days + 1:
        return {last - timedelta(days=i) for i in range(n)}
    return {last}


def _not_yet_days(persona: str, ids: set[str], since: date) -> set[date]:
    """Days a "not yet" was tapped on one of these tasks — the tap log carries the id since § 17."""
    import json
    D, O = _D(), _O()
    out: set[date] = set()
    try:
        lines = D._log_path(persona).read_text().splitlines()
    except OSError:
        return out
    for line in lines[-5000:]:
        if '"remind_requested"' not in line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        day = O._stamp_day(row.get("at"))
        if row.get("ref") in ids and day and day >= since:
            out.add(day)
    return out


def _unfulfilled_days(persona: str, words: list[str], since: date) -> set[date]:
    """Days an intention matching the goal or one of its steps was judged unfulfilled by the
    Accountability Index's gate (its window's end). Read from the stored verdicts — no model call,
    no calendar fetch."""
    O = _O()
    out: set[date] = set()
    try:
        from tools.accountability import read_gate_verdicts
        rows = read_gate_verdicts(persona).values()
    except Exception:  # noqa: BLE001
        return out
    toks = [O._task_tokens(w) for w in words if w]
    for v in rows:
        if v.get("verdict") != "unfulfilled":
            continue
        day = O._d(v.get("window_end"))
        if not day or day < since:
            continue
        it = O._task_tokens(str(v.get("intention") or ""))
        if any(O._tokens_match(it, t) for t in toks):
            out.add(day)
    return out


def noncompliance(persona: str, gid: str, goal: dict, tasks: list[dict], slips: dict,
                  since: date, today: date) -> set[date]:
    """Trigger 1's evidence: the distinct days in [since, today] on which this goal's steps were
    let slide — slipped on a day's plan, skipped/dismissed, "not yet", or a matching intention
    judged unfulfilled."""
    O = _O()
    steps = _steps_of(gid, tasks)
    ids = {t["id"] for t in steps}
    days: set[date] = set()
    for tid in ids:
        days |= _slip_days(slips.get(tid) or {})
    for t in steps:
        if t.get("status") == "dismissed":
            d = O._stamp_day(t.get("closed_at"))
            if d:
                days.add(d)
    days |= _not_yet_days(persona, ids, since)
    days |= _unfulfilled_days(persona, [str(goal.get("title") or "")] + [t.get("what") or ""
                                                                         for t in steps], since)
    return {d for d in days if since <= d <= today}


def _checkpoint(age: int, cps: list[int], every: int) -> int | None:
    """The latest checkpoint (days after vetting) reached at `age`, or None."""
    passed = [c for c in cps if c <= age]
    if cps and every and age > max(cps):
        k = (age - max(cps)) // every
        if k >= 1:
            passed.append(max(cps) + k * every)
    return max(passed) if passed else None


def revet_daily(persona: str | None = None, today: date | None = None) -> int:
    """Once a day (refresh_tick, first tick): fire triggers 1 and 2, once per checkpoint. Firing
    only records the question; the weekly look back carries it. Returns how many fired."""
    if not _flag("revet"):
        return 0
    persona = resolve_persona(persona)
    O, D, PP = _O(), _D(), _PP()
    today = today or D._today()
    rc = (_cfg().get("revet") or {})
    window = int(rc.get("window_days") or 7)
    need = int(rc.get("noncompliance_days") or 4)
    rearm = int(rc.get("rearm_days") or 28)
    cps = rc.get("checkpoints_days") or {}
    every = rc.get("every_days") or {}
    tasks = [O._norm(t) for t in O._load(persona)]
    slips = D._load_state(persona).get("slips") or {}
    goals = O._goal_index()
    fired = 0
    with D._locked(persona):
        st = PP._load(persona)
        rv = st.setdefault("revet", {})
        from tools.goals import CURRENT
        for gid, g in goals.items():
            if str(g.get("status") or "active") not in CURRENT:      # Fable L6
                continue
            rec = rv.setdefault(gid, {"fires": []})
            fires = rec["fires"]
            obligation = str(g.get("kind") or "") == "obligation"
            size = str(g.get("size") or "").upper()
            # Trigger 1 — quiet while an earlier one is unanswered and young; counts only days
            # after the last one was answered or fired.
            t1 = [f for f in fires if f.get("trigger") == "noncompliance"]
            last = t1[-1] if t1 else None
            since = today - timedelta(days=window - 1)
            quiet = False
            if last:
                at = O._d(last.get("at")) or today
                ans = O._d(last.get("answered"))
                if not ans and (today - at).days < rearm:
                    quiet = True
                since = max(since, (ans or at) + timedelta(days=1))
            req = st["requests"].get(gid) or {}
            stalled = next((m for m in req.get("milestones") or [] if m.get("status") == "stalled"
                            and not any(f.get("key") == f"stalled:{m.get('key')}" for f in fires)),
                           None)
            if not quiet and stalled:
                fires.append({"trigger": "noncompliance", "key": f"stalled:{stalled['key']}",
                              "at": today.isoformat(), "days": 0, "stalled": True, "shows": 0,
                              "obligation": obligation})
                fired += 1
                quiet = True
            if not quiet:
                days = noncompliance(persona, gid, g, tasks, slips, since, today)
                if len(days) >= need:
                    fires.append({"trigger": "noncompliance", "key": f"w{today.isoformat()}",
                                  "at": today.isoformat(), "days": len(days), "window": window,
                                  "shows": 0, "obligation": obligation})
                    fired += 1
            # Trigger 2 — L goals only, never an obligation, from when it was TAKEN ON (Fable S6:
            # `vetted.date` moves on every re-vet, so a "keep" answer would push the next check-in
            # out by a quarter). Keys carry the anchor: a goal parked and taken on again starts
            # its 2-week and 6-week checks afresh.
            vetted = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
            anchor = O._d(g.get("taken_on")) or O._d(vetted.get("date"))
            if size in cps and not obligation and anchor:
                cp = _checkpoint((today - anchor).days, [int(x) for x in cps[size]],
                                 int(every.get(size) or 0))
                key = f"{anchor.isoformat()}:d{cp}"
                done = {f.get("key") for f in fires if f.get("trigger") == "time"}
                if cp is not None and key not in done:
                    # Only the latest checkpoint reached is asked: a goal past two at deploy is
                    # asked once, not twice in a row.
                    fires.append({"trigger": "time", "key": key, "at": today.isoformat(),
                                  "checkpoint_days": cp, "shows": 0})
                    fired += 1
            if not fires:
                rv.pop(gid, None)
        PP._save(st, persona)
    if fired:
        D._log("revet_fired", persona, n=fired)
    return fired


def _pending(st: dict, goals: dict, max_shows: int) -> list[tuple[str, dict]]:
    out = []
    from tools.goals import CURRENT
    for gid, rec in (st.get("revet") or {}).items():
        g = goals.get(gid)
        if not g or str(g.get("status") or "active") not in CURRENT:
            continue
        for f in rec.get("fires") or []:
            if not f.get("said") and not f.get("answered") and int(f.get("shows") or 0) < max_shows:
                out.append((gid, f))
    out.sort(key=lambda x: str(x[1].get("at") or ""))
    return out


def _age_words(days: int) -> str:
    if days < 28:
        return f"{max(1, round(days / 7))} weeks"
    return f"about {max(1, round(days / 30.4))} months"


def _line(gid: str, g: dict, f: dict) -> str:
    title = " ".join(str(g.get("title") or gid).split())[:80]
    vetted = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
    keep = (f"to keep it as it is: update_goal vet `{gid}` verdict active, size "
            f"{str(g.get('size') or '').upper() or 'as before'}"
            + (f", priority {vetted.get('priority')}" if vetted.get("priority") else "")
            + (f", displaces \"{vetted.get('displaces')}\"" if vetted.get("displaces") else ""))
    choices = (f"keep it ({keep}), change it (update_goal update), set it aside until a date "
               f"(vet parked, revisit_on), or let it go (vet declined)")
    if f.get("obligation"):
        return (f"\"{title}\" `{gid}` — its steps have kept slipping. It has to be done, so never "
                f"ask whether they want it: ask whether its date still works and what would help "
                f"— a set time, someone's help, or a later date (update_goal update due)")
    if f.get("stalled"):
        return (f"\"{title}\" `{gid}` — none of its latest steps got done, so nothing more has "
                f"been planned for it. Ask, as a question and never a verdict, whether it still "
                f"fits: {choices}. Keeping it brings fresh steps")
    if f.get("trigger") == "noncompliance":
        return (f"\"{title}\" `{gid}` — its steps have slipped or been put off on {f.get('days')} "
                f"of the last {f.get('window')} days. Ask, as a question and never a verdict, "
                f"whether it still fits as it is: {choices}")
    return (f"\"{title}\" `{gid}` — {_age_words(int(f.get('checkpoint_days') or 14))} since it "
            f"was taken on. Ask, as a question and never a verdict, how it is going and whether "
            f"it is still worth the time it takes: {choices}")


def weekly_revet(persona: str, today: date) -> list[tuple[str, str]]:
    """The re-vet question(s) for this week's look back — (goal id, line), at most `per_week`,
    none if one was said in the last 7 days. READ ONLY: called under the day-plan lock."""
    if not _flag("revet"):
        return []
    O, PP = _O(), _PP()
    rc = _cfg().get("revet") or {}
    st = PP._load(persona)
    goals = O._goal_index()
    week = (today - timedelta(days=6)).isoformat()
    if any(str(f.get("said") or "") >= week
           for rec in (st.get("revet") or {}).values() for f in rec.get("fires") or []):
        return []
    out: list[tuple[str, str]] = []
    seen: set = set()
    for gid, f in _pending(st, goals, int(rc.get("max_shows") or 3)):
        if gid in seen:
            continue
        seen.add(gid)
        out.append((gid, _line(gid, goals[gid], f)))
        if len(out) >= int(rc.get("per_week") or 1):
            break
    return out


def mark_shown(gids: list[str], persona: str | None = None) -> None:
    """A weekly look back carried these goals' questions (after the lock is released)."""
    if not gids:
        return
    D, PP = _D(), _PP()
    # Once per ISO week (Fable L7): `max_shows` counts weekly reviews, and a review that renders
    # the block on several turns is still one review.
    week = "%d-W%02d" % D._today().isocalendar()[:2]
    try:
        with D._locked(persona):
            st = PP._load(persona)
            for gid in gids:
                for f in ((st.get("revet") or {}).get(gid) or {}).get("fires") or []:
                    if not f.get("said") and not f.get("answered") and f.get("shown_week") != week:
                        f["shows"] = int(f.get("shows") or 0) + 1
                        f["shown_week"] = week
            PP._save(st, persona)
    except Exception as exc:  # noqa: BLE001 — bookkeeping never breaks a reply
        logger.warning(f"[goal_network] re-vet show not recorded: {exc}")


def _signal(kind: str, persona: str, **fields) -> None:
    if not _flag("ranking_signals"):               # "Off: nothing is written" (Fable L8)
        return
    try:
        from tools.ranking_review import append_signals
        D = _D()
        now = D._now()
        append_signals([{"at": now.isoformat(timespec="seconds"), "day": now.date().isoformat(),
                         "kind": kind, "source": "goal_network", **fields}], persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[goal_network] signal not written: {exc}")


def mark_said(gids: list[str], persona: str | None = None) -> int:
    """A reply asked about these goals: every open fire on each is said (one question answers
    them all), and one `revet_asked` row each. After the lock is released."""
    if not gids:
        return 0
    D, PP = _D(), _PP()
    today = D._today().isoformat()
    rows = []
    with D._locked(persona):
        st = PP._load(persona)
        for gid in gids:
            fs = [f for f in ((st.get("revet") or {}).get(gid) or {}).get("fires") or []
                  if not f.get("said") and not f.get("answered")]
            for f in fs:
                f["said"] = today
            if fs:
                rows.append({"goal_id": gid, "trigger": fs[0].get("trigger"),
                             "checkpoint": fs[0].get("key"), "days": fs[0].get("days")})
        PP._save(st, persona)
    for r in rows:
        _signal("revet_asked", persona, **{k: v for k, v in r.items() if v is not None})
    return len(rows)


_ANSWER_DAYS = 14


def note_answer(goal_id: str, verdict: str, persona: str | None = None) -> bool:
    """`update_goal vet` on a goal whose re-vet was asked within `_ANSWER_DAYS`: that is the
    answer. Records it, writes `revet_answer`, and — kept, after a stalled milestone — queues
    fresh steps. Best effort; never blocks the verdict."""
    if not _flag("revet"):
        return False
    D, O, PP = _D(), _O(), _PP()
    persona = resolve_persona(persona)
    today = D._today()
    hit = None
    try:
        with D._locked(persona):
            st = PP._load(persona)
            for f in ((st.get("revet") or {}).get(goal_id) or {}).get("fires") or []:
                said = O._d(f.get("said"))
                if said and not f.get("answered") and (today - said).days <= _ANSWER_DAYS:
                    f["answered"] = today.isoformat()
                    f["verdict"] = verdict
                    hit = hit or f
            if hit:
                PP._save(st, persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[goal_network] re-vet answer not recorded: {exc}")
        return False
    if not hit:
        return False
    _signal("revet_answer", persona, goal_id=goal_id, verdict=verdict,
            trigger=hit.get("trigger"), checkpoint=hit.get("key"), asked_on=hit.get("said"))
    if verdict == "active" and hit.get("stalled"):
        try:
            PP.replan_stalled(goal_id, persona)
        except Exception:  # noqa: BLE001
            pass
    return True
