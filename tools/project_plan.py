"""
tools/project_plan.py — the project planner: a goal or obligation taken on in chat is broken into
small dated steps, out of sight, and the user is fed one step at a time.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md — § 4.3, and § 10, which governs:
  R3  Synth sizes it S/M/L in the turn and vets it there; only an M is planned here (S is one task,
      L waits for phase 3's re-interview). A planner estimate one size LARGER sends it back for
      vetting — nothing is written.
  R4  every step is `flexible` with a required `due` (its latest date) and `eligible_from` (its
      earliest), so the day planner places it on a day with room.
  R8  `plan_project` only QUEUES. The planner runs as a worker off the scheduler's tick with the
      reshuffle's four controls: single flight, a per-persona daily cap, a minimum gap, and one
      locked write (`open_plan`, all-or-nothing).

Costs (named beside the cap, as plan § 8 requires): one reasoning-tier call per planned item,
plus at most one retry. Measured on the playbook-sized payload, ~3k tokens in and ~1.5–4k out —
about $0.02 a call at the current reasoning-tier price, ~$0.04 after its introductory price ends.
`project_plans_per_day` (default 6) caps a persona at ~$0.12/day (~$0.24 after), and the queue
holds at most one request per end state. Unseen: steps the user never asked for — bounded
because only a goal taken on (vetted) is ever planned, and a refused plan writes nothing.

Phase 3, part A (plan § 17) — ROLLING WAVE, behind `rolling_wave`. An L goal is planned only
after the Goals Interviewer's FULL pass (`vetted.pass == "full"`; Mike 2026-11-24: "2 questions
isn't nearly enough for an L goal"). The planner returns the next milestone as steps and every
later one as an outline — kept on this request (`milestones`), never as a ledger row, so no
reader of the task list can place, show, judge, park or dedupe against one (the R7 leak class).
When the last step of the current milestone closes, `advance_waves` (every tick) queues the next
one's expansion through the same queue, worker and daily cap (§ 10 R8); a milestone that closed
with no step done is `stalled` instead — more steps for a user ignoring these is the wrong
answer, and the re-vet (tools/goal_network.py) asks about it. Expansions are said to no one: the
next step simply appears. Run cost: one planner call per milestone, a few a month per L goal.
"""
from __future__ import annotations

import json
import logging
import re
import time as _time
from datetime import date, datetime, timedelta
from pathlib import Path

from core.persona import resolve_persona, persona_scope

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_PLAYBOOKS = _ROOT / "config" / "playbooks"

# Tests inject a callable(payload: dict) -> str here; production calls the project_planner agent.
_MODEL_CALL = None

_SIZES = ("S", "M", "L")
_RANK = {s: i for i, s in enumerate(_SIZES)}
_MAX_STEPS = 12
_ADOPT_MAX = 8
_SAID_WINDOW = timedelta(minutes=15)
_CALL_TRIES = 3
_CALL_BACKOFF = timedelta(hours=1)
# A notice offered this many times is let go even if no reply was matched to it — saying "it's
# planned" on every turn for three days is worse than once unrecorded (Fable #7).
_MAX_OFFERS = 3
_NOTICE_DAYS = 3

_SIGNALS = {
    "planned": re.compile(r"\b(plan|planned|steps?|sorted|mapped|broken|break|first|lined|"
                          r"set up|organi[sz]ed|on your list)\b", re.I),
    "needs_plan": re.compile(r"\b(work (it|this|that) out|figure|together|what'?s involved|"
                             r"plan|walk me through|talk (it|this) through)\b", re.I),
    "resize": re.compile(r"\b(bigger|more than|larger|longer|more work|check|again|rethink)\b",
                         re.I),
}


def _D():
    import tools.day_plan as D
    return D


def _O():
    import tools.obligations as O
    return O


def _flag() -> bool:
    return _D()._flag("project_planner")


def _wave_flag() -> bool:
    return _flag() and _D()._flag("rolling_wave")


def _gn() -> dict:
    try:
        from tools import day_plan_config as C
        return C.goal_network()
    except Exception:  # noqa: BLE001
        return {}


def _full_pass(end: dict | None) -> bool:
    """Has the Goals Interviewer talked this L goal through in full (plan § 4.2's L row)? Only
    `vet_goal` writes `pass`, and writes "full" only when the calling agent is the Interviewer."""
    return bool(end and end.get("pass") == "full")


def _limit(name: str, default):
    try:
        v = _D()._limit(name)
    except Exception:  # noqa: BLE001
        v = None
    return default if v in (None, "") else v


def _path(persona: str | None = None) -> Path:
    return _D()._dir(persona) / "projects.json"


def _load(persona: str | None = None) -> dict:
    st = _D()._read_json(_path(persona), {})
    st = st if isinstance(st, dict) else {}
    st.setdefault("requests", {})
    st.setdefault("counters", {})
    return st


def _save(st: dict, persona: str | None = None) -> None:
    _D()._write_json(_path(persona), st)


def _log(event: str, persona: str | None = None, **fields) -> None:
    _D()._log(event, persona, **fields)


# --- the end state -----------------------------------------------------------------------------

def _end(part_of: str, persona: str | None = None) -> dict | None:
    """A goal (by id) or an open one-off task (an obligation's end state) — what steps serve."""
    O = _O()
    pid = str(part_of or "").strip()
    if not pid:
        return None
    if pid.startswith("ob_"):
        t = next((O._norm(x) for x in O._load(persona) if x.get("id") == pid), None)
        if not t:
            return None
        return {"kind": "task", "id": pid, "title": t["what"], "deadline": t.get("due"),
                "status": t.get("status"), "one_off": t.get("kind") in O._ONE_OFF, "row": t}
    g = O._goal_index().get(pid)
    if not g:
        return None
    vetted = g.get("vetted") if isinstance(g.get("vetted"), dict) else {}
    try:
        wm = int(g.get("weekly_minutes") or vetted.get("weekly_minutes") or 0) or None
    except (TypeError, ValueError):
        wm = None
    return {"kind": "goal", "id": pid, "title": str(g.get("title") or pid),
            "deadline": str(g.get("due") or "")[:10] or None,
            "status": str(g.get("status") or "active"), "size": str(g.get("size") or "").upper(),
            "what": str(g.get("shareable_what") or "")[:300], "vetted": bool(g.get("vetted")),
            "pass": vetted.get("pass"), "weekly_minutes": wm,
            "goal_kind": str(g.get("kind") or "goal"),
            "starts_on": str(g.get("starts_on") or "")[:10] or None,
            # What the goal talk recorded (part B, § 18) — present only once one has.
            **{k: g[k] for k in ("done_means", "starting_point", "effort_hours") if g.get(k)}}


def _open_steps(end_id: str, persona: str | None = None) -> list[dict]:
    # A goal's talk-through task (§ 18) is not a plan step: it never makes a goal "already
    # planned", never takes its weekly time away, and is never adopted (Fable S4).
    return [t for t in _O()._load(persona) if t.get("part_of") == end_id and t.get("status") == "open"
            and not str(t.get("source_id") or "").startswith("goal_talk:")]


