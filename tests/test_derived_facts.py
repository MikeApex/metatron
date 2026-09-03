"""
tests/test_derived_facts.py — a stored count is recomputed from its date, not read
back as fact ([DB-0822-06], the derived-count half).

`physical_health` wrote *"Day 3 of 5-day exercise hiatus"* into the health log on
2026-08-21. The hiatus ended 2026-08-23 — Mike's own journal entry. Later runs kept
reading the stored number as current: 08-30 *"day three of your scheduled exercise
hiatus"*, 08-31 *"officially over"* (a week late), 09-02 *"officially wraps up today"*.
Three different wrong states across three days, spanning the 09-01 model migration, so
it is the carried state and not the model.

This half was considered on 2026-08-27 and deliberately not built, with the condition
*"revisit only if a dated count still gets misread after deploy"*. The age annotations
shipped, and the count was misread anyway on three subsequent days — the condition
fired. Dating a sentence ("logged 9 days ago") is not the same as correcting the number
inside it.

The arithmetic is checked against reality below: "Day 3" written on 2026-08-21 puts day
1 at 2026-08-19, so a 5-day period ends 2026-08-23, which is the date Mike's journal
records. That agreement is the evidence the approach is sound, so it is asserted here
rather than left as a comment.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_derived_facts.py

Exits 0 if every check passes, 1 otherwise.
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.orchestrator as ORC  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


LIVE = "Day 3 of 5-day exercise hiatus"
WRITTEN = "2026-08-21"


# ---------------------------------------------------------------------------

@check("the derived end date matches Mike's journal (2026-08-23)")
def _():
    facts = ORC.derived_facts(LIVE, WRITTEN, date(2026, 8, 30))
    assert facts, "the live log line parsed to nothing"
    assert "2026-08-23" in facts[0], facts
    assert "2026-08-19" in facts[0], "day 1 should be derived as 2026-08-19: " + facts[0]


@check("read on 2026-08-30 it says the period ended, and how long ago")
def _():
    facts = ORC.derived_facts(LIVE, WRITTEN, date(2026, 8, 30))
    assert "ENDED" in facts[0], facts
    assert "7 days ago" in facts[0], facts
    assert "not running now" in facts[0], facts


@check("read on 2026-09-02 it does not say the hiatus wraps up today")
def _():
    # The 09-02 08:07 failure verbatim: "officially wraps up today".
    facts = ORC.derived_facts(LIVE, WRITTEN, date(2026, 9, 2))
    assert "ENDED" in facts[0], facts
    assert "10 days ago" in facts[0], facts


@check("while the period is still running it reports the correct current day")
def _():
    facts = ORC.derived_facts(LIVE, WRITTEN, date(2026, 8, 22))
    assert "day 4 of 5" in facts[0], facts
    assert "ENDED" not in facts[0], facts


@check("on the day it was written the count is unchanged")
def _():
    facts = ORC.derived_facts(LIVE, WRITTEN, date(2026, 8, 21))
    assert "day 3 of 5" in facts[0], facts


@check("worded numerals parse the same as digits")
def _():
    facts = ORC.derived_facts("day three of a five-day break", WRITTEN, date(2026, 8, 30))
    assert facts and "2026-08-23" in facts[0], facts


@check("'N days since' is recomputed too")
def _():
    facts = ORC.derived_facts("It has been 3 days since the last run", WRITTEN,
                              date(2026, 8, 30))
    assert facts and "12 days since, not 3" in facts[0], facts


@check("text with no derived count produces nothing at all")
def _():
    for text in ("Slept well, long walk in Greenwich.", "", "5-day forecast looks wet",
                 "Day 3 was hard"):
        assert ORC.derived_facts(text, WRITTEN, date(2026, 8, 30)) == [], text


@check("a nonsensical count is skipped, not guessed at")
def _():
    assert ORC.derived_facts("day 9 of 5-day hiatus", WRITTEN, date(2026, 8, 30)) == []


@check("a missing or unparseable date yields nothing rather than raising")
def _():
    assert ORC.derived_facts(LIVE, "") == []
    assert ORC.derived_facts(LIVE, "not-a-date") == []
    assert ORC.derived_facts(LIVE, None) == []


@check("a log dated in the future is ignored")
def _():
    assert ORC.derived_facts(LIVE, "2026-08-21", date(2026, 8, 20)) == []


@check("the block states it is arithmetic and overrides the text above it")
def _():
    block = ORC.derived_facts_block([(WRITTEN, LIVE)])
    assert "DERIVED FACTS" in block
    assert "the line below is correct and the text is stale" in block, block
    assert "2026-08-23" in block


@check("the same count on several days collapses to one line")
def _():
    block = ORC.derived_facts_block([(WRITTEN, LIVE), (WRITTEN, LIVE), (WRITTEN, LIVE)])
    assert block.count("- ") == 1, block


@check("nothing to say costs nothing — no header, no tokens")
def _():
    assert ORC.derived_facts_block([]) == ""
    assert ORC.derived_facts_block([("2026-08-21", "Slept well.")]) == ""


@check("context assembly feeds both logs and open threads into the block")
def _():
    import inspect
    src = inspect.getsource(ORC.load_recent_context)
    assert "derived_sources.append((d, body))" in src, "recent logs are not fed in"
    assert 'derived_sources.append((t["added"], t.get("text", "")))' in src, (
        "open threads are not fed in — thread text carries the same counts")
    assert "derived_facts_block(derived_sources)" in src, "the block is never built"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
