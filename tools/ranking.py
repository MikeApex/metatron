"""
tools/ranking.py — ranking Part B: what the user does next is decided by which delay they would
regret more.

Plan: archive/plans/ranking_values_plan_2026-11-23.md — rulings B1–B32 (§ 2), the design (§ 4),
the Fable review that governs it (§ 10, R1–R9), the research values (§ 11). Mike, 2026-11-23:
"Urgency is largely defined by consequence, so consequence as a cost must be compared to the value
of doing something else with that time … $30 for a day's delay might be ok, $30*365 days vs not
speaking to Dad for a year is unacceptable. There's the convexity."

The pieces, each a pure function of a task, the day and `config/modules/ranking.yaml`:

  importance G   — the task's cost record (§ 4.1): each cost a share of the maximum, combined
                   G = 100 × [1 − ∏(1 − sᵢ)] (§ 11 row 1), social × 1.5 (row 3).
  stakes_v2      — vital ⇔ the UNWEIGHTED worst grade is major or severe (R1); a plan step keeps
                   Part A's rule. Read by `is_essential` only under `ranking_v2`.
  cost of delay  — G × who-bears-it × the shape's factor today (§ 4.3, R4): step, accruing,
                   cliff through slack; neglect as min(M, (r − 1)^k) (row 7).
  slack          — days left after today minus the days the task needs, start-late buffer
                   included (row 5); ≤ 0 means it must start today (R3).
  attention      — the cost of delay is weighed per attention block (B7, row 6), never against a
                   must (R9).

Phase 1 is SHADOW: with `ranking_v2` off, `tools/day_plan.py` computes this order beside Part A's
and writes it to the plan's trace; nothing a user sees changes. State (the learned buffer, the
first build of each morning, contacts already offered a clock) is
data/personas/{p}/day_plan/ranking_state.json — bytes, per persona, deleted with it.
"""
from __future__ import annotations

import copy
import logging
import math
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "config" / "modules" / "ranking.yaml"

# What a missing or unreadable file means: the shipped values (kept equal to ranking.yaml; the
# test file checks they agree), so a broken file never ranks by nonsense.
_DEFAULTS: dict = {
    "grades": {"minor": 10, "major": 30, "severe": 90},
    "shares": {"minor": 0.1, "major": 0.3, "severe": 0.9},
    "share_cap": 0.99,
    "dimension_weight": {"financial": 1.0, "legal": 1.0, "health": 1.0, "social": 1.5,
                         "psychological": 1.0},
    "bearer_weight": {"self": 1.0, "close": 1.0, "own_org": 1.0, "others": 0.7, "org": 0.5},
    "fallback": {"vital": "major", "missable": "minor", "unjudged": "minor"},
    "shapes": {"step_residual": 0.2, "accrual_rate": 0.1, "reversibility_weight": 2.0,
               "neglect_k": 1.5, "neglect_cap": 3},
    "buffer": {"tiers": [{"under_minutes": 15, "buffer": 0.0},
                         {"under_minutes": 240, "buffer": 0.35},
                         {"under_minutes": None, "buffer": 0.65}],
               "fallback": 0.40, "aversive": 1.0,
               "learn": {"enabled": True, "sigma": 0.5, "tau": 0.25, "keep": 50}},
    "free_minutes_per_day": 120,
    "climb_max_days": 14,
    "attention_block": {"between": 5, "focus": 15, "batch_max_minutes": 15},
    "advance_floor": 10,
    "undated_step_factor": 0.5,
    "medication_lift": 90,
    "score_scale": 1.0,
    "reshuffle_delta": 15,
    "implied_promise_days": {"quick": 3, "effortful": 7, "quick_max_minutes": 15},
    "cadence_defaults": {"intimate": 7, "close_friend": 30, "wider": 120, "network": 365},
    # Phase 2.
    "protected": {"bases": {"family": 30, "rest": 18, "own": 18, "exercise": 12},
                  "default_base": 18, "exponent": 1.5, "half_life_days": 3.5, "keep_days": 21},
    "behind": {"overdue_min": 3, "top_skipped_min": 2, "skip_window": 3, "quick_wins_max": 2,
               "quick_wins_minutes": 20, "first_step_minutes": 10},
    "raise": {"skipped_days": 2, "max_without_news": 2, "prompts_per_day": 3},
    "enjoyed_gap_minutes": 15,
    "lookups": {"enabled": False, "per_day": 5, "refuse_figures": True},
}

GRADES = ("minor", "major", "severe")
DIMENSIONS = ("financial", "legal", "health", "social", "psychological")
BEARERS = ("self", "close", "own_org", "others", "org")
SHAPES = ("step", "accruing", "neglect", "cliff")

_LOCK = threading.Lock()
_CACHE: dict = {}
# Tests set a dict here: merged over the defaults instead of reading any file.
_OVERRIDE: dict | None = None


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _read(path: Path) -> dict:
    """A YAML mapping, re-read when it changes on disk; {} when absent or unreadable."""
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return {}
    with _LOCK:
        hit = _CACHE.get(str(path))
        if hit and hit[0] == mtime:
            return copy.deepcopy(hit[1])
        try:
            raw = yaml.safe_load(path.read_text()) or {}
            if not isinstance(raw, dict):
                raise ValueError("top level is not a mapping")
        except Exception as exc:  # noqa: BLE001 — a broken file means the defaults
            logger.warning(f"[ranking] {path.name} unreadable, ignored: {exc}")
            raw = {}
        _CACHE[str(path)] = (mtime, raw)
        return copy.deepcopy(raw)


