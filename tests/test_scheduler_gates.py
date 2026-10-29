"""
tests/test_scheduler_gates.py — the two scheduler gates added 2026-08-28.

1. Collision suppression ([DB-0822-07]). On 2026-08-21 companion_checkin (a
   roaming interval job) landed at 07:23 and morning_brief fired at 07:30 — two
   conversations back to back, and the second read the first's prompt as an
   instruction from the user (fed the [DB-0815-11] false action claim). An
   interval session job now yields when it lands within N minutes (default 30)
   of a fixed-time session job, either side.

2. Function jobs run the gate stack ([DB-0808-11]). Until this change
   `fire_function` ran no gates at all — a function job with a push channel and
   an interval cadence could have pushed at 3am. Both firing paths now share
   `_gates_block`. The flip side is also tested: the silent pre-dawn maintenance
   defaults must carry `respect_quiet_hours: False` explicitly or the new gate
   would hold them every night.

Style follows tests/test_scheduler_quiet_hours.py: a plain check script driving
the real firing functions with the surrounding I/O stubbed.

Run: python3 tests/test_scheduler_gates.py
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import scheduler  # noqa: E402

# 2026-08-28 is a Friday; -29 a Saturday; -30 a Sunday.
FRIDAY = "2026-08-28"
SATURDAY = "2026-08-29"
SUNDAY = "2026-08-30"

CFG = {
    "quiet_hours": {"start": "22:00", "end": "07:00"},
    "schedules": {
        "morning_brief": {"enabled": True, "time": "07:30", "days": "daily",
                          "agent": "coordinator"},
        "evening_close": {"enabled": True, "time": "20:00", "days": "daily",
                          "agent": "coordinator"},
        "companion_checkin": {"enabled": True, "interval_minutes": 180,
                              "days": "daily", "agent": "coordinator"},
        # A fixed-time FUNCTION job — must never count as a collision target.
        "daily_travel_check": {"enabled": True, "time": "06:45", "days": "daily",
                               "function": "tools.travel_watch.travel_check",
                               "notification": "push",
                               "respect_quiet_hours": False},
    },
}

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def _fixed_clock(day: str, hhmm: str):
    """A datetime subclass whose now() is pinned. Subclassing keeps combine(),
    fromisoformat() and date arithmetic working inside the module under test."""
    base = datetime.fromisoformat(f"{day}T{hhmm}:00")

    class _Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(base.year, base.month, base.day,
                       base.hour, base.minute, base.second)

    return _Fixed


# ---------------------------------------------------------------------------
# Part 1 — collision suppression (session jobs)
# ---------------------------------------------------------------------------

def session_fired(day: str, hhmm: str, job: str, cfg: dict | None = None,
                  job_cfg: dict | None = None,
                  recorded: list | None = None) -> bool:
    cfg = CFG if cfg is None else cfg
    ran: list[str] = []
    rec = recorded if recorded is not None else []

    with mock.patch.object(scheduler, "_load_config", return_value=cfg), \
         mock.patch.object(scheduler, "_record_fire",
                           side_effect=lambda *a, **k: rec.append(a)), \
         mock.patch.object(scheduler, "_dispatch"), \
         mock.patch.object(scheduler, "datetime", _fixed_clock(day, hhmm)), \
         mock.patch("core.remote_client.send_one",
                    side_effect=lambda *a, **k: ran.append("fired") or "ok"):
        scheduler.fire_session(job, "coordinator", "prompt", "push", "danny_park",
                               job_cfg=job_cfg)
    return bool(ran)


def part1() -> None:
    # These checks are about the fixed check-in itself, so the day plan must not own it — pinned
    # off, never read from the live switch file (step 2 turned it on 2026-10-29 and seven of
    # them read the correct skip as a failure). part3 tests the owned case explicitly.
    import tools.day_plan_config as C
    C._OVERRIDE = {"flags": {"owns_checkins": False, "nudges": False},
                   "replaces_jobs": ["companion_checkin"]}
    try:
        _collision_checks()
    finally:
        C._OVERRIDE = None


def _collision_checks() -> None:
    print("Collision suppression — [DB-0822-07]")
    checkin = CFG["schedules"]["companion_checkin"]

    # The incident itself: 07:23 vs the 07:30 brief.
    rec: list = []
    check("check-in at 07:23 yields to the 07:30 brief",
          not session_fired(FRIDAY, "07:23", "companion_checkin",
                            job_cfg=checkin, recorded=rec))
    check("a suppressed run is NOT recorded as a fire (min_gap unaffected)",
          not rec)

    # Both directions: landing just after the brief is equally redundant.
    check("check-in at 07:35 yields too (5m after the brief)",
          not session_fired(FRIDAY, "07:35", "companion_checkin", job_cfg=checkin))

    # An ordinary mid-morning tick is untouched.
    check("check-in at 10:24 fires normally",
          session_fired(FRIDAY, "10:24", "companion_checkin", job_cfg=checkin))

    # The observed 2026-08-21 evening pattern survives the default window:
    # 19:28 is 32 minutes from the 20:00 close.
    check("check-in at 19:28 still fires (32m from evening close)",
          session_fired(FRIDAY, "19:28", "companion_checkin", job_cfg=checkin))
    check("check-in drifted to 19:40 yields to the 20:00 close",
          not session_fired(FRIDAY, "19:40", "companion_checkin", job_cfg=checkin))

    # The knob: 0 disables the behaviour outright.
    cfg_off = dict(CFG, interval_near_fixed_minutes=0)
    check("interval_near_fixed_minutes: 0 disables suppression",
          session_fired(FRIDAY, "07:23", "companion_checkin", cfg=cfg_off,
                        job_cfg=checkin))

    # A disabled fixed job is not a collision target.
    cfg_dis = {"quiet_hours": CFG["quiet_hours"], "schedules": {
        "morning_brief": {"enabled": False, "time": "07:30", "days": "daily",
                          "agent": "coordinator"},
        "companion_checkin": dict(checkin),
    }}
    check("a disabled fixed job does not suppress anything",
          session_fired(FRIDAY, "07:23", "companion_checkin", cfg=cfg_dis,
                        job_cfg=checkin))

    # A fixed-time FUNCTION job is silent — no conversation to collide with.
    cfg_fn = {"quiet_hours": CFG["quiet_hours"], "schedules": {
        "daily_travel_check": dict(CFG["schedules"]["daily_travel_check"]),
        "companion_checkin": dict(checkin),
    }}
    check("a fixed-time function job is not a collision target",
          session_fired(FRIDAY, "07:10", "companion_checkin", cfg=cfg_fn,
                        job_cfg=checkin))

    # A fixed session job that quiet hours will suppress never actually fires,
    # so the check-in must not yield to it.
    cfg_qh = {"quiet_hours": CFG["quiet_hours"], "schedules": {
        "pre_dawn_brief": {"enabled": True, "time": "06:30", "days": "daily",
                           "agent": "coordinator"},
        "companion_checkin": dict(checkin),
    }}
    check("a fixed job that quiet hours suppress is not a collision target",
          session_fired(FRIDAY, "07:05", "companion_checkin", cfg=cfg_qh,
                        job_cfg=checkin))

    # A weekly fixed job collides only on its own day.
    cfg_wk = {"quiet_hours": CFG["quiet_hours"], "schedules": {
        "weekly_review": {"enabled": True, "day": "sunday", "time": "09:00",
                          "agent": "coordinator"},
        "companion_checkin": dict(checkin),
    }}
    check("a Sunday 09:00 job does not suppress a Friday 09:05 check-in",
          session_fired(FRIDAY, "09:05", "companion_checkin", cfg=cfg_wk,
                        job_cfg=checkin))
    check("the same job DOES suppress a Sunday 09:05 check-in",
          not session_fired(SUNDAY, "09:05", "companion_checkin", cfg=cfg_wk,
                            job_cfg=checkin))

    # One-offs and fixed-time session jobs are exempt — only roaming interval
    # jobs yield. The brief itself must fire at 07:30 with the check-in nearby.
    check("the 07:30 brief itself is never suppressed",
          session_fired(FRIDAY, "07:30", "morning_brief",
                        job_cfg=CFG["schedules"]["morning_brief"]))
    one_off = {"enabled": True, "one_off": True, "agent": "coordinator"}
    check("a one-off reminder at 07:29 is exempt (no interval)",
          session_fired(FRIDAY, "07:29", "user_reminder", job_cfg=one_off))


# ---------------------------------------------------------------------------
# Part 2 — function jobs run the gate stack
# ---------------------------------------------------------------------------

PROBE_RUNS: list[str] = []


def probe_fn() -> str:
    PROBE_RUNS.append("ran")
    return "probe ok"


def _probe_runs() -> list[str]:
    """The list the probe actually appends to. When this file runs as a script
    it is `__main__`, but fire_function imports it by its module name — a
    second copy with its own PROBE_RUNS. Read that copy's list."""
    import importlib
    return importlib.import_module("tests.test_scheduler_gates").PROBE_RUNS


