"""
tools/goal_talk.py — goal–task network phase 3, part B: a large goal talked through properly.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md § 4.2 (the L row), § 17 (part A's gate),
§ 18 (this build and Mike's rulings, 2026-11-24). Behind `goal_talk` (config/modules/day_plan.yaml),
OFF; off, nothing here opens a task, starts a talk or routes a message, and part A is unchanged.

WHAT THE USER SEES. A goal Synth sizes L gets one task under it — the talk-through — which
is the first task of its project (Mike: "The talk itself is the first task within the project").
It reads "Talk through: <goal>".
The day planner places it like any step; Synth offers it once ("this deserves a proper talk — now,
or whenever you say?"). A yes starts the talk there and then: from the next message the user is
talking to the Goals Interviewer about that one goal, focused, ~8–15 turns (Mike: "Focused to
start. If more is needed then a continuation can be offered, or a second talk scheduled with
user."), and it ends in a verdict — taken on, parked with a date, or declined — recorded with
`update_goal vet`, which writes the full pass rolling wave plans from (§ 17, Mike: "2 questions
isn't nearly enough for an L goal"). Stopping partway keeps the task open; the next talk picks up
from what was recorded. A quiet talk lapses after `talk.idle_hours`, so the user is never trapped
in it. A Done tap never closes the talk task (tools/obligations.py): only the verdict does.

REALISTIC, NOT ONLY USER-GENERATED (Mike: "the facts can't all be user generated. The goal itself
should be developed and research by Metatron so that the rendering of the goal is realistic";
and "the goal might already have a shape within Metatron (taxes, language learning) to start
from"). The talk starts from what Metatron already holds for this kind of goal — a playbook
(tools/project_plan.py `_playbook`), method only, Mike-reviewed — and only when none applies, one
guarded public lookup of what it realistically takes (tools/lookup_guard.py `ask_public`, the same
guard and daily cap as every lookup). Code then does the arithmetic: the effort the Interviewer
records against the weekly time and date the user gives (`realism`).

STATE. `data/personas/{p}/interview/goal_talk.json`, apart from the first interview's
`state.json` — so nothing that reads that file (the scheduler's hold gate, the app's setup chips)
sees a goal talk. One talk at a time per user:

    {"talk": {id, goal_id, task_id, status: active|paused|done, started_at, updated_at,
              opened, turns, shape: {source, text}}, "offered": {goal_id: day}, "past": [...]}

Costs. Run: one Interviewer session per L goal, a few model turns on the reasoning tier
(~$0.05–0.15 a talk), plus at most one grounded lookup (~$0.01–0.04, inside the 5-a-day cap);
rare. Ancillary: one small JSON file per user; one task row per L goal. Unseen: the user's
attention for the talk — bounded by one offer, a task they can skip, and focus on one goal.
What persists: the state file (owned here; a finished talk moves to `past`, capped at 20) and the
talk task (closed by the verdict, by the goal's own parking or declining, or by the user).
"""
from __future__ import annotations

import contextlib
import fcntl
import threading
import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

AGENT = "goals_interviewer"
SOURCE_PREFIX = "goal_talk:"
_PAST_MAX = 20
# One talk turn at a time per user (verify L1): the app's opening and a quick first message are
# serialised, and the later one is handed the earlier one's reply as history.
_TURN_LOCKS: dict[str, threading.Lock] = {}
_TURN_LOCKS_GUARD = threading.Lock()
_APP_TURN = "(The app started this turn.)"


def _turn_lock(persona: str) -> threading.Lock:
    with _TURN_LOCKS_GUARD:
        return _TURN_LOCKS.setdefault(persona, threading.Lock())
_SHAPE_MAX = 2400          # the fallback lookup: outside content, kept short
# A playbook reaches the talk whole (Mike, 2026-11-25: "lift the cap"). It was cut at
# _SHAPE_MAX, which halved even the taxes file and dropped every stage past the first few of the
# language one. The block is re-sent each turn: the ~12k-character language playbook is ~3,000
# tokens × ~15 turns ≈ $0.03 a talk at the reasoning tier, one talk per large goal. This ceiling is a guard against a runaway file, not a
# budget — no reviewed playbook comes near it.
_PLAYBOOK_MAX = 16000


def _O():
    import tools.obligations as O
    return O


def _D():
    import tools.day_plan as D
    return D


def on() -> bool:
    return _D()._flag("goal_talk")


# As shipped in day_plan.yaml `goal_network.talk`; the YAML is the authority.
_DEFAULTS = {"task_minutes": 30, "due_days": 14, "idle_hours": 6, "min_user_turns": 4}


def _cfg() -> dict:
    try:
        from tools import day_plan_config as C
        return {**_DEFAULTS, **(C.goal_network().get("talk") or {})}
    except Exception:  # noqa: BLE001
        return dict(_DEFAULTS)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp() -> str:
    return _now().isoformat(timespec="seconds")


# --- state ------------------------------------------------------------------------------------

def _path(persona: str) -> Path:
    from core.persona import persona_data_dir
    return persona_data_dir(persona) / "interview" / "goal_talk.json"


def _read(persona: str) -> dict:
    p = _path(persona)
    try:
        data = json.loads(p.read_text()) if p.exists() else {}
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