def cfg(persona: str | None = None) -> dict:
    """The module file merged over the defaults, then the persona's own ranking.yaml over that
    (plan § 4.15: a user's deviations are config, not code). Never raises."""
    if _OVERRIDE is not None:
        return _merge(_DEFAULTS, _OVERRIDE)
    out = _merge(_DEFAULTS, _read(_PATH))
    try:
        from core.persona import persona_config_dir
        out = _merge(out, _read(persona_config_dir(persona) / "ranking.yaml"))
    except Exception:  # noqa: BLE001 — no persona bound: the module file alone
        pass
    return out


def _O():
    import tools.obligations as O
    return O


# --- the cost record (§ 4.1, R1) -------------------------------------------------------------

def has_record(t: dict) -> bool:
    """A cost record exists once anything recorded one — the judge, an agent, the user."""
    return bool(t.get("costs_source"))


def _grade_of(stakes: str | None, c: dict) -> str:
    fb = c.get("fallback") or {}
    return str(fb.get(stakes or "unjudged") or "minor")


def record_of(t: dict, c: dict, now: datetime | None = None) -> dict:
    """{costs, bears, shape, real_due, recorded}: the stored record, or — while a task awaits the
    recording pass — Part A's stakes read as one cost (§ 4.1: vital → major, missable → minor)
    on the shape its kind implies (step for a deadline, neglect for an interval)."""
    O = _O()
    kind = t.get("kind") or "deadline"
    default_shape = "neglect" if kind == "interval" else "step"
    if has_record(t):
        costs = t.get("costs") if isinstance(t.get("costs"), dict) else {}
        return {"costs": {k: v for k, v in costs.items() if k in DIMENSIONS and v in GRADES},
                "bears": t.get("bears") if t.get("bears") in BEARERS else "self",
                "shape": t.get("shape") if t.get("shape") in SHAPES else default_shape,
                "real_due": O._d(t.get("real_due")), "recorded": True}
    # Stakes apply to deadlines and windowed monthly habits only; anything else falls back light.
    applies = kind == "deadline" or bool(O._month_window(t))
    st = O.stakes_of(t, now) if applies else None
    return {"costs": {"_any": _grade_of(st, c)}, "bears": "self", "shape": default_shape,
            "real_due": None, "recorded": False}


def inherit(t: dict, by_id: dict[str, dict]) -> dict:
    """A plan step with no record of its own weighs as its end state does (plan § 3: "a step of a
    severe end carries it") — the end's costs and bearer, on a step's shape. A copy; nothing is
    stored, and the step's own stakes stay Part A's (R1)."""
    if has_record(t) or not t.get("part_of"):
        return t
    end = by_id.get(str(t["part_of"]))
    if not end or not has_record(end):
        return t
    return {**t, "costs": end.get("costs") or {}, "bears": end.get("bears") or "self",
            "shape": "step", "costs_source": "inherited",
            **({"passion": end["passion"]} if end.get("passion") else {})}


# --- passions (§ 4.8, B15–B17; § 6 test 11) ------------------------------------------------------

_LIFTED = ("psychological", "social")


def passion_served(t: dict, passions: list[dict] | None) -> str | None:
    """The STATED passion a task serves, or None: the one its cost record names (`passion`), or
    one tied to the goal it serves (Mike, 2026-11-23: passions tie into goals and mission). An
    inferred passion is never in `passions` — it never lifts (B16)."""
    if not passions:
        return None
    named = str(t.get("passion") or "").strip().lower()
    gids = {str(t.get("goal_id") or ""), str(t.get("part_of") or "")} - {""}
    for p in passions:
        what = str(p.get("what") or "").strip()
        if named and what.lower() == named:
            return what
        if gids & set(p.get("goals") or []):
            return what
    return None


def lift(costs: dict) -> dict:
    """One grade up for the psychological and social costs a task already has (§ 4.2: "raises
    the grade … by one step"); severe stays severe, and no cost is added that was not there."""
    out = dict(costs or {})
    for dim in _LIFTED:
        g = out.get(dim)
        if g in GRADES:
            out[dim] = GRADES[min(len(GRADES) - 1, GRADES.index(g) + 1)]
    return out


def floor_grade(costs: dict) -> str | None:
    """The worst grade among the costs, unweighted."""
    rank = [GRADES.index(g) for g in (costs or {}).values() if g in GRADES]
    return GRADES[max(rank)] if rank else None


def importance(costs: dict, c: dict) -> float:
    """G = 100 × [1 − ∏(1 − sᵢ)], sᵢ = the grade's share × its dimension's weight, capped below 1
    (§ 11 rows 1, 3). Worst sets the floor, further costs compound with diminishing effect, the
    total is bounded — B2 — and minors compound a little instead of not at all."""
    shares, dims = c.get("shares") or {}, c.get("dimension_weight") or {}
    cap = float(c.get("share_cap", 0.99))
    keep = 1.0
    for dim, grade in (costs or {}).items():
        s = float(shares.get(grade, 0.0)) * float(dims.get(dim, 1.0))
        keep *= 1.0 - min(cap, max(0.0, s))
    return round(100.0 * (1.0 - keep), 3)