def function_fired(day: str, hhmm: str, job_cfg: dict | None,
                   cfg: dict | None = None, job_name: str = "probe_job") -> bool:
    cfg = CFG if cfg is None else cfg
    _probe_runs().clear()
    with mock.patch.object(scheduler, "_load_config", return_value=cfg), \
         mock.patch.object(scheduler, "_record_fire"), \
         mock.patch.object(scheduler, "_dispatch"), \
         mock.patch.object(scheduler, "datetime", _fixed_clock(day, hhmm)):
        scheduler.fire_function(job_name, "tests.test_scheduler_gates.probe_fn",
                                "danny_park", "push", job_cfg=job_cfg)
    return bool(_probe_runs())


def part2() -> None:
    print("\nFunction jobs run the gate stack — [DB-0808-11]")

    # The filed bug: a pushing interval function job at 3am.
    pushy = {"enabled": True, "interval_minutes": 60, "days": "daily",
             "notification": "push",
             "function": "tests.test_scheduler_gates.probe_fn"}
    check("a pushing interval function job does NOT run at 03:00",
          not function_fired(FRIDAY, "03:00", pushy))
    check("the same job runs at 10:00",
          function_fired(FRIDAY, "10:00", pushy))

    # The travel-check shape: explicit opt-out still works.
    overnight = dict(pushy, respect_quiet_hours=False)
    check("respect_quiet_hours: false still runs at 03:00",
          function_fired(FRIDAY, "03:00", overnight))

    # The days gate now reaches function jobs.
    weekday_job = dict(pushy, days="weekdays")
    check("a weekdays function job does NOT run on Saturday",
          not function_fired(SATURDAY, "10:00", weekday_job))
    check("and does run on Friday",
          function_fired(FRIDAY, "10:00", weekday_job))

    # Enabled and the activity gate reach function jobs too.
    check("enabled: false is honoured",
          not function_fired(FRIDAY, "10:00", dict(pushy, enabled=False)))
    gap_job = dict(pushy, min_gap_minutes=60)
    with mock.patch.object(scheduler, "_minutes_since_last_fire", return_value=10.0):
        check("min_gap_minutes is honoured for function jobs",
              not function_fired(FRIDAY, "10:00", gap_job))

    # With no job_cfg passed, the fallback resolves _DEFAULT_JOBS — so the
    # 05:30 rule audit still runs inside quiet hours via its explicit flag.
    no_entry_cfg = {"quiet_hours": CFG["quiet_hours"], "schedules": {}}
    check("daily_rule_audit resolves its default config and runs at 05:30",
          function_fired(FRIDAY, "05:30", None, cfg=no_entry_cfg,
                         job_name="daily_rule_audit"))

    # Structural guard: every silent maintenance default must opt out of quiet
    # hours explicitly, or the new gate holds it every night. A future default
    # added without the flag fails here, not in production.
    missing = [n for n, j in scheduler._DEFAULT_JOBS.items()
               if j.get("respect_quiet_hours") is not False]
    check("every _DEFAULT_JOBS entry sets respect_quiet_hours: False "
          f"(missing: {missing or 'none'})", not missing)


