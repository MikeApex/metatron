"""
tools/goals.py — read and write goals.yaml.

Goals are Sensitive-tier from day one:
- Written with 600 permissions (owner read/write only)
- Never routed to a cloud LLM for analysis (Phase 3+: local LLM only)
- The `private_why` field is the user's underlying motivation — it must never
  leave this system. The `shareable_what` field is the instrumental behavior
  and may be summarized for cloud LLM advice in Phase 3+.

Structure:
    quarterly:   90-day goals
    weekly:      weekly priorities (link to quarterly via parent_goal)
    daily:       today's focus items (link to weekly via parent_goal)
"""

import os
import re
from datetime import datetime
from pathlib import Path

import yaml

from core.persona import persona_config_dir

_ROOT = Path(__file__).parent.parent


def _goals_path() -> Path:
    return persona_config_dir() / "goals.yaml"


def read_goals() -> dict:
    """
    Read the current goals file.

    Returns:
        Parsed goals as a dict, or empty dict if no goals file exists yet.
    """
    goals_path = _goals_path()
    if not goals_path.exists():
        return {}

    with open(goals_path) as f:
        data = yaml.safe_load(f)

    return data or {}


def write_goals(content: dict) -> str:
    """
    Write goals to config/goals.yaml with 600 permissions.

    Merges top-level keys with any existing content (quarterly, weekly, daily).
    A key present in content replaces the existing value entirely — use this
    to update one horizon at a time without stomping the others.

    Args:
        content: Dict with one or more of: quarterly, weekly, daily.

    Returns:
        Confirmation string.
    """
    existing = read_goals()
    existing.update(content)

    goals_path = _goals_path()
    goals_path.parent.mkdir(parents=True, exist_ok=True)

    with open(goals_path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    os.chmod(goals_path, 0o600)

    return f"Goals written to {goals_path}"


# `long` sits above quarterly (goal–task network plan § 4.6, § 10 R6): a language is not a
# 90-day goal. Every reader that walks horizons reads this tuple, so a long goal links,
# weights and sweeps like the rest.
HORIZONS = ("long", "quarterly", "weekly", "daily")
_ID_PREFIX = {"long": "l", "quarterly": "q", "weekly": "w", "daily": "d"}

# Goal statuses. `proposed` is a goal stated in chat and not yet vetted; `parked` is "later",
# with a date to re-ask; `declined` is kept, not deleted (archive-on-merge). Only the first
# four reach prompts as current goals; `proposed` reaches them under "being considered";
# `parked` and `declined` never (§ 10 R6, `prompt_view`). Only `active` goals are decomposed.
STATUSES = ("active", "not_started", "at_risk", "completed", "proposed", "parked", "declined")
CURRENT = ("active", "not_started", "at_risk")
_SIZES = ("S", "M", "L")

# Fields an in-conversation edit may set. `private_why` is here because a goal
# added mid-conversation usually arrives with its motivation attached — the
# reason is the part worth capturing, and asking the user to repeat it in a
# formal interview later is how it gets lost.
_EDITABLE = ("title", "private_why", "shareable_what", "status", "due",
             "parent_goal", "context", "essential", "size", "kind", "timeline",
             "open_questions", "revisit_on", "starts_on", "hold_note")


# --- not now: a later start, a hold that comes back (goal walkthrough fixes, plan § 19) -------
# Mike, 2026-11-25. Two ways a goal is "not now", chosen by the user's words:
#   * "on hold until X" / "starts again X" — taken on, `starts_on` X. Nothing is planned, counted,
#     re-checked or alerted for it before that day; from it, it simply runs (ruling 2, ruling 3).
#   * "park it" / "revisit X" — `parked`, `revisit_on` X. On that day it comes back to Synth's
#     view and Synth asks once: take it up, give it a new date, or let it go (ruling 1).
# Both carry an optional `hold_note` ("stretching only until then"), shown only while the goal is
# held — a hold's note goes when the hold does, so it cannot outlive it (Mike: no inertia).

def _today() -> "date":
    try:
        from tools.obligations import _today as _t
        return _t()
    except Exception:  # noqa: BLE001
        return datetime.now().date()


def not_started(g: dict | None, today=None) -> bool:
    """A goal taken on with a `starts_on` still ahead: not planned, counted or re-checked yet."""
    if not isinstance(g, dict):
        return False
    sd = _iso(g.get("starts_on") or "")
    return bool(sd and sd > (today or _today()).isoformat())


def live(g: dict | None, today=None) -> bool:
    """Current AND started — what plans, weekly time, re-checks and finish alerts act on."""
    return (isinstance(g, dict) and str(g.get("status") or "active") in CURRENT
            and not not_started(g, today))


def _title_of(g: dict) -> str:
    return str(g.get("title") or g.get("id") or "this goal").strip()


def _children(data: dict, goal_id: str) -> list[dict]:
    """The habits and goals filed under this one (`parent_goal`)."""
    return [c for h in HORIZONS for c in (data.get(h) or [])
            if isinstance(c, dict) and str(c.get("parent_goal") or "") == str(goal_id)]


def _parent(data: dict, g: dict) -> dict | None:
    pid = str(g.get("parent_goal") or "").strip()
    hit = _find_goal(data, pid) if pid else None
    return hit[2] if hit else None


def _end_hold(g: dict) -> None:
    """The goal is current and running again: the hold's date, note and asked-stamp go."""
    for k in ("revisit_on", "revisit_raised", "hold_note", "parked_with"):
        g.pop(k, None)


def _start_date(value) -> str | None:
    """`starts_on` as given: a date, or "today"/"now" — start it now (Fable S7: "actually, start
    it now" had no way out of a later start)."""
    v = str(value or "").strip().lower()
    if v in ("today", "now"):
        return _today().isoformat()
    return _iso(v)


def _follow_parent(data: dict, parent: dict, before: dict) -> tuple[list[str], list[str]]:
    """A habit moves with the goal it serves (Mike, 2026-11-25 #8): parked with it, back with it,
    starting when it starts. Returns (titles that moved, titles left as they were) — the result
    names both, so whichever is being talked about, the other is raised."""
    moved, left = [], []
    pid = str(parent.get("id"))
    status, was = str(parent.get("status") or "active"), str(before.get("status") or "active")
    for c in _children(data, pid):
        cs = str(c.get("status") or "active")
        if status == "parked" and cs in CURRENT:
            c.update(status="parked", revisit_on=parent.get("revisit_on"), parked_with=pid)
            moved.append(_title_of(c))
        elif status in CURRENT and was == "parked" and cs == "parked" and (
                c.get("parked_with") == pid or (c.get("revisit_on")
                                                and c.get("revisit_on") == before.get("revisit_on"))):
            c["status"] = "active"
            _end_hold(c)
            if str(c.get("size") or "").upper() == "L":
                c.pop("size", None)         # a practice is not a large goal of its own (#8)
            moved.append(_title_of(c))
        elif status in CURRENT and cs in CURRENT and parent.get("starts_on") != before.get("starts_on"):
            if not_started(parent):
                c["starts_on"] = parent["starts_on"]
            else:
                c.pop("starts_on", None)
            moved.append(_title_of(c))
        elif status != was:
            left.append(f"{_title_of(c)} ({cs})")
    return moved, left


def _park_children_steps(data: dict, g: dict) -> None:
    """A practice parked with its goal has its open steps closed, as the goal's own are."""
    if str(g.get("status") or "") != "parked":
        return
    for c in _children(data, str(g.get("id"))):
        if c.get("parked_with") == str(g.get("id")):
            _close_steps(str(c.get("id")), "parked")


def _family_tail(data: dict, g: dict, moved: list[str], left: list[str]) -> str:
    out = ""
    if moved:
        out += f" Its practice — {', '.join(moved)} — goes with it; mention that."
    if left:
        out += f" Under it, still as it was: {', '.join(left)} — ask whether that changes too."
    par = _parent(data, g)
    if par:
        out += (f" This is the practice under \"{_title_of(par)}\" "
                f"({par.get('status') or 'active'}) — raise that goal with them too.")
    return out


def _started_tail(g: dict) -> str:
    if not not_started(g) or str(g.get("status") or "active") not in CURRENT:
        return ""
    tail = (f" It stays taken on and starts on {g['starts_on']}: nothing is planned, counted or "
            f"checked before then.")
    try:
        from tools.obligations import _load
        open_ = [str(t.get("what") or "") for t in _load(None) if t.get("status") == "open"
                 and str(t.get("goal_id") or t.get("part_of") or "") == str(g.get("id"))]
    except Exception:  # noqa: BLE001
        open_ = []
    if open_:
        tail += (f" Its open tasks stay on the list ({'; '.join(open_[:4])}) — ask whether any "
                 f"should wait until then (update_task defer).")
    return tail


def _next_id(goals: list, horizon: str) -> str:
    prefix = _ID_PREFIX[horizon]
    used = set()
    for g in goals:
        gid = str(g.get("id", ""))
        if gid.startswith(prefix) and gid[len(prefix):].isdigit():
            used.add(int(gid[len(prefix):]))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}{n}"


