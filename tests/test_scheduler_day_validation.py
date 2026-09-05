"""
tests/test_scheduler_day_validation.py — a mistyped day name is refused loudly.

[DB-0903-02]. `days: sun` matched nothing on any day: `_is_active_day` compares
against `strftime("%A").lower()`, so only `daily`, `weekdays`, `weekend` or a full
lowercase day name ever matched. There was no error and no warning — which is how
weekly_clinical_review shipped inert twice on 2026-09-03, twice unnoticed.

The fix validates the day keys instead of widening `_is_active_day` to accept
abbreviations: accepting `sun` would fix one spelling and leave the next silent key
exactly as silent. A job with a bad value is SKIPPED loudly — one typo must not take
down the six good jobs — and the error repeats, so it cannot scroll out of sight.

Standalone runner (no pytest dependency), matching tests/test_scheduler_gates.py.

Usage:
    python3 tests/test_scheduler_day_validation.py

Exits 0 if every test passes, 1 otherwise.
"""

import io
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import schedule  # noqa: E402

from core import scheduler  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((bool(condition), label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


# ---------------------------------------------------------------------------
# 1. The validator itself
# ---------------------------------------------------------------------------

def part1() -> None:
    print("\n1. schedule_key_error — what it accepts and what it refuses")

    err = scheduler.schedule_key_error({"days": "sun", "time": "18:00",
                                        "agent": "coordinator"})
    check("days: sun is refused", bool(err))
    if err:
        check("the message quotes the bad value", "sun" in err)
        check("the message lists the accepted forms",
              all(w in err for w in ("daily", "weekdays", "weekend", "monday")))

    # Every accepted form still passes.
    for value in ("daily", "weekdays", "weekend",
                  "monday", "tuesday", "wednesday", "thursday",
                  "friday", "saturday", "sunday"):
        check(f"days: {value} is accepted",
              scheduler.schedule_key_error({"days": value}) is None)

    # Case is normalised, not refused — `_is_active_day` already lowercased the
    # day-name branch, so refusing `Daily` here would invent a new silent failure.
    check("days: Daily is accepted (case-insensitive)",
          scheduler.schedule_key_error({"days": "Daily"}) is None)
    check("days: Sunday is accepted (case-insensitive)",
          scheduler.schedule_key_error({"days": "Sunday"}) is None)

    # A job with no day keys at all is a plain daily job.
    check("no day keys is fine",
          scheduler.schedule_key_error({"time": "07:30", "agent": "coordinator"}) is None)

    # `day:` (singular) drives schedule.every().<day> — full names only.
    check("day: sunday is accepted",
          scheduler.schedule_key_error({"day": "sunday", "time": "18:00"}) is None)
    day_err = scheduler.schedule_key_error({"day": "sun", "time": "18:00"})
    check("day: sun is refused", bool(day_err))
    check("day: weekdays is refused (not a schedule-library attribute)",
          bool(scheduler.schedule_key_error({"day": "weekdays", "time": "18:00"})))

    # Non-strings must not crash the validator — YAML happily yields ints/lists.
    check("days: 5 is refused, not crashed on",
          bool(scheduler.schedule_key_error({"days": 5})))
    check("days: [monday] is refused, not crashed on",
          bool(scheduler.schedule_key_error({"days": ["monday"]})))


# ---------------------------------------------------------------------------
# 2. The firing gate refuses a bad value rather than silently never matching
# ---------------------------------------------------------------------------

def part2() -> None:
    print("\n2. _is_active_day and the gate stack")

    # 2026-08-30 is a Sunday.
    class FakeNow(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 30, 18, 0)

    with mock.patch.object(scheduler, "datetime", FakeNow):
        check("_is_active_day('sunday') is True on a Sunday",
              scheduler._is_active_day("sunday"))
        check("_is_active_day('weekend') is True on a Sunday",
              scheduler._is_active_day("weekend"))
        check("_is_active_day('daily') is True on a Sunday",
              scheduler._is_active_day("daily"))
        check("_is_active_day('weekdays') is False on a Sunday",
              not scheduler._is_active_day("weekdays"))
        check("_is_active_day('sun') is still False — no abbreviations",
              not scheduler._is_active_day("sun"))

        cfg = {"quiet_hours": {"start": "22:00", "end": "07:00"}, "schedules": {}}
        bad = {"enabled": True, "time": "18:00", "days": "sun",
               "agent": "coordinator", "respect_quiet_hours": False}
        with mock.patch.object(scheduler, "_activity_gate_blocks", return_value=None):
            reason = scheduler._gates_block("weekly_clinical_review", bad, cfg, "mike")
            check("the gate blocks a bad days: value", bool(reason))
            check("and says why, naming the bad value",
                  bool(reason) and "sun" in reason and "not an active day" != reason)

            good = dict(bad, days="sunday")
            check("the same job with days: sunday is not blocked",
                  scheduler._gates_block("weekly_clinical_review", good, cfg, "mike")
                  is None)


# ---------------------------------------------------------------------------
# 3. Registration: skip the bad job loudly, register the good ones
# ---------------------------------------------------------------------------

_GOOD_JOBS = {
    "morning_brief": {"enabled": True, "time": "07:30", "days": "weekdays",
                      "agent": "coordinator"},
    "companion_checkin": {"enabled": True, "interval_minutes": 180,
                          "days": "daily", "agent": "coordinator"},
    "weekend_review": {"enabled": True, "time": "10:00", "days": "weekend",
                       "agent": "coordinator"},
    # A day:-only weekly job — no days: key at all. Must be untouched.
    "weekly_planning": {"enabled": True, "time": "18:00", "day": "sunday",
                        "agent": "coordinator"},
}


def _register(schedules: dict) -> tuple[str, list]:
    """Register `schedules` for a stub persona; return (stdout, schedule.jobs)."""
    schedule.clear()
    buf = io.StringIO()
    with mock.patch.object(scheduler, "_load_config",
                           return_value={"schedules": schedules}), \
         mock.patch.object(scheduler, "_load_agent_schedules", return_value={}), \
         mock.patch.object(scheduler, "_log_error"), \
         redirect_stdout(buf):
        scheduler._register_schedules(persona="mike")
    jobs = list(schedule.jobs)
    schedule.clear()
    return buf.getvalue(), jobs


def part3() -> None:
    print("\n3. _register_schedules — skip-loudly, not daemon-down")

    baseline_out, baseline_jobs = _register(dict(_GOOD_JOBS))
    check("all four good jobs register (plus maintenance defaults)",
          len(baseline_jobs) == len(_GOOD_JOBS) + len(scheduler._DEFAULT_JOBS))
    check("a clean config logs no ERROR",
          "ERROR" not in baseline_out)

    with_bad = dict(_GOOD_JOBS)
    with_bad["weekly_clinical_review"] = {"enabled": True, "time": "18:00",
                                          "days": "sun", "agent": "coordinator"}
    out, jobs = _register(with_bad)

    check("the typo'd job is NOT registered", len(jobs) == len(baseline_jobs))
    check("the daemon still registers the good jobs — one typo takes nothing down",
          len(jobs) == len(_GOOD_JOBS) + len(scheduler._DEFAULT_JOBS))
    check("an ERROR is logged", "ERROR" in out)
    check("the error names the job", "weekly_clinical_review" in out)
    check("the error quotes the bad value", "sun" in out)
    check("the error lists the accepted forms",
          all(w in out for w in ("daily", "weekdays", "weekend", "monday")))

    # The same, for the singular key.
    with_bad_day = dict(_GOOD_JOBS)
    with_bad_day["weekly_clinical_review"] = {"enabled": True, "time": "18:00",
                                              "day": "sun", "agent": "coordinator"}
    out2, jobs2 = _register(with_bad_day)
    check("a bad day: value is refused too", len(jobs2) == len(baseline_jobs))
    check("and its error names job, value and accepted forms",
          "weekly_clinical_review" in out2 and "sun" in out2 and "sunday" in out2)

    # The day:-only weekly job survives all of this untouched.
    weekly_only, _ = _register({"weekly_planning": _GOOD_JOBS["weekly_planning"]})
    check("a day:-only weekly job registers on its day",
          "weekly_planning: sunday at 18:00" in weekly_only)
    check("and logs no ERROR", "ERROR" not in weekly_only)


# ---------------------------------------------------------------------------
# 4. The error repeats — it is not one line at startup
# ---------------------------------------------------------------------------

def part4() -> None:
    print("\n4. _report_invalid_schedules — the error repeats on a cadence")

    with_bad = dict(_GOOD_JOBS)
    with_bad["weekly_clinical_review"] = {"enabled": True, "time": "18:00",
                                          "days": "sun", "agent": "coordinator"}

    def report() -> tuple[str, list]:
        buf = io.StringIO()
        with mock.patch.object(scheduler, "_load_config",
                               return_value={"schedules": with_bad}), \
             mock.patch.object(scheduler, "_load_agent_schedules", return_value={}), \
             mock.patch.object(scheduler, "_log_error"), \
             redirect_stdout(buf):
            bad = scheduler._report_invalid_schedules("mike")
        return buf.getvalue(), bad

    first_out, first = report()
    second_out, second = report()
    check("the invalid job is reported", [n for n, _ in first] == ["weekly_clinical_review"])
    check("and reported again on the next pass — not once at startup",
          [n for n, _ in second] == ["weekly_clinical_review"])
    check("each report is a full ERROR line",
          all("ERROR" in o and "sun" in o and "weekly_clinical_review" in o
              for o in (first_out, second_out)))

    # Re-read from disk each pass, so a typo introduced while the daemon runs
    # is caught without a restart.
    clean_buf = io.StringIO()
    with mock.patch.object(scheduler, "_load_config",
                           return_value={"schedules": _GOOD_JOBS}), \
         mock.patch.object(scheduler, "_load_agent_schedules", return_value={}), \
         mock.patch.object(scheduler, "_log_error"), \
         redirect_stdout(clean_buf):
        clean = scheduler._report_invalid_schedules("mike")
    check("a clean config reports nothing", clean == [])
    check("and prints nothing", clean_buf.getvalue().strip() == "")

    # Agent-written jobs go through the same validation.
    agent_buf = io.StringIO()
    with mock.patch.object(scheduler, "_load_config",
                           return_value={"schedules": _GOOD_JOBS}), \
         mock.patch.object(scheduler, "_load_agent_schedules",
                           return_value={"agent_reminder": {
                               "enabled": True, "time": "09:00", "days": "tues",
                               "agent": "coordinator"}}), \
         mock.patch.object(scheduler, "_log_error"), \
         redirect_stdout(agent_buf):
        bad_agent = scheduler._report_invalid_schedules("mike")
    check("an agent-written job with a bad days: value is caught too",
          [n for n, _ in bad_agent] == ["agent_reminder"])


def main() -> int:
    part1()
    part2()
    part3()
    part4()
    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print(f"All {len(_results)} scheduler day-validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
