"""
tools/satisfaction.py — goal–task network phase 3, part B: how much the user looked forward to
something, against how it turned out (re-vet trigger 3, plan § 4.2; Mike's ruling, § 18).

Behind `satisfaction_gap` (config/modules/day_plan.yaml) AND `ranking_signals` — rows go to the one
signals file the ranking's monthly review reads (ranking plan § 4.13), never a second. Off,
nothing is recorded, asked or said.

MIKE, 2026-11-24: "This isn't just a long term metric. Example: someone whose spending is out of
control can benefit from the realization that the anticipation of buying something, even if only
an hour, and the let down after receiving it are a mismatch. This needs to be a holistic, and
targeted approach that is both metric for Metatron and occasionally lesson for the user — good or
bad." And: "Spending was just an example, and sits first and foremost with Finance and Synth."

So:
1. HOLISTIC — any class of thing a person looks forward to (CLASSES), at any distance: an hour
   between ordering and the parcel counts as much as a concert booked weeks ahead.
2. HEARD FIRST, ASKED RARELY. What the user says unprompted ("can't wait for Saturday", "that was
   a let-down") is recorded by Synth at no cost in attention. Asking costs attention, the
   denominator of the core metric (ROADMAP § A9): at most `asks_per_week` questions a week, both
   kinds together, and only for TARGETED classes — one a current goal's title names (spending,
   exercise…), purchases while spending is over a budget Finance holds, or a class whose pairs
   already show a gap.
3. METRIC FOR METATRON — per class, from the pairs: how many, the average before and after, and
   whether the gap is consistent. Given to Synth as evidence when the next one in that class
   comes up (the tool's own result — "feeds that class's vetting"), and to Finance beside its
   spending figures for purchases.
4. LESSON FOR THE USER, OCCASIONALLY — once a class has `lesson_pairs` pairs with a consistent
   gap of at least `lesson_gap`, the next time one in that class comes up, Synth is told to put
   it to the user once, as a question, good or bad (the gym dreaded at 2 and enjoyed at 4 is as
   much a lesson as the parcel that disappoints). At most once every `lesson_every_days` in all.

Rows (ids, classes, scores and the user's own one-liners only):
    satisfaction_anticipated  {pair, class, score, item, text, when, asked}
    satisfaction_experienced  {pair, class, score, item, text, asked}
    satisfaction_lesson       {class, n, before, after}

Costs. Run: zero model calls — it records inside turns that happen anyway; a block line adds
~40–80 tokens to Synth's input on a day an ask is due. Ancillary: a few signal rows a week; one
small state file. Unseen: attention — bounded by the weekly cap, targeting, and the lesson cap.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date, datetime, timedelta

from core.persona import persona_data_dir, resolve_persona

logger = logging.getLogger(__name__)

CLASSES = ("purchase", "outing", "trip", "social", "activity", "commitment")
_LABEL = {"purchase": "purchases", "outing": "outings and events", "trip": "trips",
          "social": "times with people", "activity": "activities and exercise",
          "commitment": "commitments taken on"}
KINDS = ("satisfaction_anticipated", "satisfaction_experienced", "satisfaction_lesson")
_TEXT_MAX = 280
_ITEM_MAX = 60
_MATCH_DAYS = 60
_OFFER_DAYS = 2


def _D():
    import tools.day_plan as D
    return D


def on() -> bool:
    D = _D()
    return D._flag("satisfaction_gap") and D._flag("ranking_signals")


# The shipped tuning (config/modules/day_plan.yaml `goal_network.satisfaction`), so a config that
# omits the block still asks rarely and targets the same classes. The YAML is the authority.
_DEFAULTS = {
    "asks_per_week": 1, "invite_days": 2, "after_days": 1, "after_days_purchase": 3, "evidence_pairs": 3,
    "lesson_pairs": 4, "lesson_gap": 1.0, "lesson_every_days": 30,
    "targets": {
        "purchase": ["spend", "spending", "budget", "money", "saving", "savings", "debt", "shopping"],
        "activity": ["exercise", "swim", "gym", "strength", "run", "running", "fitness", "yoga",
                     "walk", "sport"],
        "social": ["friends", "social", "friendship", "community"],
        "outing": ["outings", "concert", "theatre", "evenings"],
        "trip": ["travel", "trip", "holiday"],
        "commitment": ["volunteer", "commitment", "commitments"],
    },
}


def _cfg() -> dict:
    try:
        from tools import day_plan_config as C
        return {**_DEFAULTS, **(C.goal_network().get("satisfaction") or {})}
    except Exception:  # noqa: BLE001
        return dict(_DEFAULTS)


def _n(name: str, default):
    v = _cfg().get(name)
    return default if v in (None, "") else v


def _state_path(persona: str):
    return persona_data_dir(persona) / "satisfaction_state.json"


def _state(persona: str) -> dict:
    p = _state_path(persona)
    try:
        st = json.loads(p.read_text()) if p.exists() else {}
    except (OSError, ValueError):
        st = {}
    return st if isinstance(st, dict) else {}


def _save_state(persona: str, st: dict) -> None:
    D = _D()
    D._write_json(_state_path(persona), st)


def _rows(persona: str) -> list[dict]:
    from tools.ranking_review import read_signals
    return [r for r in read_signals(persona) if r.get("source") == "goal_network"
            and r.get("kind") in KINDS]


def _day(r: dict) -> date | None:
    try:
        return date.fromisoformat(str(r.get("day") or "")[:10])
    except ValueError:
        return None


def _today() -> date:
    return _D()._today()


# --- the metric ------------------------------------------------------------------------------

def pairs(persona: str) -> list[dict]:
    """Every anticipated row joined with its experienced row (by pair id)."""
    rows = _rows(persona)
    after = {r.get("pair"): r for r in rows
             if r.get("kind") == "satisfaction_experienced" and r.get("pair")}
    out = []
    for r in rows:
        if r.get("kind") == "satisfaction_anticipated" and r.get("pair") in after:
            a, e = r, after[r["pair"]]
            out.append({"pair": r["pair"], "class": a.get("class"), "before": int(a["score"]),
                        "after": int(e["score"]), "item": a.get("item")})
    return out


def history(persona: str) -> dict[str, dict]:
    """Per class: n pairs, average before and after, the gap (after − before), and whether it is
    consistent — at least 3 in 4 pairs on the gap's side, and `lesson_gap` or more on average."""
    by: dict[str, list[dict]] = {}
    for p in pairs(persona):
        by.setdefault(str(p["class"]), []).append(p)
    gap_min = float(_n("lesson_gap", 1.0))
    out = {}
    for cls, ps in by.items():
        n = len(ps)
        b = sum(p["before"] for p in ps) / n
        a = sum(p["after"] for p in ps) / n
        gap = a - b
        side = sum(1 for p in ps if (p["after"] - p["before"]) * gap > 0)
        out[cls] = {"n": n, "before": round(b, 1), "after": round(a, 1), "gap": round(gap, 1),
                    "consistent": abs(gap) >= gap_min and side >= 0.75 * n}
    return out


