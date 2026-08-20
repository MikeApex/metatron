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


def time_in_quiet_hours(cfg: dict, when: dtime) -> bool:
    """
    Is `when` inside this persona's quiet hours?

    Split out of `_in_quiet_hours` so `tools/schedule.py` can ask the question
    about a *future* fire time when deciding whether a user-requested reminder
    needs overnight permission. One implementation, because a second copy of an
    overnight-range comparison is a second thing to get wrong at the boundary.
    """
    qh = cfg.get("quiet_hours", {})
    if not qh:
        return False
    try:
        start = dtime.fromisoformat(qh["start"])
        end = dtime.fromisoformat(qh["end"])
    except (KeyError, ValueError):
        return False
    # Handles overnight ranges (e.g. 22:00 – 07:00)
    if start > end:
        return when >= start or when <= end
    return start <= when <= end


def _in_quiet_hours(cfg: dict) -> bool:
    """Is it quiet hours *now*? The scheduler's own gate."""
    return time_in_quiet_hours(cfg, datetime.now().time())


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
                 notification: str, persona: str,
                 job_cfg: dict | None = None) -> None:
    """
    Run one orchestrator session and dispatch the response.

    `job_cfg` carries the job's own settings — the gates below read it. Passing it
    is not an optimisation: `_load_config()` returns **`scheduler.yaml` only**, so
    an agent-written job from `data/personas/{p}/schedules.yaml` looked up by name
    here resolves to `{}` and every one of its own settings is invisible. That was
    harmless while all four gates defaulted to permissive; it stopped being
    harmless when quiet hours became opt-out on 2026-08-15, because a user's own
    "remind me at 06:00" reminder would have been silently held until 07:00 with
    no setting able to reach the gate. Callers that hold the job dict pass it;
    the scheduler.yaml lookup remains the fallback.
    """
    cfg = _load_config(persona)
    if job_cfg is None:
        job_cfg = cfg.get("schedules", {}).get(job_name, {})

    if not _is_active_day(job_cfg.get("days", "daily")):
        return
    if not job_cfg.get("enabled", True):
        return
    # Quiet hours are opt-OUT, not opt-in (2026-08-15). They were opt-in until a
    # session fired at 00:11 on 2026-08-12 and opened with a four-item briefing —
    # the gate ran and passed, because that job simply never set the flag. Any job
    # that has to be *remembered* into silence will eventually be forgotten into
    # waking someone at midnight, and the cost of the two failure directions is not
    # symmetric: a job wrongly held until morning is a delay, a job wrongly fired at
    # 00:11 is the product waking the user. A job that genuinely must run overnight
    # sets `respect_quiet_hours: false` and says so where it is read.
    if job_cfg.get("respect_quiet_hours", True) and _in_quiet_hours(cfg):
        print(f"[scheduler] [{persona}] skipping {job_name} — quiet hours", flush=True)
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

def fire_function(job_name: str, fn_path: str, persona: str,
                  notification: str = "false") -> None:
    """
    Call a Python function directly (no LLM session). Used for maintenance jobs.

    The persona is bound for the call. Without it these jobs inherited whatever
    persona happened to be left in the process from the last session — which is
    how ambient_refresh wrote to the wrong tree.

    **Return contract.** A function job that returns a plain string is logged and
    goes no further — that is every existing job (ambient_refresh, the two audits)
    and their behaviour is unchanged. A job that returns a dict with
    `{"notify": True, "title": ..., "body": ...}` is dispatched to the job's
    configured notification channel.

    The dict form exists because a function job had no way to reach the user at
    all, which forced anything user-facing to be an agent session and pay model
    tokens for it. The proactive travel check (tools/travel_watch.py) is the first
    caller: it costs nothing on a quiet day and must speak up on a bad one. Opting
    in per-return rather than per-job is deliberate — the job stays silent unless
    that specific run actually found something, so "nothing wrong" cannot notify.
    """
    import importlib
    try:
        with persona_scope(persona):
            module_path, fn_name = fn_path.rsplit(".", 1)
            mod = importlib.import_module(module_path)
            fn = getattr(mod, fn_name)
            result = fn()

        if isinstance(result, dict) and result.get("notify"):
            title = result.get("title") or job_name.replace("_", " ").title()
            body = result.get("body") or ""
            print(f"[scheduler] [{persona}] {job_name}: "
                  f"{result.get('summary', 'notifying')}", flush=True)
            if body:
                _dispatch(notification, title, body)
        else:
            print(f"[scheduler] [{persona}] {job_name}: {result}", flush=True)
    except Exception as e:
        _log_error(job_name, str(e), persona)
        print(f"[scheduler error] [{persona}] {job_name}: {e}", flush=True)


# ---------------------------------------------------------------------------
# Default maintenance jobs — every persona, no config required
# ---------------------------------------------------------------------------