def _wave_on() -> bool:
    try:
        from tools import day_plan_config as C
        return C.flag("rolling_wave")
    except Exception:  # noqa: BLE001
        return False


def _calling_agent() -> str:
    """The agent whose tool call this is, from the request trace; "" when none is bound (a
    direct call, a test). Read, never trusted from an argument a model fills in."""
    try:
        from core.trace import get_current_agent
        rec = get_current_agent()
        return str(getattr(rec, "agent", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _find_goal(data: dict, goal_id: str) -> tuple[str, int, dict] | None:
    for h in HORIZONS:
        for i, g in enumerate(data.get(h) or []):
            if isinstance(g, dict) and str(g.get("id", "")) == goal_id:
                return h, i, g
    return None


def _iso(value: str) -> str | None:
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _close_steps(goal_id: str, status: str) -> None:
    """A task part_of a goal that is declined, parked or completed is closed with that reason
    (§ 4.1). The ledger owns the write; a failure never blocks the goal change."""
    _end_talk(goal_id, f"goal_{status}")
    try:
        from tools.obligations import close_plan_of
        close_plan_of(goal_id, f"its goal was {status}")
    except Exception:  # noqa: BLE001
        pass


_VET_PRIORITIES = ("high", "normal", "low")


def vet_goal(goal_id: str, verdict: str, size: str = "", displaces: str = "", priority: str = "",
             revisit_on: str = "", by: str = "", kind: str = "", weekly_minutes=None,
             done_means: str = "", starting_point: str = "", effort_hours=None,
             due: str = "", starts_on: str = "", hold_note: str = "") -> str:
    """Record a vetting verdict on one goal (§ 4.2, § 10 R3). Depth is the size Synth gave it in
    the turn: S needs nothing beyond the ledger; M needs a date it is feasible by and a priority
    against what is open; L is vetted by the Goals Interviewer's re-interview, which is phase 3 —
    until then an L goal stays `proposed` ("being considered") and is never decomposed."""
    verdict = str(verdict or "").strip().lower()
    if verdict not in ("active", "parked", "declined"):
        return "Error: verdict must be active, parked or declined."
    size = str(size or "").strip().upper()
    data = read_goals()
    hit = _find_goal(data, str(goal_id or "").strip())
    if not hit:
        return f"Error: no goal with id '{goal_id}'."
    h, _i, g = hit
    before = dict(g)
    if size == "L" and _parent(data, g):
        # A practice under a goal (`d1` under Bulgarian, 11-25 #8) is not a large goal of its
        # own: its time is part of its goal's weekly time, and it parks and returns with it.
        par = _parent(data, g)
        return (f"Error: \"{_title_of(g)}\" is the practice under \"{_title_of(par)}\" — its time "
                f"is part of that goal's, so it is not sized as a large goal of its own. Talk "
                f"about it together with \"{_title_of(par)}\". Nothing was changed.")
    size = size or str(g.get("size") or "").upper()
    if size == "L" and _parent(data, g) and verdict == "active":
        size = ""                        # an old L on a practice is not carried into a take-on
    sd = ""
    if str(starts_on or "").strip():
        sd = _start_date(starts_on) or ""
        if not sd:
            return "Error: starts_on is YYYY-MM-DD. Nothing was changed."
        if verdict != "active":
            return ("Error: `starts_on` is for a goal taken on now that begins later (verdict "
                    "active). A goal to decide on again later is parked with `revisit_on`. "
                    "Nothing was changed.")
    # high | normal | low since 2026-11-22 (ranking § 16): free text ("ahead of the Northwind
    # review", 11-21) was recorded and then ignored by every score. What it ranks above goes in
    # `displaces`.
    priority = str(priority or "").strip().lower()
    if priority and priority not in _VET_PRIORITIES:
        return ("Error: `priority` is high, normal or low — put what it ranks above in "
                "`displaces`. Nothing was changed.")
    kind = str(kind or "").strip().lower()
    if kind and kind not in ("goal", "obligation"):
        return "Error: kind is goal or obligation. Nothing was changed."
    if verdict == "active":
        if size not in _SIZES and not _parent(data, g):
            return ("Error: say how big it is first — size S (one sitting), M (hours to days, one "
                    "end date) or L (recurring time for weeks or more). Nothing was changed.")
        if size == "L":
            # § 4.2's L row: Synth's SHORT pass — what it displaces in a real week and where it
            # ranks — takes it on; the Interviewer's full pass is phase 3. Without this, every
            # recurring goal stated in chat stayed "being considered" for the whole phase 2 → 3
            # interval, where today it becomes current and gets weekly time (Fable diff review #4).
            # An L goal is given weekly time, never steps (plan_project refuses it).
            if not str(displaces or "").strip() or not str(priority or "").strip():
                return ("Error: a goal that needs regular time is taken on only once it is clear "
                        "what it takes that time from in a real week (`displaces`) and where it "
                        "ranks (`priority`). Nothing was changed.")
        if size == "M":
            if not _iso(g.get("due") or ""):
                return ("Error: an M goal is vetted against its date — set `due` first (update_goal "
                        "action=update), then vet. Nothing was changed.")
            if not str(priority or "").strip():
                return ("Error: say where it ranks against what is already open (`priority`). "
                        "Nothing was changed.")
    # Part B (§ 18): the Goals Interviewer's verdict at the end of a goal talk records what the
    # planner plans from — the time a week and what "done" means (Mike: five fields), with where
    # they are now and the effort it realistically takes when known. Off, none of this is read.
    talk = _talk_on_goal(str(g.get("id")))
    extra = _talk_fields(weekly_minutes, done_means, starting_point, effort_hours, due) \
        if _talk_flag() else {}
    if isinstance(extra, str):
        return extra
    if talk and extra.get("weekly_minutes") and not (verdict == "active" and size == "L"):
        err = _theirs_check(str(g.get("id")), extra["weekly_minutes"])
        if err:
            return err
    if talk and verdict == "active" and size == "L":
        # A real talk, not an opening line (Fable S2): the full pass needs the user to have
        # spoken in it several times. Parking or declining needs no minimum.
        need = _talk_min_turns()
        if _talk_user_turns(str(g.get("id"))) < need:
            return ("Error: this has hardly been talked through yet — keep going with them; the "
                    "verdict comes once what done looks like, the time a week and the trade-off "
                    "are theirs. Nothing was changed.")
        have_wm = extra.get("weekly_minutes") or g.get("weekly_minutes")
        have_dm = extra.get("done_means") or g.get("done_means")
        missing = [n for n, v in (("weekly_minutes", have_wm), ("done_means", have_dm)) if not v]
        if missing:
            return ("Error: before it is taken on, settle with them " + " and ".join(
                {"weekly_minutes": "the time a week it gets (`weekly_minutes`)",
                 "done_means": "what done looks like, in a line (`done_means`)"}[m]
                for m in missing) + ". Nothing was changed.")
        # The weekly time is THEIRS (11-25 #3) — passed now or already on the goal (a short
        # pass, an earlier talk's proposal: `q4`'s 120 on 11-25), it is confirmed with them in
        # THIS talk before it is planned from. After the turn minimum, so "keep going" comes first.
        err = _theirs_check(str(g.get("id")), have_wm)
        if err:
            return err
        # The realism point has to land before they commit (11-25 #4): what their time means in
        # years or months, said in the talk — checked against the Interviewer's own turns.
        calc = _realism_line({**g, **extra})
        if calc and not _realism_said(str(g.get("id"))):
            return ("Error: before the verdict, put plainly to them what their time means — "
                    f"{calc} — in your words, as a question they can answer (more time, a later "
                    "date, or a smaller \"done\"). Nothing was changed.")
    if verdict == "parked":
        when = _iso(revisit_on)
        if not when:
            return "Error: a parked goal needs `revisit_on` (YYYY-MM-DD), the day to ask again."
        g["revisit_on"] = when
    # The depth of an L vet (goal network phase 3 § 17): "full" only when the Goals Interviewer
    # records it — read from the call trace, never an argument a model fills in — and a later
    # re-vet that keeps the goal never lowers it. Rolling wave plans only a "full" one (Mike,
    # 2026-11-24: "2 questions isn't nearly enough for an L goal").
    # Fable diff review L9: "full" is written only while `rolling_wave` is on — off, the marker is
    # phase 2's ("short"), and no Interviewer vet made before part B's re-interview exists can
    # license wave planning the day the flag is flipped. L3: a parked or declined verdict carries
    # the depth through, so a goal parked and taken on again keeps what it was talked through.
    prev = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
    depth_pass = None
    if size == "L" and verdict == "active":
        # While `goal_talk` is on, the talk is the only way to a full pass (verify S2): an
        # Interviewer vet of some OTHER goal mid-talk stays short. Off, part A's rule stands.
        depth_pass = ("full" if prev.get("pass") == "full" or (
            _calling_agent() == "goals_interviewer"
            and (talk or (_wave_on() and not _talk_flag()))) else "short")
    elif verdict in ("parked", "declined"):
        depth_pass = prev.get("pass")
    # The re-vet clock's anchor (Fable S6): when the goal was TAKEN ON — set on a fresh take-on,
    # never moved by a re-vet that keeps it, so a "keep" answer does not push the next check-in
    # out by a quarter. A goal already current with no anchor keeps its last vetting date.
    was_current = str(g.get("status") or "") in CURRENT
    if verdict == "active":
        if not was_current or not g.get("taken_on"):
            g["taken_on"] = (prev.get("date") if was_current and prev.get("date")
                             else datetime.now().strftime("%Y-%m-%d"))
    g.update(extra)
    g["status"] = verdict
    if verdict == "active":
        if str(before.get("status") or "") == "parked" and not sd:
            g.pop("starts_on", None)      # taken up from parked means now (S7)
        _end_hold(g)
        if sd:
            g["starts_on"] = sd
    if verdict == "parked":
        g.pop("revisit_raised", None)        # a new date is asked about afresh
        g.pop("parked_with", None)
    note = " ".join(str(hold_note or "").split())[:200]
    if note and (verdict == "parked" or not_started(g)):
        g["hold_note"] = note
    if size in _SIZES:
        g["size"] = size
    if kind:
        g["kind"] = kind
    g["vetted"] = {k: v for k, v in (
        ("date", datetime.now().strftime("%Y-%m-%d")), ("depth", size or None),
        ("displaces", str(displaces or "").strip() or None),
        ("priority", str(priority or "").strip() or None),
        ("by", by or _calling_agent() or None),
        ("pass", depth_pass)) if v}
    moved, left = _follow_parent(data, g, before)
    _write(data)
    # A goal asked about again (re-vet) — this verdict is the answer: recorded for the monthly
    # review, and a stalled plan kept is given fresh steps. Never blocks the verdict.
    try:
        from tools.goal_network import note_answer
        note_answer(str(g["id"]), verdict)
    except Exception:  # noqa: BLE001
        pass
    ended = offer = False
    if talk:
        try:
            from tools.goal_talk import on_vet
            ended = on_vet(str(g["id"]), verdict)
        except Exception:  # noqa: BLE001
            pass
    elif verdict == "active" and size == "L" and depth_pass != "full":
        # Synth's short pass takes it on with weekly time; the proper talk is its first task.
        offer = (_talk_task(str(g["id"]), by="short_pass")
                 and _calling_agent() != "goals_interviewer")
    elif verdict in ("parked", "declined"):
        _end_talk(str(g["id"]), f"goal_{verdict}")
    if verdict in ("parked", "declined"):
        _close_steps(str(g["id"]), verdict)
        _park_children_steps(data, g)
    elif verdict == "active":
        # A goal re-vetted at a new priority (or as an obligation) re-weighs its open steps now,
        # not at tomorrow's sweep (ranking § 16). Never blocks the verdict.
        try:
            from tools.obligations import reweigh_plan_steps, _GOAL_CACHE
            _GOAL_CACHE.update(key=None)
            reweigh_plan_steps()
        except Exception:  # noqa: BLE001
            pass
    word = {"active": "taken on", "parked": f"parked until {g.get('revisit_on')}",
            "declined": "declined (kept on record)"}[verdict]
    tail = (" Ask plan_project to break it into steps." if verdict == "active" and size == "M"
            else " It is given regular time each week, not steps." if verdict == "active"
            and size == "L" and depth_pass != "full" else
            " It will be planned out of sight, a stage at a time." if verdict == "active"
            and size == "L" and _talk_flag() else
            " It is given regular time each week, not steps." if verdict == "active"
            and size == "L" else "")
    if verdict == "active" and not_started(g):
        tail = (f" It starts on {g['starts_on']}: nothing is planned or counted before then, and "
                f"from that day it is " + ("planned out of sight, a stage at a time."
                                           if depth_pass == "full" else "given its weekly time."))
    if offer:
        tail += _OFFER
    if ended and verdict == "parked":
        still = _open_fields(g)
        if still:
            # A parked talk keeps what was settled and says what was not (11-25 #3, 5b): "have we
            # talked it out enough?" then has an honest answer.
            tail += (f" Still open for when it comes back: {', '.join(still)} — say so in a "
                     f"sentence; what was settled is kept.")
    if ended:
        tail += (" The talk is over: thank them in a sentence and say what happens next — their "
                 "next message is the usual conversation.")
    tail += _family_tail(data, g, moved, left)
    calc = _realism_line(g) if _talk_flag() else ""
    return f"{h} goal {g['id']} {word}.{tail}" + (f" Arithmetic: {calc}" if calc else "")


def _theirs_check(goal_id: str, wm) -> str:
    """In a goal talk, a weekly time is recorded only when it is the user's (11-25 #3): a figure
    they said, or a plain yes to one figure the Interviewer named. Never the Interviewer's own
    proposal. "" when fine; an `Error:` string otherwise."""
    try:
        from core.persona import resolve_persona
        from tools.goal_talk import minutes_theirs
        if minutes_theirs(resolve_persona(None), goal_id, wm):
            return ""
    except Exception:  # noqa: BLE001 — unreadable talk state: do not block on it
        return ""
    return ("Error: that weekly time is a suggestion, not their figure — they have not said it or "
            "agreed to it. Ask for theirs: a number they give, or a yes to ONE figure you name "
            "(\"shall we say 120 minutes a week?\"). Nothing was changed.")


def _realism_said(goal_id: str) -> bool:
    try:
        from core.persona import resolve_persona
        from tools.goal_talk import realism_said
        return realism_said(resolve_persona(None), goal_id)
    except Exception:  # noqa: BLE001
        return True


def _open_fields(g: dict) -> list[str]:
    try:
        from tools.goal_talk import open_fields
        return open_fields(g)
    except Exception:  # noqa: BLE001
        return []


def _talk_flag() -> bool:
    try:
        from tools.goal_talk import on
        return on()
    except Exception:  # noqa: BLE001
        return False


def _talk_on_goal(goal_id: str) -> bool:
    """Is the Goals Interviewer, right now, in an ACTIVE goal talk about this goal? Read from the call
    trace and the talk's own state — never from an argument a model fills in."""
    if not _talk_flag() or _calling_agent() != "goals_interviewer":
        return False
    try:
        from core.persona import resolve_persona
        from tools.goal_talk import current
        talk = current(resolve_persona(None))
        return bool(talk and talk.get("goal_id") == goal_id and talk.get("status") == "active")
    except Exception:  # noqa: BLE001
        return False


def _talk_user_turns(goal_id: str) -> int:
    try:
        from core.persona import resolve_persona
        from tools.goal_talk import user_turns
        return user_turns(resolve_persona(None), goal_id)
    except Exception:  # noqa: BLE001
        return 0


def _talk_min_turns() -> int:
    try:
        from tools.goal_talk import _cfg
        return int(_cfg().get("min_user_turns") or 4)
    except Exception:  # noqa: BLE001
        return 4


def _end_talk(goal_id: str, reason: str) -> None:
    """The goal stopped being one to talk through (closed, removed, made smaller): any talk about
    it ends and its task closes (Fable S3/S4). Off: nothing."""
    if not _talk_flag():
        return
    try:
        from tools.goal_talk import end
        end(goal_id, reason)
    except Exception:  # noqa: BLE001
        pass


def _talk_fields(weekly_minutes, done_means, starting_point, effort_hours, due) -> dict | str:
    """The talk's fields, checked; an `Error:` string when one is unreadable. Empty ones skipped."""
    out: dict = {}
    if weekly_minutes not in (None, ""):
        try:
            wm = int(round(float(weekly_minutes)))
        except (TypeError, ValueError):
            return "Error: `weekly_minutes` is a number of minutes a week. Nothing was changed."
        if not 10 <= wm <= 3000:
            return "Error: `weekly_minutes` is between 10 and 3000. Nothing was changed."
        out["weekly_minutes"] = wm
    for name, val, cap in (("done_means", done_means, 300), ("starting_point", starting_point, 200)):
        v = " ".join(str(val or "").split())
        if v:
            out[name] = v[:cap]
    if effort_hours not in (None, "", []):
        from tools.goal_talk import parse_effort
        eff = parse_effort(effort_hours)
        if not eff:
            return ("Error: `effort_hours` is hours, or a range like \"200-300\". Nothing was "
                    "changed.")
        out["effort_hours"] = eff
    if str(due or "").strip():
        iso = _iso(due)
        if not iso:
            return "Error: due is YYYY-MM-DD."
        out["due"] = iso
    return out


def _realism_line(g: dict) -> str:
    try:
        from tools.goal_talk import realism
        return realism(g.get("weekly_minutes"), g.get("effort_hours"), g.get("due"))
    except Exception:  # noqa: BLE001
        return ""


_HIDDEN_KEYS = ("vetted", "revisit_raised", "start_said", "parked_with", "hold_note")


def _held_line(g: dict, when: str) -> str:
    par = f" (practice for {g['parent_goal']})" if g.get("parent_goal") else ""
    note = f" — {g['hold_note']}" if g.get("hold_note") else ""
    return f"- {g.get('id', '?')}: {g.get('title', '')}{par} — {when}{note}"


def prompt_view(data: dict, today=None) -> str:
    """Goals as every prompt sees them (§ 10 R6) — the one filter. Current goals (active,
    not_started, at_risk; and completed, which the record keeps) as YAML; proposed ones under a
    short "being considered" heading; declined never; `vetted` records never. A goal with no
    status is active, as it has always been read.

    Amended 2026-11-25 (Mike, walkthrough ruling 1): parked goals are no longer invisible — that
    left "when we bring it back in mid-January" with nothing to bring it back. Each is one line
    under "On hold", with its date and note; on its date it moves to "Back today" for one ask. A
    goal taken on with a later `starts_on` is listed under "Starting later", not as current; on
    its day it is current again and named once under "Back from today"."""
    today = today or _today()
    iso = today.isoformat()
    current: dict = {}
    considered: list[str] = []
    held: list[str] = []
    back: list[str] = []
    later: list[str] = []
    started: list[str] = []
    for h in HORIZONS:
        for g in data.get(h) or []:
            if not isinstance(g, dict):
                continue
            status = str(g.get("status") or "active")
            if status == "declined":
                continue
            if status == "parked":
                when = _iso(g.get("revisit_on") or "") or ""
                if when and when <= iso and not g.get("revisit_raised"):
                    back.append(_held_line(g, f"on hold until {when}"))
                elif when and when <= iso:
                    held.append(_held_line(g, f"its date ({when}) has come and it was put to them "
                                              f"on {g['revisit_raised']} — leave it unless they "
                                              f"bring it up"))
                else:
                    held.append(_held_line(g, f"until {when}" if when else "no date"))
                continue
            if status == "proposed":
                considered.append(f"- {g.get('id', '?')}: {g.get('title', '')}"
                                  + (f" (by {g['due']})" if g.get("due") else ""))
                continue
            if status in CURRENT and not_started(g, today):
                later.append(_held_line(g, f"starts {g['starts_on']}"))
                continue
            if (status in CURRENT and _iso(g.get("starts_on") or "")
                    and not g.get("start_said")):
                started.append(f"- {g.get('id', '?')}: {g.get('title', '')}")
            current.setdefault(h, []).append({k: v for k, v in g.items()
                                              if k not in _HIDDEN_KEYS})
    for k, v in data.items():
        if k not in HORIZONS and k not in current:
            current[k] = v
    out = yaml.dump(current, default_flow_style=False, allow_unicode=True, sort_keys=False).strip() \
        if current else ""
    text = f"```yaml\n{out}\n```" if out else ""
    if started:
        text += ("\n\n### Back from today (taken on earlier to start now — mention it once, in a "
                 "sentence)\n" + "\n".join(started))
    if back:
        text += ("\n\n### Back on the list today (on hold until now — ask them once: take it up, "
                 "give it a new date, or let it go)\n" + "\n".join(back))
    if considered:
        text += ("\n\n### Being considered (not yet taken on — never treat these as current goals)\n"
                 + "\n".join(considered))
    if later:
        text += ("\n\n### Taken on, starting later (nothing is planned or nudged for these before "
                 "their date — never push them now; to start one now, update_goal starts_on "
                 "\"today\")\n" + "\n".join(later))
    if held:
        text += ("\n\n### On hold (not current — never plan or push these)\n" + "\n".join(held))
    return text.strip()


_RETURN_RE = re.compile(
    r"\bback\b|\bagain\b|\bon hold\b|\bparked\b|\bresum\w*|\brestart\w*|\btake (?:it|this|that)? ?up"
    r"|\bpick (?:it|this|that)? ?(?:back )?up|\bre-?date|\bnew date\b|\blet (?:it|this|that) go\b"
    r"|\brevisit\w*|\bstarts? (?:today|now|from)\b|\bfrom today\b", re.IGNORECASE)


# A sentence recording something done is not putting a goal back to the user (verify N5).
_LOGGED_RE = re.compile(r"\b(?:logged|recorded|noted|tracked|done|did|completed|finished|minutes of|"
                        r"appointment|session)\b", re.IGNORECASE)


def raised_in(reply: str, persona: str | None = None) -> list[str]:
    """After a reply reached the user: a goal under "Back on the list today" or "Back from today"
    that the reply names (a word of its title) has been put to them — stamped, so it is asked
    once. Returns the ids stamped. Never raises."""
    try:
        from tools.obligations import _task_tokens
        # A sentence that names the goal AND speaks of its return (Fable S4: "Logged 30 minutes of
        # exercise" must not spend exercise's one "it's back" question).
        sents = [x for x in re.split(r"(?<=[.!?])\s+|\n+", reply or "")
                 if _RETURN_RE.search(x) and not _LOGGED_RE.search(x)]
        if not sents:
            return []
        words = _task_tokens(" ".join(sents))
        if not words:
            return []
        data = read_goals()
        iso = _today().isoformat()
        hit: list[str] = []
        for h in HORIZONS:
            for g in data.get(h) or []:
                if not isinstance(g, dict):
                    continue
                status = str(g.get("status") or "active")
                due_back = (status == "parked" and not g.get("revisit_raised")
                            and (_iso(g.get("revisit_on") or "") or "9999") <= iso)
                due_start = (status in CURRENT and not g.get("start_said")
                             and (_iso(g.get("starts_on") or "") or "9999") <= iso)
                if not (due_back or due_start):
                    continue
                if not (_task_tokens(str(g.get("title") or "")) & words):
                    continue
                if due_back:
                    g["revisit_raised"] = iso
                else:
                    g["start_said"] = iso
                    g.pop("hold_note", None)      # the hold is over; its note goes with it
                hit.append(str(g.get("id")))
        if hit:
            _write(data)
        return hit
    except Exception:  # noqa: BLE001
        return []


def update_goal(
    action: str,
    horizon: str = "",
    goal_id: str = "",
    title: str = "",
    private_why: str = "",
    shareable_what: str = "",
    status: str = "",
    due: str = "",
    parent_goal: str = "",
    context: str = "",
    essential: bool | str | None = None,
    size: str = "",
    kind: str = "",
    verdict: str = "",
    displaces: str = "",
    priority: str = "",
    revisit_on: str = "",
    weekly_minutes: int | None = None,
    done_means: str = "",
    starting_point: str = "",
    effort_hours: str | None = None,
    starts_on: str = "",
    hold_note: str = "",
) -> str:
    """
    Add, edit, complete or remove a single goal.

    Separate from `write_goals`, which replaces a whole horizon at once. That
    shape is right for the goals interview, which authors the full set, and
    wrong for everything else: updating one daily goal means resending the
    entire daily list, and any goal left out of that list is silently deleted.
    Goals change continuously — one is finished, one is added — so the ordinary
    path has to be one goal at a time.

    Args:
        action:   add | update | complete | remove.
        horizon:  quarterly | weekly | daily. Required for add; inferred from
                  goal_id otherwise.
        goal_id:  Required for update, complete and remove.
        The rest:  Fields to set. For `update`, only the ones passed change.

    Returns:
        Confirmation, or an explanatory refusal.
    """
    action = str(action).strip().lower()
    actions = ("add", "update", "complete", "remove", "vet") + (("talk",) if _talk_flag() else ())
    if action not in actions:
        return f"Error: action must be one of {', '.join(actions)}."
    if action == "talk":
        # Part B (§ 18): the user said yes to talking this goal through properly, now.
        from tools.goal_talk import start
        return start(goal_id)
    if action == "vet":
        return vet_goal(goal_id, verdict, size=size, displaces=displaces, priority=priority,
                        revisit_on=revisit_on, kind=kind, weekly_minutes=weekly_minutes,
                        done_means=done_means, starting_point=starting_point,
                        effort_hours=effort_hours, due=due, starts_on=starts_on,
                        hold_note=hold_note)

    data = read_goals()
    fields = {k: v for k, v in (
        ("title", title), ("private_why", private_why),
        ("shareable_what", shareable_what), ("status", status), ("due", due),
        ("parent_goal", parent_goal), ("context", context), ("starts_on", starts_on),
        ("hold_note", " ".join(str(hold_note or "").split())[:200]),
    ) if str(v).strip()}
    if fields.get("starts_on") and not _start_date(fields["starts_on"]):
        return "Error: starts_on is YYYY-MM-DD, or \"today\" to start it now."
    if fields.get("starts_on"):
        fields["starts_on"] = _start_date(fields["starts_on"])
    if fields.get("status") and fields["status"].strip().lower() not in STATUSES:
        return f"Error: status must be one of {', '.join(STATUSES)}."
    if "status" in fields:
        fields["status"] = fields["status"].strip().lower()
    if str(size).strip():
        if str(size).strip().upper() not in _SIZES:
            return "Error: size is S, M or L."
        fields["size"] = str(size).strip().upper()
    if str(kind).strip():
        if str(kind).strip().lower() not in ("goal", "obligation"):
            return "Error: kind is goal or obligation."
        fields["kind"] = str(kind).strip().lower()
    if fields.get("due") and not _iso(fields["due"]):
        return "Error: due is YYYY-MM-DD."
    if _talk_flag():
        extra = _talk_fields(weekly_minutes, done_means, starting_point, effort_hours, "")
        if isinstance(extra, str):
            return extra
        fields.update(extra)
    # § 10 R6: a goal stated in chat is written `proposed`, in code, whatever status the model
    # sent — and only a vetting verdict (action=vet) takes it on. The Goals Interviewer authors
    # vetted goals and keeps its default.
    from_synth = _calling_agent() == "synthesizer"
    if from_synth and action == "update" and fields.get("status") in ("active", "not_started",
                                                                      "at_risk", "parked",
                                                                      "declined"):
        hit = _find_goal(data, str(goal_id).strip())
        if hit and str(hit[2].get("status") or "active") == "proposed":
            return ("Error: a goal being considered is taken on, parked or declined with "
                    "action=vet (it records the verdict). Nothing was changed.")
    # `essential` — "survived trade-off forcing": the goals the day planner protects time for
    # (archive/plans/day_planner_plan_2026-10-24.md § 4.1). Only write_goals could set it before,
    # so the Synthesizer could not mediate goal importance (Mike, F4). A real bool is stored,
    # never the string a model may send.
    if essential is not None and str(essential).strip() != "":
        ess = str(essential).strip().lower()
        if ess not in ("true", "false"):
            return "Error: essential must be true or false."
        fields["essential"] = ess == "true"

    if action == "add":
        if horizon not in HORIZONS:
            return f"Error: horizon must be one of {list(HORIZONS)} to add a goal."
        if "title" not in fields:
            return "Error: title is required to add a goal."
        bucket = data.setdefault(horizon, []) or []
        data[horizon] = bucket
        new = {"id": _next_id(bucket, horizon)}
        new.update(fields)
        if from_synth:
            new["status"] = "proposed"
        new.setdefault("status", "active")
        bucket.append(new)
        _write(data)
        has_task = new.get("size") == "L" and _talk_task(new["id"])
        offer = _OFFER if has_task and from_synth else ""
        if new["status"] == "proposed":
            return (f"Added {horizon} goal {new['id']} as being considered: {new['title']}. "
                    f"Size it and check it with the user (action=vet) before it is taken on."
                    + offer)
        return f"Added {horizon} goal {new['id']}: {new['title']}" + offer

    if not str(goal_id).strip():
        return f"Error: goal_id is required to {action} a goal. Use read_goals to find it."
    goal_id = str(goal_id).strip()

    # Locate the goal. Searching every horizon rather than trusting the caller's
    # `horizon` means a wrong horizon corrects itself instead of reporting a
    # goal missing that is plainly there.
    for h in HORIZONS:
        bucket = data.get(h) or []
        for i, g in enumerate(bucket):
            if str(g.get("id", "")) == goal_id:
                if action == "remove":
                    bucket.pop(i)
                    _write(data)
                    _end_talk(goal_id, "goal_removed")
                    return (f"Removed {h} goal {goal_id}: {g.get('title', '')}. "
                            f"Use action 'complete' instead when a goal was "
                            f"achieved — that keeps the record.")
                if action == "complete":
                    g["status"] = "completed"
                    g["completed_on"] = datetime.now().strftime("%Y-%m-%d")
                    g.update(fields)
                    _write(data)
                    _close_steps(goal_id, "completed")
                    return f"Completed {h} goal {goal_id}: {g.get('title', '')}"
                if not fields:
                    return (f"Error: nothing to change on {goal_id} — pass at "
                            f"least one of {list(_EDITABLE)}.")
                if fields.get("size") == "L" and _parent(data, g):
                    par = _parent(data, g)
                    return (f"Error: \"{_title_of(g)}\" is the practice under "
                            f"\"{_title_of(par)}\" — its time is part of that goal's, so it is not "
                            f"a large goal of its own. Nothing was changed.")
                if fields.get("weekly_minutes") and _talk_on_goal(goal_id):
                    err = _theirs_check(goal_id, fields["weekly_minutes"])
                    if err:
                        return err
                if fields.get("status") == "parked" and not (
                        fields.get("revisit_on") or _iso(revisit_on) or g.get("revisit_on")):
                    return ("Error: a goal on hold needs the day to look at it again — `revisit_on` "
                            "(YYYY-MM-DD); or, if it is decided and only starts later, keep it "
                            "taken on with `starts_on`. Nothing was changed.")
                before = dict(g)
                if _iso(revisit_on):
                    fields["revisit_on"] = _iso(revisit_on)
                g.update(fields)
                if fields.get("status") in CURRENT and str(before.get("status") or "") == "parked":
                    _end_hold(g)
                    if not fields.get("starts_on"):
                        g.pop("starts_on", None)   # taken up from parked means now (S7)
                if fields.get("status") == "parked" and before.get("status") != "parked":
                    g.pop("revisit_raised", None)
                if fields.get("starts_on"):
                    if not_started(g):
                        g.pop("start_said", None)      # a new later start is said afresh
                    elif not fields.get("hold_note"):
                        g.pop("hold_note", None)       # started now: the hold's note goes
                moved, left = _follow_parent(data, g, before)
                _write(data)
                if fields.get("status") in ("parked", "declined", "completed"):
                    _close_steps(goal_id, fields["status"])
                _park_children_steps(data, g)
                offer = (_OFFER if fields.get("size") == "L" and from_synth
                         and _talk_task(goal_id) else "")
                if (not offer and from_synth and str(before.get("status") or "") == "parked"
                        and fields.get("status") in CURRENT
                        and str(g.get("size") or "").upper() == "L"
                        and _talk_task(goal_id, by="back")):
                    # Taken up again from parked (ruling 1): a large goal not yet talked through
                    # gets a fresh talk task — the old one closed with the park — and one offer.
                    offer = _OFFER
                if fields.get("size") and fields["size"] != "L":
                    _end_talk(goal_id, "not_large")
                if fields.get("due"):
                    # A new date is how an obligation's re-vet is answered ("is the date still
                    # right?") — recorded like a vet's verdict (Fable L10). Never blocks.
                    try:
                        from tools.goal_network import note_answer
                        note_answer(goal_id, "date_changed")
                    except Exception:  # noqa: BLE001
                        pass
                return (f"Updated {h} goal {goal_id}: "
                        f"{', '.join(sorted(fields))} changed." + offer
                        + (_started_tail(g) if fields.get("starts_on") else "")
                        + _family_tail(data, g, moved, left))

    known = ", ".join(str(g.get("id", "?")) for h in HORIZONS for g in (data.get(h) or []))
    return f"Error: no goal with id '{goal_id}'. Existing ids: {known or 'none'}."


_OFFER = (" It deserves a proper talk: offer it once, in your words — now, or whenever they say; "
          "on a yes, update_goal action=talk.")


def _talk_task(goal_id: str, by: str = "sized") -> bool:
    """A goal sized L gets its talk-through task — the project's first task (§ 18). True only when
    it was opened by this call (so the result says to offer the talk once). Off: none, False."""
    if not _talk_flag():
        return False
    try:
        from tools.goal_talk import opened_task
        return opened_task(goal_id, by=by)      # True only when opened now — offered once (L4)
    except Exception:  # noqa: BLE001
        return False


def _write(data: dict) -> None:
    """Atomic (temp file + rename): a reader mid-write never sees an empty goals file — which a
    goal talk would read as "the goal was removed" (goal network § 18, verify N4)."""
    import tempfile
    path = _goals_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".goals.", dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


# Tool schemas — registered in orchestrator.register_tools()

READ_GOALS_SCHEMA = {
    "name": "read_goals",
    "description": (
        "Read the user's current goals (quarterly, weekly, daily). "
        "Use this at the start of a session to ground direction in the user's stated priorities."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

UPDATE_GOAL_SCHEMA = {
    "name": "update_goal",
    "description": (
        "Add, edit, complete or remove ONE goal. This is the ordinary way goals "
        "change: the user finishes something, adds something, or revises what "
        "they are aiming at, in the middle of a normal conversation.\n\n"
        "Use 'complete' when a goal has been achieved — it keeps the goal on "
        "record with a completion date. Use 'remove' only for a goal that was "
        "abandoned or entered by mistake.\n\n"
        "Call read_goals first to get the goal's id. Nothing outside the one "
        "goal named is touched.\n\n"
        "A goal added from conversation is recorded as being considered, not taken on. "
        "Use 'vet' to record the verdict once it has been checked with the user: verdict "
        "active (taken on), parked (with revisit_on) or declined (kept on record)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "add | update | complete | remove | vet"},
            "horizon": {"type": "string", "description": "long | quarterly | weekly | daily. Required for add. long = longer than a quarter."},
            "goal_id": {"type": "string", "description": "Id of the goal, e.g. 'd2'. Required for update, complete, remove."},
            "title": {"type": "string", "description": "The goal in one line. Required for add."},
            "private_why": {"type": "string", "description": "The user's underlying motivation, in their own terms. Sensitive — never leaves this system."},
            "shareable_what": {"type": "string", "description": "The instrumental behaviour: what doing this looks like concretely."},
            "status": {"type": "string", "description": "active | not_started | at_risk | completed"},
            "due": {"type": "string", "description": "YYYY-MM-DD, if there is a date."},
            "parent_goal": {"type": "string", "description": "Id of the goal this serves, e.g. a weekly goal under 'q1'."},
            "context": {"type": "string", "description": "Anything worth knowing about how this goal has been going."},
            "size": {"type": "string", "description": "S (one sitting, about an hour) | M (hours to days, one end date) | L (recurring time for weeks or more)."},
            "kind": {"type": "string", "description": "goal | obligation (something that must be done, e.g. filing taxes). Also for vet."},
            "verdict": {"type": "string", "description": "For vet: active | parked | declined."},
            "priority": {"type": "string", "description": "For vet: high | normal | low — how it ranks against what is already open, by what missing it would cost (an obligation like taxes is high even when it serves no goal)."},
            "displaces": {"type": "string", "description": "For vet: what it takes time from, if anything."},
            "revisit_on": {"type": "string", "description": "For parked (vet, or update with status parked): YYYY-MM-DD to look at it again — the goal comes back to you that day to ask once. For \"park it\", \"revisit it in June\"."},
            "starts_on": {"type": "string", "description": "YYYY-MM-DD: a goal that stays taken on but begins (or begins again) that day — nothing is planned or counted for it before then, and from that day it runs by itself. For \"on hold until mid-January\", \"start this after the holidays\"; \"today\" starts it now. For update, or vet with verdict active."},
            "hold_note": {"type": "string", "description": "One line on what happens meanwhile, while it is on hold or starting later (\"stretching only until then\"). Shown only while it is held."},
        },
        "required": ["action"],
    },
}

WRITE_GOALS_SCHEMA = {
    "name": "write_goals",
    "description": (
        "Replace one or more whole goal horizons at once. Use ONLY when authoring "
        "a complete set, as at the end of a goals interview — every goal omitted "
        "from a horizon you pass is deleted. To change a single goal, use "
        "update_goal instead.\n\n"
        "Pass a dict with one or more horizon keys "
        "(long, quarterly, weekly, daily). Each key replaces the existing value for that horizon. "
        "Each goal should include: title, private_why (sensitive — motivation), "
        "shareable_what (semi-sensitive — instrumental behavior), status, and optionally "
        "due (YYYY-MM-DD) and parent_goal (id of the parent goal)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "description": (
                    "Goals to write. Keys: quarterly, weekly, and/or daily. "
                    "Each is a list of goal objects."
                ),
            },
        },
        "required": ["content"],
    },
}