# --- targeting --------------------------------------------------------------------------------

def _over_budget(persona: str) -> bool:
    try:
        from tools.finance_totals import period_figures
        fig = period_figures(persona)
        for lim in ((fig.get("budget") or {}).get("limits") or []):
            if lim.get("limit") is not None and int(lim.get("spent") or 0) > int(lim["limit"]):
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def targets(persona: str) -> dict[str, str]:
    """Which classes are worth ASKING about, each with why (for Synth's line): a current goal's
    title carries one of the class's words; purchases while a budget is over; a class whose pairs
    already lean one way. Everything else is only heard."""
    out: dict[str, str] = {}
    words = _cfg().get("targets") or {}
    try:
        import tools.obligations as O
        from tools.goals import CURRENT
        for gid, g in O._goal_index().items():
            if str(g.get("status") or "active") not in CURRENT:
                continue
            title = str(g.get("title") or "")
            toks = set(re.findall(r"[a-z]+", title.lower()))
            for cls, ws in words.items():
                if cls in CLASSES and cls not in out and toks & {str(w).lower() for w in ws}:
                    out[cls] = f"a goal: {title.strip()[:60]}"
    except Exception:  # noqa: BLE001
        pass
    if "purchase" not in out and _over_budget(persona):
        out["purchase"] = "spending is over a budget"
    gap_min = float(_n("lesson_gap", 1.0))
    for cls, h in history(persona).items():
        if cls not in out and h["n"] >= 2 and abs(h["gap"]) >= gap_min:
            out[cls] = "what they expected and what they got have differed"
    return out


