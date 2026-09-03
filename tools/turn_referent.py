"""
tools/turn_referent.py — what the previous turn actually did, for a turn that points at it.

[DB-0826-01] A short referring turn — "undo that merge", "approved", "now set it back to
Iva", "cancel my previous request" — resolves against the wrong thing. Five live instances
between 2026-08-10 and 2026-08-29.

THE CAUSE, measured 2026-09-03 and not what the item assumed. The Coordinator is never
given the conversation. Both live call sites in core/orchestrator.py invoke
`_run_single_agent("coordinator", ...)` with no `history=` argument; only the Synthesizer
receives the last ten turns. Everything the Coordinator knows about the recent past arrives
through `load_recent_context()` — ambient facts, open threads, five days of day-logs — none
of which contains a conversational turn. So "undo that merge" was matched against the only
merge-shaped thing in scope, which on 2026-08-26 was a Prudential Apex *branch* merge in the
day logs. coordinator.md:129 tells the model to notice "a pronoun without a clear referent";
it was being asked to do that in a context holding no referents at all. The rule was
unfollowable, not ignored — and `tests/run_coord_model_probe.py` could not see this, because
it has always supplied `history` and therefore always measured an easier condition than
production. Probe, `gemini-3.5-flash-lite`, 4 cases x 3: 3/12 resolved without history,
10/12 with.

WHY A BLOCK AND NOT ONLY THE TRANSCRIPT. Passing history is the larger half of the fix and
is done separately, in the orchestrator. It is not sufficient. On 2026-08-29 the assistant's
own text said the email to Iva was sent; it was pending, and the user then declined it. A
transcript replays that claim as fact — it is the record of what was *said*. This block is
the record of what *happened*: the tools that actually ran, on which objects, and whether
the action completed, failed, is still waiting on the user, or was refused. Where the two
disagree, this one is right, and it is the disagreement that produced the fifth instance.

FAIL OPEN, and this is the opposite of tools/turn_context.py's fail-closed rule — the two
are easy to confuse. That module gates whether a refused action may be re-proposed, where
being wrong re-opens a loop the user already escaped. This one only adds evidence to a
prompt. Absent, unreadable or stale evidence must leave the Coordinator exactly where it is
today, never raise: a missing trace file is not a reason to fail a user's turn. Every reader
below returns empty on any error, and load_recent_context's plugin loop catches whatever
still escapes.

Sensitive-tier, persona-scoped. It reaches the same agent that already receives the day
logs and open threads through the same function, so no new data boundary is crossed.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from core.actions import is_action
from core.persona import persona_data_dir

logger = logging.getLogger(__name__)

# How far back a short referring turn may reach. A pronoun points at the exchange the user
# is still in; "undo that" three hours later is a different conversation and offering it a
# stale referent would invent the failure this exists to prevent. The block also states the
# age in words for anything not immediate, so the model can discount it rather than having
# to trust the window. Most turns of a quiet day therefore carry no block and cost nothing.
_WINDOW = timedelta(hours=2)

# Days of trace files to consider. Two, not one: a turn just after midnight refers to one
# just before it, and the files are named by date.
_LOOKBACK_DAYS = 2

# Which tools count is core/actions.py's question, not this module's. It holds the explicit
# ACTION_TOOLS/READ_TOOLS classification that tests/test_action_provenance.py keeps
# exhaustive, and an unknown tool there is already treated as an action rather than dropped
# — the same direction this block needs. Re-deriving it from name prefixes here would give
# the user two different answers to "what ran last turn": this block and the ACTIONS line
# the Synthesizer receives, disagreeing.

# Tool arguments can carry an email body or a whole log entry. The block needs the object of
# the action, not its payload.
_ARG_CHARS = 90
_MAX_ACTIONS = 6
_SAY_CHARS = 200


def _trace_files(persona: str | None) -> list[Path]:
    d = persona_data_dir(persona) / "traces"
    if not d.is_dir():
        return []
    today = datetime.now().date()
    names = [(today - timedelta(days=i)).isoformat() + ".jsonl" for i in range(_LOOKBACK_DAYS)]
    return [d / n for n in names if (d / n).exists()]


def last_trace(persona: str | None = None) -> dict | None:
    """
    The most recently written trace record, or None.

    This is the *previous* turn by construction, not the current one:
    core/trace.py writes at `finish_request_trace()`, and the Coordinator runs long before
    that, so nothing about the turn in flight is on disk yet.
    """
    for path in _trace_files(persona):          # newest date first
        try:
            lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        except OSError:
            continue
        for line in reversed(lines):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue                        # a torn final line is not a reason to give up
    return None


def _walk(agents: list) -> list:
    """Agents and their subagents — a specialist's tool calls are nested one level down."""
    out = []
    for a in agents or []:
        out.append(a)
        out.extend(_walk(a.get("subagents") or []))
    return out


def _describe_args(args: dict) -> str:
    """The object of the action, short. Empty when the arguments say nothing useful."""
    if not isinstance(args, dict):
        return ""
    parts = []
    for k, v in args.items():
        if isinstance(v, (dict, list)):
            continue                            # payloads, not objects
        s = str(v).strip().replace("\n", " ")
        if not s or s.lower() in ("none", "true", "false", ""):
            continue
        parts.append(f"{k}={s[:40]}")
        if len(", ".join(parts)) > _ARG_CHARS:
            break
    return ", ".join(parts)[:_ARG_CHARS]