def goal_schemas() -> tuple[dict, dict]:
    """(read_goals, update_goal) as models should see them. `essential` is added only when the
    day planner's `ledger_fields` flag is on (review R1-1); off, the constants are returned as
    they have always been."""
    try:
        from tools.day_plan_config import flag
        exposed = flag("ledger_fields")
        talk = flag("goal_talk")
    except Exception:  # noqa: BLE001
        exposed = talk = False
    if not exposed and not talk:
        return READ_GOALS_SCHEMA, UPDATE_GOAL_SCHEMA
    import copy
    upd = copy.deepcopy(UPDATE_GOAL_SCHEMA)
    props = upd["input_schema"]["properties"]
    if exposed:
        props["essential"] = {
            "type": "boolean",
            "description": "True for a goal that must not slip — one the user has said matters "
                           "more than the rest. Its tasks are protected when the day is planned.",
        }
    if talk:
        # Part B (§ 18): the talk-through. Off, the schema is part A's exactly.
        props["action"]["description"] = "add | update | complete | remove | vet | talk"
        upd["description"] += (
            "\n\n'talk': the user said yes to talking a large goal (size L) through properly, "
            "now — from their next message the conversation is about that one goal.")
        props["weekly_minutes"] = {"type": "integer", "description": "Minutes a week the user will give it, in their words. For update or vet."}
        props["done_means"] = {"type": "string", "description": "What done looks like, in one line of theirs. For update or vet."}
        props["starting_point"] = {"type": "string", "description": "Where they are with it now, in a line. For update or vet."}
        props["effort_hours"] = {"type": "string", "description": "Hours it realistically takes from where they are to done, e.g. \"200-300\" — from what is known about goals like this, not a guess. For update or vet."}
    return READ_GOALS_SCHEMA, upd
