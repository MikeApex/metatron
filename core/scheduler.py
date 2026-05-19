"""
core/scheduler.py — proactive initiation daemon.

Reads config/modules/scheduler.yaml, fires orchestrator sessions on schedule,
and dispatches output to terminal and/or Web Push.

Run:
    python core/scheduler.py              # uses routing.yaml for model selection
    python core/scheduler.py --persona ryan_holiday   # dev persona mode

The orchestrator is stateless; this daemon holds all timing state.
Errors are logged to data/logs/scheduler_errors.json — the daemon keeps
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
_SCHEDULER_CONFIG = _ROOT / "config" / "modules" / "scheduler.yaml"
_ERROR_LOG = _ROOT / "data" / "logs" / "scheduler_errors.json"

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}
WEEKEND = {"saturday", "sunday"}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if _SCHEDULER_CONFIG.exists():
        with open(_SCHEDULER_CONFIG) as f:
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


def _notify_push(title: str, body: str) -> None:
    try:
        from core.push import send_push
        send_push(title=title, body=body)
    except Exception as e:
        _log_error("push_notification", str(e))


def _dispatch(channel: str, title: str, body: str) -> None:
    if channel in ("terminal", "both"):
        _notify_terminal(title, body)
    if channel in ("push", "both"):
        _notify_push(title, body)


# ---------------------------------------------------------------------------
# Session firing
# ---------------------------------------------------------------------------

def fire_session(job_name: str, agent: str, prompt: str,
                 notification: str, persona: str | None) -> None:
    """Run one orchestrator session and dispatch the response."""
    if not _is_active_day(_load_config().get("schedules", {})
                          .get(job_name, {}).get("days", "daily")):
        return

    cfg = _load_config()
    job_cfg = cfg.get("schedules", {}).get(job_name, {})
    if not job_cfg.get("enabled", True):
        return

    if job_cfg.get("respect_quiet_hours") and _in_quiet_hours(cfg):
        return

    print(f"[scheduler] firing {job_name} ({agent})", flush=True)

    try:
        from core.orchestrator import run_session
        response = run_session(agent_name=agent, user_input=prompt, persona=persona)
        title = job_name.replace("_", " ").title()
        _dispatch(notification, title, response)
    except Exception as e:
        _log_error(job_name, str(e))
        _notify_terminal(f"[scheduler error] {job_name}", str(e))


# ---------------------------------------------------------------------------
# Error logging
# ---------------------------------------------------------------------------

def _log_error(job: str, message: str) -> None:
    _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries: list = []
    if _ERROR_LOG.exists():
        try:
            with open(_ERROR_LOG) as f:
                entries = json.load(f)
        except Exception:
            pass
    entries.append({
        "timestamp": datetime.now().isoformat(),
        "job": job,
        "error": message,
    })
    with open(_ERROR_LOG, "w") as f:
        json.dump(entries, f, indent=2)


# ---------------------------------------------------------------------------
# Schedule registration
# ---------------------------------------------------------------------------

def _register_schedules(persona: str | None) -> None:
    cfg = _load_config()
    schedules_cfg = cfg.get("schedules", {})

    for job_name, job in schedules_cfg.items():
        if not job.get("enabled", True):
            continue

        agent = job["agent"]
        prompt = job.get("prompt", "What's going on?")
        notification = job.get("notification", "terminal")

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import time

    parser = argparse.ArgumentParser(description="Life Manager — Scheduler Daemon")
    parser.add_argument("--persona", help="Dev persona to use for all sessions")
    args = parser.parse_args()

    print("\nLife Manager — Scheduler Daemon")
    print(f"Config: {_SCHEDULER_CONFIG}")
    if args.persona:
        print(f"Persona: {args.persona}")
    print("Registering schedules...")

    _register_schedules(persona=args.persona)

    print("\nRunning. Ctrl+C to stop.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
