"""
tools/build.py — the ONLY agent-callable surface on the Build vertical.

Plan: archive/plans/build_vertical_plan_2026-09-24.md sections 2, 5.

THE COORDINATOR NEVER SPEAKS TO A BUILD AGENT. `request_build()` files a ticket
and returns in milliseconds; nothing runs on the VM afterwards. Build itself is
DEVELOPMENT (ruling 1) — it runs in Claude Code on the Mac, started by Mike, and
the VM's only remaining jobs are filing tickets, serving the read doors, counting
dispatches and running whatever gets deployed.

The reason a Build agent is not in the valid-agent list is unchanged and is about
honesty: specialist dispatch is synchronous inside one user turn, a Build run is
a session with a person in it, and a name in that list would be a lie about what
calling it costs.

A TICKET IS FILED, NEVER QUEUED. It has exactly one state on the VM — open — and
the only thing that closes it is the tracked registry arriving by deploy. There
is no triage command here, no approve, no resume: those were VM-state commands
and the Mac session is the state now.

TWO RECORDS UNTIL ONE EARNS TRUST. Beside the ticket, a `BUILD_PROPOSED` quality
event. The VM has no write path to DEV_BACKLOG.md, but sync_dev_backlog.py
already pulls quality events over /monitor/file, so the event reaches the Inbox
on the next sync. Redundant deliberately, and the redundancy retires when Build
is proven.

`gap` is validated by `is_null_ish` exactly as `write_quality_event` does. The
precedent is the slot that produced "None." ninety times: a field that looks
required gets filled with something plausible rather than left out, and a gap
reading "None." cannot be deduped, planned or verified.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# How many open tickets the context block will name before it stops listing them.
# A block that grows without bound is a block agents learn to skim, which is the
# tools/obligations.py lesson: guaranteed delivery of something nobody reads is
# not delivery.
_BLOCK_MAX_ITEMS = 5


# ---------------------------------------------------------------------------
# The registered tool
# ---------------------------------------------------------------------------

def request_build(gap: str, trigger: str = "", mode: str = "construct",
                  capability_hint: str = "") -> str:
    """
    File a capability gap. Returns immediately; nothing is built in this turn.

    Never raises — refusals come back as explanatory strings, house style, so a
    duplicate or a full inbox reads as information rather than as a tool error
    the model then narrates to the user.
    """
    from core.build import tickets as T

    try:
        # `writer` names one of the two VM-side callers file_ticket admits. The
        # ticket inbox is VM state with no write path from the Mac, and a Build
        # session calling this would append to a local tree the VM never reads.
        row = T.file_ticket(gap=gap, trigger=trigger or "coordinator", mode=mode,
                            capability_hint=capability_hint,
                            writer="request_build")
    except T.TicketError as exc:
        return f"Not filed: {exc}"
    except Exception as exc:
        logger.warning("[build] request_build failed: %s", exc)
        return f"Not filed: {type(exc).__name__}: {exc}"

    _file_backlog_event(row)
    return (f"Filed as {row['job_id']} and waiting for triage. Nothing has been "
            f"built and nothing is scheduled — this is a note that the gap exists.")


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

    ONE LINE NOW, and that is the whole v4 change to this function. There are no
    mid-pipeline states left on the VM to surface: a job in flight is a session
    Mike is sitting in, and telling him about it in his own session would be
    narrating process to the person running it. What is left is the only thing
    the VM knows and he does not — how many gaps have been filed since he last
    looked.
    """
    try:
        return _context_block(persona)
    except Exception as exc:
        logger.warning("[build] context block failed: %s", exc)
        return ""


def _context_block(persona: str | None) -> str:
    # tickets only — never the driver. This runs on every user turn through
    # load_recent_context, and importing the driver would drag the gates, the
    # registry and the schemas onto the hot path of every ordinary session to
    # learn one number.
    from core.build import tickets as T

    waiting = T.open_tickets(persona)
    if not waiting:
        return ""

    lines = ["## Capability building", "",
             f"- {len(waiting)} gap(s) filed, waiting for you to start a build."]
    for job_id, row in sorted(waiting.items())[:_BLOCK_MAX_ITEMS]:
        mode = row.get("mode", "construct")
        gap = str(row.get("gap") or "")[:120]
        lines.append(f"    - `{job_id}`"
                     + (" (repair)" if mode == "repair" else "") + f" {gap}")
    overflow = len(waiting) - _BLOCK_MAX_ITEMS
    if overflow > 0:
        lines.append(f"    - …and {overflow} more.")

    lines += [
        "",
        "*Mention these only if they are relevant to what the user is doing, or "
        "if they ask. Nothing here is urgent and nothing is running unattended.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schema
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
