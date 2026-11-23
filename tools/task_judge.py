"""
tools/task_judge.py — every open task gets judged: vital or missable, and a priority, by what
missing it would cost this user, against their goals, mission and values.

Plan: archive/plans/goal_task_network_plan_2026-11-18.md § 16 (ranking, Part A). Mike, 2026-11-22:
"Tasks should be scored always, and if not vital should have a weaker score and be relegated to
back burner … Metatron should check new tasks against user goals and core values to ensure
appropriate ranking. If someone is a passionate gardener, repotting the plants is likely more
important than for the weekend warrior." And: "Taxes might not align with mission, but still are
high priority", and costs "financial — easy to quantify, social — much harder, existential/
psychological — harder still" should inform the weighing.

The FIRST judge is the agent that opens a task (open_task's `stakes`, `priority`, `stakes_why`,
whose descriptions carry the rule). This is the net for what it missed — and, on the day it
ships, the backlog: every task nobody ever judged, which until 11-22 counted as vital. An unjudged
task is back-burner (tools/day_plan.py `_score`), so a task judged late costs ranking, never a
false alarm.

Controls (the project planner's, R8): one worker per persona at a time, a daily cap, a minimum
gap, a stale worker re-run; the model call runs with no lock and the write is one locked ledger
write that never replaces what the user stated or an agent already judged.

Costs, named beside the cap: one reasoning-tier call (gemini-3.8-flash, thinking capped at 1,024)
judges up to `task_judge_batch` (25) tasks, ~3k tokens in and ~1.5–2.5k out — about $0.01 a call
at today's price, ~$0.02 after the introductory price ends. `task_judge_calls_per_day` (6) caps a
persona at ~$0.06/day (~$0.12 after); a failed call gives its place back. Typical: one call the day
this ships, then rarely. Ancillary: a verdict that moves a score by 10+ makes the next build a
day_planner reshuffle — under that path's own cap (`reshuffles_per_day`), not this one. Unseen: a
real obligation judged missable fades the way trivia should — guarded by the obligation rule in
the agent file and by the user's own review of the back burner (§ 16). A task the judge never
reaches is read as vital after `obligations._JUDGE_GRACE` (60 min), so a broken judge hides
nothing.

RANKING PART B (2026-11-23, archive/plans/ranking_values_plan_2026-11-23.md § 10 R1), behind
`cost_record`: the same pass also records each task's COST RECORD — what a delay would cost, who
bears it, how it grows — for every open task without one (`unrecorded`), judged or not. It writes
only cost fields, never `stakes`, never over a record already on file. The record adds ~40% output
(~70–90 tokens a task; a 25-task batch stays near 3k of the 5k output ceiling) → ~$0.014 a call,
still ≤ 6 a day; for one user the first pass after deploy is 2–3 calls (~$0.04), then rare.
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta

from core.persona import resolve_persona, persona_scope, persona_config_dir

logger = logging.getLogger(__name__)

# Tests inject a callable(payload: dict) -> str here; production calls the task_judge agent.
_MODEL_CALL = None

_STATE = "judge.json"
_TEXT_MAX = 2500


def _D():
    import tools.day_plan as D
    return D


def _O():
    import tools.obligations as O
    return O


def _limit(name: str, default):
    try:
        v = _D()._limit(name)
    except Exception:  # noqa: BLE001
        v = None
    return default if v in (None, "") else v


def _load(persona: str) -> dict:
    st = _D()._read_json(_D()._dir(persona) / _STATE, {})
    st = st if isinstance(st, dict) else {}
    st.setdefault("counters", {})
    return st


def _save(st: dict, persona: str) -> None:
    _D()._write_json(_D()._dir(persona) / _STATE, st)


def unjudged(persona: str | None = None) -> list[dict]:
    """Open deadlines and monthly-window habits with no stakes — what `_score` reads as back
    burner. Steps of a plan are excluded: they take their end state's weight (_end_weight)."""
    O = _O()
    out = []
    for t in O._load(persona):
        t = O._norm(t)
        # A code-made prep is vital by rule (open_plan); a chat task linked to an event is the
        # user's own task and is judged like any other.
        pf = t.get("prep_for") or {}
        if t.get("status") != "open" or t.get("stakes") or t.get("part_of") or (pf and not pf.get("chat")):
            continue
        if t.get("kind") == "deadline" or O._month_window(t):     # what `stakes` applies to
            out.append(t)
    # Most urgent first (Fable diff review #6): overdue and soonest-due before far-off and undated,
    # so a backlog bigger than one batch reaches the real current bills in the first pass.
    out.sort(key=lambda t: (O._d(t.get("due")) is None, str(O._d(t.get("due")) or "")))
    return out