def _end_usable(end: dict | None) -> str | None:
    """None if this end state may be planned; else why not (the model sees it)."""
    if end is None:
        return "error: no goal or task with that id."
    if end["kind"] == "goal" and end["status"] not in ("active", "not_started", "at_risk"):
        return (f"error: {end['title']} is {end['status']} — only a goal that has been taken on "
                f"is planned. Check it with the user first (update_goal action=vet). Nothing "
                f"was queued.")
    if end["kind"] == "goal" and end.get("starts_on") and end["starts_on"] > _D()._today().isoformat():
        # Taken on, starting later (walkthrough fixes § 19, ruling 2): planned on the first tick
        # on or after its day — by the sweep, so nothing is planned, and no wave advanced, early.
        return (f"error: {end['title']} starts on {end['starts_on']} — it is planned from that day "
                f"by itself. Nothing was queued.")
    if end["kind"] == "task" and (end["status"] != "open" or not end["one_off"]):
        return "error: only an open one-off task can be planned out. Nothing was queued."
    return None


def _queue(end: dict, size: str, persona: str, weekly_minutes=None, note: str = "",
           by: str = "synthesizer") -> str:
    D = _D()
    now = D._now()
    with D._locked(persona):
        st = _load(persona)
        prev = st["requests"].get(end["id"]) or {}
        if prev.get("status") in ("queued", "inflight"):
            return f"{end['title']} is already being planned — nothing more to do."
        # Queued again at the same size after the planner found it bigger (R3): the user has
        # confirmed the size, so the planner's estimate no longer sends it back (Fable #3 — else
        # it loops at one call a time).
        confirmed = prev.get("status") == "resize" and size == prev.get("size")
        st["requests"][end["id"]] = {
            "id": end["id"], "kind": end["kind"], "title": end["title"][:160],
            "deadline": end["deadline"], "size": size, "status": "queued",
            "queued_at": now.isoformat(timespec="seconds"), "by": by,
            **({"weekly_minutes": int(weekly_minutes)} if weekly_minutes else {}),
            **({"note": str(note).strip()[:300]} if str(note or "").strip() else {}),
            **({"size_confirmed": True} if confirmed else {}),
        }
        _save(st, persona)
    _log("project_queued", persona, end=end["id"], size=size, by=by)
    # Live 11-21: Synth echoed this result's wording to the user ("that is vetted", "planned out of
    # sight") — so the result says what to tell them, in their words, and names the words to avoid.
    return (f"Queued: {end['title']} will be broken into small steps, and the first one will "
            f"appear on their list on a day with room. Tell them in a few everyday words that "
            f"it's under way — never 'vetted', 'queued' or 'out of sight' — and ask nothing about "
            f"its details or steps now; you will be told once it is planned.")


def plan_project(part_of: str, size: str = "", weekly_minutes: int | None = None,
                 note: str = "") -> str:
    """Synth's tool (R8): queue a goal or obligation it has sized M and checked with the user in
    the turn. Never calls a model — the planner runs in the scheduler's tick."""
    if not _flag():
        return "error: planning things out is not available yet. Nothing was queued."
    persona = resolve_persona(None)
    end = _end(part_of, persona)
    why = _end_usable(end)
    if why:
        return why
    size = (str(size or "").strip().upper() or end.get("size") or "")
    if end["kind"] == "goal" and end.get("size") and size != end["size"]:
        size = end["size"]                          # the vetted size is the one that counts
    if size == "S":
        return ("Small enough to be one task — open it with open_task instead. Nothing was "
                "queued.")
    if size == "L":
        if not _wave_flag():
            return ("A large goal is talked through properly before it is planned — not yet. It "
                    "stays as being considered. Nothing was queued.")
        return _plan_large(end, persona, weekly_minutes, note)
    if size != "M":
        return "error: say how big it is — size M (hours to days, one end date). Nothing was queued."
    if end["kind"] == "goal" and not end.get("vetted"):
        return ("error: check it with the user first and record the verdict (update_goal "
                "action=vet) — only a vetted goal is planned. Nothing was queued.")
    dl = _O()._d(end.get("deadline"))
    if not dl or dl <= _D()._today():
        return ("error: it needs a date in the future to be planned back from — set its due date "
                "first. Nothing was queued.")
    if _open_steps(end["id"], persona):
        return f"{end['title']} is already planned — read_plan shows the steps if they ask."
    try:
        wm = int(weekly_minutes) if weekly_minutes not in (None, "") else None
    except (TypeError, ValueError):
        wm = None
    return _queue(end, size, persona, weekly_minutes=wm, note=note)


def _plan_large(end: dict, persona: str, weekly_minutes=None, note: str = "") -> str:
    """An L goal, under `rolling_wave`: queued only once the Interviewer's full pass is on record,
    with the time a week it gets, and a date ahead if it has one (else `l_horizon_days`)."""
    if end["kind"] != "goal":
        return ("error: an obligation has one end date — plan it as size M. Nothing was queued.")
    if not _full_pass(end):
        # Mike, 2026-11-24: the two-question short pass is not enough to put a large goal's steps
        # on someone's days — the Goals Interviewer's full talk-through comes first.
        return ("A goal this size is talked through properly with the user before anything is "
                "planned — that conversation comes first. It keeps its weekly time meanwhile. "
                "Nothing was queued.")
    dl = _O()._d(end.get("deadline"))
    if dl and dl <= _D()._today():
        return ("error: its date has passed — set a new one first, or clear it. Nothing was "
                "queued.")
    if _open_steps(end["id"], persona):
        return f"{end['title']} is already planned — read_plan shows the steps if they ask."
    try:
        wm = int(weekly_minutes) if weekly_minutes not in (None, "") else end.get("weekly_minutes")
    except (TypeError, ValueError):
        wm = end.get("weekly_minutes")
    if not wm or int(wm) < 10:
        return ("error: a large goal is planned against the time a week the user gives it — pass "
                "weekly_minutes (what they said). Nothing was queued.")
    prev = _load(persona)["requests"].get(end["id"]) or {}
    if any(m.get("status") != "done" for m in prev.get("milestones") or []):
        # A wave plan already exists (Fable S5a): plan its next milestone, keeping the map, the
        # waves done and the finish record — never a fresh first wave that forgets them.
        return _requeue_wave(end, persona, int(wm), note)
    return _queue(end, "L", persona, weekly_minutes=int(wm), note=note)


