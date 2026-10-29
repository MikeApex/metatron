"""
tests/test_habit_done_words.py — a habit's own words report it done, so the user is not asked
for what they already said [DB-1029-03].

Mike, 2026-10-29, on the daily meals-and-snacks habit: "Metatron should consider unsolicited
completion of the habit a good reason to not then prompt the user." The planner already holds
back a done occurrence; what was missing is the report itself. completion_hints() fired only on
a clause with a "done" word that also named the task — "for breakfast I had eggs" carries
neither for a task called "Log meals and snacks". A habit may now carry `done_words`.

    python3 tests/test_habit_done_words.py
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.day_plan_config as C  # noqa: E402
import tools.obligations as O  # noqa: E402

C._OVERRIDE = {"flags": {"ledger_fields": False, "unconfirmed_rule": False}}
_TMP = Path(tempfile.mkdtemp(prefix="habit_done_words_"))
_CLOCK = {"now": datetime(2026, 10, 29, 9, 0, 0)}
O._now = lambda: _CLOCK["now"]

_results: list[tuple[str, bool, str]] = []


def check(name):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


def _fresh(name: str) -> None:
    d = _TMP / name
    d.mkdir(parents=True, exist_ok=True)
    O.persona_data_dir = lambda persona=None, _d=d: _d


def _meals() -> str:
    msg = O.open_task("Log meals and snacks", kind="habit", every="day", times=3,
                      done_words=["breakfast", "lunch", "dinner", "snack", "ate", "Lunch", "a"])
    assert msg.startswith("task "), msg
    return msg.split()[1]


@check("done_words are stored cleaned: lower-case, deduplicated, no short words")
def _():
    _fresh("store")
    tid = _meals()
    t = next(t for t in O._load() if t["id"] == tid)
    assert t["done_words"] == ["breakfast", "lunch", "dinner", "snack", "ate"], t["done_words"]


@check("an unprompted meal report with no 'done' word is hinted as completing the habit")
def _():
    _fresh("hint")
    tid = _meals()
    note = O.completion_hints("For breakfast I had two soft-boiled eggs and some crackers")
    assert tid in note, note


@check("a negated report is not")
def _():
    _fresh("neg")
    tid = _meals()
    assert tid not in O.completion_hints("I haven't had lunch yet")


@check("without done_words the same sentence says nothing — the old behaviour, unchanged")
def _():
    _fresh("old")
    O.open_task("Log meals and snacks", kind="habit", every="day", times=3)
    assert O.completion_hints("For breakfast I had two soft-boiled eggs") == ""


@check("once today's three are recorded, a fourth meal is not hinted")
def _():
    _fresh("full")
    tid = _meals()
    for i in range(3):
        _CLOCK["now"] = datetime(2026, 10, 29, 9 + 3 * i, 0, 0)
        out = O.update_task(tid, "done", evidence=f"meal {i + 1}")
        assert "error" not in out.lower(), out
    _CLOCK["now"] = datetime(2026, 10, 29, 21, 0, 0)
    assert tid not in O.completion_hints("had a snack of crackers and brie"), "over-completes"


@check("done_words on a one-off deadline are ignored")
def _():
    _fresh("deadline")
    msg = O.open_task("Pay Chase credit card bill", kind="deadline", done_words=["chase"])
    tid = msg.split()[1]
    assert "done_words" not in next(t for t in O._load() if t["id"] == tid)


if __name__ == "__main__":
    failed = [r for r in _results if not r[1]]
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if not ok else ""))
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
