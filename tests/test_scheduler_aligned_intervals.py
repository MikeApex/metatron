"""
tests/test_scheduler_aligned_intervals.py — interval jobs keep to the clock, not to the restart.

Mike, 2026-11-23: every deploy restarts the scheduler, and `schedule` counted an interval from
registration — so deploying more often than hourly meant the hourly intake sweep never ran
between deploys. Interval jobs now run on an N-minute grid from local midnight, and are put back
on it after each run.

    python3 tests/test_scheduler_aligned_intervals.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import schedule  # noqa: E402

from core import scheduler  # noqa: E402

_failures: list[str] = []


def check(label: str, condition: bool) -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        _failures.append(label)


D = datetime(2026, 11, 23)
nxt = scheduler.aligned_next_run

# --- the grid -----------------------------------------------------------------------------
check("hourly from 14:01:05 → 15:00", nxt(D.replace(hour=14, minute=1, second=5), 60) == D.replace(hour=15))
check("hourly from exactly 15:00:00 → 16:00 (strictly after)", nxt(D.replace(hour=15), 60) == D.replace(hour=16))
check("30 min from 14:29:59 → 14:30", nxt(D.replace(hour=14, minute=29, second=59), 30) == D.replace(hour=14, minute=30))
check("5 min from 14:02 → 14:05", nxt(D.replace(hour=14, minute=2), 5) == D.replace(hour=14, minute=5))
check("180 min from 13:27 → 15:00", nxt(D.replace(hour=13, minute=27), 180) == D.replace(hour=15))
check("hourly from 23:30 → next midnight", nxt(D.replace(hour=23, minute=30), 60) == D + timedelta(days=1))
check("polling cadences go on the clock: 5, 30, 60, 180",
      all(scheduler.aligns_to_clock(m) for m in (5, 30, 60, 180)))
check("reminder-length intervals keep the old timing: 6 h, 12 h, 24 h, a week",
      not any(scheduler.aligns_to_clock(m) for m in (360, 720, 1440, 10080)))
check("an interval that does not divide the day is not aligned (7, 50, 100 min)",
      not any(scheduler.aligns_to_clock(m) for m in (7, 50, 100)))
check("a restart at any minute lands on the same slot",
      len({nxt(D.replace(hour=14, minute=m), 60) for m in range(0, 60)}) == 1)

# --- registration -------------------------------------------------------------------------
schedule.clear()
cfg = {"schedules": {"probe_interval": {"enabled": True, "interval_minutes": 60, "days": "daily",
                                        "function": "builtins.len", "notification": False}}}
with mock.patch.object(scheduler, "_load_config", return_value=cfg), \
     mock.patch.object(scheduler, "_DEFAULT_JOBS", {}), \
     mock.patch.object(scheduler, "_load_agent_schedules", return_value={}):
    before = datetime.now()
    scheduler._register_schedules("danny_park")
    after = datetime.now()
jobs = [j for j in schedule.jobs if getattr(j, "align_minutes", None) == 60]
check("a registered interval job is marked for alignment", len(jobs) == 1)
if jobs:
    j = jobs[0]
    check("its first run is the next top of the hour, not an hour from registration",
          j.next_run in (nxt(before, 60), nxt(after, 60)) and j.next_run.minute == 0
          and j.next_run.second == 0)
schedule.clear()

# --- a reminder-length job is not aligned -------------------------------------------------------
daily = {"schedules": {"probe_daily_interval": {"enabled": True, "interval_minutes": 1440,
                                                "days": "daily", "function": "builtins.len",
                                                "notification": False}}}
with mock.patch.object(scheduler, "_load_config", return_value=daily), \
     mock.patch.object(scheduler, "_DEFAULT_JOBS", {}), \
     mock.patch.object(scheduler, "_load_agent_schedules", return_value={}):
    t0 = datetime.now()
    scheduler._register_schedules("danny_park")
j = schedule.jobs[0]
check("an every-24-h job keeps its old timing (24 h from registration, never pinned to 00:00)",
      not getattr(j, "align_minutes", None) and j.next_run >= t0 + timedelta(hours=23, minutes=59))
schedule.clear()

# --- a re-registration keeps a just-due slot ------------------------------------------------------
two = {"schedules": {
    "probe_hourly": {"enabled": True, "interval_minutes": 60, "days": "daily",
                     "function": "builtins.len", "notification": False},
    "probe_removed": {"enabled": True, "interval_minutes": 30, "days": "daily",
                      "function": "builtins.len", "notification": False}}}
patches = (mock.patch.object(scheduler, "_DEFAULT_JOBS", {}),
           mock.patch.object(scheduler, "_load_agent_schedules", return_value={}))
with patches[0], patches[1], mock.patch.object(scheduler, "_load_config", return_value=two):
    scheduler._register_schedules("danny_park")
due = datetime.now() - timedelta(seconds=10)          # the slot came due 10 s ago, not yet run
for j in schedule.jobs:
    j.next_run = due
carry = scheduler.aligned_slots()
schedule.clear()
one = {"schedules": {"probe_hourly": two["schedules"]["probe_hourly"]}}   # the user removed one
with patches[0], patches[1], mock.patch.object(scheduler, "_load_config", return_value=one):
    scheduler._register_schedules("danny_park", carry=carry)
names = {getattr(j, "job_name", None): j for j in schedule.jobs}
check("re-registration keeps the just-due slot, so it still runs this tick",
      "probe_hourly" in names and names["probe_hourly"].next_run == due)
check("a removed job is not brought back by the carry", "probe_removed" not in names)
schedule.clear()

# --- the autumn clock change: a carried slot an hour ahead is not kept ---------------------------
with patches[0], patches[1], mock.patch.object(scheduler, "_load_config", return_value=one):
    scheduler._register_schedules("danny_park")
ahead = scheduler.aligned_next_run(datetime.now(), 60) + timedelta(hours=1)   # as after fall-back
carry = {"probe_hourly": (60, ahead)}
schedule.clear()
with patches[0], patches[1], mock.patch.object(scheduler, "_load_config", return_value=one):
    scheduler._register_schedules("danny_park", carry=carry)
check("after the clock goes back, the job takes the next slot from now, not the carried one",
      schedule.jobs[0].next_run == scheduler.aligned_next_run(datetime.now(), 60))
schedule.clear()

# --- after a run ----------------------------------------------------------------------------
ran = []
job = schedule.every(60).minutes.do(lambda: ran.append(1))
job.align_minutes = 60
job.last_run = D.replace(hour=15, second=4)                 # a 4-second run of the 15:00 slot
job.next_run = job.last_run + timedelta(minutes=60)          # what `schedule` would set: 16:00:04
check("realign moves the drifted next run back to 16:00", scheduler.realign_interval_jobs([job]) == 1
      and job.next_run == D.replace(hour=16))
check("realign is a no-op once on the grid", scheduler.realign_interval_jobs([job]) == 0)
job.last_run = D.replace(hour=16, minute=1, second=30)       # a run that overran its slot
scheduler.realign_interval_jobs([job])
check("an overrun goes to the next free slot, no catch-up burst", job.next_run == D.replace(hour=17))
plain = schedule.every(60).minutes.do(lambda: None)
plain.last_run = D.replace(hour=15, second=4)
plain.next_run = plain.last_run + timedelta(minutes=60)
scheduler.realign_interval_jobs([plain])
check("a job not marked for alignment (daily/weekly) is left alone",
      plain.next_run == D.replace(hour=16, second=4))
schedule.clear()

# --- real run through `schedule` ---------------------------------------------------------------
job = schedule.every(60).minutes.do(lambda: ran.append(1))
job.align_minutes = 60
job.next_run = datetime.now() - timedelta(seconds=1)        # due now
schedule.run_pending()
scheduler.realign_interval_jobs()
check("a due job runs once and is then put on the grid",
      ran == [1] and job.next_run == nxt(job.last_run, 60) and job.next_run.minute == 0)
schedule.clear()

print(f"\n{'All' if not _failures else len(_failures)} aligned-interval checks "
      f"{'passed' if not _failures else 'FAILED'}.")
sys.exit(1 if _failures else 0)
