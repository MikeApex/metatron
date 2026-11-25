"""
tools/goal_claims.py — what a user-facing reply may say about their goals, checked by code.

Built 2026-11-25 from `mike`'s goals walkthrough (goal network plan § 19). Three things a user saw:

1. **"I have corrected the standing records: purposeful exercise and heavy lifting are on hold"**
   — and neither goal was on hold, twice (seqs 032, 037). The log-only check
   (`check_false_action_claims`) let both through, because SOME write happened in each turn (a
   fitness note, the Coordinator's quality event, an unrelated task). So a hold or completion claim
   about a goal is checked against **that goal's actual state** — is it on hold (parked, or taken on
   with a later start), was it until today, is it completed — and a claim the state contradicts is
   REPLACED (Mike's ruling 4: false action claims are "unacceptable", `[DB-0815-11]`). Only the
   false sentence: the rest of the reply — the true Prudential line, the next question — is kept.
   *State, not "did this turn change it" (Fable review S2/S3/S6):* a true recap the turn after
   ("Bulgarian has been parked until January, as we agreed"), the day a hold ends ("exercise has
   been on hold until today"), and a note written while the goal stayed current all read correctly.
2. **"We have talked it out fully… the weekly load is settled"** (seq 026) about a goal whose
   weekly time was never the user's. A "settled" claim about a large goal with fields still open is
   replaced by what is open — only when the sentence names that goal, or is about talking it
   through within a few hours of the talk (S5: "the dinner plan is all settled" is left alone).
3. **Internal ids**: "(Q5)", "goal q6: File…", a raw task id. Removed, or replaced by the task's
   title — only the user's real goal ids, only in a reference shape next to that goal's own words.

Precision over recall, as everywhere replies are touched (Fable S1): a sentence is checked only
when it NAMES a goal and is not about a task, reminder, routine, session or log; a question or an
offer is never a claim; a completion claim needs the word "goal"; one named goal that is held makes
the sentence true. Every replacement is logged with its sentence (`FALSE_GOAL_CLAIM`) — a wrong one
is only visible there, and Stage 1's first weekly review reads it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- reading the goals -------------------------------------------------------------------------


def _goals(persona: str | None) -> dict[str, dict]:
    from core.persona import persona_scope, resolve_persona
    from tools.goals import HORIZONS, read_goals
    with persona_scope(resolve_persona(persona)):
        data = read_goals() or {}
    out: dict[str, dict] = {}
    for h in HORIZONS:
        for g in data.get(h) or []:
            if isinstance(g, dict) and g.get("id"):
                out[str(g["id"])] = g
    return out


def _digest(g: dict) -> str:
    body = {k: v for k, v in g.items() if k not in ("revisit_raised", "start_said")}
    return hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def snapshot(persona: str | None = None) -> dict[str, str] | None:
    """Each goal's digest at the start of a turn; None when unreadable (then nothing is checked).
    Since the Fable review the claim check reads goal STATE; the snapshot only decides whether a
    vaguer "I've updated your goal" is logged."""
    try:
        return {gid: _digest(g) for gid, g in _goals(persona).items()}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[goal_claims] snapshot failed: {type(exc).__name__}")
        return None


# --- sentences ---------------------------------------------------------------------------------

# Not a sentence end: "Jan. 15", "e.g. this", "Dr. Lee", "No. 4" (Fable L5); "9.30" is kept whole by
# the digit-after test, and "…at 9.30." still ends its sentence (verify N2).
_ABBREV_RE = re.compile(
    r"(?:\b(?:jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|mon|tue|tues|wed|thu|thur|thurs|"
    r"fri|sat|sun|mr|mrs|ms|dr|st|vs|etc|no|approx|e\.g|i\.e))\.$", re.IGNORECASE)


def _sentences(text: str) -> list[tuple[int, int]]:
    """(start, end) spans of sentences — split at . ! ? and newlines, not after an abbreviation or
    inside a number; closing quotes and brackets stay with their sentence."""
    spans, start, i, n = [], 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            if i > start:
                spans.append((start, i))
            start = i + 1
        elif ch in ".!?":
            j = i + 1
            while j < n and text[j] in ".!?\"'”’)*_":
                j += 1
            if ch == "." and (_ABBREV_RE.search(text[max(start, i - 6):i + 1])
                              or (j < n and text[j].isdigit())):
                i += 1
                continue
            if j >= n or text[j] in " \t\n":
                spans.append((start, j))
                start = j
                i = j
                continue
        i += 1
    if start < n:
        spans.append((start, n))
    return [(a, b) for a, b in spans if text[a:b].strip()]


_HOLD_RE = re.compile(
    r"\bon hold\b|\bparked\b|\bpaused\b|\bdeferred\b|\bshelved\b|\bon ice\b"
    r"|\b(?:set|put)\s+(?:\w+\s+){0,2}aside\b", re.IGNORECASE)
_COMPLETE_RE = re.compile(r"\bmarked\b[^.?!]{0,40}\b(?:complete|completed|done|finished)\b"
                          r"|\bcompleted\b", re.IGNORECASE)
_GOAL_WORD_RE = re.compile(r"\bgoals?\b|\bstanding records?\b", re.IGNORECASE)
_UPDATED_RE = re.compile(r"\b(?:updated|changed|revised|corrected)\b[^.?!]{0,50}\bgoals?\b",
                         re.IGNORECASE)
# The object is something other than a goal: "paused the exercise reminders", "marked the workout
# done", "deferred the boiler task" (Fable S1).
_NOT_GOAL_OBJ_RE = re.compile(
    r"\b(?:tasks?|reminders?|routines?|sessions?|workouts?|calls?|appointments?|"
    r"planning|plans?|logs?|notifications?|nudges?|flights?|meetings?|events?|bookings?|"
    r"check-?ins?|lessons?|classes|class|subscriptions?|orders?|deliver(?:y|ies)|payments?|"
    r"podcasts?|episodes?|videos?|books?|purchases?|refunds?|thoughts?|questions?|conversations?|"
    r"chats?|ideas?|items?|timers?|music|playlists?|memberships?|emails?|drafts?|messages?)\b",
    re.IGNORECASE)
_SETTLED_TALK_RE = re.compile(
    r"\btalked\s+(?:\w+\s+){0,3}?(?:out|through)\s+(?:fully|properly|completely|enough|in full)\b"
    r"|\bwon'?t\s+need\s+to\s+re-?litigate\b", re.IGNORECASE)
_SETTLED_ANY_RE = re.compile(
    r"\beverything\b[^.?!]{0,50}\b(?:is|are)\s+(?:now\s+)?(?:settled|agreed|on record|decided)\b"
    r"|\b(?:all|fully)\s+settled\b"
    r"|\bnothing\s+(?:left|more|else)\s+to\s+(?:settle|decide|agree)\b", re.IGNORECASE)
_NOT_A_CLAIM_RE = re.compile(
    r"^\W*(?:shall|should|can|could|would|will)\s+(?:I|we)\b|^\W*(?:do|would)\s+you\b|^\W*if\b"
    r"|\b(?:shall|should|can|could)\s+I\b|\bwould you like\b", re.IGNORECASE)
# A clause that denies the change ("I have not put it on hold") or reports the USER's own action
# or words ("you told me you've paused the taxes") claims nothing on Metatron's part.
_NOT_MINE_RE = re.compile(
    r"\b(?:not|never)\b|n[’']t\b|\byou(?:'ve|’ve| have| had| said| told| mentioned| wanted| asked| could)\b"
    r"|\b(?:could|might|may|would|should|can|if|when|whenever|usually|often|many|most people|says?|"
    r"said|told)\b", re.IGNORECASE)
# The claim is Metatron's own, made now (verify N1): "I've put…", "I have corrected…", "we've
# parked…", "I'm putting…". A third party's news, advice, history or a hypothetical is not one.
_MINE_RE = re.compile(
    r"\b(?:I|we)(?:'ve|’ve| have)\b|\bI(?:'m|’m| am)\s+(?:putting|parking|pausing|marking|moving|"
    r"setting)\b|\b(?:I|we)\s+(?:put|parked|paused|marked|moved|set|deferred|shelved)\b",
    re.IGNORECASE)
# The claim is about the past ("has been on hold until today") — true on the day a hold ends.
_PAST_HOLD_RE = re.compile(r"\b(?:has|have|had)\s+been\b|\bwas\b|\bwere\b|\buntil (?:today|now)\b",
                           re.IGNORECASE)
_ID_RE = r"[qwdlQWDL]\d{1,3}"
_CLAUSE_RE = re.compile(r"\s*[,;:—–]\s+|\s+(?:and|but)\s+(?=(?:I|we|put|parked|paused|moved|marked|"
                        r"set|closed|updated|corrected)\b)")
_TALK_RECENT = timedelta(hours=3)


def _named(clause: str, goals: dict[str, dict]) -> set[str]:
    """Goals a clause names — by id, or by a word of the title. A practice is dropped when its goal
    is named too ("Bulgarian" names the language goal, not also its vocabulary habit — L5)."""
    from tools.obligations import _task_tokens
    ids = {m.lower() for m in re.findall(rf"\b({_ID_RE})\b", clause)}
    toks = _task_tokens(clause)
    out = {gid for gid, g in goals.items()
           if gid.lower() in ids or (_task_tokens(str(g.get("title") or "")) & toks)}
    return {gid for gid in out if str(goals[gid].get("parent_goal") or "") not in out}


def _held(g: dict, past: bool = False) -> bool:
    """On hold now (parked, or taken on with a start still ahead) — or, for a claim about the past
    ("has been on hold until today"), a hold that ended in the last two days (verify N3: a start
    date months gone, or one just lifted, never makes a new "on hold" true)."""
    from tools.goals import _today, not_started
    if str(g.get("status") or "") == "parked" or not_started(g):
        return True
    if not past:
        return False
    today = _today()
    for k in ("starts_on", "revisit_on", "revisit_raised"):
        try:
            d = datetime.strptime(str(g.get(k) or "")[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if timedelta(0) <= today - d <= timedelta(days=2):
            return True
    return False


def _quote(goals: dict[str, dict], gids) -> str:
    names = [f"\"{str(goals[g].get('title') or g).strip()}\"" for g in sorted(gids) if g in goals]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _recent_talk_goal(persona: str | None) -> str | None:
    """The goal of the talk in progress, or of one that ended within `_TALK_RECENT` (Fable S5: a
    talk parked weeks ago is not what "everything is settled" is about)."""
    try:
        from core.persona import resolve_persona
        from tools.goal_talk import _now, _read
        st = _read(resolve_persona(persona))
        talk = st.get("talk")
        if isinstance(talk, dict) and talk.get("goal_id") and talk.get("status") in ("active", "paused"):
            return str(talk["goal_id"])
        past = (st.get("past") or [])[-1:]
        if past and past[0].get("goal_id") and past[0].get("ended_at"):
            if _now() - datetime.fromisoformat(str(past[0]["ended_at"])) <= _TALK_RECENT:
                return str(past[0]["goal_id"])
    except Exception:  # noqa: BLE001
        pass
    return None


def _log(agent: str, kind: str, sentence: str, event: str = "FALSE_GOAL_CLAIM") -> None:
    try:
        from tools.logger import write_quality_event
        write_quality_event(event, agent, f"{kind}: {sentence.strip()[:300]}")
    except Exception:  # noqa: BLE001
        pass
    logger.warning(f"[goal_claims] {kind}: {sentence.strip()[:120]}")


def _wrap(raw: str, line: str) -> str:
    """The replacement keeps the sentence's leading space, bullet and bold markers (L5)."""
    m = re.match(r"^(\s*(?:[-*+>]\s+|#+\s+|\d+\.\s+)?)((?:\*\*|__)?)", raw)
    lead, mark = (m.group(1), m.group(2)) if m else ("", "")
    tail = re.search(r"(\s*)$", raw).group(1)
    return f"{lead}{mark}{line}{mark}{tail}"