def stakes_v2(t: dict, now: datetime | None = None) -> str | None:
    """The stakes `is_essential` reads under `ranking_v2` — derived, never stored (R1).

    A step of a plan, or a code prep, keeps Part A's rule whatever its record says (R1: "a
    required plan step stays vital"). Otherwise vital ⇔ the UNWEIGHTED worst grade is major or
    severe — who bears it moves the cost of delay, never whether it is vital (an org-borne step of
    the tax plan must not turn missable). No record yet: Part A's stored stakes, exactly."""
    O = _O()
    pf = t.get("prep_for") or {}
    if t.get("part_of") or (pf and not pf.get("chat")) or not has_record(t):
        return O.stakes_of(t, now)
    # The user's own word stands over any record (B4; Fable diff review #1: a "vital" the user
    # stated would otherwise turn missable at the flip on an inferred minor record).
    if t.get("stakes_source") == "stated" and t.get("stakes"):
        return t["stakes"]
    fg = floor_grade(t.get("costs") if isinstance(t.get("costs"), dict) else {})
    return "vital" if fg in ("major", "severe") else "missable"


def implied_due(t: dict, c: dict) -> date | None:
    """A promise to someone with no date (B25, R8, § 11 row 9): opened + 3 days for a quick
    digital favour, + 7 for an effortful one. Derived on read, so a record the judge writes later
    gives the date too, and nothing is stored that the Today list would show before the flip."""
    O = _O()
    if t.get("kind", "deadline") != "deadline" or str(t.get("due") or "").strip():
        return None
    if not has_record(t) or t.get("bears") not in ("close", "others"):
        return None
    opened = O._d(str(t.get("created_at") or "")[:10])
    if opened is None:
        return None
    # The grace runs from when the promise was known to be one — the later of opening and the
    # first cost record (Fable diff review #4: an undated August promise recorded on deploy day
    # must not become a must, overdue, the day the flag flips).
    for h in t.get("history") or []:
        if h.get("event") in ("costs_recorded", "costs_set"):
            rec = O._d(str(h.get("at") or "")[:10])
            if rec and rec > opened:
                opened = rec
            break
    ip = c.get("implied_promise_days") or {}
    mins = t.get("minutes")
    quick = (int(mins) <= int(ip.get("quick_max_minutes", 15)) if mins
             else str(t.get("activity") or "") == "admin")
    return opened + timedelta(days=int(ip.get("quick" if quick else "effortful", 7)))


# --- slack and the start-late buffer (§ 4.3, § 4.10, § 11 row 5) -----------------------------

def tier_buffer(minutes: int | None, c: dict) -> float:
    b = c.get("buffer") or {}
    if not minutes:
        return float(b.get("fallback", 0.4))
    for tier in b.get("tiers") or []:
        cut = tier.get("under_minutes")
        if cut is None or int(minutes) < int(cut):
            return float(tier.get("buffer", 0.0))
    return float(b.get("fallback", 0.4))


def shrink_weight(n: int, c: dict) -> float:
    """n/σ² ÷ (n/σ² + 1/τ²) — 0.43 at 3 observations, 0.71 at 10, 0.83 at 20 (research § 2)."""
    lr = (c.get("buffer") or {}).get("learn") or {}
    sigma, tau = float(lr.get("sigma", 0.5)), float(lr.get("tau", 0.25))
    if n <= 0:
        return 0.0
    a = n / sigma ** 2
    return a / (a + 1 / tau ** 2)


def person_bias(observations: list[float], c: dict) -> float:
    """The user's own log bias against the tier defaults, pooled across task classes and shrunk
    toward zero (no bias) by how much evidence there is. Each observation is
    log(actual whole days ÷ whole days the tier allots) — `observe`."""
    obs = [float(x) for x in observations or [] if isinstance(x, (int, float))]
    if not obs:
        return 0.0
    return shrink_weight(len(obs), c) * (sum(obs) / len(obs))


def buffer_for(minutes: int | None, c: dict, bias: float = 0.0) -> float:
    """The tier's buffer, moved by the user's learned bias: (1 + tier) × e^bias − 1, never < 0."""
    return max(0.0, (1.0 + tier_buffer(minutes, c)) * math.exp(bias) - 1.0)


def _minutes(t: dict) -> int:
    try:
        from tools.day_plan_config import limit
        dflt = int(limit("default_task_minutes") or 30)
    except Exception:  # noqa: BLE001
        dflt = 30
    return int(t.get("minutes") or dflt)


def needed_days(t: dict, c: dict, bias: float = 0.0) -> tuple[float, float]:
    """(days the task needs with the buffer, the buffer) — its minutes spread over the free time
    of a day (`free_minutes_per_day`, heuristic in phase 1)."""
    buf = buffer_for(t.get("minutes"), c, bias)
    free = max(1.0, float(c.get("free_minutes_per_day", 120)))
    return _minutes(t) * (1.0 + buf) / free, buf


