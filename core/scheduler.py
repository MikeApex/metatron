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
from datetime import datetime, time as dtime
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

    print(f"[scheduler] [{persona}] firing {job_name} ({agent})", flush=True)

    try:
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

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
