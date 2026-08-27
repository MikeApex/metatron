"""
tests/test_context_age_annotation.py — [DB-0822-06] stored state carried forward as fact.

On 2026-08-21 the same exercise hiatus was described five different ways in one day — a
derived count ("Day 3 of a 5-day hiatus") was written into the log and read back as current
three days later — and the finished "Metatron sprint" surfaced in 5 of 9 runs. The assembled
context said what was recorded but never when, so nothing in it could be weighed as old.

The intervention under test makes age visible rather than making code decide truth: open
threads and log lines both carry their age into the prompt. Expiry still does the removing.

Run:  python3 tests/test_context_age_annotation.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import _age_annotated, _relative_age, load_recent_context  # noqa: E402
from core.persona import persona_data_dir, persona_scope  # noqa: E402

PERSONA = "context_age_annotation_test"
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


print("_relative_age:")
check("0 days is today", _relative_age(0) == "today")
check("1 day is yesterday", _relative_age(1) == "yesterday")
check("9 days is counted", _relative_age(9) == "9 days ago")

print("\n_age_annotated:")
today = date.today()
nine_ago = (today - timedelta(days=9)).isoformat()
check("an aged thread states its age",
      _age_annotated("Metatron sprint", nine_ago) == "Metatron sprint (logged 9 days ago)",
      _age_annotated("Metatron sprint", nine_ago))
check("a thread opened today says so",
      _age_annotated("Teams link missing", today.isoformat()).endswith("(logged today)"))
check("legacy data with no added date is left alone",
      _age_annotated("old thread", None) == "old thread")
check("an unparseable date is left alone",
      _age_annotated("old thread", "not-a-date") == "old thread")

print("\nload_recent_context — the age reaches the assembled prompt:")
with persona_scope(PERSONA):
    data_dir = persona_data_dir()
    shutil.rmtree(data_dir, ignore_errors=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)

    (data_dir / "context.json").write_text(json.dumps({
        "last_session": today.isoformat(),
        "open_threads": [
            {"text": "Metatron sprint", "added": nine_ago},
            {"text": "Teams link missing from the invite", "added": today.isoformat()},
            "a legacy bare-string thread",
        ],
        "patterns": [],
        "follow_ups": [],
    }))
    three_ago = (today - timedelta(days=3)).isoformat()
    (data_dir / "logs" / f"{three_ago}.json").write_text(
        json.dumps({"date": three_ago, "notes": "Day 3 of a 5-day hiatus"})
    )

    ctx = load_recent_context(days=5)

    check("a nine-day-old thread carries its age",
          "Metatron sprint (logged 9 days ago)" in ctx, ctx[:400])
    check("a thread opened today carries its age",
          "Teams link missing from the invite (logged today)" in ctx)
    check("a legacy bare-string thread still appears, unannotated",
          "a legacy bare-string thread" in ctx
          and "a legacy bare-string thread (logged" not in ctx)
    check("a log line carries its age beside its date",
          f"{three_ago} (3 days ago)" in ctx, ctx[-400:])
    check("the log header says a line is a record, not current state",
          "not necessarily what is true now" in ctx)
    check("the derived count is still shown — code does not rewrite the log",
          "Day 3 of a 5-day hiatus" in ctx)

    shutil.rmtree(data_dir, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All context age-annotation checks passed.")
sys.exit(0)