# --- the cost of delay (§ 4.3 as amended by R4 and § 11) -------------------------------------

def assess(t: dict, v: dict, today: date, c: dict, bias: float = 0.0,
           now: datetime | None = None, on_list: bool = False,
           passions: list[dict] | None = None) -> dict:
    """Everything the rank reads, kept apart so the shadow can say which term moved a task (R4):
    {G, bearer, shape, factor, cod, slack, needed, buffer, S, due, must, recorded}.
    `on_list` — the task is on today's list (Part A's `_on_todays_list`), a must by R3 (a).
    `passions` — the user's STATED passions: one the task serves lifts its psychological and
    social costs a grade (§ 4.8). Importance only — whether it is vital stays the record's (R1)."""
    O = _O()
    rec = record_of(t, c, now)
    # The user's own grading already weighs what they love (Fable #12): a stated record is
    # never lifted; an inferred or inherited one is.
    served = passion_served(t, passions) if (rec["recorded"]
                                             and t.get("costs_source") != "stated") else None
    G = importance(lift(rec["costs"]) if served else rec["costs"], c)
    bearer = float((c.get("bearer_weight") or {}).get(rec["bears"], 1.0))
    sh = c.get("shapes") or {}
    kind = t.get("kind") or "deadline"
    out = {"G": G, "bearer": bearer, "shape": rec["shape"], "factor": 0.0, "slack": None,
           "needed": None, "buffer": None, "S": None, "due": None, "must": bool(on_list),
           "recorded": rec["recorded"], **({"passion": served} if served else {})}
    if kind == "interval":
        due = O._interval_due(t, today)
        out["due"] = due.isoformat()
        if rec["shape"] == "neglect":
            # Zero until the wished cadence has passed, then convex, saturating at M (R4, row 7).
            n = max(1, int(t.get("interval_days") or 1))
            r = 1.0 + (today - due).days / n
            if r > 1.0:
                out["factor"] = min(float(sh.get("neglect_cap", 3)),
                                    (r - 1.0) ** float(sh.get("neglect_k", 1.5)))
            out["r"] = round(r, 3)
        else:
            out["factor"] = 1.0 if due <= today else 0.0
    elif kind == "habit":
        # A habit due today costs its whole weight if today goes by (a step on its day).
        out["factor"] = 1.0 if on_list else 0.0
    elif kind == "deadline":
        due = rec["real_due"] or O._d(t.get("due")) or implied_due(t, c)
        if due is not None:
            out["due"] = due.isoformat()
            need, buf = needed_days(t, c, bias)
            slack = (due - today).days - need
            # The look-ahead over which a day's delay starts to cost (Part A's 14-day climb). A
            # must (slack ≤ 0) costs its whole weight whatever S is, so S orders ADVANCE work
            # only — and S = the task's own need (plan § 4.10's first reading) would have put
            # nothing more than a day ahead above the floor (plan § 11a, deviation 2).
            S = max(1.0, need, float(c.get("climb_max_days", 14)))
            out.update(slack=round(slack, 3), needed=round(need, 3), buffer=round(buf, 3),
                       S=round(S, 3))
            if due < today:
                late = (today - due).days
                out["factor"] = {"step": float(sh.get("step_residual", 0.2)),
                                 "accruing": 1.0 + float(sh.get("accrual_rate", 0.1)) * late,
                                 "cliff": 0.0}.get(rec["shape"], float(sh.get("step_residual", 0.2)))
            else:
                r = 1.0 if slack <= 0 else max(0.0, 1.0 - slack / S)
                if rec["shape"] == "cliff":
                    r *= float(sh.get("reversibility_weight", 2.0))
                out["factor"] = r
            # Must start today (R3 a): it cannot be done in time otherwise. A cliff past its date
            # is moot, never a must — not even from today's list (Fable diff review #13).
            if due < today and rec["shape"] == "cliff":
                out["must"] = False
            elif slack <= 0:
                out["must"] = True
    cod = G * bearer * out["factor"]
    # A linked medication habit lifts by its profile criticality, an unlinked task by the name
    # net — the same test is_essential and the day plan's weight use (O.is_required_dose).
    if O.is_required_dose(t) and out["must"]:
        cod += float(c.get("medication_lift", 90))
    out["cod"] = round(cod, 3)
    out["factor"] = round(out["factor"], 4)
    return out


def attention_blocks(cands: list[dict], c: dict) -> dict[str, float]:
    """Attention blocks per candidate ref (B7, § 11 row 6): a task costs at least one block
    (`between`, 5 min); small tasks of one kind share one block between them — each pays its
    share of max(block, their total minutes)."""
    ab = c.get("attention_block") or {}
    block = max(1.0, float(ab.get("between", 5)))
    small = float(ab.get("batch_max_minutes", 15))
    groups: dict[str, list[dict]] = {}
    out: dict[str, float] = {}
    for x in cands:
        m = float(x.get("minutes") or 30)
        if m <= small and x.get("activity"):
            groups.setdefault(str(x["activity"]), []).append(x)
        else:
            out[x["ref"]] = max(block, m) / block
    for members in groups.values():
        total = sum(float(x.get("minutes") or 30) for x in members)
        cost = max(block, total)
        for x in members:
            out[x["ref"]] = (cost * float(x.get("minutes") or 30) / total) / block
    return out


