"""
tests/test_scheduler_quiet_hours.py — quiet hours are opt-out, not opt-in.

WHY THIS EXISTS. On 2026-08-12 at 00:11 a scheduled session fired and opened with
a four-item briefing. The quiet-hours gate ran and passed: `respect_quiet_hours`
was opt-in and that job never set it. Interval jobs (the check-ins, the inbox
sweeps) are the ones with no `time:` anchor, so they are exactly the jobs that can
land at midnight and exactly the ones most likely to omit the flag.

The gate is four lines inside `fire_session`, so these tests drive `fire_session`
itself with the surrounding I/O stubbed — testing a copy of the condition would
prove nothing about the code that runs.

Run: python3 tests/test_scheduler_quiet_hours.py
"""

import sys
from datetime import time as dtime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import scheduler  # noqa: E402

CFG = {
    "quiet_hours": {"start": "22:00", "end": "07:00"},
    "schedules": {
        "companion_checkin": {"enabled": True, "interval_minutes": 90},
        "morning_brief": {"enabled": True, "time": "07:30"},
        "overnight_job": {"enabled": True, "respect_quiet_hours": False},
    },
}

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def fired_at(clock: str, job: str, cfg: dict | None = None,
             job_cfg: dict | None = None) -> bool:
    """Run fire_session at a fixed wall-clock time; report whether it got through."""
    hh, mm = (int(p) for p in clock.split(":"))
    cfg = CFG if cfg is None else cfg
    ran: list[str] = []

    class _Now:
        @staticmethod
        def now():
            class _D:
                @staticmethod
                def time():
                    return dtime(hh, mm)
            return _D()

    with mock.patch.object(scheduler, "_load_config", return_value=cfg), \
         mock.patch.object(scheduler, "_is_active_day", return_value=True), \
         mock.patch.object(scheduler, "_activity_gate_blocks", return_value=None), \
         mock.patch.object(scheduler, "_record_fire"), \
         mock.patch.object(scheduler, "_dispatch"), \
         mock.patch.object(scheduler, "datetime", _Now), \
         mock.patch.object(scheduler, "_day_plan_owns", return_value=False), \
         mock.patch("core.remote_client.send_one",
                    side_effect=lambda *a, **k: ran.append("fired") or "ok"):
        scheduler.fire_session(job, "coordinator", "prompt", "push", "danny_park",
                               job_cfg=job_cfg)
    return bool(ran)