def _actions(trace: dict) -> list[str]:
    """Tools that changed something last turn, with their object and how each ended."""
    out = []
    for agent in _walk(trace.get("pipeline") or []):
        for turn in agent.get("turns") or []:
            for tc in turn.get("tool_calls") or []:
                name = str(tc.get("name") or "")
                if not name or not is_action(name):
                    continue
                obj = _describe_args(tc.get("args") or {})
                # Failure is read the same way core/actions.py:_failed does, and for the
                # same reason: `ok` is False only when dispatch raised, so a tool that
                # returned "Error: no such contact" from its own body still records
                # ok=True. Two readers of the same trace must not disagree about whether
                # the action worked.
                failed = (not tc.get("ok", True)
                          or str(tc.get("result_preview") or "").startswith("Error"))
                # Neither flag can see a confirm-gated call, which returns ok=True having
                # only raised a card. The pending/declined lines below are what separate
                # those two, and that gap is the whole 2026-08-29 instance.
                ended = "FAILED" if failed else "completed"
                out.append(f"{name}({obj}) — {ended}" if obj else f"{name} — {ended}")
    return out[:_MAX_ACTIONS]


def _age_phrase(ts: str | None) -> tuple[str, bool]:
    """(phrase, within_window). Unparseable or missing timestamps are treated as stale."""
    if not ts:
        return "", False
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return "", False
    now = datetime.now(when.tzinfo) if when.tzinfo else datetime.now()
    delta = now - when
    if delta > _WINDOW or delta.total_seconds() < 0:
        return "", False
    mins = int(delta.total_seconds() // 60)
    if mins < 2:
        return "just now", True
    if mins < 60:
        return f"{mins} minutes ago", True
    return "about an hour ago", True


def _pending_and_declined(persona: str | None) -> tuple[list[str], list[str]]:
    """Outcomes the trace cannot see: what is still waiting on the user, and what they refused.

    These are the correction to the transcript. A gated action leaves a tool call that looks
    successful and a reply that may claim it was done; only the ledgers know it was neither.
    """
    pend: list[str] = []
    dec: list[str] = []
    try:
        from tools import confirm
        pend = [str(p.get("description") or "").strip()
                for p in confirm.pending(persona) if p.get("description")]
        cutoff = _WINDOW.total_seconds()
        dec = [str(r.get("description") or "").strip()
               for r in confirm.declined(cutoff, persona) if r.get("description")]
    except Exception as exc:  # noqa: BLE001 — evidence is optional; the turn is not
        logger.warning(f"[turn_referent] confirm ledgers unreadable: {exc}")
    return pend[-3:], dec[-3:]


def context_block(persona: str | None = None) -> str:
    """
    The previous exchange as evidence, for load_recent_context.

    Empty whenever there is nothing recent to point at — a first turn of the day, a quiet
    morning, an unreadable trace — so the ordinary case pays nothing and the failure mode is
    today's behaviour rather than an error.
    """
    try:
        trace = last_trace(persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[turn_referent] trace unreadable: {exc}")
        return ""
    if not trace:
        return ""

    age, fresh = _age_phrase(trace.get("ts"))
    if not fresh:
        return ""

    said = (trace.get("user_input") or "").strip().replace("\n", " ")[:_SAY_CHARS]
    replied = (trace.get("synth_response") or "").strip().replace("\n", " ")[:_SAY_CHARS]
    actions = _actions(trace)
    pend, dec = _pending_and_declined(persona)

    if not (said or actions or pend or dec):
        return ""

    lines = [
        "## The exchange immediately before this one",
        "What the user last said and what the system actually did about it. A short "
        "referring turn — \"undo that\", \"approved\", \"cancel it\", \"set it back\", "
        "\"read that back\" — points HERE unless this message names something else. Resolve "
        "it against this before anything in the day logs or open threads above, which are "
        "older and are not what the user is referring to.",
    ]
    if trace.get("is_proactive"):
        lines.append("- This was a scheduled run — the user did not speak in it.")
    elif said:
        lines.append(f'- The user said ({age}): "{said}"')
    if replied:
        lines.append(f'- The reply began: "{replied}"')
    if actions:
        lines.append("- What actually ran: " + "; ".join(actions))
    else:
        lines.append("- What actually ran: nothing — no action was taken.")
    if pend:
        lines.append("- STILL WAITING on the user's approval, not done: " + "; ".join(pend)
                     + ". An \"approved\" or \"yes\" most likely means this.")
    if dec:
        lines.append("- REFUSED by the user, and it stands: " + "; ".join(dec)
                     + ". Do not read a referring turn as reviving it.")
    # The half a transcript gets wrong on its own, stated where the model cannot miss it.
    if pend or dec:
        lines.append("- Where the reply above claims something was sent, booked or saved and "
                     "the two lines beneath it say otherwise, THESE lines are correct — the "
                     "reply is what was said, this is what happened.")
    return "\n".join(lines)