def _requeue_wave(end: dict, persona: str, weekly_minutes: int, note: str = "",
                  by: str = "synthesizer") -> str:
    """Queue the expansion of the milestone a wave plan is stuck on: a stalled one, else the
    current one, else the first still pending."""
    D = _D()
    with D._locked(persona):
        st = _load(persona)
        r = st["requests"].get(end["id"]) or {}
        if r.get("status") in ("queued", "inflight"):
            return f"{end['title']} is already being planned — nothing more to do."
        ms = r.get("milestones") or []
        # A current milestone whose steps are closed with one done is finished, even if the tick
        # that would say so has not run yet (verify pass N3) — never planned a second time.
        rows = {t["id"]: t for t in _O()._load(persona)}
        ids = r.get("ids") or []
        cur = next((x for x in ms if x.get("status") == "current"), None)
        if (cur and ids and not any((rows.get(i) or {}).get("status") == "open" for i in ids)
                and any((rows.get(i) or {}).get("status") == "done" for i in ids)):
            cur.update(status="done", done_at=D._now().isoformat(timespec="seconds"))
        m = (next((x for x in ms if x.get("status") == "stalled"), None)
             or next((x for x in ms if x.get("status") == "current"), None)
             or next((x for x in ms if x.get("status") == "pending"), None))
        if not m:
            return f"{end['title']} has no stage left to plan."
        m["status"] = "pending"
        r.update(status="queued", expand=m["key"], weekly_minutes=weekly_minutes, by=by,
                 queued_at=D._now().isoformat(timespec="seconds"))
        if str(note or "").strip():
            r["note"] = str(note).strip()[:300]
        for k in ("call_failures", "not_before", "expand_failures", "wave_failed", "error"):
            r.pop(k, None)
        _save(st, persona)
    _log("project_wave_queued", persona, end=end["id"], milestone=m["key"], by=by)
    return (f"Queued: the next part of {end['title']} will be broken into small steps, and the "
            f"first will appear on their list on a day with room. Tell them in a few everyday "
            f"words that it's under way; ask nothing about its steps now.")


# --- the worker (R8) ---------------------------------------------------------------------------

def start_planning(persona: str | None = None) -> bool:
    """Start one queued plan on a worker — single flight per persona (stricter than per end
    state), the daily cap and the minimum gap checked under the plan lock, which is held only to
    read and mark; the model call runs with no lock (the reshuffle's V1-N3)."""
    persona = resolve_persona(persona)
    if not _flag():
        return False
    D = _D()
    with persona_scope(persona):
        now, day = D._now(), D._today().isoformat()
        stale = int(_limit("project_plan_stale_seconds", 600))
        with D._locked(persona):
            st = _load(persona)
            reqs = st["requests"]
            for r in reqs.values():
                started = D._dt(r.get("started_at"))
                if r.get("status") == "inflight":
                    if started and (now - started).total_seconds() < stale:
                        return False                       # single flight
                    r["status"] = "queued"                 # a dead worker: try again
            queued = sorted((r for r in reqs.values() if r.get("status") == "queued"
                             and not (D._dt(r.get("not_before")) and D._dt(r["not_before"]) > now)),
                            key=lambda r: r.get("queued_at") or "")
            if not queued:
                return False
            count = int(st["counters"].get(day, 0))
            if count >= int(_limit("project_plans_per_day", 6)):
                _save(st, persona)
                _log("project_capped", persona, queued=len(queued))
                return False
            last = D._dt(st.get("last_model_at"))
            if last and now - last < timedelta(minutes=int(_limit("project_plan_gap_minutes", 10))):
                _save(st, persona)
                return False
            r = queued[0]
            gen = int(st.get("gen") or 0) + 1
            r.update(status="inflight", gen=gen, started_at=now.isoformat(timespec="seconds"))
            st["gen"] = gen
            st["counters"] = {k: v for k, v in st["counters"].items()
                              if k >= (D._today() - timedelta(days=7)).isoformat()}
            st["counters"][day] = count + 1
            st["last_model_at"] = now.isoformat(timespec="seconds")
            _save(st, persona)
            req = dict(r)
        D._spawn_bound(_worker, persona, req["id"], gen, req, name="project_planner")
        return True


def _playbook(title: str, what: str = "") -> str | None:
    """The playbook whose `applies_to` phrases one of the end state's words hit. Method only;
    shared by every persona (§ 4.4)."""
    O = _O()

    def words(text: str) -> set:
        # Plain words, every length kept — "UK" is the word that tells UK tax from car tax, and
        # the ledger's matcher drops words under three letters.
        return {O._tstem(w) for w in re.findall(r"[a-z0-9]+", text.lower())}

    toks = words(f"{title} {what}")
    low = f"{title} {what}".lower()
    try:
        files = sorted(_PLAYBOOKS.glob("*.md"))
    except OSError:
        return None
    for p in files:
        try:
            text = p.read_text()
        except OSError:
            continue
        # `applies_when: a, b | c, d` (phase 3 § 17): a whole word from EVERY group must be there
        # — "speaking" + "Bulgarian" — so one playbook covers every language without a file each,
        # and "public speaking" (no language) or "Bulgarian taxes" (no learning word) does not
        # match. Plain words, as `applies_to`.
        w = re.search(r"^applies_when:\s*(.+)$", text, re.M)
        if w:
            def hit(entry: str) -> bool:
                entry = entry.strip().lower()
                # A phrase ("sign language") is matched as written; a word as a plain word.
                return (f" {entry} " in f" {' '.join(re.findall(r'[a-z0-9]+', low))} "
                        if " " in entry else O._tstem(entry) in toks)

            groups = [[x for x in g.split(",") if x.strip()] for g in w.group(1).split("|")]
            if groups and all(g and any(hit(x) for x in g) for g in groups):
                return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
        m = re.search(r"^applies_to:\s*(.+)$", text, re.M)
        if not m:
            continue
        for phrase in (x.strip() for x in m.group(1).split(",")):
            ptoks = words(phrase)
            # Every word of the phrase must be there: "UK taxes" matches "File UK taxes", never
            # "Renew the car tax" or "Sort the council tax" (Fable #10) — so `applies_to` lists
            # specific phrases, never a bare "tax".
            if phrase and ptoks and (ptoks <= toks or phrase.lower() in low):
                return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
    return None


def _adoptable(end: dict, persona: str) -> list[dict]:
    """Open one-offs that may already be steps of this plan (§ 11: open tax tasks adopted): linked
    to the goal, or sharing a word with it. Never a step of another plan, never the end itself."""
    O = _O()
    etoks = O._task_tokens(f"{end['title']} {end.get('what', '')}")
    out = []
    for t in (O._norm(x) for x in O._load(persona)):
        if (t.get("status") != "open" or t.get("kind") not in O._ONE_OFF or t["id"] == end["id"]
                or (t.get("part_of") and t.get("part_of") != end["id"]) or t.get("prep_for")
                or str(t.get("source_id") or "").startswith("goal_talk:")):
            continue
        if t.get("goal_id") == end["id"] or etoks & O._task_tokens(t["what"]):
            out.append({"id": t["id"], "what": t["what"], "due": t.get("due"),
                        "minutes": t.get("minutes")})
    return out[:_ADOPT_MAX]