_YOURS = {"where they are now": "where you are with it now",
          "minutes a week": "the minutes a week you'll give it",
          "what it takes that time from": "what that time comes from",
          "where it ranks": "where it ranks against the rest"}


def fix_claims(text: str, goals: dict[str, dict], changed: set[str] | None = None,
               persona: str | None = None, agent: str = "synthesizer") -> str:
    """Replace each sentence whose claim about a named goal its state contradicts: on hold when it
    is not, completed when it is not; or "settled" about a large goal with fields still open."""
    from tools.goal_talk import open_fields
    if not text:
        return text
    out: list[str] = []
    said: set[str] = set()
    pos = 0
    for a, b in _sentences(text):
        out.append(text[pos:a])
        pos = b
        raw = text[a:b]
        core = raw.strip()
        if core.endswith("?") or _NOT_A_CLAIM_RE.search(core):
            out.append(raw)
            continue
        replaced = None
        hold_named: set[str] = set()
        done_named: set[str] = set()
        mine = bool(_MINE_RE.search(core))
        for clause in _CLAUSE_RE.split(core) if mine else []:
            if _NOT_GOAL_OBJ_RE.search(clause) or _NOT_MINE_RE.search(clause):
                continue
            if _HOLD_RE.search(clause):
                hold_named |= _named(clause, goals)
            elif _COMPLETE_RE.search(clause) and _GOAL_WORD_RE.search(clause):
                done_named |= _named(clause, goals)
        past = bool(_PAST_HOLD_RE.search(core))
        if hold_named and not any(_held(goals[g], past) for g in hold_named):
            key = "hold:" + ",".join(sorted(hold_named))
            replaced = "" if key in said else _wrap(
                raw, f"I haven't actually put {_quote(goals, hold_named)} on hold on your goals "
                     f"yet — shall I do that now?")
            said.add(key)
            _log(agent, "on hold, but not", core)
        elif done_named and not any(str(goals[g].get("status") or "") == "completed"
                                    for g in done_named):
            key = "done:" + ",".join(sorted(done_named))
            replaced = "" if key in said else _wrap(
                raw, f"I haven't actually marked {_quote(goals, done_named)} complete on your "
                     f"goals yet — shall I?")
            said.add(key)
            _log(agent, "completed, but not", core)
        elif _SETTLED_TALK_RE.search(core) or _SETTLED_ANY_RE.search(core):
            named = [g for g in _named(core, goals) if str(goals[g].get("size") or "").upper() == "L"]
            gid = named[0] if named else (
                _recent_talk_goal(persona)
                if (_SETTLED_TALK_RE.search(core) or _GOAL_WORD_RE.search(core)) else None)
            g = goals.get(gid or "")
            still = open_fields(g) if g and str(g.get("size") or "").upper() == "L" else []
            if still:
                key = f"settled:{gid}"
                replaced = "" if key in said else _wrap(
                    raw, f"Not quite — still open on {_quote(goals, [gid])}: "
                         f"{', '.join(_YOURS.get(x, x) for x in still)}.")
                said.add(key)
                _log(agent, "settled, but not", core)
        elif (changed is not None and _UPDATED_RE.search(core) and not changed
              and re.search(r"\b(?:I|we)(?:'ve|’ve| have)\b", core)):
            # "I've updated your goal" with no goal changed this turn: logged, never replaced —
            # what an update changed cannot be read back from state.
            _log(agent, "updated, nothing changed", core, event="FALSE_ACTION_CLAIM")
        out.append(raw if replaced is None else replaced)
    out.append(text[pos:])
    result = "".join(out)
    return re.sub(r"\n{3,}", "\n\n", result) if result != text else result