# These three are **infrastructure, not preference.** They are silent to the
# user, cost no model tokens, carry no prompt, and there is no meaningful sense
# in which one person wants the calendar-duplicate sweep configured differently
# from another. That is the test for belonging here: a job with a prompt or a
# notification channel is a preference and stays in the persona's scheduler.yaml.
#
# WHY THIS EXISTS. Until 2026-08-08 these lived only in
# config/templates/scheduler.yaml, which scripts/new_persona.sh copies **once, at
# persona creation.** Nothing propagated a template change to an already-existing
# persona, and nothing reported the drift. The result: daily_calendar_dedup_audit
# shipped 2026-08-05 and had never once run for mike three days later — the sweep
# was live in the repo, in the template, and inert in production. It was found by
# reading his config for an unrelated reason. daily_travel_check would have been
# the second instance the same day.
#
# Registered here, a new maintenance job is live for every persona the moment it
# deploys, which is the actual requirement. A persona overrides any of these by
# defining the same key in its own scheduler.yaml — including `enabled: false` to
# turn one off. Persona config always wins; this is a floor, not a ceiling.
_DEFAULT_JOBS: dict[str, dict] = {
    "ambient_refresh": {
        "enabled": True,
        "interval_minutes": 180,
        "days": "daily",
        "function": "tools.ambient.refresh_ambient_context",
        "notification": False,
    },
    "daily_rule_audit": {
        "enabled": True,
        "time": "05:30",          # before the morning brief, so a fix can land same-day
        "days": "daily",
        "function": "tools.rule_audit.audit_rules",
        "notification": False,
    },
    "daily_calendar_dedup_audit": {
        "enabled": True,
        "time": "05:35",          # right after daily_rule_audit, same reasoning
        "days": "daily",
        "function": "tools.calendar_audit.audit_calendar_duplicates",
        "notification": False,
    },
    # A9 product analytics. 05:40 so it follows the other two audits, and it rolls up
    # YESTERDAY, which is a closed day. Collection has to start before Alpha even while
    # the metric definitions are still provisional: rows derive from traces, so a changed
    # definition can be re-derived, but cohort_day cannot be reconstructed after the fact.
    "daily_analytics_rollup": {
        "enabled": True,
        "time": "05:40",
        "days": "daily",
        "function": "tools.analytics.rollup_yesterday",
        "notification": False,
    },
    # Notes passed events that nothing in the record mentions, for the morning brief to
    # decide about. `notification: False` is not a preference — reconcile_check returns a
    # plain string and never a notify dict, because the check is crude text matching and
    # cannot support the claim that anything was missed. Fixed time because fire_function
    # runs no gate stack at all (`[DB-0808-11]`), so an interval job here could fire at 3am.
    "daily_calendar_reconcile": {
        "enabled": True,
        "time": "05:40",          # after the dedup audit; ~2h before the morning brief reads it
        "days": "daily",
        "function": "tools.calendar_reconcile.reconcile_check",
        "notification": False,
    },
    # Inbound intake (tools/intake.py): read new messages, classify, queue per domain.
    # Notifies nothing, ever — sweep() returns a plain string, so fire_function's notify
    # path is never taken; what reaches the user rides the morning brief via
    # context_block(). An interval job is safe here despite the absent gate stack
    # (`[DB-0808-11]`) because sweep() checks quiet hours itself and no-ops — the
    # in-code check exists precisely so this entry does not depend on a gate the
    # mechanism does not run. No-op when the persona has intake disabled (the default).
    "intake_sweep": {
        "enabled": True,
        "interval_minutes": 60,
        "days": "daily",
        "function": "tools.intake.sweep",
        "notification": False,
    },
    # Builds the weekly review digest and PARKS it — context_block() hands it to the
    # next session that loads coordinator context (in practice the morning brief) and
    # clears it. Deliberately no notification channel of its own: a dedicated push here
    # would rebuild the six-messages-in-one-day problem (tools/obligations.py header).
    # 06:30 Sunday, ahead of any weekend-morning session that could carry it.
    # NOTE the singular "day" — that is what selects the weekly registration branch
    # below; "days" would silently fall through to schedule.every().day and fire every
    # morning (caught by the 2026-08-19 code review before it shipped). This entry IS
    # the digest's cadence — intake.yaml deliberately carries none; a persona changes
    # it by redefining "intake_digest" in its own scheduler.yaml, which wins on name.
    "intake_digest": {
        "enabled": True,
        "time": "06:30",
        "day": "sunday",
        "function": "tools.intake.digest_job",
        "notification": False,
    },
}


def _agent_schedules_path(persona: str) -> Path:
    """Agent-written jobs. Separate file from the user's scheduler.yaml — see
    tools/schedule.py for why they must never share one."""
    return persona_data_dir(persona) / "schedules.yaml"


def _load_agent_schedules(persona: str) -> dict:
    """Agent-written recurring jobs, in the same shape as scheduler.yaml entries."""
    path = _agent_schedules_path(persona)
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as e:
        print(f"  [scheduler] WARNING: could not read {path}: {e}", flush=True)
        return {}
    # One-offs are not registered with the schedule library — they are fired from
    # the main loop against their `at` timestamp, then deleted.
    return {k: v for k, v in data.items()
            if isinstance(v, dict) and not v.get("one_off")}


