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
    return {"kind": "goal", "id": pid, "title": str(g.get("title") or pid),
            "deadline": str(g.get("due") or "")[:10] or None,
            "status": str(g.get("status") or "active"), "size": str(g.get("size") or "").upper(),
            "what": str(g.get("shareable_what") or "")[:300], "vetted": bool(g.get("vetted"))}


def _open_steps(end_id: str, persona: str | None = None) -> list[dict]:
    return [t for t in _O()._load(persona) if t.get("part_of") == end_id and t.get("status") == "open"]


def _end_usable(end: dict | None) -> str | None:
    """None if this end state may be planned; else why not (the model sees it)."""
    if end is None:
        return "error: no goal or task with that id."
    if end["kind"] == "goal" and end["status"] not in ("active", "not_started", "at_risk"):
        return (f"error: {end['title']} is {end['status']} — only a goal that has been taken on "
                f"is planned. Check it with the user first (update_goal action=vet). Nothing "
                f"was queued.")
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
        return ("A large goal is talked through properly before it is planned — not yet. It stays "
                "as being considered. Nothing was queued.")
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
                or (t.get("part_of") and t.get("part_of") != end["id"]) or t.get("prep_for")):
            continue
        if t.get("goal_id") == end["id"] or etoks & O._task_tokens(t["what"]):
            out.append({"id": t["id"], "what": t["what"], "due": t.get("due"),
                        "minutes": t.get("minutes")})
    return out[:_ADOPT_MAX]


def _payload(req: dict, persona: str) -> dict:
    D = _D()
    end = _end(req["id"], persona) or {"title": req.get("title"), "id": req["id"],
                                       "kind": req.get("kind")}
    try:
        from tools.ambient import _get_timezone
        tz = _get_timezone() or ""
    except Exception:  # noqa: BLE001
        tz = ""
    return {
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
        size, steps, errors = validate(D._extract_json(raw), req, payload)
        bigger = bool(size and _RANK[size] > _RANK.get(req["size"], 1) and not req.get("size_confirmed"))
        if outcome == "failed" and errors and not bigger:
            # One re-ask, told what was wrong (§ 4.3). Not after a failed call — a spend refusal
            # stays refused. It does not count against the daily cap a second time.
            retried = True
            try:
                raw = _call_model({**payload, "previous_errors": errors[:8]}, persona)
            except Exception as exc:  # noqa: BLE001
                raw, outcome = "", f"retry_call_failed:{type(exc).__name__}"
            size, steps, errors = validate(D._extract_json(raw), req, payload)
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
            _finish(persona, end_id, gen, status="needs_plan", said=None, call_failures=tries,
                    error=outcome)
            return
        if outcome != "failed" or errors:
            outcome = outcome if outcome != "failed" else "invalid"
            _finish(persona, end_id, gen, status="needs_plan", said=None,
                    error="; ".join(errors[:4]) if errors else outcome)
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
            _finish(persona, end_id, gen, status="needs_plan", said=None,
                    error=str(res.get("error") or "refused")[:200])
            return
        outcome = "planned"
        _finish(persona, end_id, gen, status="planned", said=None,
                ids=[v for k, v in res["ids"].items() if k != "__end"],
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
    if not _flag():
        return 0
    persona = resolve_persona(persona)
    O, D = _O(), _D()
    today = D._today()
    st = _load(persona)
    queued = 0
    for gid, g in O._goal_index().items():
        if (str(g.get("status") or "active") != "active" or str(g.get("size") or "").upper() != "M"
                or not g.get("vetted") or gid in st["requests"]):
            continue
        dl = O._d(g.get("due"))
        if not dl or dl <= today or _open_steps(gid, persona):
            continue
        end = _end(gid, persona)
        if end and not _end_usable(end):
            _queue(end, "M", persona, by="sweep")
            queued += 1
    return queued


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
        out.append(n)
    return out


def render(items: list[dict]) -> list[str]:
    lines = []
    for n in items:
        if n["status"] == "planned":
            first = (f" Its first step — {n['first']} — is on their list from {n['from']}."
                     if n.get("first") else "")
            lines.append(f"\"{n['title']}\" is planned.{first} Say once, in a few everyday "
                         f"words, that it's planned and what its first step is; never list the "
                         f"other steps (read_plan has them if they ask).")
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
    lines = [f"{title}" + (f" — due {req.get('deadline')}" if req.get("deadline") else "") + ":"]
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
