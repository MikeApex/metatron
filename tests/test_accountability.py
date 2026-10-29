"""
tests/test_accountability.py — Accountability Index (DEV_BACKLOG.md [DB-0827-09]).

Follows the check-decorator convention used by tests/test_analytics_rollup.py and
tests/test_obligation_due_sort.py (no pytest in this environment). Every fixture is
synthetic data written to a tempdir or passed in as plain dicts/lists — never real
persona data under data/personas/.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.accountability as ACC  # noqa: E402
import tools.analytics as A  # noqa: E402

_results = []


def check(name):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


def _intention(intention: str, logged_date: str, stated_for: str = "") -> dict:
    return {"intention": intention, "logged_date": logged_date, "stated_for": stated_for}


def _event(title: str, start_date: str) -> dict:
    return {"title": title, "start": f"{start_date}T09:00:00", "end": f"{start_date}T10:00:00"}


def _closed_obligation(what: str, closed_date: str) -> dict:
    return {"what": what, "status": "closed", "closed_at": f"{closed_date}T18:00:00"}


def _write_log(tmp: Path, persona: str, day: str, content: dict) -> None:
    d = tmp / "data" / "personas" / persona / "logs"
    d.mkdir(parents=True, exist_ok=True)
    body = dict(content)
    body["date"] = day
    (d / f"{day}.json").write_text(json.dumps(body))


# ---------------------------------------------------------------------------
# 1. Dated intention fulfilled within grace
# ---------------------------------------------------------------------------

@check("a dated intention with a matching calendar event inside the grace window is fulfilled")
def _():
    i = _intention("go for a run", "2026-08-10", stated_for="2026-08-12")
    events = [_event("go for a run", "2026-08-13")]  # 1 day into the 2-day grace
    item = ACC.resolve_intention(i, events, [], as_of=date(2026, 8, 20))
    assert item["verdict"] == "fulfilled", item
    assert "calendar" in item["reason"], item


# ---------------------------------------------------------------------------
# 2. Fulfilled outside grace -> unfulfilled
# ---------------------------------------------------------------------------

@check("a matching event that lands after the grace window closes is unfulfilled, not fulfilled")
def _():
    i = _intention("go for a run", "2026-08-10", stated_for="2026-08-12")
    # window is [08-12, 08-14]; event lands on 08-17, well outside it
    events = [_event("go for a run", "2026-08-17")]
    item = ACC.resolve_intention(i, events, [], as_of=date(2026, 8, 20))
    assert item["verdict"] == "unfulfilled", item
    assert "outside the grace window" in item["reason"], item


# ---------------------------------------------------------------------------
# 3. Undated intention defaults to 7 days
# ---------------------------------------------------------------------------

@check("an undated intention gets a 7-day window from the day it was logged")
def _():
    i = _intention("start running again", "2026-08-01")
    start, end = ACC.intention_window(i)
    assert start == date(2026, 8, 1), (start, end)
    assert end == date(2026, 8, 8), (start, end)  # +7 days


@check("an undated intention fulfilled on day 6 of 7 is fulfilled")
def _():
    i = _intention("clean the garage", "2026-08-01")
    obligations = [_closed_obligation("clean the garage", "2026-08-07")]
    item = ACC.resolve_intention(i, [], obligations, as_of=date(2026, 8, 20))
    assert item["verdict"] == "fulfilled", item


@check("an undated intention with a close on day 9 (past the 7-day default) is unfulfilled")
def _():
    i = _intention("clean the garage", "2026-08-01")
    obligations = [_closed_obligation("clean the garage", "2026-08-10")]
    item = ACC.resolve_intention(i, [], obligations, as_of=date(2026, 8, 20))
    assert item["verdict"] == "unfulfilled", item


# ---------------------------------------------------------------------------
# 4. Free-text / unmatched -> indeterminate with reason
# ---------------------------------------------------------------------------

@check("no structured match anywhere, window closed: indeterminate, awaiting judgment gate")
def _():
    i = _intention("reconnect with an old friend", "2026-08-01")
    item = ACC.resolve_intention(i, [], [], as_of=date(2026, 8, 20))
    assert item["verdict"] == "indeterminate", item
    assert "awaiting judgment gate" in item["reason"], item


@check("no structured match yet but window still open: indeterminate, window still open — not unfulfilled")
def _():
    i = _intention("reconnect with an old friend", "2026-08-18")
    item = ACC.resolve_intention(i, [], [], as_of=date(2026, 8, 19))  # window runs to 08-25
    assert item["verdict"] == "indeterminate", item
    assert item["reason"] == "window still open", item


# ---------------------------------------------------------------------------
# 5. Trailing-30d rate math
# ---------------------------------------------------------------------------

@check("fulfilment rate excludes indeterminate from the denominator")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # 2 fulfilled, 1 unfulfilled, 1 indeterminate, all inside the trailing window
        _write_log(tmp, "t", "2026-08-01", {"intention": "run 5k", "stated_for": "2026-08-02"})
        _write_log(tmp, "t", "2026-08-03", {"intention": "call the plumber", "stated_for": "2026-08-04"})
        _write_log(tmp, "t", "2026-08-05", {"intention": "finish the tax forms", "stated_for": "2026-08-06"})
        _write_log(tmp, "t", "2026-08-07", {"intention": "read that book"})  # undated, no match ever

        events = [_event("run 5k", "2026-08-03")]  # fulfilled, within grace
        obligations = [
            _closed_obligation("call the plumber", "2026-08-20"),  # closed way outside grace
        ]
        idx = ACC.build_index("t", as_of=date(2026, 8, 25), trailing_days=30, root=tmp,
                               calendar_events=events, obligations=obligations)
        c = idx["counts"]
        assert c["fulfilled"] == 1, c
        assert c["unfulfilled"] == 1, c
        assert c["indeterminate"] == 2, c
        assert idx["fulfilment_rate"] == 0.5, idx  # 1 / (1 + 1), indeterminate excluded


@check("an intention logged outside the trailing window is not read at all")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log(tmp, "t", "2026-06-01", {"intention": "ancient plan"})
        idx = ACC.build_index("t", as_of=date(2026, 8, 25), trailing_days=30, root=tmp,
                               calendar_events=[], obligations=[])
        assert idx["counts"]["total"] == 0, idx


# ---------------------------------------------------------------------------
# 6. Analytics rollup accountability counts are content-free
# ---------------------------------------------------------------------------

@check("daily_accountability_counts returns counts only, never carries the intention text")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log(tmp, "t", "2026-08-10", {"intention": "SECRET-CONFESS-TO-MOM"})
        counts = ACC.daily_accountability_counts("2026-08-10", "t", root=tmp)
        blob = json.dumps(counts)
        assert "SECRET-CONFESS-TO-MOM" not in blob, blob
        assert set(counts) == {
            "intentions_stated", "intentions_resolved_fulfilled",
            "intentions_resolved_unfulfilled", "intentions_resolved_indeterminate",
        }, counts
        assert counts["intentions_stated"] == 1, counts


@check("the A9 daily rollup row carries accountability counts and no intention text")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        A.ROOT = tmp
        # a trace so rollup_day produces a row at all
        traces = tmp / "data" / "personas" / "t" / "traces"
        traces.mkdir(parents=True, exist_ok=True)
        (traces / "2026-08-18.jsonl").write_text(json.dumps({
            "ts": "2026-08-18T09:00:00", "is_proactive": False, "duration_ms": 1000,
            "pipeline": [],
        }) + "\n")
        _write_log(tmp, "t", "2026-08-18", {"intention": "SECRET-DO-NOT-LEAK", "stated_for": "2026-08-19"})

        row = A.rollup_day("2026-08-18", "t")
        assert row is not None
        assert row["intentions_stated"] == 1, row
        blob = json.dumps(row)
        assert "SECRET-DO-NOT-LEAK" not in blob, blob


# ---------------------------------------------------------------------------
# Open ledger tasks join in code (2026-10-29 audit: 13 of 14 verdicts indeterminate)
# ---------------------------------------------------------------------------

def _open_task(what: str, due: str = "", eligible_from: str = "") -> dict:
    return {"what": what, "status": "open", "opened_at": "2026-10-15T10:00:00",
            "due": due or None, "eligible_from": eligible_from or None}


@check("an intention that is still an open, overdue task after its window is unfulfilled")
def _():
    i = _intention("Post a hybrid programmer/babysitter job next week", "2026-10-15")
    ob = [_open_task("Post hybrid programmer/babysitter job", due="2026-10-20")]
    item = ACC.resolve_intention(i, [], ob, as_of=date(2026, 10, 29))
    assert item["verdict"] == "unfulfilled", item
    assert "open task" in item["reason"] and not item["reason"].startswith(ACC._AWAITING_GATE), item


@check("an open task the user rescheduled past today is not counted as a failure")
def _():
    i = _intention("Post a hybrid programmer/babysitter job next week", "2026-10-15")
    ob = [_open_task("Post hybrid programmer/babysitter job", due="2026-10-30")]
    item = ACC.resolve_intention(i, [], ob, as_of=date(2026, 10, 29))
    assert item["verdict"] == "indeterminate", item
    assert "not due until 2026-10-30" in item["reason"], item
    assert not item["reason"].startswith(ACC._AWAITING_GATE), "must not spend a gate call"


@check("an open task deferred by the user is not counted as a failure")
def _():
    i = _intention("review the Schwab treasury notes", "2026-10-15")
    ob = [_open_task("Review Schwab treasury note maturities", due="2026-10-20",
                     eligible_from="2026-11-02")]
    item = ACC.resolve_intention(i, [], ob, as_of=date(2026, 10, 29))
    assert item["verdict"] == "indeterminate" and "2026-11-02" in item["reason"], item


@check("one shared word is not a match — 'book dentist' is not 'Book flights for the US trip'")
def _():
    i = _intention("book dentist", "2026-10-01")
    ob = [_open_task("Book flights for the US trip", due="2026-10-05")]
    item = ACC.resolve_intention(i, [], ob, as_of=date(2026, 10, 29))
    assert item["reason"].startswith(ACC._AWAITING_GATE), item


@check("while the window is open, an open task changes nothing")
def _():
    i = _intention("Post a hybrid programmer/babysitter job next week", "2026-10-25")
    ob = [_open_task("Post hybrid programmer/babysitter job", due="2026-10-20")]
    item = ACC.resolve_intention(i, [], ob, as_of=date(2026, 10, 29))
    assert item["reason"] == "window still open", item


@check("a closed match still wins over an open task of the same name")
def _():
    i = _intention("Post a hybrid programmer/babysitter job next week", "2026-10-15")
    ob = [_open_task("Post hybrid programmer/babysitter job", due="2026-10-20"),
          _closed_obligation("Post hybrid programmer/babysitter job", "2026-10-18")]
    item = ACC.resolve_intention(i, [], ob, as_of=date(2026, 10, 29))
    assert item["verdict"] == "fulfilled", item


if __name__ == "__main__":
    for n, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
        if not ok:
            print(f"        {detail}")
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results)-failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