def order(cands: list[dict]) -> list[dict]:
    """Selection (R9): the musts by absolute cost of delay, largest first; then the rest by cost
    of delay per attention block. The ratio decides among the optional, never against a must.
    Ties: the earlier date, then the shorter task."""
    def key(x):
        r = x["v2"]
        tier = 0 if r["must"] else 1
        val = r["cod"] if r["must"] else r["cod"] / max(1e-6, r["blocks"])
        return (tier, -val, str(r.get("due") or "9999"), x.get("minutes") or 0)
    return sorted(cands, key=key)


# --- state: the learned buffer, the morning shadow, people offered -----------------------------

_STATE = "ranking_state.json"
_SHADOW_DAYS = 14


def _D():
    import tools.day_plan as D
    return D


def load_state(persona: str | None = None) -> dict:
    D = _D()
    st = D._read_json(D._dir(persona) / _STATE, {})
    return st if isinstance(st, dict) else {}


def save_state(st: dict, persona: str | None = None) -> None:
    D = _D()
    D._write_json(D._dir(persona) / _STATE, st)


def bias_of(st: dict, c: dict) -> float:
    return person_bias((st.get("buffer") or {}).get("obs") or [], c)


def allotted_days(raw: float, tier: float) -> int:
    """The whole days the tier allots a task of `raw` days: max(1, ⌈raw × (1 + tier)⌉)."""
    return max(1, math.ceil(round(float(raw) * (1.0 + float(tier)), 6)))


def observe(st: dict, tasks: list[dict], today: date, c: dict, assessed: dict[str, dict],
            placed: set[str] | None = None, live: bool = False) -> bool:
    """Feed the buffer learner (§ 11 row 5), with the observation phase 2 designed (plan § 11b).

    Phase 1's measure — calendar days from the day a task first must start, against fractional
    predicted days — failed twice over (Fable diff review #7): in shadow the user is never SHOWN
    that start, so every long task trained "starts late"; and whole days against fractions read
    +0.2–0.4 even for a task done on its date. Now:
      - learning only when `live` — `ranking_v2` on, so the start is one the user was shown;
      - tracked from the day the task was PLACED in a live plan ON its computed must-start day
        (−1 < slack ≤ 0) and only if it existed before that day — the day the user was told it
        had to start. A task placed later than that (opened late, due today, already past its
        start on flip day) would read "finishes early" whatever the user did (Fable diff review
        #7), so it is never tracked;
      - one observation on closing done: log(actual whole days ÷ whole days allotted), allotted =
        max(1, ⌈raw × (1 + tier)⌉). Done on its last allotted day reads 0, exactly.
    Short tasks never qualify (raw < one day) — their length in days is noise — so for most users
    the tier defaults govern for a long while. Returns whether anything changed."""
    O = _O()
    if not live or not (((c.get("buffer") or {}).get("learn") or {}).get("enabled")):
        return False
    placed = placed or set()
    buf = st.setdefault("buffer", {})
    track = buf.setdefault("tracking", {})
    obs = buf.setdefault("obs", [])
    by_id = {t["id"]: t for t in tasks}
    changed = False
    free = max(1.0, float(c.get("free_minutes_per_day", 120)))
    for tid in sorted(placed):
        t, a = by_id.get(tid), assessed.get(tid) or {}
        if not t or tid in track or t.get("kind") != "deadline" or not a.get("must"):
            continue
        raw = _minutes(t) / free
        due = O._d(a.get("due")) if a.get("due") else None
        if raw < 1.0 or due is None or due < today:
            continue
        slack = a.get("slack")
        opened = O._d(str(t.get("created_at") or "")[:10])
        if slack is None or not (-1.0 < float(slack) <= 0.0) or opened is None or opened >= today:
            continue
        track[tid] = {"since": today.isoformat(), "raw": round(raw, 3),
                      "tier": tier_buffer(t.get("minutes"), c)}
        changed = True
    for tid in list(track):
        t = by_id.get(tid)
        if t is not None and t.get("status") == "open":
            continue
        e = track.pop(tid)
        changed = True
        if t is None or t.get("status") != "done":
            continue
        closed = O._stamp_day(t.get("closed_at")) or today
        since = O._d(e.get("since")) or today
        actual = max(1, (closed - since).days + 1)
        try:
            obs.append(round(math.log(actual / allotted_days(e["raw"], e["tier"])), 4))
        except (ValueError, ZeroDivisionError, KeyError, TypeError):
            continue
    keep = int(((c.get("buffer") or {}).get("learn") or {}).get("keep", 50))
    if len(obs) > keep:
        buf["obs"] = obs[-keep:]
    return changed


def keep_shadow(st: dict, day: date, shadow: dict) -> None:
    """The first build of each morning, kept 14 days — what `ranking_report --compare` reads."""
    days = st.setdefault("shadow", {})
    days.setdefault(day.isoformat(), shadow)
    cut = (day - timedelta(days=_SHADOW_DAYS)).isoformat()
    st["shadow"] = {k: v for k, v in days.items() if k > cut}


