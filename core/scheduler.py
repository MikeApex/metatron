"""
core/scheduler.py — proactive initiation daemon.

Reads config/modules/scheduler.yaml, fires orchestrator sessions on schedule,
and dispatches output to terminal and/or Web Push.

Run:
    python core/scheduler.py              # uses routing.yaml for model selection
    python core/scheduler.py --persona ryan_holiday   # dev persona mode

The orchestrator is stateless; this daemon holds all timing state.
Errors are logged per-persona to data/personas/{persona}/logs/ — the daemon keeps
running after any single failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

import schedule
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

_ROOT = Path(__file__).parent.parent
from core.persona import (
    persona_config_dir,
    persona_data_dir,
    persona_scope,
    validate_persona_name,
)

# Quiet hours and job times are personal facts, so the schedule is per-persona.
# One daemon still serves every persona; it registers each persona's jobs separately.
def _scheduler_config_path(persona: str | None = None):
    return persona_config_dir(persona) / "scheduler.yaml"


def _error_log_path(persona: str | None = None):
    return persona_data_dir(persona) / "logs" / "scheduler_errors.json"

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}
WEEKEND = {"saturday", "sunday"}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config(persona: str | None = None) -> dict:
    path = _scheduler_config_path(persona)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _in_quiet_hours(cfg: dict) -> bool:
    qh = cfg.get("quiet_hours", {})
    if not qh:
        return False
    now = datetime.now().time()
    try:
        start = dtime.fromisoformat(qh["start"])
        end = dtime.fromisoformat(qh["end"])
    except (KeyError, ValueError):
        return False
    # Handles overnight ranges (e.g. 22:00 – 07:00)
    if start > end:
        return now >= start or now <= end
    return start <= now <= end


def _last_fired_path(persona: str | None = None):
    return persona_data_dir(persona) / "logs" / "scheduler_last_fired.json"


def _minutes_since_last_user_message(persona: str) -> float | None:
    """
    Minutes since the user last actually said something, or None if unknown.

    Proactive sessions are written to the same conversation log as real ones and
    are flagged `proactive: true` — without that filter the scheduler would read
    its own check-ins as user activity and never fire again.

    Returns None on any failure, and callers treat None as "do not gate": an
    unreadable log must not silently switch check-ins off altogether.
    """
    try:
        conv_dir = persona_data_dir(persona) / "conversations"
        latest = None
        # Yesterday as well as today: at 00:30 today's file may not exist yet,
        # and a conversation an hour ago is still an active conversation.
        for day_offset in (0, 1):
            day = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            path = conv_dir / f"{day}.jsonl"
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("proactive"):
                    continue
                # Key is "ts", written by _log_conversation in core/server.py as a
                # naive local-time isoformat string. Not "timestamp" — that is the
                # key in the quality-event log, and using it here silently matched
                # nothing, which (failing open) looked exactly like a working gate.
                ts = entry.get("ts")
                if not ts:
                    continue
                try:
                    when = datetime.fromisoformat(ts)
                except ValueError:
                    continue
                if when.tzinfo is not None:
                    when = when.astimezone().replace(tzinfo=None)
                if latest is None or when > latest:
                    latest = when
        if latest is None:
            return None
        return (datetime.now() - latest).total_seconds() / 60.0
    except Exception:
        return None


def _minutes_since_last_fire(job_name: str, persona: str) -> float | None:
    """Minutes since this job last actually fired, or None if it never has."""
    try:
        path = _last_fired_path(persona)
        if not path.exists():
            return None
        stamps = json.loads(path.read_text())
        ts = stamps.get(job_name)
        if not ts:
            return None
        return (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 60.0
    except Exception:
        return None


def _record_fire(job_name: str, persona: str) -> None:
    """Persist this job's fire time. On disk, not in memory: a deploy restarts
    the daemon several times a day, and an in-memory clock would reset each
    time and let a check-in through early."""
    try:
        path = _last_fired_path(persona)
        path.parent.mkdir(parents=True, exist_ok=True)
        stamps = {}
        if path.exists():
            try:
                stamps = json.loads(path.read_text())
            except json.JSONDecodeError:
                pass
        stamps[job_name] = datetime.now().isoformat()
        path.write_text(json.dumps(stamps, indent=2))
        os.chmod(path, 0o600)
    except Exception as e:
        print(f"[scheduler] could not record fire time for {job_name}: {e}", flush=True)


def _activity_gate_blocks(job_name: str, job_cfg: dict, persona: str) -> str | None:
    """
    Decide whether an activity-gated job should stay quiet. Returns a reason to
    skip, or None to proceed.

    Two independent conditions, both opt-in per job:

      quiet_after_user_minutes — do not interrupt a live conversation. A check-in
        that lands while the user is mid-exchange is noise; it should arrive once
        they have gone quiet.
      min_gap_minutes — never more often than this, however long they stay quiet.

    Together these let the job be polled frequently while still firing rarely:
    the check-in arrives once the user has been quiet for a while, and never more
    than once per gap. Absent both keys, behaviour is exactly as before.
    """
    quiet_after = job_cfg.get("quiet_after_user_minutes")
    if quiet_after:
        idle = _minutes_since_last_user_message(persona)
        # None means unknown — proceed rather than fall silent forever.
        if idle is not None and idle < float(quiet_after):
            return f"user active {idle:.0f}m ago (needs {quiet_after}m quiet)"

    min_gap = job_cfg.get("min_gap_minutes")
    if min_gap:
        since = _minutes_since_last_fire(job_name, persona)
        if since is not None and since < float(min_gap):
            return f"last fired {since:.0f}m ago (min gap {min_gap}m)"

    return None


def _is_active_day(days_str: str) -> bool:
    day_name = datetime.now().strftime("%A").lower()
    if days_str == "daily":
        return True
    if days_str == "weekdays":
        return day_name in WEEKDAYS
    if days_str == "weekend":
        return day_name in WEEKEND
    return day_name == days_str.lower()


# ---------------------------------------------------------------------------
# Notification dispatch
# ---------------------------------------------------------------------------

def _notify_terminal(title: str, body: str) -> None:
    print(f"\n[{datetime.now().strftime('%H:%M')}] {title}")
    print(body)
    # macOS notification banner
    try:
        script = f'display notification "{body[:200]}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass


def _notify_push(title: str, body: str, persona: str | None = None) -> None:
    try:
        from core.push import send_push
        send_push(title=title, body=body)
    except Exception as e:
        _log_error("push_notification", str(e), persona)


def _dispatch(channel: str, title: str, body: str) -> None:
    if channel in ("terminal", "both"):
        _notify_terminal(title, body)
    if channel in ("push", "both"):
        _notify_push(title, body)


# ---------------------------------------------------------------------------
# Session firing
# ---------------------------------------------------------------------------

def fire_session(job_name: str, agent: str, prompt: str,
                 notification: str, persona: str) -> None:
    """Run one orchestrator session and dispatch the response."""
    cfg = _load_config(persona)
    job_cfg = cfg.get("schedules", {}).get(job_name, {})

    if not _is_active_day(job_cfg.get("days", "daily")):
        return
    if not job_cfg.get("enabled", True):
        return
    if job_cfg.get("respect_quiet_hours") and _in_quiet_hours(cfg):
        return

    blocked = _activity_gate_blocks(job_name, job_cfg, persona)
    if blocked:
        print(f"[scheduler] [{persona}] skipping {job_name} — {blocked}", flush=True)
        return

    # Recorded before the session runs, not after: a pipeline takes 20-70s, and
    # crediting the fire only on success would let a failing job retry on every
    # poll. Firing is what the gap limits, whether or not it succeeds.
    _record_fire(job_name, persona)

    print(f"[scheduler] [{persona}] firing {job_name} ({agent})", flush=True)

    try:
        if agent == "coordinator":
            # Go through the server so a proactive session is an ordinary
            # exchange: conversation record (and seq), row in the shared
            # database, and a live broadcast to every connected device.
            # Run in-process and it produces a trace and a push notification but
            # no record anywhere the user can see — Metatron opens a conversation
            # that then appears nowhere in their history.
            from core.remote_client import send_one
            response = send_one(persona, prompt)
        else:
            # Single-agent jobs (pattern_miner, physical_health) are analysis
            # runs that write their own outputs; they are not conversation.
            from core.orchestrator import run_session
            response = run_session(agent_name=agent, user_input=prompt, persona=persona)
        title = job_name.replace("_", " ").title()
        _dispatch(notification, title, response)
    except Exception as e:
        _log_error(job_name, str(e), persona)
        _notify_terminal(f"[scheduler error] {job_name}", str(e))


# ---------------------------------------------------------------------------
# Error logging
# ---------------------------------------------------------------------------

def _log_error(job: str, message: str, persona: str | None = None) -> None:
    log_path = _error_log_path(persona)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entries: list = []
    if log_path.exists():
        try:
            with open(log_path) as f:
                entries = json.load(f)
        except Exception:
            pass
    entries.append({
        "timestamp": datetime.now().isoformat(),
        "job": job,
        "error": message,
        # Without this a failure is one opaque line. 189 identical
        # "not JSON serializable" entries took a live reproduction to diagnose.
        "traceback": traceback.format_exc() if sys.exc_info()[0] else "",
    })
    with open(log_path, "w") as f:
        json.dump(entries, f, indent=2)


# ---------------------------------------------------------------------------
# Schedule registration
# ---------------------------------------------------------------------------

def fire_function(job_name: str, fn_path: str, persona: str) -> None:
    """
    Call a Python function directly (no LLM session). Used for maintenance jobs.

    The persona is bound for the call. Without it these jobs inherited whatever
    persona happened to be left in the process from the last session — which is
    how ambient_refresh wrote to the wrong tree.
    """
    import importlib
    try:
        with persona_scope(persona):
            module_path, fn_name = fn_path.rsplit(".", 1)
            mod = importlib.import_module(module_path)
            fn = getattr(mod, fn_name)
            result = fn()
        print(f"[scheduler] [{persona}] {job_name}: {result}", flush=True)
    except Exception as e:
        _log_error(job_name, str(e), persona)
        print(f"[scheduler error] [{persona}] {job_name}: {e}", flush=True)


def _register_schedules(persona: str) -> None:
    cfg = _load_config(persona)
    schedules_cfg = cfg.get("schedules", {})
    if not schedules_cfg:
        print(f"  [scheduler] WARNING: no schedules for persona {persona!r} "
              f"({_scheduler_config_path(persona)}) — registering none", flush=True)
        return

    for job_name, job in schedules_cfg.items():
      # Registration runs once at daemon start. An uncaught raise here is a
      # crash loop, not a degraded job — so each job is isolated.
      try:
        if not job.get("enabled", True):
            continue

        notification = job.get("notification", "terminal")

        # Function jobs call a Python callable directly — no LLM session
        if "function" in job:
            fn_path = job["function"]
            def make_fn_job(jn=job_name, fp=fn_path, pe=persona):
                return lambda: fire_function(jn, fp, pe)
            job_fn = make_fn_job()
        else:
            agent = job["agent"]
            prompt = job.get("prompt", "What's going on?")
            def make_job(jn=job_name, ag=agent, pr=prompt, no=notification, pe=persona):
                return lambda: fire_session(jn, ag, pr, no, pe)
            job_fn = make_job()

        if "interval_minutes" in job:
            schedule.every(job["interval_minutes"]).minutes.do(job_fn)
            print(f"  [scheduler] {job_name}: every {job['interval_minutes']} min")

        elif "time" in job and "day" in job:
            # Weekly — specific day + time
            day = job["day"].lower()
            t = job["time"]
            getattr(schedule.every(), day).at(t).do(job_fn)
            print(f"  [scheduler] {job_name}: {day} at {t}")

        elif "time" in job:
            schedule.every().day.at(job["time"]).do(job_fn)
            print(f"  [scheduler] {job_name}: daily at {job['time']}")

      except Exception as e:
        _log_error(job_name, f"registration failed: {e}", persona)
        print(f"  [scheduler] ERROR registering {job_name} for {persona}: {e} "
              f"— skipping this job, daemon continues", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import time

    parser = argparse.ArgumentParser(description="Life Manager — Scheduler Daemon")
    parser.add_argument(
        "--persona",
        required=True,
        help="Persona whose schedule this daemon runs (e.g. mike). Required — "
             "every scheduled session must belong to a persona.",
    )
    args = parser.parse_args()

    persona = validate_persona_name(args.persona)

    print("\nLife Manager — Scheduler Daemon")
    print(f"Persona: {persona}")
    print(f"Config: {_scheduler_config_path(persona)}")
    print("Registering schedules...")

    _register_schedules(persona=persona)

    print("\nRunning. Ctrl+C to stop.\n")

    # The schedule library computes each job's next_run once, from the clock at
    # registration. At a DST boundary those precomputed times are an hour wrong,
    # and this daemon runs for weeks without restarting — so detect the change
    # and re-register. Self-healing; no cron entry or manual step needed.
    current_offset = datetime.now().astimezone().utcoffset()

    while True:
        offset = datetime.now().astimezone().utcoffset()
        if offset != current_offset:
            print(f"\n[scheduler] clock offset changed {current_offset} -> {offset} "
                  f"(daylight saving); re-registering schedules", flush=True)
            schedule.clear()
            _register_schedules(persona=persona)
            current_offset = offset

        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