def _asks_this_week(persona: str, today: date) -> int:
    since = today - timedelta(days=6)
    return sum(1 for r in _rows(persona) if r.get("asked") and (_day(r) or since) >= since
               and r.get("kind") != "satisfaction_lesson")


# --- Synth's line ------------------------------------------------------------------------------

def _due_after(persona: str, today: date, tg: dict) -> dict | None:
    """The oldest anticipated row, in a targeted class, whose day has passed by `after_days` (a
    purchase `after_days_purchase`) with no experienced row — offered on at most two days."""
    rows = _rows(persona)
    done = {r.get("pair") for r in rows if r.get("kind") == "satisfaction_experienced"}
    offers = _state(persona).get("offers") or {}
    for r in rows:
        if r.get("kind") != "satisfaction_anticipated" or r.get("pair") in done:
            continue
        cls = str(r.get("class") or "")
        if cls not in tg and not r.get("asked"):
            continue
        try:
            when = date.fromisoformat(str(r.get("when") or r.get("day"))[:10])
        except ValueError:
            continue
        lag = int(_n("after_days_purchase", 3) if cls == "purchase" else _n("after_days", 1))
        if when + timedelta(days=lag) > today or (today - when).days > _MATCH_DAYS:
            continue
        seen = offers.get(str(r["pair"])) or []
        if len(seen) >= _OFFER_DAYS and today.isoformat() not in seen:
            continue
        return r
    return None


def _invite_days(persona: str, today: date) -> int:
    since = today - timedelta(days=6)
    days = (_state(persona).get("invites") or [])
    return len({d for d in days if since.isoformat() <= d <= today.isoformat()})


def context_block(persona: str | None = None, today: date | None = None,
                  user_turn: bool = False) -> str:
    """Synth's block while on: always the listening line (heard costs nothing); plus, while the
    week's question is unused, either one "how did it turn out?" that is due, or the targeted
    classes it may ask about. "" while off.

    The weekly cap does not rest only on the model labelling its question or the user answering
    it (Fable S8): a specific "how did it turn out?" shown on a user's own turn is stamped by day,
    and after `invite_days` such days in a week no more asks are shown, answered or not. The
    standing "you may ask when one comes up" line spends nothing (verify N3) — there the cap is
    the recorded asks plus the instruction. Stamps are made only on the user's own turns (L12)."""
    if not on():
        return ""
    try:
        persona = resolve_persona(persona)
        today = today or _today()
        listen = ("- When they say, unprompted, how much they're looking forward to something — a "
                  "purchase, an outing, a trip, time with people, an activity, a commitment — or "
                  "how one turned out, keep it with note_expectation (asked false). Never ask "
                  "unless a line below says you may.")
        if (_asks_this_week(persona, today) >= int(_n("asks_per_week", 1))
                or _invite_days(persona, today) >= int(_n("invite_days", 2))):
            return "ANTICIPATION AND EXPERIENCE:\n" + listen
        tg = targets(persona)
        lines = [listen]
        due = _due_after(persona, today, tg)
        if due:
            lines.append(f"- Ask once, in passing, how it turned out: \"{due.get('item')}\" "
                         f"(pair {due['pair']}; they looked forward to it {due.get('score')}/5). "
                         "Record their answer with note_expectation, stage after, asked true.")
        elif tg:
            why = "; ".join(f"{_LABEL[c]} ({w})" for c, w in tg.items())
            lines.append("- When one of these comes up, you may ask once how much they're looking "
                         f"forward to it, 1–5 in their words: {why}. Record it with "
                         "note_expectation, stage before, asked true.")
        # Only a SPECIFIC question spends the budget (verify N3): the standing "when one comes
        # up, you may ask" line costs nothing until something relevant is said, so it never uses
        # up the week on days nothing came up.
        if due and user_turn:
            st = _state(persona)
            day = today.isoformat()
            invites = st.setdefault("invites", [])
            if day not in invites:
                invites.append(day)
                st["invites"] = invites[-30:]
            if due:
                seen = st.setdefault("offers", {}).setdefault(str(due["pair"]), [])
                if day not in seen:
                    seen.append(day)
            _save_state(persona, st)
        head = ("ANTICIPATION AND EXPERIENCE — at most one question this week; skip it if the "
                "moment is wrong:" if len(lines) > 1 else "ANTICIPATION AND EXPERIENCE:")
        return head + "\n" + "\n".join(lines)
    except Exception as exc:  # noqa: BLE001 — never costs the turn
        logger.warning("[satisfaction] block failed: %s", exc)
        return ""