def keep_trace(st: dict, day: date, key: str, value, first: bool = False) -> None:
    """Phase 2's shadow, per day, kept 14 days beside phase 1's (what the `protected_v2` and
    `behind_v2` walkthroughs read): `first` keeps the day's first value; otherwise entries merge
    by key — a would-be ask seen at 07:00 and again at 15:00 is one entry, its latest reading."""
    days = st.setdefault("trace", {})
    today = days.setdefault(day.isoformat(), {})
    if first:
        today.setdefault(key, value)
    elif isinstance(value, dict):
        today.setdefault(key, {}).update(value)
    else:
        today[key] = value
    cut = (day - timedelta(days=_SHADOW_DAYS)).isoformat()
    st["trace"] = {k: v for k, v in days.items() if k > cut}


# --- protected time (§ 4.5 as amended by R6; § 11 rows 10–11) ---------------------------------

def window_class(b: dict) -> str | None:
    """The class an intrusion is priced by: a protected window's first activity (R6); time held
    for an unanswered family event, and a duty that is family time (childcare), are family."""
    kind = b.get("kind")
    if kind == "hold" or (kind == "duty" and b.get("activities")):
        return "family"
    if kind == "protected":
        acts = b.get("activities") or []
        return str(acts[0]) if acts else None
    return None


def intrusion_base(cls: str | None, c: dict) -> float:
    p = c.get("protected") or {}
    return float((p.get("bases") or {}).get(cls or "", p.get("default_base", 18)))


def intrusion_k(st: dict, cls: str | None, now: datetime, c: dict,
                skip: tuple[str, str] | None = None) -> float:
    """k for the next intrusion into `cls`: 1 + the recent intrusions into it, each fading on the
    half-life (§ 11 row 11). `skip` — (task id, day) — leaves out the one being decided, so a
    rebuild does not count a task against its own place."""
    p = c.get("protected") or {}
    half = max(0.1, float(p.get("half_life_days", 3.5)))
    k = 1.0
    for e in st.get("intrusions") or []:
        if not isinstance(e, dict) or e.get("class") != cls:
            continue
        if skip and (e.get("task_id"), e.get("day")) == skip:
            continue
        try:
            at = datetime.fromisoformat(str(e["at"]))
        except (KeyError, ValueError):
            continue
        age = max(0.0, (now - at).total_seconds() / 86400.0)
        k += 0.5 ** (age / half)
    return k


def intrusion_cost(cls: str | None, st: dict, now: datetime, c: dict,
                   skip: tuple[str, str] | None = None) -> tuple[float, float]:
    """(I, k): the k-th intrusion into `cls` costs base × k^exponent (§ 11 row 11)."""
    k = intrusion_k(st, cls, now, c, skip)
    exp = float((c.get("protected") or {}).get("exponent", 1.5))
    return round(intrusion_base(cls, c) * k ** exp, 3), round(k, 3)


def note_intrusion(st: dict, cls: str | None, task_id: str, window: str, day: date,
                   now: datetime, c: dict) -> bool:
    """Record that a task took protected time (once per task a day, however often the day is
    rebuilt); forget what is past `keep_days`. Returns whether anything was added."""
    keep = int((c.get("protected") or {}).get("keep_days", 21))
    cut = (now - timedelta(days=keep)).isoformat(timespec="seconds")
    rows = [e for e in st.get("intrusions") or [] if isinstance(e, dict)
            and str(e.get("at") or "") > cut]
    st["intrusions"] = rows
    if any((e.get("task_id"), e.get("day")) == (task_id, day.isoformat()) for e in rows):
        return False
    rows.append({"class": cls, "task_id": task_id, "window": window, "day": day.isoformat(),
                 "at": now.isoformat(timespec="seconds")})
    return True


def ask_id(task_id: str, window: str, day: date) -> str:
    """A protected-time question's id: short, stable for the task, window and day, no words."""
    import hashlib
    return "in-" + hashlib.sha256(f"{task_id}|{window}|{day.isoformat()}".encode()).hexdigest()[:8]


def intrusion_advice(a: dict, today: date) -> tuple[str, str | None]:
    """The recommendation an intrusion question carries (B12): yes when no later day keeps the
    task on time — due today or before, or no slack left — else another day, the latest that
    still does."""
    due = _O()._d(a.get("due")) if a.get("due") else None
    slack = a.get("slack")
    if due is None or due <= today or slack is None or float(slack) < 1.0:
        return "yes", None
    later = min(due, today + timedelta(days=int(math.floor(float(slack)))))
    return "other_time", later.isoformat()


# --- behind, and raising what slips (§ 4.10; § 11 rows 12–13) ----------------------------------

def note_top(st: dict, day: date, task_id: str | None) -> None:
    """The day's top-ranked must, as the first build at or after waking saw it — what "the top
    task skipped on 2 of the last 3 days" reads. Kept 14 days."""
    if not task_id:
        return
    tops = st.setdefault("top", {})
    tops.setdefault(day.isoformat(), task_id)
    cut = (day - timedelta(days=_SHADOW_DAYS)).isoformat()
    st["top"] = {k: v for k, v in tops.items() if k > cut}