def _agent_schedules_mtime(persona: str) -> float:
    path = _agent_schedules_path(persona)
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _fire_due_one_offs(persona: str) -> None:
    """
    Fire and remove any one-off job whose time has come.

    Handled here rather than through the schedule library, which has no concept
    of a job that runs once. Deleted before firing, not after: a session takes
    20-70s and the loop ticks every 30, so crediting it afterwards would fire the
    same job twice.
    """
    path = _agent_schedules_path(persona)
    if not path.exists():
        return
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return

    now = datetime.now()
    due = []
    for name, job in list(data.items()):
        if not isinstance(job, dict) or not job.get("one_off") or not job.get("enabled", True):
            continue
        try:
            when = datetime.fromisoformat(str(job.get("at", "")))
        except ValueError:
            continue
        if when <= now:
            due.append((name, job))

    if not due:
        return

    for name, job in due:
        data.pop(name, None)
    try:
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False,
                                  allow_unicode=True))
        os.chmod(path, 0o600)
    except Exception as e:
        print(f"  [scheduler] ERROR removing fired one-offs: {e}", flush=True)
        return

    for name, job in due:
        print(f"[scheduler] [{persona}] one-off {name} due — firing and removing", flush=True)
        try:
            fire_session(name, job.get("agent", "coordinator"),
                         job.get("prompt", ""), job.get("notification", "push"),
                         persona, job_cfg=job)
        except Exception as e:
            _log_error(name, f"one-off failed: {e}", persona)


def _register_schedules(persona: str) -> None:
    cfg = _load_config(persona)
    persona_cfg = dict(cfg.get("schedules", {}))

    # Default maintenance jobs form the base layer; the persona's own file is
    # layered on top, so any key it defines wins outright — including turning a
    # default off with `enabled: false`. Merged per-key rather than deep-merged:
    # a persona that redefines a job owns the whole definition, so a half-stated
    # override can't inherit a stray field from the default and produce a job
    # neither layer actually describes.
    schedules_cfg = {name: dict(job) for name, job in _DEFAULT_JOBS.items()}
    inherited = [n for n in _DEFAULT_JOBS if n not in persona_cfg]
    schedules_cfg.update(persona_cfg)
    if inherited:
        print(f"  [scheduler] {len(inherited)} default maintenance job(s) "
              f"inherited: {', '.join(sorted(inherited))}", flush=True)

    # Agent-written jobs are merged in at registration. On a name collision the
    # user's own scheduler.yaml wins — an agent must not be able to redefine the
    # morning brief.
    agent_jobs = _load_agent_schedules(persona)
    for name, job in agent_jobs.items():
        if name in schedules_cfg:
            print(f"  [scheduler] agent job {name!r} ignored — name taken by "
                  f"the user's scheduler.yaml", flush=True)
            continue
        schedules_cfg[name] = job
    if agent_jobs:
        print(f"  [scheduler] {len(agent_jobs)} agent-written job(s) from "
              f"{_agent_schedules_path(persona)}", flush=True)

    # Checked against the persona's *own* config, not the merged set — the
    # merged set now always carries the default maintenance jobs, so testing it
    # would silence this warning permanently. A persona with no scheduler.yaml
    # still gets maintenance, but gets no brief, no check-in and no close, which
    # is the thing worth saying out loud.
    if not persona_cfg:
        print(f"  [scheduler] WARNING: no persona schedules for {persona!r} "
              f"({_scheduler_config_path(persona)}) — maintenance defaults only, "
              f"no briefs or check-ins", flush=True)

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
            def make_fn_job(jn=job_name, fp=fn_path, pe=persona, no=notification):
                return lambda: fire_function(jn, fp, pe, no)
            job_fn = make_fn_job()
        else:
            agent = job["agent"]
            prompt = job.get("prompt", "What's going on?")
            def make_job(jn=job_name, ag=agent, pr=prompt, no=notification,
                         pe=persona, jc=job):
                return lambda: fire_session(jn, ag, pr, no, pe, job_cfg=jc)
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

    # Agents create jobs while the daemon is already running. Without this the
    # file would only be read at startup, so a reminder set at 09:00 for 10:00
    # would never fire until the next deploy — the user told it was set, nothing
    # happening, no error anywhere. Same silent-failure shape as SEQ 021.
    agent_mtime = _agent_schedules_mtime(persona)

    while True:
        offset = datetime.now().astimezone().utcoffset()
        if offset != current_offset:
            print(f"\n[scheduler] clock offset changed {current_offset} -> {offset} "
                  f"(daylight saving); re-registering schedules", flush=True)
            schedule.clear()
            _register_schedules(persona=persona)
            current_offset = offset

        new_mtime = _agent_schedules_mtime(persona)
        if new_mtime != agent_mtime:
            print("\n[scheduler] agent schedules changed; re-registering", flush=True)
            schedule.clear()
            _register_schedules(persona=persona)
            agent_mtime = new_mtime

        _fire_due_one_offs(persona)

        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