def main() -> int:
    # The regression: an interval job that never set the flag.
    check("an interval job does NOT fire at 00:11",
          not fired_at("00:11", "companion_checkin"))
    check("an interval job does NOT fire at 23:30",
          not fired_at("23:30", "companion_checkin"))
    check("an interval job DOES fire at 10:00",
          fired_at("10:00", "companion_checkin"))
    check("an interval job DOES fire at 19:48",
          fired_at("19:48", "companion_checkin"))

    # Boundaries of the 22:00-07:00 window.
    check("22:00 exactly is quiet", not fired_at("22:00", "companion_checkin"))
    check("07:00 exactly is quiet", not fired_at("07:00", "companion_checkin"))
    check("07:01 is awake", fired_at("07:01", "companion_checkin"))
    check("21:59 is awake", fired_at("21:59", "companion_checkin"))

    # No timed session job in the shipped template sits inside the window, so
    # nothing legitimate is newly suppressed by the default flip.
    check("the 07:30 morning brief still fires",
          fired_at("07:30", "morning_brief"))

    # The explicit opt-out remains available for a job that must run overnight.
    check("respect_quiet_hours: false still fires at 03:00",
          fired_at("03:00", "overnight_job"))

    # With no quiet_hours configured at all the gate is inert, so the default
    # flip cannot silence a persona that never defined a night.
    no_qh = {"quiet_hours": {}, "schedules": {"companion_checkin": {"enabled": True}}}
    check("no quiet_hours configured means no suppression",
          fired_at("03:00", "companion_checkin", cfg=no_qh))

    # --- agent-written jobs reach the gate at all ---------------------------
    # These live in data/personas/{p}/schedules.yaml, which _load_config() does
    # not read. Before job_cfg was passed through, every one of them resolved to
    # {} here — so a user's own 06:00 reminder could never carry the permission.
    user_reminder = {"enabled": True, "one_off": True, "agent": "coordinator",
                     "respect_quiet_hours": False}
    agent_idea = {"enabled": True, "one_off": True, "agent": "coordinator"}
    check("a user-requested 06:00 reminder wakes the user",
          fired_at("06:00", "irrelevant_name", job_cfg=user_reminder))
    check("an agent-invented 06:00 job is held until morning",
          not fired_at("06:00", "irrelevant_name", job_cfg=agent_idea))

    # --- the permission is asked for at write time, never assumed (2026-10-29) -----
    from datetime import datetime as _dt, timedelta as _td
    from unittest.mock import patch as _patch
    import tools.confirm as confirm_tool
    import tools.schedule as sched_tool

    def _write(at_time: str, created_by: str) -> tuple[dict, list, str]:
        """Write a one-off at tomorrow's `at_time`; return (stored entry, cards raised,
        the tool's reply)."""
        when = (_dt.now() + _td(days=1)).replace(
            hour=int(at_time[:2]), minute=int(at_time[3:]), second=0, microsecond=0)
        stored: dict = {}
        cards: list = []

        def _card(action, args, description, persona=None):
            cards.append((action, args, description))
            return {"status": "PENDING_CONFIRMATION", "confirm_token": "t"}

        with _patch.object(sched_tool, "_load", return_value={}), \
             _patch.object(sched_tool, "_save", side_effect=lambda d: stored.update(d)), \
             _patch.object(scheduler, "_load_config", return_value=CFG), \
             _patch.object(confirm_tool, "request", side_effect=_card):
            reply = sched_tool.write_schedule(
                name="probe", prompt="wake up", at=when.isoformat(timespec="seconds"),
                created_by=created_by)
        return (next(iter(stored.values())) if stored else {}), cards, reply

    entry, cards, reply = _write("06:00", "user")
    check("a user-asked 06:00 one-off is NOT given the permission unasked",
          "respect_quiet_hours" not in entry)
    check("…a card asks for it, naming the time and the quiet hours",
          len(cards) == 1 and cards[0][0] == "allow_quiet_hours"
          and cards[0][1] == {"name": "probe", "at": entry.get("at")}
          and "06:00" in cards[0][2] and "22:00–07:00" in cards[0][2])
    check("…and the reply says it interrupts their own quiet hours, and is set either way",
          "own quiet hours" in reply and "set either way" in reply)
    entry, cards, _ = _write("06:00", "agent")
    check("an agent-created 06:00 one-off raises no card and gets no permission",
          not cards and "respect_quiet_hours" not in entry)
    entry, cards, _ = _write("14:00", "user")
    check("a user-asked 14:00 one-off needs no card",
          not cards and "respect_quiet_hours" not in entry)

    # --- the approval sets the permission on exactly that job --------------------
    job_at = "2026-11-01T06:00:00"
    store = {"probe": {"one_off": True, "at": job_at, "created_by": "user"}}
    saved: dict = {}
    with _patch.object(sched_tool, "_load", return_value=store), \
         _patch.object(sched_tool, "_save", side_effect=lambda d: saved.update(d)), \
         _patch.object(confirm_tool, "consume", return_value=(True, "approved")):
        out = sched_tool.allow_in_quiet_hours("probe", job_at, confirm_token="t")
    check("approving the card lets that reminder fire inside quiet hours",
          saved.get("probe", {}).get("respect_quiet_hours") is False and "06:00" in out)
    with _patch.object(sched_tool, "_load", return_value={"probe": {"at": "2026-11-01T06:30:00"}}), \
         _patch.object(sched_tool, "_save") as no_save, \
         _patch.object(confirm_tool, "consume", return_value=(True, "approved")):
        out = sched_tool.allow_in_quiet_hours("probe", job_at, confirm_token="t")
    check("an approval for a reminder that has since moved changes nothing",
          out.startswith("Error") and not no_save.called)
    check("the approval is registered with the server-side executor",
          confirm_tool._EXECUTORS.get("allow_quiet_hours")
          == ("tools.schedule", "allow_in_quiet_hours"))

    # --- a one-off due in quiet hours is kept, not deleted (2026-10-29) ----------
    import tempfile
    import yaml as _yaml

    def _tick(in_quiet: bool, jobs: dict) -> tuple[list, dict]:
        """Run the one-off loop once; return (names fired, what is left in the file)."""
        fired: list = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schedules.yaml"
            path.write_text(_yaml.dump(jobs))
            with _patch.object(scheduler, "_agent_schedules_path", return_value=path), \
                 _patch.object(scheduler, "_held_for_interview", return_value=False), \
                 _patch.object(scheduler, "_load_config", return_value=CFG), \
                 _patch.object(scheduler, "_in_quiet_hours", return_value=in_quiet), \
                 _patch.object(scheduler, "fire_session",
                               side_effect=lambda name, *a, **k: fired.append(name)):
                scheduler._fire_due_one_offs("probe_persona")
            left = _yaml.safe_load(path.read_text()) or {}
        return fired, left

    past = (_dt.now() - _td(minutes=5)).isoformat(timespec="seconds")
    followup = {"enabled": True, "one_off": True, "at": past, "agent": "coordinator",
                "created_by": "agent"}
    fired, left = _tick(True, {"check_back": dict(followup)})
    check("a follow-up due inside quiet hours is not fired…", fired == [])
    check("…and is still in the file, not deleted", "check_back" in left)
    fired, left = _tick(False, {"check_back": dict(followup)})
    check("once quiet hours end it fires and is removed",
          fired == ["check_back"] and "check_back" not in left)
    approved = dict(followup, created_by="user", respect_quiet_hours=False)
    fired, left = _tick(True, {"alarm": approved, "check_back": dict(followup)})
    check("an approved reminder fires inside quiet hours; the held one stays",
          fired == ["alarm"] and "check_back" in left and "alarm" not in left)

    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print("All scheduler quiet-hours checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