def _skipped_on(t: dict | None, day: date) -> bool:
    """A day's top task was skipped that day unless it was closed done by the end of it. A task
    since deleted, dismissed or moot on or before the day was not skipped — it left."""
    if t is None:
        return False
    O = _O()
    closed = O._stamp_day(t.get("closed_at"))
    if t.get("status") == "done":
        return closed is None or closed > day
    if t.get("status") in O._TERMINAL:
        return bool(closed and closed > day)
    return True


def behind_state(tasks: list[dict], today: date, st: dict, c: dict) -> dict:
    """{behind, overdue, top_skipped, why} (§ 11 row 12): behind when ≥ `overdue_min` items are
    overdue, or the day's top-ranked task was skipped on ≥ `top_skipped_min` of the last
    `skip_window` days."""
    O = _O()
    b = c.get("behind") or {}
    by_id = {t["id"]: t for t in tasks}
    overdue = sorted(t["id"] for t in tasks if t.get("status") == "open"
                     and O._view(t, today).get("state") == "overdue")
    tops = st.get("top") or {}
    skipped = []
    for n in range(1, int(b.get("skip_window", 3)) + 1):
        d = today - timedelta(days=n)
        tid = tops.get(d.isoformat())
        if tid and _skipped_on(by_id.get(tid), d):
            skipped.append(d.isoformat())
    over = len(overdue) >= int(b.get("overdue_min", 3))
    top = len(skipped) >= int(b.get("top_skipped_min", 2))
    why = ([f"{len(overdue)} overdue"] if over else []) + \
        ([f"top task skipped {len(skipped)} of the last {b.get('skip_window', 3)} days"] if top else [])
    return {"behind": over or top, "overdue": len(overdue), "overdue_ids": overdue,
            "top_skipped": len(skipped), "why": "; ".join(why)}


def quick_wins(selected: list[dict], hard: dict | None, c: dict, steps: list[dict]) -> list[dict]:
    """While behind, what the day leads with (§ 11 row 12): at most `quick_wins_max`, at most
    `quick_wins_minutes` in all — the first, where one exists, a step of the hard task no longer
    than `first_step_minutes` (`steps`: candidates whose `part_of` is the hard task), then the
    smallest of what selection already chose. The hard task itself is never a quick win."""
    b = c.get("behind") or {}
    cap_n, cap_m = int(b.get("quick_wins_max", 2)), int(b.get("quick_wins_minutes", 20))
    first_max = int(b.get("first_step_minutes", 10))
    hard_ref = (hard or {}).get("ref")
    out: list[dict] = []
    total = 0
    first = min((s for s in steps if int(s.get("minutes") or 30) <= first_max
                 and s.get("ref") != hard_ref), key=lambda s: int(s.get("minutes") or 30),
                default=None)
    if first is not None:
        out.append(first)
        total += int(first.get("minutes") or 30)
    for x in sorted(selected, key=lambda s: int(s.get("minutes") or 30)):
        if len(out) >= cap_n:
            break
        m = int(x.get("minutes") or 30)
        if x.get("ref") in (hard_ref, *(o.get("ref") for o in out)) or total + m > cap_m:
            continue
        out.append(x)
        total += m
    return out


_NEWS_FIELDS = ("what", "due", "minutes", "costs", "bears", "shape", "real_due", "stakes",
                "priority", "note", "eligible_from", "after", "before")


def news_digest(t: dict) -> str:
    """What counts as new information about a task (§ 11 row 13): anything the user or an agent
    changed about what it is, when, how long or what it costs. Code's own bookkeeping is not."""
    import hashlib
    import json
    return hashlib.sha256(json.dumps({k: t.get(k) for k in _NEWS_FIELDS}, sort_keys=True,
                                     default=str).encode()).hexdigest()[:12]


def raise_candidates(tasks: list[dict], slips: dict, negative: dict[str, str | None], today: date,
                     st: dict, c: dict, behind: bool) -> tuple[list[tuple[str, str]], list[str]]:
    """([(task id, why)], [task ids to the weekly list]) — what to raise today (§ 11 row 13).

    Raised when a placed task has been skipped `skipped_days` days, or its slack has gone below 0
    (`negative`: {task id: worst grade}). While behind, only slack < 0 on a severe grade (§ 4.10:
    "no new raises except …"). At most once a day; at most `max_without_news` times without new
    information — after that the item waits for the weekly conversation (phase 3), and is not
    raised again until something about it changes."""
    r = c.get("raise") or {}
    need = int(r.get("skipped_days", 2))
    cap = int(r.get("max_without_news", 2))
    raises = st.get("raises") or {}
    weekly = st.get("weekly") or {}
    by_id = {t["id"]: t for t in tasks}
    out: list[tuple[str, str]] = []
    to_weekly: list[str] = []
    ids = sorted(set(slips) | set(negative),
                 key=lambda i: (i not in negative, -int((slips.get(i) or {}).get("days") or 0)))
    for tid in ids:
        t = by_id.get(tid)
        if not t or t.get("status") != "open":
            continue
        days = int((slips.get(tid) or {}).get("days") or 0)
        late = tid in negative
        if not (days >= need or late):
            continue
        if behind and not (late and negative.get(tid) == "severe"):
            continue
        rec = raises.get(tid) or {}
        fresh = rec.get("news") != news_digest(t)
        n = 0 if fresh else int(rec.get("n") or 0)
        if tid in weekly and not fresh:
            continue
        if rec.get("last") == today.isoformat():
            continue
        if n >= cap:
            to_weekly.append(tid)
            continue
        out.append((tid, "its slack has run out" if late else f"skipped {days} days"))
    return out, to_weekly