@contextlib.contextmanager
def _locked(persona: str):
    p = _path(persona)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p.with_name(p.name + ".lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield p
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _write(p: Path, state: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".goal_talk.", dir=str(p.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _idle(talk: dict) -> bool:
    try:
        last = datetime.fromisoformat(str(talk.get("updated_at") or talk.get("started_at")))
    except ValueError:
        return False
    hours = float(_cfg().get("idle_hours") or 6)
    return _now() - last > timedelta(hours=hours)


def current(persona: str) -> dict | None:
    """The talk in progress (active or paused), or None."""
    talk = _read(persona).get("talk")
    if not isinstance(talk, dict) or talk.get("status") not in ("active", "paused"):
        return None
    return talk


def _gone(persona: str, goal_id: str) -> str | None:
    """Why a talk about this goal can no longer run (Fable S3), or None: the goal was removed,
    closed, made smaller, or already talked through another way."""
    from core.persona import persona_scope
    from tools.goals import read_goals
    try:
        with persona_scope(persona):
            data = read_goals()
    except Exception:  # noqa: BLE001 — unreadable is unknown, never "removed" (verify N4)
        return None
    if not any(isinstance(v, list) and v for v in (data or {}).values()):
        return None
    g = _goal(goal_id, persona)
    if not g:
        return "goal_removed"
    status = str(g.get("status") or "active")
    if status in ("parked", "declined", "completed"):
        return f"goal_{status}"
    if str(g.get("size") or "").upper() != "L":
        return "not_large"
    return None


def active(persona: str) -> dict | None:
    """The talk the user's next message goes to, or None. Off → always None, so switching the
    flag off returns every message to the usual conversation at once. A talk left quiet past
    `idle_hours` is paused here, on read, and a talk whose goal was closed, removed or made
    smaller is ended — the user is never held in a conversation that has no subject."""
    if not on():
        return None
    talk = current(persona)
    if not talk or talk.get("status") != "active":
        return None
    if _idle(talk):
        pause(persona, reason="idle")
        return None
    why = _gone(persona, str(talk.get("goal_id")))
    if why:
        end(str(talk.get("goal_id")), why, persona)
        return None
    return talk


def needs_opening(persona: str) -> bool:
    talk = active(persona)
    return bool(talk and not talk.get("opened"))


def claim_opening(persona: str) -> dict | None:
    """Atomically take the opening (Fable L1): the app's opening turn and a quick first message
    from the user race; whichever claims first opens the talk, the other does not."""
    if not active(persona):
        return None
    with _locked(persona) as p:
        st = _read(persona)
        talk = st.get("talk")
        if not isinstance(talk, dict) or talk.get("status") != "active" or talk.get("opened"):
            return None
        talk["opened"] = True
        _write(p, st)
        return dict(talk)


def user_turns(persona: str, goal_id: str) -> int:
    talk = current(persona)
    if not talk or talk.get("goal_id") != str(goal_id):
        return 0
    return int(talk.get("user_turns") or 0)


# --- the goal ---------------------------------------------------------------------------------

def _goal(goal_id: str, persona: str | None = None) -> dict | None:
    """The goal, read with the persona bound (Fable S1: the server calls in from threads that
    bind none, and the persona resolver is strict there)."""
    from core.persona import persona_scope
    from tools.goals import _find_goal, read_goals
    if persona:
        with persona_scope(persona):
            data = read_goals()
    else:
        data = read_goals()
    hit = _find_goal(data, str(goal_id or "").strip())
    return hit[2] if hit else None


def _title(g: dict | None, goal_id: str = "") -> str:
    return str((g or {}).get("title") or goal_id or "this goal").strip()


def is_talk_task(t: dict) -> bool:
    return str(t.get("source_id") or "").startswith(SOURCE_PREFIX)


def talk_task(goal_id: str, persona: str | None = None) -> dict | None:
    """The open talk task of one goal, or None."""
    sid = f"{SOURCE_PREFIX}{goal_id}"
    return next((t for t in _O()._load(persona)
                 if t.get("source_id") == sid and t.get("status") == "open"), None)


def _wants_talk(g: dict | None) -> bool:
    """An L goal still to be talked through: taken on or being considered, no full pass yet."""
    if not g:
        return False
    vetted = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
    status = str(g.get("status") or "active")
    # A practice under a goal (`parent_goal`) is talked through with its goal, never alone
    # (11-25 #8: `d1` was sized L and parked as a goal of its own).
    return (str(g.get("size") or "").upper() == "L" and vetted.get("pass") != "full"
            and status in ("proposed", "active", "not_started", "at_risk")
            and not str(g.get("parent_goal") or "").strip())


def _open_task(goal_id: str, persona: str | None, by: str) -> tuple[str | None, bool]:
    """(task id or None, opened just now). Never raises."""
    from core.persona import resolve_persona
    if not on():
        return None, False
    try:
        persona = resolve_persona(persona)
        g = _goal(goal_id, persona)
        if not _wants_talk(g):
            return None, False
        have = talk_task(goal_id, persona)
        if have:
            return have["id"], False
        cfg = _cfg()
        today = _D()._today()
        step = {
            "key": "talk", "what": f"Talk through: {_title(g, goal_id)}", "kind": "deadline",
            "due": (today + timedelta(days=int(cfg.get("due_days") or 14))).isoformat(),
            "eligible_from": today.isoformat(), "flexible": True,
            "minutes": int(cfg.get("task_minutes") or 30), "minutes_source": "estimated",
            "part_of": str(goal_id), "goal_id": str(goal_id), "stakes": "missable",
            "required": False, "source_id": f"{SOURCE_PREFIX}{goal_id}",
            "note": "Done by talking it through — the user says yes to the offer, or asks to.",
        }
        res = _O().open_plan([step], persona=persona, created_by="goal_talk")
        if not res.get("ok"):
            logger.info("[goal_talk] task not opened for %s: %s", goal_id, res.get("error"))
            return None, False
        with _locked(persona) as p:
            st = _read(persona)
            st.setdefault("offered", {})[str(goal_id)] = today.isoformat()
            _write(p, st)
        _D()._log("GOAL_TALK_TASK", persona, goal=str(goal_id), by=by)
        return res["ids"]["talk"], True
    except Exception as exc:  # noqa: BLE001 — a missing task never costs the goal change
        logger.warning("[goal_talk] ensure_task failed: %s", exc)
        return None, False


def ensure_task(goal_id: str, persona: str | None = None, by: str = "sized") -> str | None:
    """Open the talk task for an L goal that has none — the project's first task (Mike). Returns
    its id, the existing one's, or None (off, not L, already talked through)."""
    return _open_task(goal_id, persona, by)[0]


def opened_task(goal_id: str, persona: str | None = None, by: str = "sized") -> bool:
    """True only when the talk task was opened by THIS call — so Synth is told to offer the
    talk once, when the task first appears, not on every later result (Fable L4)."""
    return _open_task(goal_id, persona, by)[1]


def sweep(persona: str | None = None) -> int:
    """Daily: an L goal still to be talked through that was never given its talk task gets one
    (`mike`'s Bulgarian goal predates this build). Once per goal — a talk task the user skipped is
    not reopened behind their back; sizing the goal again, or asking, does that. And a talk task
    whose goal stopped being one to talk through (made smaller, closed) is closed."""
    from core.persona import resolve_persona
    if not on():
        return 0
    persona = resolve_persona(persona)
    offered = _read(persona).get("offered") or {}
    index = _O()._goal_index()
    if not index:
        return 0            # no goals read is unknown, not "every goal removed" (verify N4)
    for t in _O()._load(persona):
        if is_talk_task(t) and t.get("status") == "open":
            gid = str(t.get("source_id"))[len(SOURCE_PREFIX):]
            if not _wants_talk(index.get(gid)):
                end(gid, "not_a_talk_now", persona)
    n = 0
    for gid, g in index.items():
        if gid in offered or not _wants_talk(g):
            continue
        if ensure_task(gid, persona, by="sweep"):
            n += 1
    return n


# --- starting, pausing, ending ------------------------------------------------------------------

def _user_turn() -> bool:
    try:
        from tools.turn_context import current as _turn
        turn = _turn()
    except Exception:  # noqa: BLE001
        turn = None
    return bool(turn and turn.get("user_turn"))


def start(goal_id: str, persona: str | None = None) -> str:
    """`update_goal action=talk`: the user said yes to talking this goal through now — on their
    own turn only (Fable S3: a scheduled turn must never start one)."""
    from core.persona import resolve_persona
    if not on():
        return "error: not available yet — carry on the conversation as usual."
    if not _user_turn():
        return ("error: a talk starts only on the user's own yes, in their own message. Offer it "
                "instead. Nothing was started.")
    persona = resolve_persona(persona)
    gid = str(goal_id or "").strip()
    g = _goal(gid, persona)
    if not g:
        return f"error: no goal with id '{gid}'. Nothing was started."
    if str(g.get("size") or "").upper() != "L":
        return ("error: only a goal that needs regular time for weeks (size L) is talked through "
                "this way — a smaller one is checked in the turn. Nothing was started.")
    if not _wants_talk(g):
        return ("error: that goal has been talked through already, or is closed. Nothing was "
                "started.")
    tid = ensure_task(gid, persona, by="talk") or ""
    with _locked(persona) as p:
        st = _read(persona)
        paused = st.setdefault("paused", {})
        cur = st.get("talk") if isinstance(st.get("talk"), dict) else None
        if cur and cur.get("status") in ("active", "paused") and cur.get("goal_id") != gid:
            # One talk at a time: the other is kept, paused, under its goal (Fable L2), and picks
            # up later where it stood — same id, same history.
            cur.update(status="paused", updated_at=_stamp())
            paused[str(cur["goal_id"])] = cur
            cur = None
        talk = cur if cur and cur.get("goal_id") == gid else paused.pop(gid, None)
        if talk:
            talk.update(status="active", updated_at=_stamp(), opened=False,
                        task_id=tid or talk.get("task_id"))
        else:
            talk = {"id": uuid.uuid4().hex[:10], "goal_id": gid, "task_id": tid,
                    "status": "active", "started_at": _stamp(), "updated_at": _stamp(),
                    "opened": False, "turns": 0, "user_turns": 0}
        st["talk"] = talk
        _write(p, st)
    _D()._log("GOAL_TALK_START", persona, goal=gid, talk=talk["id"])
    return ("Started. In one short sentence, say you'll talk it through together now — and ask "
            "nothing yourself: the conversation about it opens with the next message.")


def pause(persona: str, reason: str = "user") -> bool:
    with _locked(persona) as p:
        st = _read(persona)
        talk = st.get("talk")
        if not isinstance(talk, dict) or talk.get("status") != "active":
            return False
        talk.update(status="paused", updated_at=_stamp(), paused_for=reason)
        _write(p, st)
    _D()._log("GOAL_TALK_PAUSE", persona, goal=talk.get("goal_id"), reason=reason)
    return True


def _redate_task(persona: str, goal_id: str, day) -> bool:
    """The talk task comes back on the day the user picked (Fable S7) — `eligible_from` that day,
    `due` at least a week after it. Code-owned; never raises."""
    O = _O()
    sid = f"{SOURCE_PREFIX}{goal_id}"

    def apply(doc: dict) -> bool:
        for t in doc["tasks"]:
            if t.get("source_id") == sid and t.get("status") == "open":
                t["eligible_from"] = day.isoformat()
                due = O._d(t.get("due"))
                if not due or due < day + timedelta(days=7):
                    t["due"] = (day + timedelta(days=7)).isoformat()
                t.setdefault("history", []).append({"event": "talk_redated", "at": O._stamp(),
                                                    "to": day.isoformat()})
                return True
        return False

    try:
        return bool(O._with_store(persona, apply))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[goal_talk] re-date failed: %s", exc)
        return False


def pause_tool(persona: str, resume_on: str = "") -> str:
    """`pause_interview(resume_on?)` while a goal talk is active — the user wants to stop (or the
    Safety section applies). The task stays open; with a day, it comes back that day."""
    talk = current(persona)
    if not pause(persona):
        return "There is no talk in progress to pause."
    day = None
    if str(resume_on or "").strip():
        try:
            day = datetime.strptime(str(resume_on).strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            day = None
    if day and day > _D()._today() and talk and _redate_task(persona, str(talk["goal_id"]), day):
        return (f"Paused. What was recorded is kept, and the talk comes back on their list on "
                f"{day.isoformat()}. Say so in a sentence.")
    return ("Paused. What was recorded is kept and the talk stays on their list; they can pick it "
            "up whenever they like. Say so in a sentence.")


def _close_task(persona: str, goal_id: str, status: str, evidence: str) -> None:
    O = _O()
    sid = f"{SOURCE_PREFIX}{goal_id}"

    def apply(doc: dict) -> None:
        for t in doc["tasks"]:
            if t.get("source_id") == sid and t.get("status") == "open":
                t.update(status=status, closed_at=O._stamp(), evidence=evidence)
                doc.setdefault("_history", []).append(O._one_off_row(t, status))

    if talk_task(goal_id, persona):
        O._with_store(persona, apply)


def end(goal_id: str, reason: str, persona: str | None = None, task_status: str = "moot") -> bool:
    """A talk about this goal is over (its verdict, or the goal closed, removed or made smaller):
    the state moves to `past` and its task is closed. True when a talk was in progress."""
    from core.persona import resolve_persona
    try:
        persona = resolve_persona(persona)
        ended = None
        with _locked(persona) as p:
            st = _read(persona)
            talk = st.get("talk")
            gone = (st.get("paused") or {}).pop(str(goal_id), None)
            if (isinstance(talk, dict) and talk.get("goal_id") == str(goal_id)
                    and talk.get("status") in ("active", "paused")):
                ended = talk
                st["talk"] = None
            ended = ended or gone
            if ended:
                ended.update(status="done", ended_at=_stamp(), verdict=reason)
                st["past"] = ((st.get("past") or []) + [ended])[-_PAST_MAX:]
            _write(p, st)
        evidence = (f"talked through with the user — verdict {reason}" if task_status == "done"
                    else f"the talk was not needed: {reason.replace('_', ' ')}")
        _close_task(persona, str(goal_id), task_status, evidence)
        if ended:
            _D()._log("GOAL_TALK_DONE", persona, goal=str(goal_id), verdict=reason,
                      turns=int(ended.get("turns") or 0))
        return bool(ended)
    except Exception as exc:  # noqa: BLE001 — never blocks the goal change
        logger.warning("[goal_talk] end failed: %s", exc)
        return False


def on_vet(goal_id: str, verdict: str, persona: str | None = None) -> bool:
    """`vet_goal` by the Interviewer on the goal being talked through: the talk is over. Its task
    is closed done by code — the verdict is what doing it meant."""
    return end(goal_id, verdict, persona, task_status="done")


def last_shape(goal_id: str, persona: str | None = None) -> dict | None:
    """What the talk started from (playbook or research) — for the planner's payload."""
    from core.persona import resolve_persona
    st = _read(resolve_persona(persona))
    for talk in [st.get("talk")] + list(reversed(st.get("past") or [])):
        if isinstance(talk, dict) and talk.get("goal_id") == str(goal_id) and talk.get("shape"):
            return talk["shape"]
    return None


# --- what the talk starts from ------------------------------------------------------------------

# What may be looked up is a GENERIC subject code picks from a fixed list — never the user's own
# sentence (Fable S5: a goal title like "stop drinking before my daughter's wedding" passes the
# identifier guard and is still the user's life). No subject on the list → no lookup; the talk
# runs on what the user says and the playbook, if any.
_LANGS = ("bulgarian", "spanish", "french", "german", "italian", "portuguese", "greek", "russian",
          "japanese", "mandarin", "chinese", "arabic", "dutch", "polish", "turkish", "korean",
          "hindi", "swedish", "norwegian", "danish", "finnish", "czech", "romanian", "hungarian",
          "ukrainian", "hebrew", "welsh", "irish", "latin", "sign language")
_INSTRUMENTS = ("piano", "guitar", "violin", "cello", "drums", "ukulele", "flute", "saxophone",
                "trumpet")
# A subject counts only as the object of a learning verb, or in a fixed phrase (verify N1:
# "Polish my CV", "run my own business", "read a book a week", "paint the house" are not
# language, running, writing or painting goals).
_LEARN = r"(?:learn|learning|speak|speaking|study|studying|practi[sc]e|practi[sc]ing|improve|improving)"
_FILL = r"(?:\s+(?:to|to\s+speak|to\s+play|my|better|more|the|some|in|at))*"
_TOPICS = (
    (r"\b(?:run(?:ning)?\s+(?:a\s+|my\s+first\s+)?(?:marathon|half[\s-]marathon|5k|10k)|"
     r"marathon\s+training|train(?:ing)?\s+for\s+a\s+(?:marathon|half[\s-]marathon|5k|10k))\b",
     "training to run a longer distance, from 5k up to a marathon, as an adult"),
    (r"\b(?:learn(?:ing)?\s+to\s+swim|swimming\s+(?:technique|fitness|lessons)|"
     r"(?:improve|improving)\s+(?:my\s+)?swimming)\b",
     "improving swimming as an adult, from basic strokes to steady distance"),
    (r"\b(?:strength|flexibility|mobility)\s+(?:and\s+\w+\s+)?training\b|\bbuild(?:ing)?\s+strength\b",
     "building strength and flexibility as an adult beginner"),
    (r"\blearn(?:ing)?\s+(?:to\s+)?(?:code|coding|program|programming)\b",
     "learning to program as an adult beginner"),
    (r"\b(?:write|writing|finish|finishing)\s+(?:a\s+|my\s+)?(?:first\s+)?(?:novel|book)\b",
     "writing a first book-length manuscript"),
    (r"\blearn(?:ing)?\s+to\s+(?:draw|paint)\b|\b(?:drawing|painting)\s+(?:lessons|classes)\b",
     "learning to draw or paint as an adult beginner"),
)


def research_subject(g: dict) -> str | None:
    """The generic subject for this goal, or None. Code-chosen from the fixed lists above, and
    only when the goal's words use it as something to learn."""
    text = " ".join(" ".join(str(g.get(k) or "").split()) for k in
                    ("title", "shareable_what", "done_means")).lower()
    for lang in _LANGS:
        l = re.escape(lang).replace(r"\ ", r"\s+")
        if (re.search(rf"\b{_LEARN}{_FILL}\s+{l}\b", text)
                or re.search(rf"\b{l}\s+(?:lessons|classes|conversation|fluency|language)\b", text)):
            return f"learning {lang.title()} as an adult, from beginner to fluent conversation"
    for inst in _INSTRUMENTS:
        if re.search(rf"\b(?:{_LEARN[3:-1]}|play|playing){_FILL}\s+{inst}\b", text):
            return f"learning to play the {inst} as an adult beginner"
    for pattern, subject in _TOPICS:
        if re.search(pattern, text):
            return subject
    return None


def _research_question(subject: str) -> str:
    return (f"Realistically, what does {subject} take? Give the usual stages, a typical number of "
            "hours of practice to reach each, a sensible amount of time a week, and the most "
            "common reasons people stall. Short, plain answer.")


def _shape(g: dict, persona: str) -> dict:
    """The playbook when one applies (Mike: "the goal might already have a shape within
    Metatron"), else one guarded lookup of a generic subject; else nothing. Made once per talk."""
    try:
        from tools.project_plan import _playbook
        pb = _playbook(str(g.get("title") or ""), str(g.get("shareable_what") or ""))
    except Exception:  # noqa: BLE001
        pb = None
    if pb:
        return {"source": "playbook", "text": pb[:_PLAYBOOK_MAX]}
    subject = research_subject(g)
    if not subject:
        return {"source": "none", "text": ""}
    try:
        from core.persona import persona_scope
        from tools.lookup_guard import ask_public
        with persona_scope(persona):
            # Cut BEFORE it is wrapped, so the closing tag survives (Fable L5).
            ans = ask_public(_research_question(subject), persona, source="goal_talk",
                             max_chars=_SHAPE_MAX)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[goal_talk] research failed: %s", type(exc).__name__)
        ans = ""
    low = str(ans or "").lstrip().lower()
    if not ans or low.startswith(("refused", "not available", "the lookup")):
        _D()._log("GOAL_TALK_RESEARCH", persona, goal=str(g.get("id")), ok=False)
        return {"source": "none", "text": ""}
    _D()._log("GOAL_TALK_RESEARCH", persona, goal=str(g.get("id")), ok=True)
    return {"source": "research", "text": str(ans)}


# --- the arithmetic (code, not the model) ---------------------------------------------------------

def parse_effort(raw) -> list[int] | None:
    """Hours: "200-300", "200 to 300 hours", "1,500–2,000", "250", [200, 300], 250 → [low, high];
    "2 years, roughly 400 hours" → [400, 400] (the number that is hours). None if unreadable."""
    if raw in (None, ""):
        return None
    if isinstance(raw, (list, tuple)):
        nums = [n for n in raw if isinstance(n, (int, float))]
    elif isinstance(raw, (int, float)):
        nums = [raw]
    else:
        text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(raw).lower()).strip()
        unit = r"\s*(?:h|hrs?|hours?)\b(?!\s*(?:a|per|each|/)\s*(?:week|wk|day))"
        num = r"(\d+(?:\.\d+)?)"
        rng_h = re.search(rf"{num}\s*(?:-|–|—|to)\s*{num}{unit}", text)
        bare = re.fullmatch(rf"(?:about\s+|around\s+|~\s*)?{num}(?:\s*(?:-|–|—|to)\s*{num})?", text)
        hrs = re.findall(rf"{num}{unit}", text)
        # A range counts only when it is hours, or is all there is (verify N5: "3-4 months at
        # 5 hours a week" is neither — and 5 hours A WEEK is a pace, not the effort).
        if rng_h:
            nums = [float(rng_h.group(1)), float(rng_h.group(2))]
        elif bare:
            nums = [float(x) for x in bare.groups() if x]
        elif hrs:
            nums = [float(x) for x in hrs[:2]]
        else:
            return None
    nums = [int(round(n)) for n in nums if 0 < n < 100000]
    if not nums:
        return None
    return [min(nums), max(nums)]


def realism(weekly_minutes, effort, due: str | None = None, today=None) -> str:
    """Plain lines: how long the effort takes at the weekly time, what the date needs, and — the
    comparison the Interviewer acts on (Fable L8) — whether their time reaches their date."""
    eff = parse_effort(effort)
    try:
        wm = int(weekly_minutes or 0)
    except (TypeError, ValueError):
        wm = 0
    if not eff:
        return ""
    today = today or _D()._today()
    lo, hi = eff
    span = f"{lo}" if lo == hi else f"{lo}–{hi}"
    parts = []
    d_lo = d_hi = None
    if wm >= 10:
        wk_lo, wk_hi = lo * 60 / wm, hi * 60 / wm
        d_lo = today + timedelta(weeks=wk_lo)
        d_hi = today + timedelta(weeks=wk_hi)
        when = (d_lo.strftime("%b %Y") if d_lo.strftime("%b %Y") == d_hi.strftime("%b %Y")
                else f"{d_lo.strftime('%b %Y')} – {d_hi.strftime('%b %Y')}")
        parts.append(f"At {wm} minutes a week, about {span} hours takes "
                     f"{_dur(wk_lo, wk_hi)}: done around {when}.")
    try:
        dd = datetime.strptime(str(due or "")[:10], "%Y-%m-%d").date() if due else None
    except ValueError:
        dd = None
    if dd and dd > today:
        weeks = max(1.0, (dd - today).days / 7)
        need_lo, need_hi = round(lo * 60 / weeks), round(hi * 60 / weeks)
        need = f"{need_lo}" if need_lo == need_hi else f"{need_lo}–{need_hi}"
        parts.append(f"By {dd.isoformat()} ({round(weeks)} weeks) it needs about {need} minutes "
                     f"a week.")
        if d_lo and d_lo > dd:
            parts.append("Their time does not reach their date.")
        elif d_hi and d_hi > dd:
            parts.append("Their time may not reach their date (it does only at the low end).")
        elif d_hi:
            parts.append("Their time reaches their date.")
    return " ".join(parts)


def _dur(wk_lo: float, wk_hi: float) -> str:
    def one(w: float) -> str:
        if w < 9:
            return f"{max(1, round(w))} weeks"
        if w < 104:
            return f"{max(1, round(w / 4.35))} months"
        return f"{w / 52:.1f} years"
    a, b = one(wk_lo), one(wk_hi)
    return a if a == b else f"{a} to {b}"


# --- whose figure, and whether the arithmetic was said (walkthrough fixes, plan § 19) ----------
# 11-25: the Interviewer proposed "120 to 150 minutes", Mike never gave a figure, and 120 was
# recorded as his; the 300–450 hours were quoted but "at two hours a week that is 3–4 years" never
# was. Both are now evidence code keeps from the talk's own turns, never the model's say-so.

_NUM_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20,
              "thirty": 30, "forty": 40, "forty-five": 45, "fifty": 50, "sixty": 60,
              "ninety": 90, "couple": 2, "a couple of": 2}
_NUM = r"(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|" \
       r"thirty|forty-five|forty|fifty|sixty|ninety|couple(?: of)?)"
_DUR_RE = re.compile(
    r"\b" + _NUM + r"(?:\s*(?:-|–|to)\s*" + _NUM + r")?(\s+and\s+a\s+half)?\s*"
    r"(hours?|hrs?|h\b|minutes?|mins?)(?:\s+and\s+a\s+half)?", re.IGNORECASE)
_HALF_HOUR_RE = re.compile(r"\bhalf\s+an\s+hour\b", re.IGNORECASE)
_TIMES_RE = re.compile(r"\b" + _NUM + r"\s+(?:times|sessions|days|mornings|evenings|nights)\b(?:\s+a\s+week)?|"
                       r"\b(twice|thrice)\b", re.IGNORECASE)
_DAILY_RE = re.compile(r"\b(?:a|per|each|every)\s+day\b|\bdaily\b", re.IGNORECASE)
_YES_RE = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|sure|ok(?:ay)?|agreed|deal|fine|perfect|great|good|"
    r"sounds\s+(?:good|right|fine|great)|that\s+works|that'?s\s+(?:fine|good|right)|"
    r"let'?s\s+(?:do|go\s+with)\s+(?:that|it)|go\s+with\s+that|works\s+for\s+me)\b", re.IGNORECASE)
_RATE_SAID_RE = re.compile(
    r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|eighteen|a "
    r"couple of|a few|several)(?:\s*(?:-|–|to)\s*(?:\d+(?:\.\d+)?|two|three|four|five|six|"
    r"seven|eight|nine|ten|twelve|eighteen))?(?:\s+and\s+a\s+half)?\s+(?:years?|months?)\b",
    re.IGNORECASE)


def _n(tok: str | None) -> float | None:
    if not tok:
        return None
    t = tok.strip().lower()
    if t.startswith("couple"):
        return 2.0
    try:
        return float(t)
    except ValueError:
        return float(_NUM_WORDS[t]) if t in _NUM_WORDS else None


_WEEK_AFTER_RE = re.compile(r"^\s*(?:a|per|each|every)\s+week\b|^\s*weekly\b", re.IGNORECASE)
# A figure the message turns down: "not 120", "can't do 150", "150 is too much" — the negation
# governs it directly (within three words), and a cap ("no more than 90", "can't do more than 2
# hours", "up to") is still their figure (verify N6).
_NEG_NEAR_RE = re.compile(r"\b(?:not|can'?t|cannot|won'?t|never)(?:\s+\w+){0,2}\s*$", re.IGNORECASE)
_CAP_NEAR_RE = re.compile(r"\b(?:more than|up to|at most|max(?:imum)?|over)\s*$", re.IGNORECASE)
_NEG_AFTER_RE = re.compile(r"^\s*(?:\w+\s+){0,3}(?:is|are|would be|sounds|feels|'s)?\s*"
                           r"(?:too (?:much|many|long|high)|a lot)\b", re.IGNORECASE)
_HOURMIN_RE = re.compile(r"\b(\d{1,2})\s*h\s*(\d{2})\b", re.IGNORECASE)


def _figures(text: str) -> list[tuple[int, int, bool]]:
    """(low, high, said-per-week) for each duration a message names, in minutes a week.
    "2 hours a week" is a week's figure as said, never multiplied (Fable L2: "2 hours a week over 3
    days" is 120, not 360); "15 minutes a day" is ×7, or × the days when they say how many ("20
    minutes a day, five days a week" is 100); "30 minutes three times a week" × 3. A figure the
    message turns down ("150 is too much", "not 120") is not theirs (L3); one over 3,000 minutes is
    a total, not a week (L1: "the 300 to 450 hours")."""
    s = _HALF_HOUR_RE.sub("30 minutes", text or "")
    s = _HOURMIN_RE.sub(lambda m: f"{int(m.group(1)) * 60 + int(m.group(2))} minutes", s)
    s = re.sub(r"\bbetween\s+(\S+)\s+and\s+", r"\1 to ", s, flags=re.IGNORECASE)
    out: list[tuple[int, int, bool]] = []
    times = None
    m = _TIMES_RE.search(s)
    if m:
        times = 2.0 if (m.group(2) or "").lower() == "twice" else 3.0 if m.group(2) else _n(m.group(1))
    for d in _DUR_RE.finditer(s):
        lo, hi = _n(d.group(1)), _n(d.group(2))
        if lo is None:
            continue
        pre = s[max(0, d.start() - 30):d.start()]
        if (_NEG_NEAR_RE.search(pre) and not _CAP_NEAR_RE.search(pre)) or \
                _NEG_AFTER_RE.search(s[d.end():d.end() + 30]):
            continue
        hi = hi if hi is not None else lo
        half = 0.5 if (d.group(3) or re.search(r"and\s+a\s+half", d.group(0), re.I)) else 0.0
        mult = 60.0 if d.group(4).lower().startswith("h") else 1.0
        lo_m, hi_m = (lo + half) * mult, (hi + half) * mult
        after = s[d.end():d.end() + 40]
        weekly = bool(_WEEK_AFTER_RE.search(after))
        if not weekly:
            if _DAILY_RE.search(after[:20]):
                k = times if times and times > 1 else 7.0
                lo_m, hi_m = lo_m * k, hi_m * k
            elif times and times > 1:
                lo_m, hi_m = lo_m * times, hi_m * times
        if 5 <= lo_m <= 3000:
            out.append((int(round(lo_m)), int(round(min(hi_m, 3000))), weekly))
    return out


def weekly_figures(text: str) -> list[tuple[int, int]]:
    """The minutes a week a message names, as (low, high) ranges. A bare duration counts as stated
    (an answer to "how much a week?"). Over-inclusive by design: this decides only that a figure is
    theirs, never what it is."""
    return [(lo, hi) for lo, hi, _w in _figures(text)]


_RATE_MARK_RE = re.compile(r"\b(?:a|per|each|every)\s+week\b|\bweekly\b|\bat (?:this|that|your|the) "
                           r"(?:rate|pace)\b|\bat that\b", re.IGNORECASE)


_ASKS_PACE_RE = re.compile(
    r"^\W*(?:how|what|which|could|would|can|will|do|does|did|is|are|should|shall)\b"
    r"|\bhow\s+(?:many|much|long)\b", re.IGNORECASE)


def _says_rate(reply: str) -> bool:
    """The Interviewer put what their time means in months or years — one sentence tying a pace
    ("a week", "at this rate") to a duration (Fable L4: "you've been at it two years" is not it,
    "at this pace about three and a half years" is)."""
    sents = [x for x in re.split(r"(?<=[.!?])\s+|\n+", reply or "") if x.strip()]
    for i, sent in enumerate(sents):
        if _ASKS_PACE_RE.search(sent) or not _RATE_SAID_RE.search(sent):
            # Asking about the pace is not saying the rate (verify N7) — but "at two hours a week
            # that is about three years — does that sit right?" is the rate said, with the question
            # the instructions ask for.
            continue
        if _RATE_MARK_RE.search(sent) or (i and _RATE_MARK_RE.search(sents[i - 1])):
            return True         # the pace in this sentence, or the one just before it
    return False


def _talk_for(persona: str, goal_id: str) -> dict | None:
    talk = current(persona)
    return talk if talk and talk.get("goal_id") == str(goal_id) else None


def minutes_theirs(persona: str, goal_id: str, wm) -> bool:
    """Is this weekly time the user's own, in this talk — a figure they said (within 15%, or
    inside a range they gave) or a plain yes to the one figure the Interviewer named?"""
    talk = _talk_for(persona, goal_id)
    if not talk:
        return True                   # not in a talk: Synth's short pass is not gated here
    try:
        wm = float(wm)
    except (TypeError, ValueError):
        return False
    for lo, hi in talk.get("their_minutes") or []:
        if lo * 0.85 <= wm <= hi * 1.15:
            return True
    return False


def realism_said(persona: str, goal_id: str) -> bool:
    talk = _talk_for(persona, goal_id)
    return True if not talk else bool(talk.get("realism_said"))


_HEDGE_RE = re.compile(r"\b(?:but|though|although|not|unsure|less|more|maybe|question|"
                      r"whatever|depends|first|instead)\b|n[’']t\b", re.IGNORECASE)


def _plain_yes(text: str) -> bool:
    """A short, unhedged yes: "yes", "that works", "sounds good" — not "ok but…", "good question,
    I'm not sure", "fine, whatever, though less" (Fable L3)."""
    t = (text or "").strip()
    return (bool(_YES_RE.match(t)) and "?" not in t and len(t.split()) <= 12
            and not _HEDGE_RE.search(t))


def _note_user_turn(cur: dict, user_input: str) -> None:
    """Before the Interviewer answers: what this message makes theirs."""
    mine = [[lo, hi] for lo, hi, _w in _figures(user_input)]
    bare = re.fullmatch(r"\D{0,15}?(\d{2,4})\D{0,15}", user_input or "")
    if not mine and bare and re.search(r"\bminutes?\b", cur.get("last_reply") or "", re.I):
        n = int(bare.group(1))           # "90" — an answer to "how many minutes a week?"
        if 10 <= n <= 1500:
            mine = [[n, n]]
    if not mine and _plain_yes(user_input):
        # The figure the yes answers is the one in the question (verify N6: "You said 90 felt
        # tight. Shall we say 120 a week?" — the yes is to 120).
        last = cur.get("last_reply") or ""
        asked = " ".join(x for x in re.split(r"(?<=[.!?])\s+|\n+", last) if x.strip().endswith("?"))
        offered = _figures(asked) or _figures(last)
        weekly = [f for f in offered if f[2]] or offered
        distinct = {(lo, hi) for lo, hi, _w in weekly}
        if len(distinct) == 1:
            lo, hi = next(iter(distinct))
            if lo == hi:                 # ONE figure named, then a plain yes to it
                mine = [[lo, hi]]
    if mine:
        cur["their_minutes"] = ((cur.get("their_minutes") or []) + mine)[-12:]


def _note_reply(cur: dict, reply: str) -> None:
    cur["last_reply"] = (reply or "")[:3000]
    if _says_rate(reply):
        cur["realism_said"] = True


def open_fields(g: dict) -> list[str]:
    """What is still to settle on an L goal, in words — the talk block's list, for a parked
    verdict and for a "we've settled it all" claim (goal_claims)."""
    vetted = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
    have = {k: g.get(k) or vetted.get(k) for k, _ in _FIELDS}
    return [label for k, label in _FIELDS
            if have.get(k) in (None, "", []) and k not in ("due", "effort_hours")]


# --- one turn ----------------------------------------------------------------------------------

_FIELDS =(("done_means", "what done looks like"), ("starting_point", "where they are now"),
           ("weekly_minutes", "minutes a week"), ("due", "by when"),
           ("displaces", "what it takes that time from"), ("priority", "where it ranks"),
           ("effort_hours", "the effort it realistically takes (hours)"))


def _practices(persona: str, goal_id: str) -> list[str]:
    try:
        from core.persona import persona_scope
        from tools.goals import _children, read_goals
        with persona_scope(persona):
            data = read_goals()
        return [f"{c.get('id')} \"{_title(c)}\" ({c.get('status') or 'active'})"
                for c in _children(data, goal_id)]
    except Exception:  # noqa: BLE001
        return []


def _their_week(persona: str) -> list[str]:
    lines = []
    try:
        from tools.baselines import _aspirational_path
        p = _aspirational_path(persona)
        ab = json.loads(p.read_text()) if p.exists() else {}
        for k, label in (("good_week", "a good week, in their words"),
                         ("hard_week", "a hard week")):
            if ab.get(k):
                lines.append(f"- {label}: {' '.join(str(ab[k]).split())[:300]}")
    except Exception:  # noqa: BLE001
        pass
    try:
        from tools.day_shape import read_shape
        shape = read_shape(persona) or {}
        for k in ("windows", "routines"):
            if shape.get(k):
                lines.append(f"- {k} on record: "
                             + json.dumps(shape[k], ensure_ascii=False, default=str)[:500])
    except Exception:  # noqa: BLE001
        pass
    return lines


def talk_block(persona: str, talk: dict) -> str:
    """The code-built account each Interviewer turn gets: the one goal, what is recorded, what it
    realistically takes, the arithmetic, the user's week, what is still to settle."""
    g = _goal(talk.get("goal_id"), persona) or {}
    vetted = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
    have = {k: g.get(k) or vetted.get(k) for k, _ in _FIELDS}
    rec = [f"{label}: {have[k]}" for k, label in _FIELDS if have.get(k) not in (None, "", [])]
    missing = [label for k, label in _FIELDS
               if have.get(k) in (None, "", []) and k not in ("due", "effort_hours")]
    status = str(g.get("status") or "active")
    lines = [
        "GOAL TALK — one goal, talked through with the user (read from what is saved):",
        f"- The goal: {talk.get('goal_id')} \"{_title(g)}\" — "
        + ("being considered" if status == "proposed" else "taken on")
        + (f"; their words: {' '.join(str(g['shareable_what']).split())[:200]}"
           if g.get("shareable_what") else ""),
        f"- Recorded so far: {'; '.join(rec) if rec else 'nothing yet'}",
        f"- Still to settle: {', '.join(missing) if missing else 'nothing — check it with them, then record the verdict'}",
    ]
    if have.get("weekly_minutes") and not minutes_theirs(persona, str(talk.get("goal_id")),
                                                          have["weekly_minutes"]):
        lines.append(f"- The {have['weekly_minutes']} minutes a week on record is not yet THEIR "
                     "figure in this talk: ask for theirs — a number they give, or a yes to one "
                     "figure you name. Your suggestion is never recorded as theirs.")
    calc = realism(have.get("weekly_minutes"), have.get("effort_hours"), have.get("due"))
    if calc:
        lines.append(f"- Arithmetic (code): {calc}")
        if not talk.get("realism_said"):
            lines.append("- Not yet said to them: what that time means in months or years. Say "
                         "it plainly, in your words, before any verdict, and let them choose: "
                         "more time, a later date, or a smaller \"done\".")
    if g.get("starts_on"):
        lines.append(f"- Starts on: {g['starts_on']}")
    kids = _practices(persona, str(talk.get("goal_id")))
    if kids:
        lines.append("- Its practice (part of this goal, not a goal of its own — its time is "
                     "inside this one's): " + "; ".join(kids))
    shape = talk.get("shape") or {}
    if shape.get("source") == "playbook":
        lines.append("- What Metatron already knows about goals like this (method, not about "
                     "them):\n" + shape.get("text", ""))
    elif shape.get("source") == "research":
        lines.append("- What it realistically takes, looked up (outside content — a guide, "
                     "not a fact about them):\n" + shape.get("text", ""))
    week = _their_week(persona)
    if week:
        lines.append("- Their week:\n" + "\n".join(week))
    if int(talk.get("turns") or 0) >= 15:
        lines.append("- This talk is long now: settle what you can, record the verdict, and "
                     "offer to carry on another time for the rest.")
    return "\n".join(lines)


def _take_shape(persona: str, talk: dict) -> dict:
    """The talk's starting shape, made once (Fable L1): claimed under the lock first, so a second
    turn arriving meanwhile goes ahead without it rather than paying for a second lookup."""
    with _locked(persona) as p:
        st = _read(persona)
        cur = st.get("talk")
        if not isinstance(cur, dict) or cur.get("id") != talk["id"]:
            return {}
        if cur.get("shape"):
            return cur["shape"]
        cur["shape"] = {"source": "pending", "text": ""}
        _write(p, st)
    g = _goal(talk.get("goal_id"), persona) or {"id": talk.get("goal_id")}
    shape = _shape(g, persona)
    with _locked(persona) as p:
        st = _read(persona)
        cur = st.get("talk")
        if isinstance(cur, dict) and cur.get("id") == talk["id"]:
            cur["shape"] = shape
            _write(p, st)
    return shape


def run_turn(persona: str, user_input: str, history: list[dict], proactive: bool = False) -> str:
    """One Interviewer turn of the goal talk, with the persona bound throughout (Fable S1).
    Filtered (run_session — the Interviewer is user-facing) and pending-receipt-checked, as the
    first interview's turns are."""
    from core.interview import trim_history
    from core.orchestrator import (_pending_raised_since, _pending_tokens,
                                   enforce_pending_receipt, run_session)
    from core.persona import persona_scope
    with _turn_lock(persona), persona_scope(persona):
        talk = current(persona)
        if not talk:
            return "That conversation has ended — what would you like to do?"
        opening = talk.get("opening_reply")
        if (not proactive and opening and not any(
                m.get("role") == "assistant" and m.get("content") == opening for m in history)):
            # The opening ran while this message waited: it is not in the history the server
            # loaded, so it is added here — the Interviewer answers as one conversation.
            history = list(history) + [{"role": "user", "content": _APP_TURN},
                                       {"role": "assistant", "content": opening}]
        if not proactive:
            # The user's own words open it too: the app's opening, if still to come, stands down.
            with _locked(persona) as p:
                st = _read(persona)
                if isinstance(st.get("talk"), dict) and st["talk"].get("id") == talk["id"]:
                    st["talk"]["opened"] = True
                    _note_user_turn(st["talk"], user_input)     # their figure, before the reply
                    _write(p, st)
        talk["shape"] = _take_shape(persona, talk)
        before = _pending_tokens(persona)
        from tools.goal_claims import amend, snapshot
        goals_before = snapshot(persona)
        message = f"{talk_block(persona, talk)}\n\n---\n\n{user_input}"
        reply = run_session(AGENT, message, persona=persona, history=list(trim_history(history)))
        reply = enforce_pending_receipt(reply, _pending_raised_since(before, persona))
        # The Interviewer's claims about the goal are held to what changed, as Synth's are (§ 19).
        reply = amend(reply, goals_before, persona, agent=AGENT)
        with _locked(persona) as p:
            st = _read(persona)
            cur = st.get("talk")
            if isinstance(cur, dict) and cur.get("id") == talk["id"]:
                cur["turns"] = int(cur.get("turns") or 0) + 1
                _note_reply(cur, reply)
                if not proactive:
                    cur["user_turns"] = int(cur.get("user_turns") or 0) + 1
                    cur.pop("opening_reply", None)
                else:
                    cur["opening_reply"] = reply
                cur["updated_at"] = _stamp()
                _write(p, st)
        return reply


def opening_prompt(persona: str) -> str:
    talk = current(persona) or {}
    g = _goal(talk.get("goal_id"), persona) or {}
    return (f"(The user has just said yes to talking their goal \"{_title(g, talk.get('goal_id'))}\" "
            "through properly, now. Open that conversation.)")


def channel(talk: dict) -> str:
    """The exchanges-table channel one talk's turns are stored under (core/server.py)."""
    return f"{SOURCE_PREFIX}{talk.get('id')}"