def _payload(req: dict, persona: str) -> dict:
    D = _D()
    end = _end(req["id"], persona) or {"title": req.get("title"), "id": req["id"],
                                       "kind": req.get("kind")}
    if end.get("deadline") is not None or end.get("kind") == "goal":
        # The date NOW, not the one queued with (Fable S3) — `validate` reads the same `req`.
        req["deadline"] = end.get("deadline")
    try:
        from tools.ambient import _get_timezone
        tz = _get_timezone() or ""
    except Exception:  # noqa: BLE001
        tz = ""
    out = {
        "today": D._today().isoformat(), "timezone": tz,
        "end_state": {"title": end.get("title"), "what": end.get("what") or "",
                      "deadline": req.get("deadline"), "kind": req.get("kind"),
                      "size_given": req.get("size")},
        "weekly_minutes": req.get("weekly_minutes"),
        "note": req.get("note") or "",
        "limits": {"max_step_minutes": int(_limit("project_step_max_minutes", 90)),
                   "max_steps": _MAX_STEPS},
        "open_tasks": _adoptable(end, persona) if end.get("title") else [],
        "playbook": _playbook(str(end.get("title") or ""), str(end.get("what") or "")),
    }
    # Part B (§ 18): what the talk-through settled, and what it started from when there was no
    # playbook — the realistic shape the planner paces milestones to. Absent until a talk is had.
    for k in ("done_means", "starting_point", "effort_hours"):
        if end.get(k):
            out["end_state"][k] = end[k]
    if end.get("kind") == "goal" and not out["playbook"]:
        try:
            from tools.goal_talk import last_shape
            shape = last_shape(str(end.get("id")), persona)
        except Exception:  # noqa: BLE001
            shape = None
        if shape and shape.get("source") == "research" and shape.get("text"):
            out["researched"] = shape["text"]
    if req.get("size") == "L":
        out["wave"] = _wave_payload(req)
        if req.get("expand"):
            out["open_tasks"] = []         # an expansion adopts nothing: the plan owns its rows
    return out


def _horizon(req: dict) -> date:
    """The furthest an L plan may reach: the goal's own date, else `l_horizon_days` out."""
    D = _D()
    dl = _O()._d(req.get("deadline"))
    return dl or D._today() + timedelta(days=int(_gn().get("l_horizon_days") or 365))