def unrecorded(persona: str | None = None) -> list[dict]:
    """Ranking Part B, the recording pass (plan § 10 R1): open tasks with no COST record — not
    "no stakes" — of every kind the day ranks (deadlines, habits, intervals). Steps of a plan take
    their end state's record (tools/day_plan `_candidates_v2`), and a code prep is vital by rule,
    so neither is offered. Only cost fields are ever written for these."""
    from tools.ranking import has_record
    O = _O()
    # A task whose record failed twice is not offered again (Fable diff review #3): one value the
    # judge keeps getting wrong would otherwise spend the whole daily cap, and a task opened later
    # would wait past the grace and read as vital. It ranks on Part A's stakes instead.
    tried = _load(resolve_persona(persona)).get("cost_attempts") or {}
    out = []
    for t in O._load(persona):
        t = O._norm(t)
        pf = t.get("prep_for") or {}
        if (t.get("status") != "open" or t.get("kind") == "waiting" or has_record(t)
                or t.get("part_of") or (pf and not pf.get("chat"))
                or int(tried.get(t["id"], 0)) >= _COST_ATTEMPTS):
            continue
        out.append(t)
    out.sort(key=lambda t: (O._d(t.get("due")) is None, str(O._d(t.get("due")) or "")))
    return out


_COST_ATTEMPTS = 2


def _todo(persona: str | None) -> list[tuple[dict, tuple]]:
    """What one pass offers, each with what is wanted of it: ("stakes", "costs") for a task
    nobody judged, ("costs",) for one judged but unrecorded. Unjudged first — the urgent half."""
    from tools.day_plan_config import flag
    todo = [(t, ("stakes",)) for t in unjudged(persona)]
    if flag("cost_record"):
        want = {t["id"]: i for i, (t, _w) in enumerate(todo)}
        for t in unrecorded(persona):
            if t["id"] in want:
                todo[want[t["id"]]] = (todo[want[t["id"]]][0], ("stakes", "costs"))
            else:
                todo.append((t, ("costs",)))
    return todo


def _text(name: str, persona: str) -> str:
    try:
        return (persona_config_dir(persona) / name).read_text(encoding="utf-8").strip()[:_TEXT_MAX]
    except Exception:  # noqa: BLE001
        return ""


def _payload(tasks: list[dict], persona: str, wants: dict | None = None) -> dict:
    """What the judge sees. Goals by title and shareable_what — NEVER private_why. `wants`
    ({id: ("stakes",) | ("costs",) | both}) says what each task needs; with a cost record wanted,
    the record's field descriptions go along as `rules` — they are the judging rule's one home."""
    O = _O()
    wants = wants or {t["id"]: ("stakes",) for t in tasks}
    goals = []
    for gid, g in O._goal_index().items():
        if str(g.get("status") or "active") not in ("active", "not_started", "at_risk"):
            continue
        goals.append({"id": gid, "title": str(g.get("title") or ""),
                      "what": str(g.get("shareable_what") or "")[:200],
                      "priority": O._goal_priority(g), "kind": g.get("kind") or "goal"})
    out = {
        "today": _D()._today().isoformat(),
        "tasks": [{"id": t["id"], "what": t.get("what", ""), "due": t.get("due"),
                   "kind": t.get("kind"), "domain": t.get("domain"),
                   "note": str(t.get("note") or "")[:200], "goal_id": t.get("goal_id"),
                   "priority": t.get("priority"),
                   **({"every_days": t.get("interval_days")} if t.get("kind") == "interval" else {}),
                   **({"want": list(wants.get(t["id"], ("stakes",)))}
                      if any("costs" in w for w in wants.values()) else {})}
                  for t in tasks],
        "goals": goals,
        "mission": _text("mission.md", persona),
        "prime_directive": _text("prime_directive.md", persona),
    }
    if any("costs" in w for w in wants.values()):
        out["rules"] = {k: O._COST_FIELD_PROPS[k]["description"]
                        for k in ("costs", "bears", "shape", "real_due", "passion")}
        # The user's STATED passions only (ranking § 4.8): an inferred one is a reason to ask
        # them, never a reason to weigh a task — so the judge never sees it.
        try:
            from tools.profile import stated_passions
            passions = [str(p["what"]) for p in stated_passions()]
        except Exception:  # noqa: BLE001
            passions = []
        if passions:
            out["passions"] = passions
    return out