# --- internal ids ------------------------------------------------------------------------------

_TASK_ID = r"ob_\d{6}_[0-9a-f]{6}"


def strip_ids(text: str, goals: dict[str, dict], persona: str | None = None) -> str:
    """Goal codes and task ids out of a reply (11-25 #7). A goal code only in a reference shape —
    "(Q5)", "(goal q5)", "(W4, W5)", "(Q2: …", "goal q6: File…" — and only next to that goal's
    own words, so "first language (L1)" or "Week 4 (W4)" survive unless the goal is the subject
    (Fable L6). Task ids: in brackets removed, in prose replaced by the task's title. Nothing else in
    the reply is touched — no whitespace is collapsed."""
    if not text:
        return text
    from tools.obligations import _task_tokens
    by_id = {g.lower(): v for g, v in goals.items()}
    titles: dict[str, str] = {}
    if re.search(_TASK_ID, text):
        try:
            from core.persona import persona_scope, resolve_persona
            from tools.obligations import _load
            with persona_scope(resolve_persona(persona)):
                titles = {str(t.get("id")): str(t.get("what") or "") for t in _load(None)}
        except Exception:  # noqa: BLE001
            titles = {}

    def about(ids: list[str], near: str, need: int = 1) -> bool:
        """Every id is the user's, and the words around it name that goal — `need` of its title
        words (or all of them, for a one-word title)."""
        toks = _task_tokens(near)

        def names(i: str) -> bool:
            tt = _task_tokens(str(by_id[i.lower()].get("title") or ""))
            return len(tt & toks) >= min(need, len(tt) or 1)
        return bool(ids) and all(i.lower() in by_id and names(i) for i in ids)

    out = re.sub(rf"\s*\(\s*`?{_TASK_ID}`?\s*\)", "", text)
    out = re.sub(rf"`?\b({_TASK_ID})\b`?",
                 lambda m: (f"\"{titles[m.group(1)]}\"" if titles.get(m.group(1)) else "that task"),
                 out)

    def paren(m: re.Match) -> str:
        ids = re.findall(_ID_RE, m.group(0))
        before = m.string[max(0, m.start() - 80):m.start()]
        if len(ids) > 1:
            # "(W4/W5)" — a group of the user's own goal ids is a reference: it goes when one of
            # them is named beside it (11-25 seq 031: "exercise and lifting sessions (W4/W5)").
            return "" if (all(i.lower() in by_id for i in ids)
                          and any(about([i], before) for i in ids)) else m.group(0)
        if about(ids, before):
            return ""
        # "purposeful exercise (W4) and heavy lifting (W5)": a lone code beside another of the
        # user's goal codes in the same sentence is a reference too (verify N4).
        lo, hi = m.string.rfind(".", 0, m.start()) + 1, m.string.find(".", m.end())
        sent = m.string[lo:hi if hi >= 0 else len(m.string)]
        others = [x for x in re.findall(rf"\(\s*(?:goals?\s+)?({_ID_RE})\s*\)", sent)
                  if x.lower() != ids[0].lower() and x.lower() in by_id]
        return "" if (ids[0].lower() in by_id and others) else m.group(0)

    out = re.sub(rf"\s*\(\s*(?:goals?\s+)?{_ID_RE}(?:\s*[/,&]\s*{_ID_RE})*\s*\)", paren, out)

    def paren_colon(m: re.Match) -> str:
        after = m.string[m.end():m.end() + 80]
        return "(" if about([m.group(1)], after) else m.group(0)

    out = re.sub(rf"\(\s*({_ID_RE})\s*:\s*", paren_colon, out)

    def goal_colon(m: re.Match) -> str:
        # "goal q6: Complete Prudential…" — the title follows, so the code goes; "For goal q4:
        # speak daily." shares one word with the title and is left (Fable L6).
        after = m.string[m.end():m.end() + 80]
        return "" if about([m.group(1)], after, need=2) else m.group(0)

    out = re.sub(rf"\bgoal\s+({_ID_RE})\s*:\s*", goal_colon, out, flags=re.IGNORECASE)
    return out