def part3() -> None:
    print("Day planner Stage B — the shared scan and the check-in yield")
    checkin = CFG["schedules"]["companion_checkin"]
    # near_fixed_session is the scan _near_fixed_job_blocks always ran: the same answer at
    # every case part 1 exercises, called directly with a clock rather than through a job.
    cases = [("07:23", True), ("07:35", True), ("10:24", False), ("19:28", False),
             ("19:40", True)]
    for hhmm, near in cases:
        now = datetime.fromisoformat(f"{FRIDAY}T{hhmm}:00")
        with mock.patch.object(scheduler, "datetime", _fixed_clock(FRIDAY, hhmm)):
            via_job = scheduler._near_fixed_job_blocks("companion_checkin", checkin, CFG)
            direct = scheduler.near_fixed_session(CFG, now, exclude="companion_checkin")
        check(f"near_fixed_session at {hhmm} gives the old scan's answer ({'near' if near else 'clear'})",
              bool(via_job) == near and direct == via_job)
    check("near_fixed_session honours interval_near_fixed_minutes: 0",
          scheduler.near_fixed_session(dict(CFG, interval_near_fixed_minutes=0),
                                       datetime.fromisoformat(f"{FRIDAY}T07:23:00")) is None)

    import tools.day_plan_config as C
    try:
        for flags, owns in (({"owns_checkins": False, "nudges": True}, False),
                            ({"owns_checkins": True, "nudges": False}, False),
                            ({"owns_checkins": True, "nudges": True}, True)):
            C._OVERRIDE = {"flags": flags, "replaces_jobs": ["companion_checkin"]}
            check(f"_day_plan_owns with {flags} → {owns}",
                  scheduler._day_plan_owns("companion_checkin") is owns)
        check("_day_plan_owns is false for a job not in replaces_jobs",
              scheduler._day_plan_owns("morning_brief") is False)
        check("an owned check-in does not fire",
              not session_fired(FRIDAY, "10:24", "companion_checkin", job_cfg=checkin))
        C._OVERRIDE = {"flags": {"owns_checkins": False, "nudges": False},
                       "replaces_jobs": ["companion_checkin"]}
        check("with the flags off the same check-in fires",
              session_fired(FRIDAY, "10:24", "companion_checkin", job_cfg=checkin))
    finally:
        C._OVERRIDE = None
    check("day_plan_refresh and day_plan_nudge are default jobs, every 5 minutes",
          all(scheduler._DEFAULT_JOBS.get(n, {}).get("interval_minutes") == 5
              for n in ("day_plan_refresh", "day_plan_nudge")))


def main() -> int:
    part1()
    part2()
    part3()
    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print(f"All {len(_results)} scheduler gate checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