def _known_passion(name) -> str | None:
    """The judge may name only a passion the user stated; anything else is dropped (None)."""
    n = str(name or "").strip()
    if not n:
        return None
    try:
        from tools.profile import stated_passions
        return next((str(p["what"]) for p in stated_passions()
                     if str(p["what"]).strip().lower() == n.lower()), None)
    except Exception:  # noqa: BLE001
        return None


def _call_model(payload: dict, persona: str) -> str:
    if _MODEL_CALL is not None:
        return _MODEL_CALL(payload)
    from core.spend_guard import check_before_session
    check_before_session()                    # raises SpendLimitExceeded — caught by the caller
    from core.orchestrator import run_session
    # bare: the payload carries everything the judge needs; no clock or personal config added.
    return run_session("task_judge", json.dumps(payload, ensure_ascii=False),
                       persona=persona, bare=True, proactive=True)


def validate(result, offered: set[str], wants: dict | None = None,
             kinds: dict | None = None) -> tuple[list[dict], list[str]]:
    """(verdicts, errors). A verdict for a task not offered, or with a value outside the ledger's
    own sets, is dropped — the rest still land. A cost record is checked by the ledger's own
    validator (`obligations._cost_fields`); a bad record drops the record, never the stakes."""
    O = _O()
    wants = wants or {}
    kinds = kinds or {}
    if not isinstance(result, dict) or not isinstance(result.get("tasks"), list):
        return [], ["the reply was not {\"tasks\": [...]}"]
    out, errors = [], []
    for v in result["tasks"]:
        if not isinstance(v, dict) or v.get("id") not in offered:
            errors.append(f"unknown task {v.get('id') if isinstance(v, dict) else v!r}")
            continue
        want = wants.get(v["id"], ("stakes",))
        why = str(v.get("why") or "").strip()[:120]
        verdict: dict = {"id": v["id"], "why": why}
        if "stakes" in want:
            st = str(v.get("stakes") or "").strip().lower()
            pr = str(v.get("priority") or "").strip().lower()
            if st not in O._STAKES or pr not in O._PRIORITIES:
                errors.append(f"{v['id']}: stakes vital|missable and priority high|normal|low")
                continue
            verdict.update(stakes=st, priority=pr)
        if "costs" in want and not (isinstance(v.get("costs"), dict) and v["costs"]):
            # No costs given is no record (Fable diff review #2): an empty one would be permanent
            # — never offered again, G 0 under v2 — when the reply merely left the field out.
            errors.append(f"{v['id']}: cost record — no costs given")
        elif "costs" in want:
            shape = v.get("shape")
            if shape == "neglect" and kinds.get(v["id"]) != "interval":
                shape = "step"                      # neglect is an interval's shape only
            rec, err = O._cost_fields(kinds.get(v["id"]) or "deadline", costs=v.get("costs") or {},
                                      bears=v.get("bears") or "self", shape=shape,
                                      real_due=v.get("real_due") or None,
                                      costs_source="inferred", costs_why=why,
                                      passion=_known_passion(v.get("passion")))
            if err:
                errors.append(f"{v['id']}: cost record — {err[:80]}")
            else:
                verdict["record"] = rec
        if "stakes" in verdict or "record" in verdict:
            out.append(verdict)
    return out, errors


def _write(verdicts: list[dict], persona: str) -> int:
    """One locked write. Never over a stated value, nor over stakes set since the call began."""
    O = _O()

    goals = O._goal_index()

    def apply(doc: dict) -> int:
        by_id = {t["id"]: t for t in doc["tasks"]}
        n = 0
        stamp = O._stamp()
        for v in verdicts:
            t = by_id.get(v["id"])
            if t is None or t.get("status") != "open":
                continue
            # The cost record (ranking § 10 R1): written only where none exists — never over a
            # stated one or one written since the call began — and it never touches `stakes`.
            if v.get("record") and not t.get("costs_source"):
                t.update(v["record"])
                t.setdefault("history", []).append({
                    "event": "costs_recorded", "at": stamp, "by": "task_judge",
                    **{k: v["record"][k] for k in ("costs", "bears", "shape") if k in v["record"]}})
                if "stakes" not in v:
                    n += 1
            if "stakes" not in v or t.get("stakes"):
                continue
            t["stakes"], t["stakes_source"] = v["stakes"], "inferred"
            if v["why"]:
                t["stakes_why"] = v["why"]
            # A task serving a goal takes its priority from that goal (`_score`, "leave unset to
            # take it from the goal it serves") — a verdict here would flatten it (Fable #3).
            if not t.get("priority") and str(t.get("goal_id") or "") not in goals:
                t["priority"], t["priority_source"] = v["priority"], "inferred"
            t.setdefault("history", []).append({"event": "judged", "at": stamp,
                                                "stakes": v["stakes"], "priority": v["priority"],
                                                "by": "task_judge"})
            n += 1
        return n
    res = O._with_store(persona, apply)
    return res if isinstance(res, int) else 0


