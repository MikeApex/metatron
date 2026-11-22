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


def _text(name: str, persona: str) -> str:
    try:
        return (persona_config_dir(persona) / name).read_text(encoding="utf-8").strip()[:_TEXT_MAX]
    except Exception:  # noqa: BLE001
        return ""


def _payload(tasks: list[dict], persona: str) -> dict:
    """What the judge sees. Goals by title and shareable_what — NEVER private_why."""
    O = _O()
    goals = []
    for gid, g in O._goal_index().items():
        if str(g.get("status") or "active") not in ("active", "not_started", "at_risk"):
            continue
        goals.append({"id": gid, "title": str(g.get("title") or ""),
                      "what": str(g.get("shareable_what") or "")[:200],
                      "priority": O._goal_priority(g), "kind": g.get("kind") or "goal"})
    return {
        "today": _D()._today().isoformat(),
        "tasks": [{"id": t["id"], "what": t.get("what", ""), "due": t.get("due"),
                   "kind": t.get("kind"), "domain": t.get("domain"),
                   "note": str(t.get("note") or "")[:200], "goal_id": t.get("goal_id"),
                   "priority": t.get("priority")} for t in tasks],
        "goals": goals,
        "mission": _text("mission.md", persona),
        "prime_directive": _text("prime_directive.md", persona),
    }


def _call_model(payload: dict, persona: str) -> str:
    if _MODEL_CALL is not None:
        return _MODEL_CALL(payload)
    from core.spend_guard import check_before_session
    check_before_session()                    # raises SpendLimitExceeded — caught by the caller
    from core.orchestrator import run_session
    # bare: the payload carries everything the judge needs; no clock or personal config added.
    return run_session("task_judge", json.dumps(payload, ensure_ascii=False),
                       persona=persona, bare=True, proactive=True)


def validate(result, offered: set[str]) -> tuple[list[dict], list[str]]:
    """(verdicts, errors). A verdict for a task not offered, or with a value outside the ledger's
    own sets, is dropped — the rest still land."""
    O = _O()
    if not isinstance(result, dict) or not isinstance(result.get("tasks"), list):
        return [], ["the reply was not {\"tasks\": [...]}"]
    out, errors = [], []
    for v in result["tasks"]:
        if not isinstance(v, dict) or v.get("id") not in offered:
            errors.append(f"unknown task {v.get('id') if isinstance(v, dict) else v!r}")
            continue
        st = str(v.get("stakes") or "").strip().lower()
        pr = str(v.get("priority") or "").strip().lower()
        if st not in O._STAKES or pr not in O._PRIORITIES:
            errors.append(f"{v['id']}: stakes vital|missable and priority high|normal|low")
            continue
        out.append({"id": v["id"], "stakes": st, "priority": pr,
                    "why": str(v.get("why") or "").strip()[:120]})
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
            if t is None or t.get("status") != "open" or t.get("stakes"):
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
        todo = unjudged(persona)
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


def _worker(persona: str, batch: list[dict]) -> None:
    """One pass. A call that FAILED (outage, spend stop) gives its place in the daily cap back —
    only answered calls count — and the gap spaces the retries (Fable diff review #1). A reply
    that judged nothing halves the next batch, down to 5, so one oversized or garbled batch
    cannot stall the rest; a pass that lands restores it. Meanwhile `stakes_of` reads anything
    left unjudged past the grace as vital, so a broken judge hides nothing."""
    D = _D()
    outcome, n, called = "failed", 0, False
    try:
        payload = _payload(batch, persona)
        raw = _call_model(payload, persona)
        called = True
        verdicts, errors = validate(D._extract_json(raw), {t["id"] for t in batch})
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
            _save(st, persona)
        D._log("task_judge", persona, outcome=outcome, judged=n, offered=len(batch))