def finance_line(persona: str | None = None) -> str:
    """Finance's line beside its spending figures (Mike: spending sits first with Finance and
    Synth) — evidence, in the user's own ratings; never a verdict."""
    if not on():
        return ""
    try:
        h = history(resolve_persona(persona)).get("purchase")
        if not h or h["n"] < int(_n("evidence_pairs", 3)):
            return ""
        return (f"HOW PURCHASES LAND (the user's own 1–5s, {h['n']} purchases): looked forward to "
                f"about {h['before']}, turned out about {h['after']}. Evidence when weighing a "
                "purchase with them — never quoted to them as a verdict.")
    except Exception:  # noqa: BLE001
        return ""


# --- the tool ----------------------------------------------------------------------------------

_GENERIC = frozenset({"new", "old", "last", "first", "next", "the", "my", "a", "an", "that",
                      "this", "one", "thing", "big", "little", "trip", "day", "night"})


def _match(persona: str, item: str, cls: str) -> dict | None:
    """The thing they looked forward to that this "how it turned out" is about (Fable L7): the
    same class, already happened (`when` not in the future), within 60 days, and sharing most of
    its distinctive words — never one shared word like "new". Otherwise None: kept unpaired."""
    import tools.obligations as O
    toks = O._task_tokens(item) - _GENERIC
    if not toks:
        return None
    rows = _rows(persona)
    done = {r.get("pair") for r in rows if r.get("kind") == "satisfaction_experienced"}
    today = _today()
    since = today - timedelta(days=_MATCH_DAYS)
    for r in reversed(rows):
        if (r.get("kind") != "satisfaction_anticipated" or r.get("pair") in done
                or (_day(r) or since) < since or r.get("class") != cls):
            continue
        try:
            if date.fromisoformat(str(r.get("when") or r.get("day"))[:10]) > today:
                continue
        except ValueError:
            continue
        theirs = O._task_tokens(str(r.get("item") or "")) - _GENERIC
        if theirs and len(toks & theirs) * 2 >= len(theirs):
            return r
    return None


def _lesson(persona: str, cls: str, today: date) -> str:
    h = history(persona).get(cls)
    if not h or h["n"] < int(_n("lesson_pairs", 4)) or not h["consistent"]:
        return ""
    st = _state(persona)
    last = st.get("lesson_on")
    try:
        if last and (today - date.fromisoformat(last)).days < int(_n("lesson_every_days", 30)):
            return ""
    except ValueError:
        pass
    st["lesson_on"] = today.isoformat()
    _save_state(persona, st)
    from tools.ranking_review import append_signals
    now = datetime.now()
    append_signals([{"at": now.isoformat(timespec="seconds"), "day": today.isoformat(),
                     "kind": "satisfaction_lesson", "source": "goal_network", "class": cls,
                     "n": h["n"], "before": h["before"], "after": h["after"]}], persona)
    way = ("turned out better than they expected" if h["gap"] > 0
           else "turned out less than they hoped")
    return (f" LESSON — put this to them once, now, as a question in your own words, kindly, "
            f"never a verdict: their last {h['n']} {_LABEL[cls]} {way} — looked forward to about "
            f"{h['before']}/5, turned out about {h['after']}/5.")


