"""
tools/build.py — the ONLY agent-callable surface on the Build vertical.

THE COORDINATOR NEVER SPEAKS TO A BUILD AGENT. `request_build()` files a row and
returns in milliseconds; a scheduler tick picks the ticket up later and *that*
process runs Inquiry -> Librarian -> Planner. The reason is honesty about cost:
specialist dispatch is synchronous inside one user turn, a Build run is minutes
and dollars, and a name in the valid-agent list would be a lie about what
calling it costs.

TICKETS LAND IN `proposed`, NOT `queued`. Mike triages. A gap filed by a fast
routing model is a candidate, not an instruction — and section 13.9's concession
stands: if the first runs show over-firing, the fix is moving the grant up a
level, not raising the cap.

TWO RECORDS UNTIL ONE EARNS TRUST. Beside the ticket, a `BUILD_PROPOSED` quality
event. The VM has no write path to DEV_BACKLOG.md, but sync_dev_backlog.py
already pulls quality events over /monitor/file, so the event reaches the Inbox
on the next sync. Redundant deliberately, and the redundancy retires when Build
is proven.

`gap` is validated by `is_null_ish` exactly as `write_quality_event` does. The
precedent is the slot that produced "None." ninety times: a field that looks
required gets filled with something plausible rather than left out, and a gap
reading "None." cannot be deduped, planned or verified.

Plan: archive/plans/build_vertical_plan_2026-09-18.md section 3, section 5
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# How many parked jobs the context block will name before it stops listing them.
# A block that grows without bound is a block agents learn to skim, which is the
# tools/obligations.py lesson: guaranteed delivery of something nobody reads is
# not delivery.
_BLOCK_MAX_ITEMS = 5


# ---------------------------------------------------------------------------
# The registered tools
# ---------------------------------------------------------------------------

def request_build(gap: str, trigger: str = "", mode: str = "construct",
                  capability_hint: str = "") -> str:
    """
    File a capability gap. Returns immediately; nothing is built in this turn.

    Never raises — refusals come back as explanatory strings, house style, so a
    duplicate or a full queue reads as information rather than as a tool error
    the model then narrates to the user.
    """
    from core.build import jobs as J

    try:
        row = J.create(gap=gap, trigger=trigger or "coordinator", mode=mode,
                       capability_hint=capability_hint)
    except J.JobError as exc:
        return f"Not filed: {exc}"
    except Exception as exc:
        logger.warning("[build] request_build failed: %s", exc)
        return f"Not filed: {type(exc).__name__}: {exc}"

    _file_backlog_event(row)
    return (f"Filed as {row['job_id']} and waiting for triage. Nothing has been "
            f"built and nothing is scheduled — this is a note that the gap exists.")


def answer_interview_item(job_id: str, question_id: str, answer: str) -> str:
    """
    Answer one question a Build job parked on. Releases the job when none remain.

    Missing data is a work item, not a blocker (section 13.8) — this is the path
    that turns one back into progress without re-running anything upstream.
    """
    from core.build import runner
    try:
        return runner.answer_interview(job_id, question_id, answer)
    except Exception as exc:
        logger.warning("[build] answer_interview_item failed: %s", exc)
        return f"Not recorded: {type(exc).__name__}: {exc}"


def _file_backlog_event(row: dict) -> None:
    """
    The second record. Best-effort: a ticket that filed is not undone by a
    quality event that did not.
    """
    try:
        from tools.logger import write_quality_event
        write_quality_event(
            event_type="BUILD_PROPOSED", source_agent="coordinator",
            detail=(f"{row['job_id']} ({row.get('mode', 'construct')}): "
                    f"{row.get('gap', '')}"),
        )
    except Exception as exc:
        logger.info("[build] BUILD_PROPOSED event not written: %s", exc)


# ---------------------------------------------------------------------------
# The conversational surface
# ---------------------------------------------------------------------------

def context_block(persona: str | None = None) -> str:
    """
    What Build is waiting on Mike for. EMPTY on a quiet day, which is most days.

    Only jobs at a HUMAN GATE appear. A job mid-pipeline is the system working
    and saying so would be narrating process, which section Discretion forbids and
    which would also train everyone to skim this block for the one line that
    actually needs them.

    Carries the budget-approval command verbatim, and says it runs ON THE VM:
    the ledger lives there, the Mac board reads it through a read-only fetch, so
    a command copied onto the wrong machine silently does nothing (correction
    v3.5 C2).
    """
    try:
        return _context_block(persona)
    except Exception as exc:
        logger.warning("[build] context block failed: %s", exc)
        return ""


def _interview_items(job_id: str, persona: str | None) -> list[dict]:
    """
    The open questions on a parked job, read straight from its ledger.

    Returns [] on any failure — a context block must never take down a turn,
    and a job whose ledger cannot be read is still worth naming without them.
    """
    try:
        from core.build import jobs as J
        ledger = J.read_artifact(job_id, "answer_ledger", persona) or {}
        return [
            {"question_id": str(item.get("question_id") or ""),
             "text": str(item.get("text") or "")}
            for item in ledger.get("interview_items") or []
            if isinstance(item, dict) and item.get("text")
        ]
    except Exception as exc:
        logger.info("[build] interview items unreadable for %s: %s", job_id, exc)
        return []


def _context_block(persona: str | None) -> str:
    # jobs only — never core.build.runner. This runs on every user turn through
    # load_recent_context, and importing the driver would drag the writer, the
    # registry, settle and the probe onto the hot path of every session to learn
    # five strings.
    from core.build import jobs as J

    states = J.states(persona)
    waiting = {job_id: job for job_id, job in states.items()
               if job["state"] in J.GATE_STATES and job["state"] != "proposed"}
    proposed = [job_id for job_id, job in states.items()
                if job["state"] == "proposed"]
    if not waiting and not proposed:
        return ""

    lines = ["## Capability building — waiting on you", ""]

    for job_id, job in sorted(waiting.items())[:_BLOCK_MAX_ITEMS]:
        state = job["state"]
        gap = str(job.get("gap") or "")[:120]
        if state == "needs_interview":
            lines.append(f"- **{job_id}** needs answers before it can be planned "
                         f"— {gap}")
            # THE QUESTIONS THEMSELVES, or the gate is unreachable. Naming the
            # job and the gap told the user something was waiting and not what
            # it wanted: there is no brief.md for a parked job (the writer
            # refuses a write from this state, correctly), so the questions
            # existed only in an artifact on disk and [N6] could not be
            # answered in conversation at all.
            for item in _interview_items(job_id, persona)[:_BLOCK_MAX_ITEMS]:
                lines.append(f"    - `{item['question_id']}` {item['text']}")
        elif state == "awaiting_approval":
            lines.append(
                f"- **{job_id}** has stopped at its spend limit — {gap}. "
                f"Raising it is a deliberate act ON THE VM: "
                f"`METATRON_PERSONA={persona or 'mike'} python3 -c \"from "
                f"core.build import cost; cost.approve_limit('{job_id}', 5.00)\"`, "
                f"then `python3 scripts/build_board.py --persona "
                f"{persona or 'mike'} --resume {job_id}`.")
        elif state == "briefed":
            lines.append(f"- **{job_id}** has a brief ready to read and approve "
                         f"— {gap}")
        elif state == "verifying":
            lines.append(f"- **{job_id}** is live and every check passed; it needs "
                         f"accepting or refusing — {gap}")

    overflow = len(waiting) - _BLOCK_MAX_ITEMS
    if overflow > 0:
        lines.append(f"- …and {overflow} more on the board.")

    if proposed:
        lines.append(f"- {len(proposed)} filed gap(s) awaiting triage.")

    lines += [
        "",
        "*Mention these only if they are relevant to what the user is doing, or "
        "if they ask. Nothing here is urgent and nothing is running unattended.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

REQUEST_BUILD_SCHEMA = {
    "name": "request_build",
    "description": (
        "File a capability gap: something the user needed that no existing "
        "specialist covers. Returns immediately — nothing is built during this "
        "conversation, and the gap goes to the user for triage before any work "
        "starts. Use this when you could not route a request because nothing "
        "owns it, not when a specialist simply answered poorly. Describe the GAP "
        "in the user's terms, not a tool you imagine solving it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "gap": {
                "type": "string",
                "description": (
                    "What the user needed and nothing could do, in plain terms. "
                    "Be specific about the request that arrived. Never write "
                    "'None', 'N/A' or a placeholder — if there is no gap, do not "
                    "call this tool."
                ),
            },
            "trigger": {
                "type": "string",
                "description": (
                    "What surfaced this — the user's request, a scheduled prompt "
                    "that went unanswered, a repeated correction."
                ),
            },
            "mode": {
                "type": "string",
                "enum": ["construct", "repair"],
                "description": (
                    "construct: nothing covers this. repair: a previously built "
                    "capability answered wrongly. Default construct."
                ),
            },
            "capability_hint": {
                "type": "string",
                "description": (
                    "For repair only: which built capability failed. Leave empty "
                    "for construct — naming a tool you imagine is how a narrow "
                    "tool gets built instead of the class it belongs to."
                ),
            },
        },
        "required": ["gap"],
    },
}

ANSWER_INTERVIEW_ITEM_SCHEMA = {
    "name": "answer_interview_item",
    "description": (
        "Record the user's answer to a question a capability-building job is "
        "parked on. Only call this when the user has actually answered one of "
        "the open items — never to guess on their behalf, and never to close an "
        "item because it seems obvious."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string",
                       "description": "The BLD-MMDD-NN id the item belongs to."},
            "question_id": {"type": "string",
                            "description": "The question id, e.g. q3."},
            "answer": {"type": "string",
                       "description": "What the user said, in their own words."},
        },
        "required": ["job_id", "question_id", "answer"],
    },
}