# --- the two hooks the pipeline calls ----------------------------------------------------------


def amend(text: str, before: dict[str, str] | None, persona: str | None = None,
          agent: str = "synthesizer") -> str:
    """After the confidentiality filter and the pending-receipt check, on a reply that reached
    the user: false goal claims replaced, internal ids out. Never raises (except PersonaError);
    anything unreadable leaves the reply exactly as it was."""
    if not text or before is None:
        return text
    try:
        goals = _goals(persona)
    except Exception as exc:  # noqa: BLE001
        from core.persona import PersonaError
        if isinstance(exc, PersonaError):
            raise
        return text
    if not goals:
        return text
    try:
        changed = {gid for gid in set(before) | set(goals)
                   if before.get(gid) != (_digest(goals[gid]) if gid in goals else None)}
        out = fix_claims(text, goals, changed, persona, agent)
        return strip_ids(out, goals, persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[goal_claims] amend failed: {type(exc).__name__}: {exc}")
        return text


_GOAL_TOOLS = frozenset({"update_goal", "read_goals", "write_goals"})


def after_reply(visible: str, persona: str | None = None,
                tool_names: set[str] | None = None) -> None:
    """A delivered reply: goals it put to the user from "Back on the list today" / "Back from
    today" are stamped asked (once, ruling 1); and a goal turn asking several questions at once is
    counted (ruling 6 — measured, never rewritten: which question to keep is a judgement). Counted
    only when a goal tool ran — a turn that read goals from the prompt alone is missed (accepted)."""
    try:
        from core.persona import persona_scope, resolve_persona
        from tools.goals import raised_in
        with persona_scope(resolve_persona(persona)):
            raised_in(visible, persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[goal_claims] raised stamp failed: {type(exc).__name__}")
    try:
        if tool_names and (_GOAL_TOOLS & set(tool_names)):
            n = sum(1 for a, b in _sentences(visible or "") if visible[a:b].strip().endswith("?"))
            if n >= 2:
                from tools.logger import write_quality_event
                write_quality_event("GOAL_TURN_MULTI_QUESTION", "synthesizer",
                                    f"{n} questions in one goal turn")
    except Exception:  # noqa: BLE001
        pass