def note_expectation(stage: str, item: str, words: str, score: int | None = None,
                     cls: str = "", when: str = "", pair: str = "", asked: bool = False) -> str:
    """Keep what the user said about looking forward to something (stage before) or how it turned
    out (stage after), with a 1–5 read from their words. Their own words, on their own turn."""
    if not on():
        return "not recorded — this is not switched on yet. Nothing to say about it."
    stage = str(stage or "").strip().lower()
    if stage not in ("before", "after"):
        return "error: `stage` is before or after. Nothing was written."
    try:
        score = int(score)
    except (TypeError, ValueError):
        return "error: `score` is 1–5, read from their words. Nothing was written."
    if not 1 <= score <= 5:
        return "error: `score` is 1–5. Nothing was written."
    text = " ".join(str(words or "").split())[:_TEXT_MAX]
    item = " ".join(str(item or "").split())[:_ITEM_MAX]
    if not text or not item:
        return "error: `item` (what it is, a few words) and `words` (theirs) are required."
    cls = str(cls or "").strip().lower()
    if cls and cls not in CLASSES:
        return f"error: `class` is one of {', '.join(CLASSES)}. Nothing was written."
    try:
        from tools.turn_context import current as _turn
        turn = _turn()
    except Exception:  # noqa: BLE001
        turn = None
    if turn is None or not turn.get("user_turn"):
        return "error: not recorded — only the user's own words, on their own turn."
    persona = resolve_persona(None)
    today = _today()
    now = datetime.now()
    from tools.ranking_review import append_signals
    base = {"at": now.isoformat(timespec="seconds"), "day": today.isoformat(),
            "source": "goal_network", "score": score, "item": item, "text": text,
            "asked": bool(asked)}
    if stage == "before":
        if not cls:
            return "error: `class` is required for stage before. Nothing was written."
        try:
            on_day = date.fromisoformat(str(when).strip()[:10]).isoformat() if when else today.isoformat()
        except ValueError:
            return "error: `when` is YYYY-MM-DD — the day it happens or arrives. Nothing was written."
        pid = f"sx_{uuid.uuid4().hex[:6]}"
        append_signals([{**base, "kind": "satisfaction_anticipated", "pair": pid, "class": cls,
                         "when": on_day}], persona)
        h = history(persona).get(cls)
        tail = ""
        if h and h["n"] >= int(_n("evidence_pairs", 3)):
            tail = (f" For your judgement, not to say: their last {h['n']} {_LABEL[cls]} — looked "
                    f"forward to about {h['before']}/5, turned out about {h['after']}/5.")
        return (f"kept (pair {pid}). Carry on the conversation; don't mention it." + tail
                + _lesson(persona, cls, today))
    hit = None
    if pair:
        hit = next((r for r in _rows(persona) if r.get("kind") == "satisfaction_anticipated"
                    and r.get("pair") == str(pair).strip()), None)
    if not hit and not cls:
        return ("error: `class` is required for stage after (or the `pair` your context gave). "
                "Nothing was written.")
    hit = hit or _match(persona, item, cls)
    append_signals([{**base, "kind": "satisfaction_experienced",
                     "pair": hit.get("pair") if hit else None,
                     "class": (hit or {}).get("class") or cls}], persona)
    return "kept. Carry on the conversation; don't mention it."


NOTE_EXPECTATION_SCHEMA = {
    "name": "note_expectation",
    "description": (
        "Only on a turn whose context carries an ANTICIPATION AND EXPERIENCE block — otherwise "
        "never call it. Keep how much the user looks forward to something (stage before) or how "
        "it turned out (stage after) — a purchase, an outing, a trip, time with people, an "
        "activity, a commitment — when they say it, or when they answer the one question that "
        "block offers. A 1–5 you read from their words, plus their words. Only on their own turn. "
        "Never mention that it was kept. The result may carry their history in that class (for "
        "your judgement) or, rarely, a lesson to put to them once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "stage": {"type": "string", "enum": ["before", "after"]},
            "item": {"type": "string", "description": "What it is, in a few words: 'the jacket', 'Saturday's concert'."},
            "words": {"type": "string", "description": "The user's own words, ≤ 280 characters."},
            "score": {"type": "integer", "description": "1 (dreading / let down) to 5 (can't wait / loved it), read from their words."},
            "cls": {"type": "string", "enum": list(CLASSES), "description": "Required (for after, unless you give the pair id)."},
            "when": {"type": "string", "description": "For before: YYYY-MM-DD it happens or arrives (default today)."},
            "pair": {"type": "string", "description": "For after: the pair id your context gave, if it gave one."},
            "asked": {"type": "boolean", "description": "True when you asked; false when they said it unprompted."},
        },
        "required": ["stage", "item", "words", "score"],
    },
}