def start_judging(persona: str | None = None) -> bool:
    """Start one judging pass on a worker when unjudged tasks exist, under the cap and the gap."""
    persona = resolve_persona(persona)
    D = _D()
    if not D._flag("task_judge"):
        return False
    with persona_scope(persona):
        todo = _todo(persona)
        if not todo:
            return False
        now, day = D._now(), D._today().isoformat()
        with D._locked(persona):
            st = _load(persona)
            started = D._dt(st.get("inflight_at"))
            if started and (now - started).total_seconds() < int(_limit("task_judge_stale_seconds", 300)):
                return False                                   # single flight
            count = int(st["counters"].get(day, 0))
            if count >= int(_limit("task_judge_calls_per_day", 6)):
                return False
            last = D._dt(st.get("last_model_at"))
            if last and now - last < timedelta(minutes=int(_limit("task_judge_gap_minutes", 10))):
                return False
            st["counters"] = {k: v for k, v in st["counters"].items()
                              if k >= (D._today() - timedelta(days=7)).isoformat()}
            st["counters"][day] = count + 1
            st["last_model_at"] = st["inflight_at"] = now.isoformat(timespec="seconds")
            size = int(st.get("batch") or _limit("task_judge_batch", 25))
            _save(st, persona)
        batch = todo[:max(1, size)]
        D._spawn_bound(_worker, persona, batch, name="task_judge")
        return True


def _worker(persona: str, batch: list) -> None:
    """One pass. A call that FAILED (outage, spend stop) gives its place in the daily cap back —
    only answered calls count — and the gap spaces the retries (Fable diff review #1). A reply
    that judged nothing halves the next batch, down to 5, so one oversized or garbled batch
    cannot stall the rest; a pass that lands restores it. Meanwhile `stakes_of` reads anything
    left unjudged past the grace as vital, so a broken judge hides nothing."""
    D = _D()
    outcome, n, called = "failed", 0, False
    recorded: set[str] = set()
    parsed = False
    # A batch is (task, wanted) pairs since ranking Part B; a bare task wants its stakes (Part A).
    pairs = [x if isinstance(x, tuple) else (x, ("stakes",)) for x in batch]
    batch = [t for t, _w in pairs]
    wants = {t["id"]: w for t, w in pairs}
    try:
        payload = _payload(batch, persona, wants)
        raw = _call_model(payload, persona)
        called = True
        verdicts, errors = validate(D._extract_json(raw), {t["id"] for t in batch}, wants,
                                    {t["id"]: t.get("kind") for t in batch})
        recorded = {v["id"] for v in verdicts if v.get("record")}
        reply = D._extract_json(raw)
        parsed = isinstance(reply, dict) and isinstance(reply.get("tasks"), list)
        n = _write(verdicts, persona) if verdicts else 0
        outcome = "judged" if n else ("unparseable" if errors and not verdicts else "nothing")
        if errors:
            logger.info(f"[task_judge] {len(errors)} verdict(s) dropped: {errors[:3]}")
        if n:
            # A judged end task re-weighs the steps that lead to it (Fable #7).
            _O().reweigh_plan_steps(persona)
    except Exception as exc:  # noqa: BLE001 — a spend refusal or a dead call: next tick retries
        logger.warning(f"[task_judge] call failed: {exc}")
    finally:
        day = D._today().isoformat()
        with D._locked(persona):
            st = _load(persona)
            st.pop("inflight_at", None)
            if not called:
                st["counters"][day] = max(0, int(st["counters"].get(day, 0)) - 1)
            elif outcome == "unparseable":
                st["batch"] = max(5, len(batch) // 2)
            elif n:
                st.pop("batch", None)
            if called and parsed:
                # A parsed reply that brought no usable record for a task counts as one attempt at
                # it (`unrecorded` stops offering it after _COST_ATTEMPTS). A garbled reply is the
                # batch's fault, not the task's — it halves the batch instead.
                tries = st.setdefault("cost_attempts", {})
                for tid, w in wants.items():
                    if "costs" in w and tid not in recorded:
                        tries[tid] = int(tries.get(tid, 0)) + 1
                st["cost_attempts"] = dict(list(tries.items())[-200:])
            _save(st, persona)
        D._log("task_judge", persona, outcome=outcome, judged=n, offered=len(batch))
