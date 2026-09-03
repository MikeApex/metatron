"""
core/actions.py — did this request change anything, and did it work?

One question, answered from the trace and nowhere else. The Synthesizer used to
receive the Coordinator's *directives* and the specialists' *prose*, and nothing
about which tools actually ran — so on 2026-08-10 it told Mike an email to
Kathaleen was "sent" when `relationships` had aborted before ever calling
`send_email`. Nothing in its context could have contradicted the prose.
[DB-0810-13]; diagnosis in
archive/plans/db081013_action_provenance_design_2026-08-15.md.

This is the same shape as the retrieval-provenance line built for the fabricated
sources incident (core/orchestrator.py `SOURCES (N retrieved)` /
`[RETRIEVAL: NONE]`): Python generates it from what the runtime observed, so it is
**evidence rather than a claim**. No model is asked whether an action happened.

Two design points that are load-bearing:

1. **Actions are not tool calls.** A line listing `search_contacts` and
   `list_obligations` would repeat the `is_grounded()` mistake documented at
   core/trace.py:107-118 — an agent that called `write_log` is *active*, not
   grounded, and an agent that read the calendar has not changed it. Reads are
   excluded here, in one place, so no agent file has to know the difference.
2. **Failures are louder than silence.** A `send_email` that was attempted and
   failed is precisely the Kathaleen case, and it is more informative to the
   Synthesizer than an empty line.

Scope is the **request**, not the agent. `pop_agent()` does not restore the prior
thread-local `current_agent` ([DB-0810-02]), so a nested `run_subagent` can
misattribute a call to the wrong specialist — "which specialist sent it" is not
reliable today, "was it sent at all this request" is. Do not add per-agent
attribution here until [DB-0810-02] is fixed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# The classification. Every tool in core/orchestrator.py's register_tools()
# handlers dict appears in exactly one of these two sets, and
# tests/test_action_provenance.py fails if a new one appears in neither.
# ---------------------------------------------------------------------------

# State-changing: after this ran, the world (or the user's data) is different.
# Mike's scoping decision, 2026-08-15: the class, not send_email — calendar
# create/move/delete, contact writes, log writes, obligations, schedules.
ACTION_TOOLS: frozenset[str] = frozenset({
    # Messaging
    "send_email",
    # Calendar
    "write_calendar_event", "update_calendar_event", "delete_calendar_event",
    # Contacts / CRM
    "write_contact", "log_interaction",
    # merge_contacts archives one record into another; import_contacts_file creates many.
    # Both change stored contact state, so both are actions the user would otherwise do
    # by hand. Added 2026-08-18 — they shipped 08-18 unclassified, and an unclassified
    # state-changing tool runs without appearing on the ACTIONS line, which is exactly
    # the [DB-0810-13] failure this module exists to prevent.
    # unmerge_contacts reverses a merge from the pre-merge snapshot — state-changing
    # in both directions, so it is an action like the merge it undoes. [DB-0822-03].
    "merge_contacts", "unmerge_contacts", "import_contacts_file",
    # apply_crm_proposals writes the accepted rows into the contact store behind the
    # batch confirm gate (tools/crm_sweep.py:918) — the model maps the user's words to
    # ledger ids and never supplies a value, but the write is real. Added 2026-09-03;
    # it had been unclassified since the sweep shipped, which is the same gap the two
    # tools above were added to close.
    "apply_crm_proposals",
    # Commitments and scheduled jobs
    "open_obligation", "close_obligation", "reopen_obligation",
    "write_schedule", "delete_schedule",
    # A taught intake rule permanently changes what mail the user sees — a standing
    # config write behind the confirm gate, and unambiguously an action.
    "teach_intake",
    # Logs, journal, wisdom — the user asks for these directly ("log that")
    "write_log", "write_quality_event",
    "write_journal", "write_archive",
    "write_wisdom", "merge_wisdom_entries",
    "write_insight_report",
    # Goals, config, identity
    "write_goals", "update_goal",
    "write_config", "write_agent_config",
    "write_persona", "write_profile",
    "write_wishes",
    # Analysis artefacts that persist
    "write_baseline_period", "write_retrospective",
    "create_semantic_anchor", "write_aspirational_baseline",
    "write_context_tracker",
})

# Read-only: looks something up, computes, or fetches. Nothing persists.
# `run_subagent` / `run_model_conference` are dispatch plumbing — the actions
# taken *inside* a subagent are recorded on its own trace record and counted
# there, so counting the dispatch itself would double-count nothing useful.
# `generate_emergency_card` formats stored data into a string and writes nothing
# (tools/wishes.py:119).
READ_TOOLS: frozenset[str] = frozenset({
    "read_log", "read_goals", "read_journal", "read_archive", "read_wisdom",
    "find_duplicate_wisdom", "search_memory", "read_context_tracker",
    "get_log_window", "read_recent_insights",
    "read_baseline_periods", "get_baseline_context",
    "shuffled_null_score", "score_against_anchors",
    "run_subagent", "run_model_conference",
    "read_contact", "list_contacts", "search_contacts", "get_tone_shape",
    "read_agent_config", "read_profile",
    "read_wishes", "generate_emergency_card",
    "read_calendar", "check_calendar_conflicts",
    "get_weather", "get_environmental_snapshot", "get_pollen_forecast",
    "get_tfl_status", "get_flight_status", "get_travel_time",
    "get_regional_transit_info", "find_places",
    "list_schedules", "list_obligations",
    "fetch_url", "read_email",
    # fetch_rendered is fetch_url with a headless browser for JS-heavy pages — it reads
    # the outside world and changes nothing. Added 2026-08-18 alongside the two above.
    "fetch_rendered",
    # read_intake_queue advances that domain's cursor — bookkeeping about what has been
    # shown, same class as read_email's BODY.PEEK avoidance of \Seen: presentation
    # state, not world state. Nothing a user would call "something the tool did".
    "read_intake_queue",
})

# Fallback for a tool registered after this file was last updated. The test
# above is the real guard; this is what happens if it is ignored. An unknown
# tool is reported as an action, not dropped: over-reporting shows Mike a name he
# can query, under-reporting is the silent failure this whole file exists to fix.
_READ_PREFIXES = ("read_", "get_", "list_", "search_", "find_", "check_", "fetch_")


def is_action(tool_name: str) -> bool:
    """Does calling this tool change state? Reads are False."""
    if tool_name in ACTION_TOOLS:
        return True
    if tool_name in READ_TOOLS:
        return False
    return not tool_name.startswith(_READ_PREFIXES)


def is_classified(tool_name: str) -> bool:
    """False when `is_action` is guessing from the name rather than knowing."""
    return tool_name in ACTION_TOOLS or tool_name in READ_TOOLS


# ---------------------------------------------------------------------------
# Line generation
# ---------------------------------------------------------------------------

_HEADER = (
    "ACTIONS EXECUTED THIS REQUEST — generated by the system from the tool calls "
    "that actually ran. This is a record of what happened, not a claim by any agent."
)

_NONE = (
    f"[{_HEADER}]\n"
    "NONE — nothing was sent, saved, scheduled, created, moved or deleted this "
    "request. Only lookups ran, or no tools at all."
)


def _walk(agents):
    for a in agents:
        yield a
        yield from _walk(getattr(a, "subagents", []) or [])


def _failed(tc) -> bool:
    """A tool call that did not do what it was asked.

    `ok` is False only when dispatch itself raised or the arguments would not
    bind (core/orchestrator.py:1390-1415). A tool that returns the string
    "Error: ..." from its own body — a CardDAV rejection, a missing contact —
    still records ok=True, so the result has to be read as well. Same test as
    `_failed_tool_calls()`, which reports upward for the same reason.
    """
    if not getattr(tc, "ok", True):
        return True
    return str(getattr(tc, "result_preview", "")).startswith("Error")


def action_provenance_block(trace) -> str:
    """The ACTIONS block for one request, ready to paste into Synthesizer input.

    Always returns a block, including when nothing ran: an absent line would be
    indistinguishable from "no information", which is the state that produced the
    false confirmation in the first place.
    """
    if trace is None:
        return _NONE

    # (name, failed) → count. Aggregated because three identical calendar writes
    # is one fact, and the args are not echoed: an email body or a journal entry
    # pasted here would cost hundreds of tokens and add nothing the specialist
    # prose does not already carry.
    tally: dict[tuple[str, bool], int] = {}
    unclassified: set[str] = set()

    for agent in _walk(getattr(trace, "pipeline", []) or []):
        for turn in getattr(agent, "turns", []) or []:
            for tc in getattr(turn, "tool_calls", []) or []:
                name = getattr(tc, "name", "")
                if not name or not is_action(name):
                    continue
                if not is_classified(name):
                    unclassified.add(name)
                key = (name, _failed(tc))
                tally[key] = tally.get(key, 0) + 1

    if not tally:
        return _NONE

    # Failures first — the case the Synthesizer most needs to see.
    rows = sorted(tally.items(), key=lambda kv: (not kv[0][1], kv[0][0]))
    lines = []
    for (name, failed), count in rows:
        times = f" x{count}" if count > 1 else ""
        mark = " (unrecognised tool — reported as an action)" if name in unclassified else ""
        if failed:
            lines.append(f"- {name} — ATTEMPTED AND FAILED{times}: did NOT complete{mark}")
        else:
            lines.append(f"- {name} — completed{times}{mark}")

    return f"[{_HEADER}]\n" + "\n".join(lines)