def note_raised(st: dict, tasks: list[dict], tids: list[str], today: date) -> None:
    """A raise the reply actually said (`day_plan.note_said`): counted against its task, with the
    task's information as it was — new information later starts the count again."""
    by_id = {t["id"]: t for t in tasks}
    raises = st.setdefault("raises", {})
    for tid in tids:
        t = by_id.get(tid)
        if not t:
            continue
        rec = raises.get(tid) or {}
        news = news_digest(t)
        n = int(rec.get("n") or 0) if rec.get("news") == news else 0
        if rec.get("last") == today.isoformat():
            continue
        raises[tid] = {"n": n + 1, "last": today.isoformat(), "news": news}
    st["raises"] = {k: v for k, v in raises.items()
                    if by_id.get(k) and by_id[k].get("status") == "open"}


def to_weekly(st: dict, tids: list[str], today: date, why: str = "raised twice, no news") -> None:
    wk = st.setdefault("weekly", {})
    for tid in tids:
        wk.setdefault(tid, {"since": today.isoformat(), "why": why})


# --- the prompt cap (§ 11 row 13: at most 3 a day the system starts from these paths) -----------

def prompt_room(st: dict, day: date, c: dict) -> tuple[set[str], int]:
    """(ids already admitted today, how many more may be)."""
    cap = int((c.get("raise") or {}).get("prompts_per_day", 3))
    have = set((st.get("prompts") or {}).get(day.isoformat()) or [])
    return have, max(0, cap - len(have))


def admit_prompts(st: dict, day: date, ids: list[str], c: dict) -> list[str]:
    """Admit what fits under today's cap, in order; returns what was admitted (already-admitted
    ids always are). Kept for today only."""
    have, room = prompt_room(st, day, c)
    out = []
    for i in ids:
        if i in have:
            out.append(i)
        elif room > 0:
            have.add(i)
            out.append(i)
            room -= 1
    st["prompts"] = {day.isoformat(): sorted(have)}
    return out


# --- the people offer (§ 4.6, B9) --------------------------------------------------------------

_INTIMATE_TYPES = ("family", "romantic")


def people_offer(persona: str | None, today: date, st: dict) -> dict | None:
    """One contact to offer a keep-in-touch clock to, once ever: an intimate one (family or
    partner, or a friend marked close) with a wished frequency on file, never offered before, with
    no open interval task already naming them. History informs the question — last contact is in
    the line — and never sets the cadence (B9): the user's answer does."""
    try:
        from tools import crm
        contacts = crm._load_contacts()
        freq_days = dict(crm._FREQUENCY_DAYS)
    except Exception:  # noqa: BLE001 — no contacts store: nothing to offer
        return None
    O = _O()
    offered = st.get("people_offered") or {}
    open_intervals = [str(t.get("what") or "").lower() for t in O._load(persona)
                      if t.get("status") == "open" and t.get("kind") == "interval"]
    c = cfg(persona)
    cad = c.get("cadence_defaults") or {}
    for p in contacts:
        cid = str(p.get("id") or "")
        if not cid or cid in offered:
            continue
        rtype = str(p.get("relationship_type") or "").lower()
        close = str(p.get("relationship_quality") or "").lower() == "close"
        if not (rtype in _INTIMATE_TYPES or (rtype == "friend" and close)):
            continue
        days = freq_days.get(str(p.get("contact_frequency_preference") or "").lower())
        if not days:
            continue
        first = str(p.get("first_name") or p.get("nickname") or p.get("name") or "").strip()
        named = re.compile(r"\b" + re.escape(first.lower()) + r"\b") if first else None
        if not first or any(named.search(w) for w in open_intervals):
            continue
        layer = "intimate" if rtype in _INTIMATE_TYPES else "close_friend"
        return {"contact_id": cid, "name": first, "wished_days": int(days),
                "last_contact": str(p.get("last_contact") or "") or None,
                "default_days": int(cad.get(layer, 7 if layer == "intimate" else 30))}
    return None


def offer_line(o: dict) -> str:
    last = f"last in touch {o['last_contact']}" if o.get("last_contact") else "no contact on record"
    return (f"Keep in touch, offer ONCE, in passing: {o['name']} — wished about every "
            f"{o['wished_days']} days, {last}. Ask whether they want help keeping in touch, about "
            f"that often (if they leave it to you: every {o['default_days']} days). On yes: "
            f"open_task kind interval, interval_days = their answer, last_done = the last contact, "
            f"shape neglect, bears close, costs {{\"social\": \"major\"}} unless they say it "
            f"matters more or less (costs_source stated only then). contact `{o['contact_id']}`")