def _expand_window(m: dict, req: dict) -> tuple[date, date]:
    """The window an outline is broken into steps over. A milestone reached late keeps its
    length: it starts today and runs at least as long as its minutes need at the weekly time —
    never past the horizon. The move is recorded on the milestone by the worker."""
    D, O = _D(), _O()
    today = D._today()
    ef = max(O._d(m.get("eligible_from")) or today, today)
    due = O._d(m.get("due")) or _horizon(req)
    wm = max(10, int(req.get("weekly_minutes") or _gn().get("default_weekly_minutes") or 150))
    need = timedelta(days=max(7, -(-int(m.get("minutes") or 0) * 7 // wm)))
    due = min(max(due, ef + need), _horizon(req))
    return ef, max(due, ef)


def _wave_payload(req: dict) -> dict:
    ms = req.get("milestones") or []
    base = {"horizon": _horizon(req).isoformat(),
            "max_milestones": int(_gn().get("max_milestones") or 8)}
    key = req.get("expand")
    if not key:
        return {**base, "mode": "first"}
    m = next((x for x in ms if x.get("key") == key), {})
    ef, due = _expand_window(m, req)
    return {**base, "mode": "expand",
            "milestone": {"what": m.get("what"), "minutes": m.get("minutes"),
                          "eligible_from": ef.isoformat(), "due": due.isoformat()},
            "done": [x.get("what") for x in ms if x.get("status") == "done"],
            "later": [x.get("what") for x in ms if x.get("status") == "pending"
                      and x.get("key") != key]}


def validate_milestones(result, payload: dict) -> tuple[list[dict], list[str]]:
    """The outlines of a first wave (§ 4.3 rolling wave): each needs a window inside the horizon
    and a total estimate in minutes — no 90-minute cap, since an outline is never placed. The
    first is the milestone the steps are for. Ordered by `due`. ([], []) for any other payload."""
    O = _O()
    wave = payload.get("wave") or {}
    if wave.get("mode") != "first":
        return [], []
    errors: list[str] = []
    ms = result.get("milestones") if isinstance(result, dict) else None
    if not isinstance(ms, list) or not ms:
        return [], ["`milestones` must be a non-empty list for a large goal — the first is the "
                    "one this answer's steps are for"]
    mx = int(wave.get("max_milestones") or 8)
    if len(ms) > mx:
        errors.append(f"at most {mx} milestones")
    today, horizon = O._d(payload.get("today")), O._d(wave.get("horizon"))
    out: list[dict] = []
    seen: set = set()
    prev = None
    for i, m in enumerate(ms):
        if not isinstance(m, dict):
            errors.append(f"milestone {i} is not an object")
            continue
        key = str(m.get("key") or f"m{i + 1}")
        what = str(m.get("what") or "").strip()
        if not what:
            errors.append(f"milestone {key}: no `what`")
        if key in seen:
            errors.append(f"milestone {key}: key used twice")
        seen.add(key)
        try:
            minutes = int(m.get("minutes"))
        except (TypeError, ValueError):
            minutes = 0
        if minutes < 5:
            errors.append(f"milestone {key}: `minutes` — its total estimate — must be at least 5")
        ef, due = O._d(m.get("eligible_from")), O._d(m.get("due"))
        if not ef or not due:
            errors.append(f"milestone {key}: `eligible_from` and `due` (YYYY-MM-DD) are required")
        else:
            if today and ef < today:
                errors.append(f"milestone {key}: eligible_from {ef} is in the past")
            if ef > due:
                errors.append(f"milestone {key}: eligible_from is after due")
            if horizon and due > horizon:
                errors.append(f"milestone {key}: due {due} is after {horizon}")
            if prev and due < prev:
                errors.append(f"milestone {key}: milestones go in order of their `due`")
            prev = due
        out.append({"key": key, "what": what[:160], "minutes": minutes,
                    "eligible_from": ef.isoformat() if ef else None,
                    "due": due.isoformat() if due else None, "status": "pending"})
    if out:
        out[0]["status"] = "current"
    return out, errors


def _call_model(payload: dict, persona: str) -> str:
    if _MODEL_CALL is not None:
        return _MODEL_CALL(payload)
    from core.spend_guard import check_before_session
    check_before_session()                    # raises SpendLimitExceeded — caught by the caller
    from core.orchestrator import run_session
    # bare: no clock and no personal config — the payload carries today and the end state only.
    # Never complexity="quick", which would route it to the bulk tier.
    return run_session("project_planner", json.dumps(payload, ensure_ascii=False),
                       persona=persona, bare=True, proactive=True)


def validate(result, req: dict, payload: dict) -> tuple[str | None, list[dict], list[str]]:
    """(size, steps, errors). Code is the authority on every date and length (R4)."""
    O = _O()
    errors: list[str] = []
    if not isinstance(result, dict):
        return None, [], ["the reply was not one JSON object"]
    size = str(result.get("size") or "").strip().upper()
    if size not in _SIZES:
        errors.append("`size` must be S, M or L")
        size = None
    steps = result.get("steps")
    if not isinstance(steps, list) or not steps:
        return size, [], errors + ["`steps` must be a non-empty list"]
    if len(steps) > _MAX_STEPS:
        errors.append(f"at most {_MAX_STEPS} steps")
    today = O._d(payload.get("today"))
    deadline = O._d(req.get("deadline"))
    wave = payload.get("wave") or {}
    floor = None
    if wave.get("mode") == "expand":
        # Steps of one milestone stay inside its window (rolling wave, § 4.3).
        deadline = O._d((wave.get("milestone") or {}).get("due")) or deadline
        floor = O._d((wave.get("milestone") or {}).get("eligible_from"))
    elif wave.get("mode") == "first":
        first = (result.get("milestones") or [{}])[0] if isinstance(result.get("milestones"),
                                                                    list) else {}
        first = first if isinstance(first, dict) else {}
        deadline = O._d(first.get("due")) or O._d(wave.get("horizon")) or deadline
        floor = O._d(first.get("eligible_from"))
    cap = int((payload.get("limits") or {}).get("max_step_minutes") or 90)
    offered = {t["id"] for t in payload.get("open_tasks") or []}
    clean: list[dict] = []
    keys: dict[str, dict] = {}
    adopted: set = set()
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            errors.append(f"step {i} is not an object")
            continue
        key = str(s.get("key") or f"s{i}")
        what = str(s.get("what") or "").strip()
        if not what:
            errors.append(f"step {key}: no `what`")
        if key in keys:
            errors.append(f"step {key}: key used twice")
        try:
            minutes = int(s.get("minutes"))
        except (TypeError, ValueError):
            minutes = 0
        if not 5 <= minutes <= cap:
            errors.append(f"step {key}: `minutes` must be 5–{cap} (split a longer step)")
        due, ef = O._d(s.get("due")), O._d(s.get("eligible_from"))
        if not due:
            errors.append(f"step {key}: `due` (YYYY-MM-DD) is required")
        if not ef:
            errors.append(f"step {key}: `eligible_from` (YYYY-MM-DD) is required")
        if due and deadline and due > deadline:
            errors.append(f"step {key}: due {due} is after the deadline {deadline}")
        if due and today and due < today:
            errors.append(f"step {key}: due {due} is in the past")
        if ef and today and ef < today:
            errors.append(f"step {key}: eligible_from {ef} is in the past")
        if ef and due and ef > due:
            errors.append(f"step {key}: eligible_from is after due")
        if ef and floor and ef < floor:
            # A milestone's steps start no earlier than the milestone (Fable L4).
            errors.append(f"step {key}: eligible_from {ef} is before its milestone starts ({floor})")
        adopt = str(s.get("adopt") or "").strip()
        if adopt and (adopt not in offered or adopt in adopted):
            errors.append(f"step {key}: `adopt` must be one of the open_tasks ids, once")
        adopted.add(adopt)
        needs = [str(n) for n in (s.get("needs") or []) if str(n).strip()]
        step = {"key": key, "what": what[:160], "minutes": minutes, "due": due, "ef": ef,
                "needs": needs, "adopt": adopt or None, "required": s.get("required") is not False}
        keys[key] = step
        clean.append(step)
    for s in clean:
        for n in s["needs"]:
            if n not in keys:
                errors.append(f"step {s['key']}: needs {n!r}, which is not a step key")
            elif keys[n]["due"] and s["due"] and s["due"] < keys[n]["due"]:
                errors.append(f"step {s['key']}: due before {n}, which it needs")
    if not errors and not O._acyclic({s["key"]: s["needs"] for s in clean}):
        errors.append("the steps' `needs` form a cycle")
    return size, clean, errors


def _open_steps_for(req: dict, steps: list[dict]) -> list[dict]:
    """The validated steps as `open_plan` rows — flexible, dated, part_of the end state (R4)."""
    end_id = req["id"]
    rows = []
    for s in steps:
        row = {"key": s["key"], "what": s["what"], "kind": "deadline",
               "due": s["due"].isoformat(), "eligible_from": s["ef"].isoformat(),
               "flexible": True, "minutes": s["minutes"], "minutes_source": "estimated",
               "needs": s["needs"], "part_of": end_id}
        if req.get("kind") == "goal":
            row["goal_id"] = end_id
        if not s["required"]:
            row["required"] = False
        if s["adopt"]:
            row["adopt"] = s["adopt"]
        rows.append(row)
    if req.get("kind") == "task":
        # An obligation's end state is itself a task: it waits on the last steps.
        needed = {n for s in steps for n in s["needs"]}
        sinks = [s["key"] for s in steps if s["key"] not in needed]
        rows.append({"key": "__end", "adopt": end_id, "what": req.get("title") or end_id,
                     "due": req.get("deadline"), "needs": sinks})
    return rows


_EXPAND_TRIES = 3


def _fail(persona: str, end_id: str, gen: int, req: dict, error: str, **fields) -> None:
    """A plan that could not be made. A first plan: `needs_plan`, said once. An EXPANSION (Fable
    S5b): tried again the next day, up to `_EXPAND_TRIES`, keeping the map; only then said — as
    the next stage, not as the whole goal "could not be broken into steps"."""
    if not req.get("expand"):
        _finish(persona, end_id, gen, status="needs_plan", said=None, error=error, **fields)
        return
    tries = int(req.get("expand_failures") or 0) + 1
    if tries < _EXPAND_TRIES:
        _finish(persona, end_id, gen, status="queued", expand_failures=tries, error=error,
                not_before=(_D()._now() + timedelta(days=1)).isoformat(timespec="seconds"),
                **fields)
        return
    _finish(persona, end_id, gen, status="needs_plan", said=None, error=error,
            expand_failures=tries, wave_failed=req["expand"], **fields)


def _check(raw: str, req: dict, payload: dict) -> tuple[str | None, list[dict], list[str], list]:
    """`validate` (whose three-value shape the fixture runner reads) plus, for a first wave, the
    milestone outlines."""
    parsed = _D()._extract_json(raw)
    size, steps, errors = validate(parsed, req, payload)
    ms, merrs = validate_milestones(parsed, payload)
    return size, steps, errors + merrs, ms


def _wave_fields(req: dict, payload: dict, ids: list[str], first_ms: list[dict]) -> dict:
    """What a written wave records on the request. A first wave: its outlines, the first one
    current, said once ("it's planned"). An expansion: that outline current with the window its
    steps were planned over (a move recorded), said to no one — the next step just appears."""
    D = _D()
    now = D._now().isoformat(timespec="seconds")
    if not req.get("expand"):
        ms = first_ms
        key = ms[0]["key"] if ms else None
        return {"status": "planned", "said": None, "ids": ids, "milestones": ms,
                "waves": [{"key": key, "ids": ids, "at": now}]}
    key = req["expand"]
    win = (payload.get("wave") or {}).get("milestone") or {}
    ms = []
    for m in req.get("milestones") or []:
        m = dict(m)
        if m.get("key") == key:
            if (win.get("eligible_from"), win.get("due")) != (m.get("eligible_from"), m.get("due")):
                m["moved"] = {"from": [m.get("eligible_from"), m.get("due")], "at": now[:10]}
                m["eligible_from"], m["due"] = win.get("eligible_from"), win.get("due")
            m["status"] = "current"
        ms.append(m)
    return {"status": "planned", "said": "silent", "ids": ids, "milestones": ms, "expand": None,
            "waves": (req.get("waves") or []) + [{"key": key, "ids": ids, "at": now}]}


def _finish(persona: str, end_id: str, gen: int, **fields) -> bool:
    D = _D()
    with D._locked(persona):
        st = _load(persona)
        r = st["requests"].get(end_id)
        if not r or int(r.get("gen") or 0) != gen:
            return False
        r.update(fields)
        r["outcome_at"] = D._now().isoformat(timespec="seconds")
        r.pop("started_at", None)
        _save(st, persona)
        return True


def _worker(persona: str, end_id: str, gen: int, req: dict) -> None:
    D = _D()
    t0 = _time.monotonic()
    outcome, retried = "failed", False
    try:
        payload = _payload(req, persona)
        try:
            raw = _call_model(payload, persona)
        except Exception as exc:  # noqa: BLE001 — a spend refusal or a dead call
            raw, outcome = "", f"call_failed:{type(exc).__name__}"
        size, steps, errors, ms = _check(raw, req, payload)
        bigger = bool(size and _RANK[size] > _RANK.get(req["size"], 1) and not req.get("size_confirmed"))
        if outcome == "failed" and errors and not bigger:
            # One re-ask, told what was wrong (§ 4.3). Not after a failed call — a spend refusal
            # stays refused. It does not count against the daily cap a second time.
            retried = True
            try:
                raw = _call_model({**payload, "previous_errors": errors[:8]}, persona)
            except Exception as exc:  # noqa: BLE001
                raw, outcome = "", f"retry_call_failed:{type(exc).__name__}"
            size, steps, errors, ms = _check(raw, req, payload)
        if size and _RANK[size] > _RANK.get(req["size"], 1) and not req.get("size_confirmed"):
            # R3: bigger than it was vetted as — nothing is written; it goes back for vetting at
            # the larger depth.
            outcome = "resize"
            _finish(persona, end_id, gen, status="resize", planner_size=size, said=None)
            return
        if outcome != "failed" and "call_failed" in outcome:
            # A spend refusal, a Vertex error, a timeout — not a verdict on the plan (Fable #6).
            # Queued again after an hour, up to three tries; only then is the user told.
            tries = int(req.get("call_failures") or 0) + 1
            if tries < _CALL_TRIES:
                retry_at = (D._now() + _CALL_BACKOFF).isoformat(timespec="seconds")
                _finish(persona, end_id, gen, status="queued", call_failures=tries,
                        not_before=retry_at)
                return
            _fail(persona, end_id, gen, req, outcome, call_failures=tries)
            return
        if outcome != "failed" or errors:
            outcome = outcome if outcome != "failed" else "invalid"
            _fail(persona, end_id, gen, req, "; ".join(errors[:4]) if errors else outcome)
            return
        end = _end(end_id, persona)
        why = _end_usable(end)
        if why:                                   # declined or closed while planning
            outcome = "end_gone"
            _finish(persona, end_id, gen, status="cancelled", error=why[:200])
            return
        with D._locked(persona):
            cur = _load(persona)["requests"].get(end_id) or {}
        if int(cur.get("gen") or 0) != gen or cur.get("status") != "inflight":
            # Superseded — a stale-window restart owns this end state now (Fable #9).
            outcome = "superseded"
            return
        res = _O().open_plan(_open_steps_for(req, steps), persona=persona, created_by="project_planner")
        if not res.get("ok"):
            outcome = "refused"
            _fail(persona, end_id, gen, req, str(res.get("error") or "refused")[:200])
            return
        outcome = "planned"
        ids = [v for k, v in res["ids"].items() if k != "__end"]
        if req.get("size") == "L":
            outcome = "expanded" if req.get("expand") else "planned"
            _finish(persona, end_id, gen, **_wave_fields(req, payload, ids, ms),
                    adopted=res.get("adopted") or [], planner_size=size)
            return
        _finish(persona, end_id, gen, status="planned", said=None, ids=ids,
                adopted=res.get("adopted") or [], planner_size=size)
    finally:
        if outcome == "superseded":
            pass
        elif outcome == "failed":
            _finish(persona, end_id, gen, status="needs_plan", said=None, error="failed")
        _log("project_plan", persona, end=end_id, outcome=outcome, retried=retried,
             ms=int((_time.monotonic() - t0) * 1000))


# --- the sweep: a vetted goal with no plan (generalises allocation_gaps) ----------------------

def sweep_unplanned(persona: str | None = None) -> int:
    """A goal taken on as M, with a date ahead, no open steps and never planned, is queued — the
    "verified goal with no plan" sweep (§ 4.3). Once per goal: a goal whose plan was made and
    finished is not re-planned behind the user's back."""
    # Part B (§ 18): an L goal still to be talked through gets its talk task (once per goal) —
    # its own flag, before the planner's, since the talk is not a plan. Never costs the sweep.
    try:
        from tools.goal_talk import sweep as _talk_sweep
        _talk_sweep(persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[project_plan] talk sweep failed: %s", exc)
    if not _flag():
        return 0
    persona = resolve_persona(persona)
    O, D = _O(), _D()
    today = D._today()
    st = _load(persona)
    queued = 0
    wave = _wave_flag()
    for gid, g in O._goal_index().items():
        size = str(g.get("size") or "").upper()
        if (str(g.get("status") or "active") != "active" or size not in ("M", "L")
                or not g.get("vetted") or gid in st["requests"]):
            continue
        if size == "L":
            # Rolling wave (§ 17): an L goal talked through in full, with its weekly time on
            # record, is planned once like an M one. Off: L goals are never queued (phase 2).
            end = _end(gid, persona)
            if (wave and end and not _end_usable(end) and _full_pass(end)
                    and end.get("weekly_minutes") and not _open_steps(gid, persona)
                    and not (O._d(end.get("deadline")) and O._d(end["deadline"]) <= today)):
                _queue(end, "L", persona, weekly_minutes=end["weekly_minutes"], by="sweep")
                queued += 1
            continue
        dl = O._d(g.get("due"))
        if not dl or dl <= today or _open_steps(gid, persona):
            continue
        end = _end(gid, persona)
        if end and not _end_usable(end):
            _queue(end, "M", persona, by="sweep")
            queued += 1
    return queued


def advance_waves(persona: str | None = None) -> int:
    """Every tick, under `rolling_wave` (§ 17): an L plan whose current milestone has no open step
    left moves on. With at least one of its steps done, the milestone is done and the next outline
    is queued for expansion — the same queue, worker and daily cap (§ 10 R8), so it starts in this
    tick if the cap allows; no reshuffle (R5). With none done it is `stalled`: nothing more is
    expanded, and the re-vet asks about the goal. Code only; returns how many were queued."""
    if not _wave_flag():
        return 0
    persona = resolve_persona(persona)
    D, O = _D(), _O()
    st = _load(persona)                 # the plan record first: a worker finishing between the
    rows = {t["id"]: t for t in O._load(persona)}   # two reads leaves steps open, never stalled
    todo = []
    for rid, r in st["requests"].items():
        if r.get("size") != "L" or r.get("status") != "planned" or not r.get("milestones"):
            continue
        cur = next((m for m in r["milestones"] if m.get("status") == "current"), None)
        if not cur:
            continue
        ids = r.get("ids") or []
        if any((rows.get(i) or {}).get("status") == "open" for i in ids):
            continue
        end = _end(rid, persona)
        if _end_usable(end):
            continue                                # parked, declined or done: nothing to move
        # Steps the goal's own parking closed (`close_plan_of`) are neither done nor ignored
        # (Fable L3): taken on again, the milestone is simply planned afresh.
        by_goal = bool(ids) and all(any(isinstance(h, dict) and h.get("event") ==
                                        "closed_with_end_state"
                                        for h in (rows.get(i) or {}).get("history") or [])
                                    for i in ids if (rows.get(i) or {}).get("status") != "done")
        done_any = any((rows.get(i) or {}).get("status") == "done" for i in ids)
        todo.append((rid, cur["key"], "done" if done_any else "parked" if by_goal else "none"))
    if not todo:
        return 0
    now = D._now().isoformat(timespec="seconds")
    queued = 0
    with D._locked(persona):
        st = _load(persona)
        for rid, key, how in todo:
            r = st["requests"].get(rid) or {}
            if r.get("status") != "planned":
                continue
            ms = r.get("milestones") or []
            cur = next((m for m in ms if m.get("key") == key and m.get("status") == "current"), None)
            if not cur:
                continue
            if how == "parked":
                r.update(status="queued", expand=key, queued_at=now, by="wave")
                queued += 1
                _log("project_wave_queued", persona, end=rid, milestone=key, by="retaken")
                continue
            if how == "none":
                cur.update(status="stalled", stalled_at=now)
                _log("project_wave_stalled", persona, end=rid, milestone=key)
                continue
            cur.update(status="done", done_at=now)
            nxt = next((m for m in ms if m.get("status") == "pending"), None)
            if not nxt:
                r["waves_done"] = now[:10]
                _log("project_waves_done", persona, end=rid)
                continue
            r.update(status="queued", expand=nxt["key"], queued_at=now, by="wave")
            r.pop("call_failures", None)
            r.pop("not_before", None)
            queued += 1
            _log("project_wave_queued", persona, end=rid, milestone=nxt["key"])
        _save(st, persona)
    return queued


def replan_stalled(goal_id: str, persona: str | None = None) -> bool:
    """A stalled milestone the user has chosen to keep (a re-vet answered `active`) is broken
    into fresh steps — queued, under the same cap. False when there is nothing stalled."""
    if not _wave_flag():
        return False
    persona = resolve_persona(persona)
    D = _D()
    if not _full_pass(_end(goal_id, persona)):
        return False                       # the depth lapsed: talked through again first (L3)
    with D._locked(persona):
        st = _load(persona)
        r = st["requests"].get(goal_id) or {}
        cur = next((m for m in r.get("milestones") or [] if m.get("status") == "stalled"), None)
        if not cur or r.get("status") in ("queued", "inflight"):
            return False
        cur["status"] = "pending"
        r.update(status="queued", expand=cur["key"],
                 queued_at=D._now().isoformat(timespec="seconds"), by="revet")
        _save(st, persona)
    _log("project_wave_queued", persona, end=goal_id, milestone=cur["key"], by="revet")
    return True


def has_plan(goal_id: str, persona: str | None = None) -> bool:
    """Steps are open, or a plan is on its way — then the goal needs no weekly time proposed."""
    r = _load(persona)["requests"].get(goal_id) or {}
    return bool(r.get("status") in ("queued", "inflight") or _open_steps(goal_id, persona))


# --- telling the user, once -------------------------------------------------------------------

def notices(persona: str | None = None) -> list[dict]:
    """Plans finished and not yet said: planned ("it's planned", with the first step), couldn't
    be planned, or bigger than vetted. Each is said once — stamped by `note_said`, not on render
    (the 2026-11-20 lesson: rendering is not saying)."""
    if not _flag():
        return []
    persona = resolve_persona(persona)
    D, O = _D(), _O()
    now = D._now()
    st = _load(persona)
    tasks = {t["id"]: O._norm(t) for t in O._load(persona)}
    out = []
    for r in st["requests"].values():
        if r.get("status") not in ("planned", "needs_plan", "resize") or r.get("said"):
            continue
        at = D._dt(r.get("outcome_at"))
        if not at or now - at > timedelta(days=_NOTICE_DAYS):
            continue
        n = {"id": r["id"], "status": r["status"], "title": r.get("title") or r["id"]}
        if r["status"] == "planned":
            steps = [tasks[i] for i in r.get("ids") or [] if i in tasks]
            first = sorted((t for t in steps if t.get("status") == "open" and not t.get("_blocked")),
                           key=lambda t: (t.get("eligible_from") or "", t.get("due") or ""))
            if first:
                n["first"] = first[0]["what"]
                n["from"] = first[0].get("eligible_from") or first[0].get("due")
            n["steps"] = len(steps)
        if r["status"] == "resize":
            n["planner_size"] = r.get("planner_size")
        if r["status"] == "needs_plan" and r.get("wave_failed"):
            n["stage"] = next((m.get("what") for m in r.get("milestones") or []
                               if m.get("key") == r["wave_failed"]), None)
        out.append(n)
    if D._flag("projected_finish"):
        # A finish that moved past its date (§ 4.5, § 17), said once as Important — the day
        # plan's block routes `late` items there; stamped like every other notice.
        from tools.goal_network import finish_notices
        out += finish_notices(st)
    return out


def render(items: list[dict]) -> list[str]:
    lines = []
    for n in items:
        if n["status"] == "late":
            continue                               # rendered under Important (goal_network)
        if n["status"] == "planned":
            first = (f" Its first step — {n['first']} — is on their list from {n['from']}."
                     if n.get("first") else "")
            lines.append(f"\"{n['title']}\" is planned.{first} Say once, in a few everyday "
                         f"words, that it's planned and what its first step is; never list the "
                         f"other steps (read_plan has them if they ask).")
        elif n["status"] == "needs_plan" and n.get("stage"):
            lines.append(f"The next stage of \"{n['title']}\" — {n['stage']} — could not be "
                         f"broken into steps. Say once that you'll work out that next part with "
                         f"them, and ask one question about it.")
        elif n["status"] == "needs_plan":
            lines.append(f"\"{n['title']}\" could not be broken into steps. Say once that you'll "
                         f"need to work out what's involved with them, and ask one question "
                         f"about it.")
        else:
            lines.append(f"\"{n['title']}\" turned out bigger than it looked. Check it with them "
                         f"once: if it needs regular time week after week, update_goal vet it as "
                         f"size L (it gets weekly time, not steps); if it really is one job with "
                         f"an end date, say so and plan_project it again as M.")
    return lines


def mark_offered(ids: list[str], persona: str | None = None) -> None:
    if not ids:
        return
    D = _D()
    now = D._now().isoformat(timespec="seconds")
    try:
        with D._locked(persona):
            st = _load(persona)
            for i in ids:
                if i.startswith("late:"):
                    from tools.goal_network import mark_late_offered
                    r = st["requests"].get(i[5:])
                    if r:
                        mark_late_offered(r)
                    continue
                r = st["requests"].get(i)
                if r:
                    r["offered_at"] = now
                    r["offers"] = int(r.get("offers") or 0) + 1
                    if r["offers"] > _MAX_OFFERS and not r.get("said"):
                        r["said"] = "let go"
            _save(st, persona)
    except Exception as exc:  # noqa: BLE001 — bookkeeping never breaks a reply
        logger.warning(f"[project_plan] offer not recorded: {exc}")


def note_said(reply: str, persona: str | None = None) -> int:
    """Stamp a notice said only when the reply names it (a word of its title) and carries words
    of what it had to say (`_SIGNALS`), within the offer window."""
    if not reply or not _flag():
        return 0
    persona = resolve_persona(persona)
    D, O = _D(), _O()
    now = D._now()
    st = _load(persona)
    rtoks = O._task_tokens(reply)
    live = [r for r in st["requests"].values() if not r.get("said") and D._dt(r.get("offered_at"))
            and now - D._dt(r["offered_at"]) <= _SAID_WINDOW]
    hits = []
    # A finish alert on offer (§ 17): said only within the offer window, when the reply names it
    # and carries the new date or the fix (Fable S2 — never on a stray "later").
    from tools.goal_network import late_said
    for r in st["requests"].values():
        al = (r.get("finish") or {}).get("alert") or {}
        if al.get("offers") and not al.get("said") and late_said(r, reply, now, _SAID_WINDOW):
            hits.append("late:" + r["id"])
    for r in live:
        sig = _SIGNALS.get(r.get("status") or "")
        if not (sig and sig.search(reply)):
            continue
        # Named by a word of its title — or, when it is the only notice on offer, said without
        # the noun ("that's all set up — the first piece will come to you"; Fable #7).
        if rtoks & O._task_tokens(r.get("title") or "") or len(live) == 1:
            hits.append(r["id"])
    if not hits:
        return 0
    with D._locked(persona):
        st = _load(persona)
        for i in hits:
            if i.startswith("late:"):
                from tools.goal_network import mark_late_said
                if i[5:] in st["requests"]:
                    mark_late_said(st["requests"][i[5:]], now.isoformat(timespec="seconds"))
                continue
            if i in st["requests"]:
                st["requests"][i]["said"] = now.isoformat(timespec="seconds")
        _save(st, persona)
    return len(hits)


# --- the whole map, on request (G4) -----------------------------------------------------------

def read_plan(part_of: str = "") -> str:
    """Every step of one goal or obligation, in order, with where each stands. Only when the
    user asks — they are fed one step at a time otherwise."""
    persona = resolve_persona(None)
    O, D = _O(), _D()
    st = _load(persona)
    pid = str(part_of or "").strip()
    if not pid:
        names = [f"{r['id']}: {r.get('title')} ({r.get('status')})" for r in st["requests"].values()]
        return ("Planned goals and obligations: " + "; ".join(names)) if names else \
            "Nothing has been planned out yet."
    end = _end(pid, persona)
    title = (end or {}).get("title") or (st["requests"].get(pid) or {}).get("title") or pid
    rows = [O._norm(t) for t in O._load(persona) if t.get("part_of") == pid]
    req = st["requests"].get(pid) or {}
    if not rows:
        state = {"queued": "being planned", "inflight": "being planned",
                 "needs_plan": "could not be broken into steps yet",
                 "resize": "bigger than first thought — to be checked again",
                 "cancelled": "no longer being planned"}.get(req.get("status"), "not planned")
        return f"{title}: {state}."
    rows.sort(key=lambda t: (t.get("eligible_from") or t.get("due") or "", t.get("due") or ""))
    today = D._today()
    due = (end or {}).get("deadline") if end else req.get("deadline")      # the date now
    lines = [f"{title}" + (f" — due {due}" if due else "") + ":"]
    for t in rows:
        if t.get("status") != "open":
            mark = t.get("status")
        elif t.get("_blocked"):
            mark = "waits on an earlier step"
        elif O._d(t.get("eligible_from")) and O._d(t["eligible_from"]) > today:
            mark = f"from {t['eligible_from']}"
        else:
            mark = "now"
        lines.append(f"- {t['what']} ({mark}; by {t.get('due')}"
                     + (f", ~{t['minutes']} min" if t.get("minutes") else "") + ")")
    # A rolling-wave plan's later milestones are outlines, not steps (§ 17): named, with their
    # rough window, so the whole map is still the whole map.
    for m in req.get("milestones") or []:
        if m.get("status") == "pending":
            lines.append(f"- later: {m.get('what')} (an outline, broken into steps when it comes "
                         f"due; around {m.get('eligible_from')} to {m.get('due')})")
    return "\n".join(lines)


PLAN_PROJECT_SCHEMA = {
    "name": "plan_project",
    "description": (
        "Break a goal or obligation the user has taken on into small dated steps, out of sight. "
        "Only after it has been sized M (hours to days, one end date) and checked with the user "
        "in this turn — for a goal, after update_goal action=vet. Returns at once; the steps are "
        "made later and the user is fed one at a time. Never tell them the steps unless they ask."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "part_of": {"type": "string", "description": "The goal id (e.g. 'q5'), or the id of the open task that is the obligation's end state."},
            "size": {"type": "string", "description": "M. (S is one task — use open_task; L is not planned yet.)"},
            "weekly_minutes": {"type": "integer", "description": "Time a week the user said they can give it, if they said."},
            "note": {"type": "string", "description": "What the user said that shapes the steps — e.g. already files online, has an accountant. No reasons why, no feelings."},
        },
        "required": ["part_of"],
    },
}

READ_PLAN_SCHEMA = {
    "name": "read_plan",
    "description": (
        "The whole map of one planned goal or obligation — every step and where it stands. Only "
        "when the user asks to see it; otherwise they are given one step at a time. With no id, "
        "lists what has been planned."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "part_of": {"type": "string", "description": "The goal or task id."},
        },
        "required": [],
    },
}
