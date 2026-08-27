"""
tests/test_log_field_timestamps.py — [DB-0822-06] intraday staleness.

The daily log is one merged file per day, so every value in it carries the same date and
nothing carries a time. On 2026-08-27 the 07:14 run resolved a missing Teams link and the
10:00 run told Mike it was "still missing" — both readings of the same file, both correct
about the date, three hours apart. The day-granular ages shipped in `cbd5ca3` cannot
separate them, and neither can a derived count ("Day 3 of a 5-day hiatus") written into a
field at 10:24 and re-read the next morning.

The intervention: tools/logger.py records when each field was last written, and the context
assembly states that time for today's log. Annotation again, not filtering — nothing here
decides what is still true.

Run:  python3 tests/test_log_field_timestamps.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import _intraday_age, _render_today_log, load_recent_context  # noqa: E402
from core.persona import persona_data_dir, persona_scope  # noqa: E402
from tools.logger import _WRITTEN_AT_KEY, _leaf_paths, read_log, write_log  # noqa: E402
from tools.pattern_miner import get_log_window  # noqa: E402

PERSONA = "log_field_timestamps_test"
FAILURES: list[str] = []
TODAY = date.today()


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


def fresh_dir() -> Path:
    data_dir = persona_data_dir()
    shutil.rmtree(data_dir, ignore_errors=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    return data_dir


print("_leaf_paths — a nested field is stamped as a field, not as its parent:")
check("nested siblings get independent paths",
      sorted(_leaf_paths({"notes": "x", "health": {"energy": "low", "sleep_hours": 7}}))
      == ["health.energy", "health.sleep_hours", "notes"])
check("a list is one leaf, matching the merge semantics",
      _leaf_paths({"tasks_completed": ["a", "b"]}) == ["tasks_completed"])
check("date and the stamp map are not fields a person asserted",
      _leaf_paths({"date": "2026-08-27", _WRITTEN_AT_KEY: {"notes": "x"}, "notes": "y"})
      == ["notes"])


print("\n_intraday_age:")
now = datetime.now()
check("a write seconds old reads as just now",
      _intraday_age((now - timedelta(seconds=30)).isoformat()) == "just now")
check("a write 12 minutes old counts minutes",
      _intraday_age((now - timedelta(minutes=12)).isoformat()) == "12 minutes ago")
check("a write 3 hours old counts hours — the Teams-link case",
      _intraday_age((now - timedelta(hours=3)).isoformat()) == "3 hours ago",
      _intraday_age((now - timedelta(hours=3)).isoformat()))
check("no timestamp yields no claim about age", _intraday_age(None) == "")
check("an unparseable timestamp yields no claim", _intraday_age("not-a-time") == "")


print("\nwrite_log — every field records when it was asserted:")
with persona_scope(PERSONA):
    fresh_dir()

    write_log({"notes": "Teams link still missing", "health": {"sleep_hours": 7.5}})
    first = read_log()
    stamps = first.get(_WRITTEN_AT_KEY) or {}
    check("a written scalar is stamped", "notes" in stamps, str(stamps))
    check("a nested field is stamped by its full path", "health.sleep_hours" in stamps)
    check("the date is not stamped as an assertion", "date" not in stamps)
    first_notes_stamp = stamps.get("notes")

    # The second write of the day — the case _deep_merge exists for, now also the case
    # per-field ages exist for.
    write_log({"health": {"energy": "low"}})
    second = read_log()
    stamps2 = second.get(_WRITTEN_AT_KEY) or {}
    check("an untouched field keeps the time it was actually asserted",
          stamps2.get("notes") == first_notes_stamp)
    check("the newly written sibling is stamped", "health.energy" in stamps2)
    check("the morning's sibling value survives the evening write",
          second["health"].get("sleep_hours") == 7.5)

    print("\nwrite_log — a model cannot stamp its own freshness:")
    forged = (TODAY - timedelta(days=400)).isoformat() + "T00:00:00"
    write_log({"notes": "rewritten", _WRITTEN_AT_KEY: {"notes": forged}})
    third = read_log()
    check("a model-supplied write time is discarded",
          (third.get(_WRITTEN_AT_KEY) or {}).get("notes") != forged,
          str(third.get(_WRITTEN_AT_KEY)))
    check("the stamp the code recorded is today's",
          str((third.get(_WRITTEN_AT_KEY) or {}).get("notes", "")).startswith(TODAY.isoformat()))

    print("\nA log file written before this shipped still merges and reads:")
    fresh_dir()
    legacy_path = persona_data_dir() / "logs" / f"{TODAY.isoformat()}.json"
    legacy_path.write_text(json.dumps({"date": TODAY.isoformat(), "mood": "flat"}))
    write_log({"focus": "sharp"})
    merged = read_log()
    check("the legacy field survives", merged.get("mood") == "flat")
    check("the legacy field has no invented stamp",
          "mood" not in (merged.get(_WRITTEN_AT_KEY) or {}))
    check("the new field is stamped", "focus" in (merged.get(_WRITTEN_AT_KEY) or {}))

    print("\nget_log_window — the Pattern Miner is not billed for timestamps:")
    window = get_log_window(TODAY.isoformat(), TODAY.isoformat(), persona=PERSONA)
    check("the stamp map is stripped from the mining window",
          bool(window) and _WRITTEN_AT_KEY not in window[0], str(window))
    check("the log content itself is intact", bool(window) and window[0].get("focus") == "sharp")

    print("\nload_recent_context — the hour reaches the assembled prompt:")
    fresh_dir()
    three_hours = (now - timedelta(hours=3)).isoformat(timespec="seconds")
    twelve_min = (now - timedelta(minutes=12)).isoformat(timespec="seconds")
    (persona_data_dir() / "logs" / f"{TODAY.isoformat()}.json").write_text(json.dumps({
        "date": TODAY.isoformat(),
        "notes": "Teams link still missing",
        "health": {"energy": "low"},
        _WRITTEN_AT_KEY: {"notes": three_hours, "health.energy": twelve_min},
    }))
    older = (TODAY - timedelta(days=3)).isoformat()
    (persona_data_dir() / "logs" / f"{older}.json").write_text(
        json.dumps({"date": older, "notes": "Day 3 of a 5-day hiatus"})
    )

    ctx = load_recent_context(days=5)

    check("today's three-hour-old field states the hours",
          '"Teams link still missing" (recorded 3 hours ago)' in ctx, ctx[-600:])
    check("today's twelve-minute-old field states the minutes",
          "health.energy=\"low\" (recorded 12 minutes ago)" in ctx, ctx[-600:])
    check("the two fields are dated apart, which one merged date could never do",
          "3 hours ago" in ctx and "12 minutes ago" in ctx)
    check("the stamp map itself never reaches the prompt", _WRITTEN_AT_KEY not in ctx)
    check("an earlier day keeps its single-line dump and day count",
          f"{older} (3 days ago)" in ctx and '{"date"' in ctx, ctx[-600:])
    check("the derived count is still shown — code does not rewrite the log",
          "Day 3 of a 5-day hiatus" in ctx)

    print("\nA today-log with no stamps renders exactly as it did before:")
    fresh_dir()
    (persona_data_dir() / "logs" / f"{TODAY.isoformat()}.json").write_text(
        json.dumps({"date": TODAY.isoformat(), "mood": "flat"})
    )
    ctx2 = load_recent_context(days=5)
    check("the pre-existing one-line form is used when nothing is stamped",
          f"{TODAY.isoformat()} (today): " + '{"date"' in ctx2, ctx2[-400:])

    print("\n_render_today_log in isolation:")
    rendered = _render_today_log({
        "date": TODAY.isoformat(), "notes": "x",
        _WRITTEN_AT_KEY: {"notes": three_hours},
    })
    check("a stamped field carries its age", rendered == 'notes="x" (recorded 3 hours ago)',
          rendered)
    unstamped = _render_today_log({"date": TODAY.isoformat(), "notes": "x"})
    check("an unstamped field makes no claim about its age", unstamped == 'notes="x"', unstamped)

    shutil.rmtree(persona_data_dir(), ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All log field-timestamp checks passed.")
sys.exit(0)
