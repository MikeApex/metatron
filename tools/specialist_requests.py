"""
tools/specialist_requests.py — one `FROM THE SPECIALISTS` block (Stage 5 #19 + D7).

Plan: archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md § 1 #19, as
Revisions 1–2 amend it. A specialist's request for a consult (`CONSULT_NEEDED`), a lookup
(`RESEARCH_NEEDED`) or a profile question (`PROFILE_GAP`) used to sit wherever it fell in its
prose — a `FLAGS:` line, a bullet, a JSON string — and was acted on or lost by chance. Code lifts
each one out and puts them in one block at the head of the Synthesizer package, with at most ONE
profile question per turn (several could reach a turn before; the rule is one per session).

THE CLINICAL RULE (binding): code may add MUST_SURFACE / CLINICAL_CONCERN /
MEDICATION_MISSED_CRITICAL, never clear, suppress or move them out of the sign-off veto's view.
So: (1) the pipeline builds the veto's text from the outputs BEFORE `lift()`; (2) a body stops at
every known token, so a clinical token after a lifted flag is never swallowed; (3) a flag whose
body would still hold a clinical token is left exactly where it is.

THE BODY STOPS ONLY AT A KNOWN TOKEN (Revision 2), never at any capitalised word — an acronym
(HMRC, ADHD, NHS) inside a body is body text. `KNOWN_TOKENS` is every flag the agent files
define, the output-section labels, and the clinical tokens; `tests/test_specialist_requests.py`
re-reads the agent files and fails when a new flag is not listed here, so a new flag cannot
silently become body text.

`CLARIFICATION_NEEDED` is not here: Stage 2's M7 owns that signal.

PERSISTENT STATE — the per-persona PROFILE_GAP queue, `persona_data_dir()/specialist_requests.json`
(0600). Unit: a few hundred bytes of local disk per persona; a longer expiry buys only staler
questions. Deleted by its 7-day expiry and cap of 10. A restart leaves it intact and harmless. No
money, so no meter reports it. `lift()` only reads it; `commit_rotation()` writes it, and the
pipeline calls that only once it knows the Synthesizer will run — never on a sign-off skip, a
day-plan nudge, or a turn with no specialist outputs — so a held question is spent only on a reply
that could carry it.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.orchestrator import _SIGNOFF_FLAG_TOKENS
from core.orchestrator import _UNTRUSTED_OUTPUT_AGENTS as _UNTRUSTED_AGENTS
from tools.logistics_log import _is_none
from core.persona import persona_data_dir

logger = logging.getLogger(__name__)

LIFTED = ("CONSULT_NEEDED", "RESEARCH_NEEDED", "PROFILE_GAP")
BLOCK_HEAD = "FROM THE SPECIALISTS (requests, from code):"

# Every flag defined in an agent file's flag list — the bulleted `**NAME**` definitions across
# config/agents/*.md, generated with
#   grep -ohE "^\s*-\s+\*\*[A-Z][A-Z_]{3,}" config/agents/*.md
# The drift-guard test re-runs that grep; add a new flag here in the same change that adds it.
_AGENT_FLAGS = frozenset("""
ARCHITECTURE_GAP BASELINE_INCOMPLETE BEHAVIORAL_PATTERN_CONCERN BLOCK_RECURRING BOUNDARY_PRESSURE
BUDGET_ON_TRACK BUDGET_OVERSPEND BURNOUT_SIGNAL BURNOUT_TRAJECTORY CAREER_CRISIS CAREER_INFLECTION
CASH_DRAG CESSATION_SUPPORT CHAIN_LIMIT_REACHED CLINICAL_CONCERN COGNITIVE_DISTORTION
COMPROMISE_MADE CONFLICT_ACTIVE CONFLICT_AVOIDED CONFLICT_POSSIBLE CONFLICT_RESOLVED
CONSULT_NEEDED CONSUMING_NOT_DOING CONTACT_INCOMPLETE CONTESTED CONTEXT_NEEDED
CONVERSATION_NOTABLE COORDINATION_OPPORTUNITY DEBT_CONCERN DEFLECT_TO_CONTACT DETAIL_MISSING
DRIFT_CHECK EMOTIONAL_GRANULARITY_LOW ENERGY_CRASH ESCALATION EXECUTION_TREE_READY EXERCISE_GAP
EXPENSE_NOTABLE EXPERIENCE_LOGGED EXPERIENCE_WORTH_ARCHIVING EXPLANATORY_STYLE_CONCERN
FAMILY_STRESS FINANCIAL_STRESS FLOW_STATE FOOD_NOT_LOGGED GOAL_AT_RISK GOAL_DRIFT GRIEF_SIGNAL
HABIT_BUILDING HEDONIC_PATTERN HELD HIGH_MOMENTUM HOBBY_LAPSE HORIZON_ITEM IDENTITY_SIGNAL
IDENTITY_TRAP INCOME_EVENT INSIGHT_WORTH_CAPTURING INVESTMENT_SIGNAL ISOLATION_SIGNAL LEARNING_GAP
LEISURE_GAP LEISURE_MISREAD LIFESTYLE_GAP LIVE_DATA_NEEDED MARKET_ALERT MEDIA_FINISHED
MEDICAL_FLAGGED MEDICATION_LINK_BROKEN MEDICATION_MISSED_AS_NEEDED MEDICATION_MISSED_CRITICAL
MEDICATION_MISSED_OPTIONAL MEDICATION_NEEDS_LINK MEETING_PREP MILESTONE_REACHED MISALIGNMENT
NEGOTIATION_OPPORTUNITY NETWORK_GAP NEW_HABIT_EXPENSE NOVELTY_ENGAGED OFFICE_DYNAMICS
OPTIMIZATION_OPPORTUNITY OUTREACH_WINDOW OVERCOMMITMENT OVER_LEISURE PATTERN_ALERT PENDING_AGED
PENDING_CONFIRMATION PLANNED_CONTACT_PENDING POSITIVE_LEISURE POSITIVE_MOMENTUM POSITIVE_PATTERN
PRACTICE_GAP PRACTICE_LAPSE PROFESSIONAL_REVIEW PROFILE_GAP RECIPROCITY_IMBALANCE
RECONNECT_OPPORTUNITY RECOVERY_OPPORTUNITY RECURRING_DUE RECURRING_ITEM RECURRING_THEME
RELATIONSHIP_AT_NATURAL_END RELATIONSHIP_THRIVING RESEARCH_AVAILABLE RESEARCH_NEEDED
RESTORATIVE_MOMENT RETIREMENT_GAP ROUTING_MISS SAVORING_OPPORTUNITY SELF_ESTEEM_SIGNAL
SERVICE_ACTIVE SERVICE_GAP SERVICE_NUDGE_OPPORTUNITY SKILL_BUILDING SLEEP_ACUTE SLEEP_CONCERN
SLEEP_MISSING SLEEP_POOR STRONG_OUTPUT SYMPTOM_RECURRENCE TAX_FLAG TOOL_NOT_BUILT TRAVEL_UPCOMING
TRIGGER_IDENTIFIED VALUES_ALIGNMENT VICE_LOGGED VICTORY_BLINDNESS VOCATION_DRIFT
WITHDRAWAL_CASCADE
""".split())

# The output-section labels specialists write.
_SECTION_LABELS = frozenset({
    "FLAGS", "MUST_SURFACE", "PROACTIVE_OBSERVATIONS", "MEDICATION_TAKEN", "MEDICATION_NEEDS_LINK",
    "MEDICATION_LINK_BROKEN", "WISDOM_PROPOSAL", "HORIZON_ITEMS", "COORDINATION_OPPORTUNITIES",
    "EXECUTION_TREE", "PENDING_CONFIRMATION", "NOTHING_LOGGED", "CAPTURED",
})

# Never lifted, never swallowed. The sign-off veto's own tokens are imported, never restated.
CLINICAL_TOKENS = frozenset(_SIGNOFF_FLAG_TOKENS) | {"MUST_SURFACE", "CLINICAL_CONCERN",
                                                    "MEDICATION_MISSED_CRITICAL", "ESCALATION"}

KNOWN_TOKENS = _AGENT_FLAGS | _SECTION_LABELS | CLINICAL_TOKENS

_FLAG_RE = re.compile(r"(\*\*)?\b(" + "|".join(LIFTED) + r")\b(\*\*)?")
_STOP_RE = re.compile(r"\b(?:" + "|".join(sorted(KNOWN_TOKENS, key=len, reverse=True)) + r")\b")
_CLINICAL_RE = re.compile("|".join(re.escape(t).replace("_", "[_ ]") for t in CLINICAL_TOKENS),
                          re.I)
_LEAD = re.compile(r"[ \t]*(?:\*\*)?[ \t]*[:\-—–]?[ \t]*")
# Flag position (review item 7): what may come before a liftable flag on its line.
_POS_LINE = re.compile(r"^[ \t]*(?:(?:[-*•>]|\d+[.)])[ \t]*)?(?:\*\*)?[ \t]*$")
_POS_FLAGS = re.compile(r"^[ \t]*(?:(?:[-*•]|\d+[.)])[ \t]*)?(?:\*\*)?FLAGS(?:\*\*)?[ \t]*:[ \t]*"
                        r"(?:\*\*)?(?:.*[,;][ \t]*(?:\*\*)?)?$")
_POS_JSON = re.compile(r'(?:^[ \t]*|[\[,][ \t]*)"$')
_BULLET = re.compile(r"^[ \t]*(?:[-*•]|\d+[.)])[ \t]+")
_CONTINUATION = re.compile(r"^[ \t]+(?![-*•][ \t]|\d+[.)][ \t])\S")
# A section header: an upper-case label and a colon at a line start, no bullet.
_HEADER = re.compile(r"^[ \t]*(?:\*\*)?[A-Z][A-Z_]{3,}(?:\*\*)?[ \t]*:")
_MARK = "\x00"

_EXPIRY = timedelta(days=7)
_CAP = 10
_FILE = "specialist_requests.json"


def _now() -> datetime:
    return datetime.now()


@dataclass
class Lift:
    outputs: dict
    block: str = ""
    pick: dict | None = None            # the one PROFILE_GAP this turn, {agent, text, queued?}
    losers: list = field(default_factory=list)   # the queue as it should stand after this turn
    lifted: int = 0
    requests: list = field(default_factory=list)  # the consult and lookup lines

    def text(self, with_gap: bool = True) -> str:
        """The block; without the profile question on a turn that must raise nothing new."""
        lines = list(self.requests)
        if with_gap and self.pick:
            held = " (held from an earlier turn)" if self.pick.get("held") else ""
            lines.append(f"- {self.pick['agent']}: PROFILE_GAP{held}: {self.pick['text']}")
        return (BLOCK_HEAD + "\n" + "\n".join(lines)) if lines else ""


def _find(text: str) -> list[tuple[int, int, str, str]]:
    """(start, end, token, body) for each liftable flag, in order. `end` is where the removal
    span ends; the body is cleaned.

    Lifted only from FLAG POSITION (review item 7): at a line start after markup or a bullet,
    as an item of a `FLAGS:` list, as a JSON list item, or straight after a flag just lifted —
    never from prose ("No CONSULT_NEEDED this turn"). Left exactly where it is: a flag on a
    line, or under a section, that holds a clinical token anywhere (review item 1 — the clinical
    rule); a bare token with no body."""
    found: list[tuple[int, int, str, str]] = []
    for m in _FLAG_RE.finditer(text):
        start, tok = m.start(), m.group(2)
        if found and start < found[-1][1]:
            continue
        line_start = text.rfind("\n", 0, start) + 1
        prefix = text[line_start:start]
        after_lift = bool(found) and start == found[-1][1]
        if not (after_lift or _POS_LINE.match(prefix) or _POS_FLAGS.match(prefix)
                or _POS_JSON.search(prefix)):
            continue
        in_string = len(re.findall(r'(?<!\\)"', prefix)) % 2 == 1
        b0 = _LEAD.match(text, m.end()).end()
        line_end = text.find("\n", b0)
        line_end = len(text) if line_end == -1 else line_end
        stop = line_end
        if in_string:
            q = text.find('"', b0)
            while q != -1 and q < line_end and text[q - 1] == "\\":
                q = text.find('"', q + 1)
            if q != -1 and q < line_end:
                stop = q
        # A known token cuts the body only in flag position — followed by ":" or at a list
        # separator. "… SLEEP_POOR three nights running" is a mention, and stays in the body.
        for k in _STOP_RE.finditer(text, b0, stop):
            before = text[b0:k.start()]
            if (re.match(r"(?:\*\*)?[ \t]*:", text[k.end():])
                    or re.search(r"[,;][ \t]*(?:\*\*)?$", before)):
                stop = k.start()
                break
        # An indented continuation line belongs to the body it continues — only when it is
        # indented DEEPER than the flag's own line; a sibling at the same depth is not part of
        # it (review round 3, item 5).
        end_line = line_end
        own_indent = _indent(text[line_start:line_end])
        if stop == line_end and not in_string:
            while end_line < len(text):
                nxt_end = text.find("\n", end_line + 1)
                nxt_end = len(text) if nxt_end == -1 else nxt_end
                nxt = text[end_line + 1:nxt_end]
                if (not _CONTINUATION.match(nxt) or _STOP_RE.match(nxt.strip())
                        or _indent(nxt) <= own_indent):
                    break
                end_line = nxt_end
            stop = end_line
        whole = text[line_start:max(stop, line_end)]
        if _CLINICAL_RE.search(whole) or _under_clinical(text, line_start):
            continue
        body = re.sub(r"\s*\n\s*", " ", text[b0:stop])
        clean = body.strip().strip("*").strip().rstrip(",;").strip()
        if not clean:
            continue        # a bare token carries no request; left where it is
        found.append((start, stop, tok, clean))
    return found


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _under_clinical(text: str, line_start: int) -> bool:
    """Is this line inside a section headed by a clinical token? Then it is part of that section
    and is never moved out of it. Walking up to a blank line or a section header:
      - a BARE clinical header ("MUST_SURFACE:") holds every line under it, whatever its
        indentation or bullet (review round 3, item 6);
      - a clinical header with its own text holds the bullets and continuations under it;
      - any other header ends the section; a clinical body line on the way means inside one."""
    line_end = text.find("\n", line_start)
    line = text[line_start:line_end if line_end != -1 else len(text)]
    is_item = bool(_BULLET.match(line) or _CONTINUATION.match(line))
    pos = line_start
    while pos > 0:
        prev_start = text.rfind("\n", 0, pos - 1) + 1
        prev = text[prev_start:pos - 1]
        if not prev.strip():
            return False
        head = _HEADER.match(prev)
        if head:
            if not _CLINICAL_RE.search(prev):
                return False
            bare = not prev[head.end():].strip(" \t*")
            return bare or is_item
        if _CLINICAL_RE.search(prev):
            return True
        pos = prev_start
    return False


def _strip(text: str, spans: list[tuple[int, int, str, str]]) -> str:
    """Remove the lifted spans and tidy the separators they leave. A removed span becomes a
    marker first, so tidying touches only what was lifted."""
    out, pos = [], 0
    for start, end, _tok, _body in spans:
        out.append(text[pos:start])
        out.append(_MARK)
        pos = end
    out.append(text[pos:])
    s = "".join(out)
    # Separators: "x, \0, y" / "\0, y" / "x, \0"
    s = re.sub(_MARK + r"[ \t]*[,;][ \t]*", _MARK, s)
    s = re.sub(r"[,;][ \t]*" + _MARK + r"(?=[ \t]*(?:\n|$|\"))", _MARK, s)
    # A JSON string emptied by the lift: drop the element with one adjacent comma.
    s = re.sub(r'"' + _MARK + r'+"\s*,\s*', "", s)
    s = re.sub(r',\s*"' + _MARK + r'+"', "", s)
    s = re.sub(r'"' + _MARK + r'+"', "", s)
    lines = []
    for line in s.split("\n"):
        if _MARK in line:
            rest = line.replace(_MARK, "")
            # A line the lift emptied (a bare bullet, an empty FLAGS: label) goes.
            if re.fullmatch(r"\s*(?:[-*•]\s*)?(?:\*\*)?(?:FLAGS)?(?:\*\*)?\s*:?\s*", rest):
                continue
            line = re.sub(r"[ \t]+$", "", rest)
        lines.append(line)
    return "\n".join(lines)


# --- the PROFILE_GAP queue ---------------------------------------------------------------------

def _path(persona: str | None):
    return persona_data_dir(persona) / _FILE


def _read(persona: str | None) -> dict:
    try:
        p = _path(persona)
        if not p.exists():
            return {"queue": [], "last_won": {}}
        data = json.loads(p.read_text())
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except Exception as exc:  # noqa: BLE001 — a held question is never worth a failed turn
        logger.warning(f"[specialist_requests] queue unreadable: {type(exc).__name__}")
        return {"queue": [], "last_won": {}}
    data.setdefault("queue", [])
    data.setdefault("last_won", {})
    return data


def _live(queue: list, now: datetime) -> list:
    keep = []
    for e in queue:
        try:
            if now - datetime.fromisoformat(e["queued"]) <= _EXPIRY and e.get("agent"):
                keep.append(e)
        except Exception:  # noqa: BLE001
            continue
    return sorted(keep, key=lambda e: e["queued"])


def _rotate(fresh: list[tuple[str, str]], persona: str | None) -> tuple[dict | None, list]:
    """The one gap this turn, and the queue as it should stand. Read-only."""
    now = _now()
    st = _read(persona)
    queue = _live(st.get("queue") or [], now)
    last_won = st.get("last_won") or {}
    new: list[tuple[str, str]] = []
    for agent, text in fresh:
        held = next((e for e in queue if e["agent"] == agent), None)
        if held:
            held["text"] = text        # a newer text replaces its entry; its place is kept
        else:
            new.append((agent, text))
    pick = None
    if queue:
        pick = dict(queue.pop(0), held=True)          # the oldest held question wins
    elif new:
        order = {a: i for i, (a, _t) in enumerate(new)}
        # The agent that won least recently; one that never won is least recent of all.
        agent, text = min(new, key=lambda f: (last_won.get(f[0], ""), order[f[0]]))
        pick = {"agent": agent, "text": text}
        new = [f for f in new if f[0] != agent]
    stamp = now.isoformat(timespec="seconds")
    queue += [{"agent": a, "text": t, "queued": stamp} for a, t in new]
    queue = sorted(queue, key=lambda e: e["queued"])[-_CAP:]
    return pick, queue


def commit_rotation(persona: str | None, pick: dict | None, losers: list,
                    spent: bool = True) -> None:
    """Write the queue after a turn the Synthesizer runs. Logged, never raised: on a write
    failure the turn still had its one gap; the losers are simply not held.

    `spent=False` — a sign-off-note turn, which raises nothing new (review round 3, item 7):
    the pick was not put to the user, so it goes back in the queue (a held one keeps its place,
    a fresh one is queued now) and no win is recorded. Nothing is lost."""
    if pick is None and not losers and not _path(persona).exists():
        return
    if not spent and pick:
        back = {"agent": pick["agent"], "text": pick["text"],
                "queued": pick.get("queued") or _now().isoformat(timespec="seconds")}
        losers = sorted([e for e in losers if e["agent"] != pick["agent"]] + [back],
                        key=lambda e: e["queued"])[-_CAP:]
    try:
        st = _read(persona)
        last_won = dict(st.get("last_won") or {})
        if pick and spent:
            last_won[pick["agent"]] = _now().isoformat(timespec="seconds")
        data = {"queue": [{"agent": e["agent"], "text": e["text"], "queued": e["queued"]}
                          for e in losers][-_CAP:],
                "last_won": last_won}
        p = _path(persona)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1))
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[specialist_requests] queue not written: {type(exc).__name__}")


# --- the lift ----------------------------------------------------------------------------------

def lift(outputs: dict, persona: str | None = None) -> Lift:
    """Lift each specialist's CONSULT_NEEDED, RESEARCH_NEEDED and PROFILE_GAP out of its output
    and build the one block. Reads the PROFILE_GAP queue; writes nothing (see commit_rotation)."""
    if not outputs:
        return Lift(outputs=outputs)
    cleaned: dict = {}
    requests: list[str] = []
    gaps: list[tuple[str, str]] = []
    n = 0
    for agent, text in outputs.items():
        if not isinstance(text, str) or "dispatched (async)" in text or not _FLAG_RE.search(text):
            cleaned[agent] = text
            continue
        spans = _find(text)
        if agent in _UNTRUSTED_AGENTS:
            # Research reads the web: its output is untrusted, so it never puts a question to the
            # user or into the held queue (review item 9). Its consult and lookup requests are
            # lifted for this turn only — they are acted on only if the Synthesizer chooses.
            spans = [sp for sp in spans if sp[2] != "PROFILE_GAP"]
        if not spans:
            cleaned[agent] = text
            continue
        n += len(spans)
        cleaned[agent] = _strip(text, spans)
        for _s, _e, tok, body in spans:
            if _is_none(body.strip(" \"'")):
                continue        # "none at this time", "n/a": removed, never a request
            if tok == "PROFILE_GAP":
                gaps = [g for g in gaps if g[0] != agent] + [(agent, body)]
            else:
                requests.append(f"- {agent}: {tok}: {body}")
    pick, losers = _rotate(gaps, persona)
    lift_ = Lift(outputs=cleaned, pick=pick, losers=losers, lifted=n, requests=requests)
    lift_.block = lift_.text(with_gap=True)
    return lift_
