"""
tools/schedule.py — agent-writable scheduled jobs.

The scheduler daemon reads two files. `config/personas/{p}/scheduler.yaml` holds
the user's own standing jobs — morning brief, evening close, check-in cadence.
This module owns the other one: `data/personas/{p}/schedules.yaml`, written by
agents.

**They are deliberately separate files.** `scheduler.yaml` is gitignored config,
hand-copied Mac → VM. An agent writing into it on the VM would be destroyed the
next time the user copied their own edited copy across — silently, with no error,
and only noticed weeks later when something failed to fire.

## What belongs here, and what does not

A scheduled job wakes an agent and runs a full pipeline session (~$0.025, ~25s).
That cost is worth paying only when something must be *judged* at the time:

    "every 2 days, check rainfall and raise watering only if it has been dry"

It is not worth paying for anything with a fixed time and no judgement:

    "pay the credit card on the 15th"  → a calendar event; free, and visible in
                                         the user's own calendar app

So: fixed timing goes to `write_calendar_event`. Conditions go here.

## Why obligations are not jobs

Tracking is free; waking up is not. Twenty obligations each polling themselves
daily would be ~$15/month and twenty interruptions. The intended shape is a small
number of sweeps that read *all* tracked obligations at once, with individual
obligations living as data (`write_agent_config`). Cost then stays flat whether
five things are tracked or five hundred — which is what the caps below enforce.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from core.persona import persona_data_dir

# Caps. The scheduler polls every 30 seconds and an agent can create jobs
# autonomously, so without a ceiling this is a system that can schedule itself
# into a runaway. Refusals name what to drop rather than failing silently —
# hitting the cap is meant to force a decision, not to be worked around.
MAX_AGENT_JOBS = 6
MIN_INTERVAL_MINUTES = 360      # 6h; anything more frequent belongs in a daily sweep
MAX_LIVE_REMINDERS = 10         # concurrent user-facing; the number that forces triage

VALID_NOTIFICATIONS = {"terminal", "push", "both", "none"}


def _schedules_path() -> Path:
    return persona_data_dir() / "schedules.yaml"


def _load() -> dict:
    path = _schedules_path()
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return {}


def _save(data: dict) -> None:
    path = _schedules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False,
                              allow_unicode=True))
    os.chmod(path, 0o600)


def _slug(name: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in name.strip().lower())
    return "_".join(filter(None, out.split("_")))[:60]


def write_schedule(
    name: str,
    prompt: str,
    agent: str = "coordinator",
    interval_minutes: int | None = None,
    at: str = "",
    notification: str = "push",
    user_facing: bool = True,
    reason: str = "",
    created_by: str = "agent",
) -> str:
    """
    Create or replace a scheduled job.

    Args:
        name:             Short identifier, e.g. "water_plants_check".
        prompt:           What the agent is asked when it wakes.
        agent:            Which agent runs. "coordinator" makes it a visible
                          conversation; a specialist name makes it a background
                          analysis run.
        interval_minutes: For a repeating job. Minimum 360 (6h).
        at:               For a one-off. ISO datetime, e.g. "2026-08-04T14:00:00".
                          Fires once and deletes itself.
        notification:     terminal | push | both | none
        user_facing:      True if this surfaces to the user; counts against the
                          live-reminder cap.
        reason:           Why this exists. Shown in list_schedules.
        created_by:       "agent" or "user".

    Returns:
        Confirmation, or an explanatory refusal.
    """
    key = _slug(name)
    if not key:
        return "Error: name must contain at least one alphanumeric character."
    if not str(prompt).strip():
        return "Error: prompt is required — it is what the agent is asked when it wakes."

    if notification not in VALID_NOTIFICATIONS:
        return f"Error: notification must be one of {sorted(VALID_NOTIFICATIONS)}."

    if bool(interval_minutes) == bool(at):
        return ("Error: give exactly one of interval_minutes (repeating) or "
                "at (one-off ISO datetime).")

    entry: dict = {
        "enabled": True,
        "agent": agent,
        "prompt": str(prompt).strip(),
        "notification": notification,
        "user_facing": bool(user_facing),
        "created_by": created_by,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "reason": str(reason).strip() or "(no reason recorded)",
    }

    if at:
        try:
            when = datetime.fromisoformat(at)
        except ValueError:
            return f"Error: 'at' must be ISO format (YYYY-MM-DDTHH:MM:SS), got '{at}'."
        if when <= datetime.now():
            return (f"Error: '{at}' is in the past. The system clock says "
                    f"{datetime.now().isoformat(timespec='seconds')}.")
        entry["at"] = when.isoformat(timespec="seconds")
        entry["one_off"] = True
    else:
        try:
            interval = int(interval_minutes)
        except (TypeError, ValueError):
            return "Error: interval_minutes must be a whole number of minutes."
        if interval < MIN_INTERVAL_MINUTES:
            return (
                f"Error: minimum interval is {MIN_INTERVAL_MINUTES} minutes (6h); "
                f"{interval} was requested. Each wake-up runs a full session. "
                f"Anything needing checking more often than four times a day "
                f"belongs in a daily sweep that reads all obligations at once, "
                f"not in its own job."
            )
        entry["interval_minutes"] = interval
        entry["one_off"] = False

    # Overnight permission (2026-08-15, Mike's rule). Quiet hours are opt-out in
    # `fire_session`, so without this a one-off the user explicitly asked for at
    # 06:00 would be held until 07:00 — the system deciding it knows better than
    # the person who set the alarm. The permission is granted automatically, and
    # only on the signal that actually distinguishes the two cases: who asked.
    #
    # A user-requested one-off firing inside quiet hours carries the permission.
    # An agent-invented job never does — an agent that decides overnight is the
    # right moment for its own idea is the failure this whole gate exists to
    # prevent. Recurring jobs are excluded regardless of who asked: an interval
    # job has no single fire time to consent to, it crosses every night by
    # construction, and a blanket exemption is not a permission.
    disturb_note = ""
    if entry.get("one_off") and created_by == "user":
        try:
            from core.scheduler import _load_config, time_in_quiet_hours
            if time_in_quiet_hours(_load_config(), when.time()):
                entry["respect_quiet_hours"] = False
                disturb_note = (" It falls inside quiet hours and is set to "
                                "wake you, because you asked for that time.")
        except Exception:
            # Never let a permission *widening* fail the write. Without the flag
            # the job is held until morning, which is the safe direction.
            pass

    data = _load()
    replacing = key in data

    if not replacing:
        agent_jobs = sum(1 for v in data.values()
                         if v.get("created_by") == "agent" and not v.get("one_off"))
        if created_by == "agent" and not entry["one_off"] and agent_jobs >= MAX_AGENT_JOBS:
            existing = ", ".join(
                k for k, v in data.items()
                if v.get("created_by") == "agent" and not v.get("one_off")
            )
            return (
                f"Error: at the limit of {MAX_AGENT_JOBS} recurring agent-created "
                f"jobs. Delete one before adding another — existing: {existing}. "
                f"Consider whether this belongs in an existing sweep instead."
            )

        live = sum(1 for v in data.values()
                   if v.get("enabled") and v.get("user_facing"))
        if entry["user_facing"] and live >= MAX_LIVE_REMINDERS:
            return (
                f"Error: {MAX_LIVE_REMINDERS} user-facing reminders are already "
                f"live, which is the ceiling. Something must be dropped or "
                f"demoted before another is promoted. Use list_schedules to see "
                f"them, then delete_schedule the least important, or set "
                f"user_facing false to track this without surfacing it."
            )

    data[key] = entry
    _save(data)

    when_str = (f"once at {entry['at']}" if entry["one_off"]
                else f"every {entry['interval_minutes']} minutes")
    verb = "Replaced" if replacing else "Scheduled"
    return (f"{verb} '{key}' — {when_str}, runs {agent}, "
            f"notification {notification}.{disturb_note}")


def list_schedules() -> str:
    """
    List every agent-written scheduled job with its provenance.

    Not a convenience. Agents create these autonomously, so without a way to see
    what exists the user gets notifications with no means of finding out where
    they came from or switching them off.
    """
    data = _load()
    if not data:
        return "No agent-written schedules. (User's own jobs live in scheduler.yaml.)"

    agent_jobs = sum(1 for v in data.values()
                     if v.get("created_by") == "agent" and not v.get("one_off"))
    live = sum(1 for v in data.values() if v.get("enabled") and v.get("user_facing"))

    lines = [
        f"{len(data)} scheduled job(s). "
        f"Recurring agent-created: {agent_jobs}/{MAX_AGENT_JOBS}. "
        f"Live user-facing: {live}/{MAX_LIVE_REMINDERS}.",
        "",
    ]
    for key, v in sorted(data.items()):
        when = (f"once at {v['at']}" if v.get("one_off")
                else f"every {v.get('interval_minutes')} min")
        state = "enabled" if v.get("enabled") else "disabled"
        facing = "user-facing" if v.get("user_facing") else "internal"
        lines.append(f"- {key} — {when}, {v.get('agent')}, {state}, {facing}")
        lines.append(f"    created by {v.get('created_by')} on "
                     f"{v.get('created_at', 'unknown')}: {v.get('reason', '')}")
    return "\n".join(lines)


def delete_schedule(name: str) -> str:
    """
    Delete a scheduled job.

    Removes the trigger, not the history. A job definition is a mechanism; the
    record that it fired lives in the logs. Calendar events, by contrast, are
    records and are never deleted this way.
    """
    key = _slug(name)
    data = _load()
    if key not in data:
        available = ", ".join(sorted(data)) or "none"
        return f"No schedule named '{key}'. Existing: {available}."
    removed = data.pop(key)
    _save(data)
    return (f"Deleted '{key}' ({removed.get('reason', 'no reason recorded')}). "
            f"{len(data)} schedule(s) remain.")


WRITE_SCHEDULE_SCHEMA = {
    "name": "write_schedule",
    "description": (
        "Create a recurring or one-off scheduled job that wakes an agent to check "
        "something.\n\n"
        "Use this ONLY when something must be judged at the time — 'every 2 days "
        "check whether it has rained and raise watering only if dry', 'weekly, "
        "check whether exercise logging has gone quiet'. Each wake-up runs a full "
        "session, so it costs real money and real time.\n\n"
        "Do NOT use this for anything with a fixed time and no judgement involved. "
        "'Pay the credit card on the 15th' and 'dentist at 2pm' are calendar "
        "entries — use write_calendar_event, which costs nothing to run and shows "
        "up in the user's own calendar.\n\n"
        "Do NOT create one job per tracked obligation. Store obligations with "
        "write_agent_config and let a single sweep read them all; twenty "
        "self-polling jobs cost twenty sessions a day.\n\n"
        "Limits: 6 recurring agent-created jobs, minimum 6h interval, 10 "
        "concurrent user-facing reminders. Hitting a limit means something must "
        "be dropped — that is deliberate."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short identifier, e.g. 'water_plants_check'."},
            "prompt": {"type": "string", "description": "What the agent is asked when it wakes."},
            "agent": {
                "type": "string",
                "description": (
                    "Which agent runs. 'coordinator' produces a visible conversation "
                    "with the user; a specialist name (e.g. 'logistics') runs a "
                    "background analysis that writes its own outputs."
                ),
            },
            "interval_minutes": {
                "type": "integer",
                "description": "Repeating job: minutes between runs. Minimum 360 (6h). Omit for a one-off.",
            },
            "at": {
                "type": "string",
                "description": "One-off job: ISO datetime, e.g. '2026-08-04T14:00:00'. Fires once, then deletes itself. Omit for recurring.",
            },
            "notification": {
                "type": "string",
                "description": "terminal | push | both | none. Use 'none' for internal checks that should stay silent unless they find something.",
            },
            "user_facing": {
                "type": "boolean",
                "description": "True if this surfaces to the user. Counts against the 10-reminder ceiling. Set false for background checks.",
            },
            "reason": {
                "type": "string",
                "description": "Why this exists, in one line. Shown to the user when they ask what is scheduled.",
            },
        },
        "required": ["name", "prompt"],
    },
}

LIST_SCHEDULES_SCHEMA = {
    "name": "list_schedules",
    "description": (
        "List every scheduled job with when it runs, who created it and why. "
        "Use before creating a new one to check nothing similar already exists, "
        "when a limit has been hit to decide what to drop, and whenever the user "
        "asks what is scheduled or where a notification came from."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}

DELETE_SCHEDULE_SCHEMA = {
    "name": "delete_schedule",
    "description": (
        "Delete a scheduled job by name. Use when the user asks to stop a "
        "recurring prompt, when a limit forces a choice, or when the reason for "
        "a job has passed. Removes the trigger only — the record that it fired "
        "stays in the logs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Identifier of the schedule to delete."},
        },
        "required": ["name"],
    },
}
