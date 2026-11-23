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
               "learn": {"enabled": False, "sigma": 0.5, "tau": 0.25, "keep": 50}},
    "free_minutes_per_day": 120,
    "climb_max_days": 14,
    "attention_block": {"between": 5, "focus": 15, "batch_max_minutes": 15},
    "advance_floor": 10,
    "medication_lift": 90,
    "score_scale": 1.0,
    "reshuffle_delta": 15,
    "implied_promise_days": {"quick": 3, "effortful": 7, "quick_max_minutes": 15},
    "cadence_defaults": {"intimate": 7, "close_friend": 30, "wider": 120, "network": 365},
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
            "shape": "step", "costs_source": "inherited"}


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
    log(actual ÷ predicted) − log(1 + the tier's buffer)."""
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
           now: datetime | None = None, on_list: bool = False) -> dict:
    """Everything the rank reads, kept apart so the shadow can say which term moved a task (R4):
    {G, bearer, shape, factor, cod, slack, needed, buffer, S, due, must, recorded}.
    `on_list` — the task is on today's list (Part A's `_on_todays_list`), a must by R3 (a)."""
    O = _O()
    rec = record_of(t, c, now)
    G = importance(rec["costs"], c)
    bearer = float((c.get("bearer_weight") or {}).get(rec["bears"], 1.0))
    sh = c.get("shapes") or {}
    kind = t.get("kind") or "deadline"
    out = {"G": G, "bearer": bearer, "shape": rec["shape"], "factor": 0.0, "slack": None,
           "needed": None, "buffer": None, "S": None, "due": None, "must": bool(on_list),
           "recorded": rec["recorded"]}
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
    if O._MEDICATION_RE.search(f"{t.get('what', '')} {t.get('note', '')}") and out["must"]:
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


def observe(st: dict, tasks: list[dict], today: date, c: dict, assessed: dict[str, dict]) -> bool:
    """Feed the buffer learner (§ 11 row 5). A deadline that needs a day or more is tracked from
    the day it first must start; when it closes done, log(actual days ÷ predicted days) less the
    tier's own log(1 + buffer) is one observation. Short tasks never qualify — their length in
    days is noise — so for most users the tier defaults govern for a long while. Returns whether
    anything changed."""
    O = _O()
    if not (((c.get("buffer") or {}).get("learn") or {}).get("enabled")):
        return False
    buf = st.setdefault("buffer", {})
    track = buf.setdefault("tracking", {})
    obs = buf.setdefault("obs", [])
    by_id = {t["id"]: t for t in tasks}
    changed = False
    free = max(1.0, float(c.get("free_minutes_per_day", 120)))
    for tid, a in assessed.items():
        t = by_id.get(tid)
        if not t or tid in track or not a.get("must") or a.get("slack") is None:
            continue
        raw = _minutes(t) / free
        if raw < 1.0 or (a.get("due") and O._d(a["due"]) and O._d(a["due"]) < today):
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
        actual = (closed - since).days + 1
        try:
            obs.append(round(math.log(actual / float(e["raw"])) - math.log(1 + float(e["tier"])), 4))
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
