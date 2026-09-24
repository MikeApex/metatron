"""
tests/test_build_registry.py — the run line, and where its numbers come from.

TWO CLAIMS UNDER TEST.

1. A LANDED CAPABILITY CANNOT BE REGISTERED WITHOUT A RUN LINE.
   scripts/check_build_registration.py asserts that a `landed` row carries
   `run.execution_mode`, and the only way to be certain that assertion never
   fires is for the function that writes the landing to write the run line in
   the same call. A plan missing execution_mode or latency_budget_ms is refused
   here rather than landing something whose standing cost nothing meters.

2. THE DISPATCH COUNT COMES FROM THE TRACES, COUNTING AGENT NAMES.
   Plan section 14 claimed tools/analytics.py "already counts dispatch per
   specialist"; it counts TOOL names (_walk_tools -> top_tools) and never agent
   names. The test that matters is the one that would have caught that: a trace
   in which a capability is DISPATCHED but calls no tools must still be counted,
   because a tool-name counter reports zero for exactly that record.
   (Correction v3.5 C1.)

Standalone runner, no pytest, matching tests/ convention.

Usage:
    python3 tests/test_build_registry.py
"""

import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.jobs as J          # noqa: E402
import core.build.registry as R      # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_registry_test_"))
PERSONA = "mike"


def _data_dir(persona=None):
    return TMP / "personas" / (persona or PERSONA)


J.persona_data_dir = _data_dir
R.persona_data_dir = _data_dir


def reset() -> None:
    shutil.rmtree(TMP / "personas", ignore_errors=True)
    J.build_dir(PERSONA).mkdir(parents=True, exist_ok=True)


def plan_for(cap_id: str, kind: str = "agent", mode: str = "blocking",
             budget: int = 8000, theme: str = "", replaces=None) -> dict:
    return {"capability": {"id": cap_id, "kind": kind, "execution_mode": mode,
                           "latency_budget_ms": budget, "theme": theme,
                           "one_line": f"{cap_id} does one thing",
                           "disposition": "new", "replaces": replaces or []}}


def write_trace(day: str, pipeline: list) -> None:
    directory = _data_dir(PERSONA) / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / f"{day}.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"pipeline": pipeline}) + "\n")


def land_on(job_id: str, cap_id: str, day: str) -> None:
    """
    Record a landing and back-date it, so a later day counts as a full day.

    The window that matters starts the day AFTER a capability lands: a partial
    landing day in the denominator always understates the rate, and its trace
    file frequently holds only Build's own tick.
    """
    R.record_landing(job_id, plan_for(cap_id), [], PERSONA)
    path = R.registry_path(PERSONA)
    rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    rows[-1]["at"] = f"{day}T09:00:00"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


# ---------------------------------------------------------------------------
# The run line
# ---------------------------------------------------------------------------

@check("a landing writes a run line, and check_build_registration's assertion cannot fire")
def _():
    reset()
    row = R.record_landing("BLD-0919-01", plan_for("home_care"), ["a.md"], PERSONA)
    assert row["state"] == "landed", row
    run = row["run"]
    assert run["execution_mode"] == "blocking", run
    assert run["latency_budget_ms"] == 8000, run
    # The sweep's own assertion, run against what was just written.
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_build_registration as C
    overlay = J.build_dir(PERSONA) / "overlay"
    overlay.mkdir(parents=True, exist_ok=True)
    assert C._findings_run_lines([overlay]) == [], "the sweep found a landing it should not"


@check("a plan with no execution_mode or budget is REFUSED, not landed without a meter")
def _():
    reset()
    for broken in ({"capability": {"id": "x_cap", "latency_budget_ms": 100}},
                   {"capability": {"id": "x_cap", "execution_mode": "blocking"}},
                   {"capability": {"execution_mode": "blocking",
                                   "latency_budget_ms": 100}}):
        try:
            R.record_landing("BLD-0919-01", broken, [], PERSONA)
            raise AssertionError(f"landed without a run line: {broken}")
        except R.RegistryError:
            pass


@check("dispatches_actual is None at landing, never 0 — no day has passed")
def _():
    reset()
    row = R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    assert row["run"]["dispatches_actual_per_day"] is None, row["run"]
    # 0 would read as "nothing routes to it" on the one day that cannot show one.


@check("a re-landing is a new row at v2 — the file is history, not a record to edit")
def _():
    reset()
    R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    second = R.record_landing("BLD-0919-02", plan_for("home_care"), [], PERSONA)
    assert second["version"] == 2, second
    assert len(R.read_rows(PERSONA)) == 2
    assert R.capabilities(PERSONA)["home_care"]["version"] == 2


@check("a retirement is appended and removes the capability from the live set")
def _():
    reset()
    R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    R.record_retirement("home_care", "BLD-0919-01", "promoted into the tree", PERSONA)
    assert "home_care" not in R.capabilities(PERSONA)
    assert "home_care" in R.capabilities(PERSONA, live_only=False)


@check("a torn line is skipped, not fatal — one bad write must not lose the rest")
def _():
    reset()
    R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    with open(R.registry_path(PERSONA), "a", encoding="utf-8") as handle:
        handle.write('{"row_type": "capability", "state": "lan\n')
    R.record_landing("BLD-0919-02", plan_for("garden"), [], PERSONA)
    live = R.capabilities(PERSONA)
    assert set(live) == {"home_care", "garden"}, sorted(live)


# ---------------------------------------------------------------------------
# Dispatch counting — the C1 correction
# ---------------------------------------------------------------------------

@check("a capability DISPATCHED but calling no tools is still counted")
def _():
    # THE TEST THAT WOULD HAVE CAUGHT THE PLAN'S CLAIM. tools/analytics.py counts
    # tool names, so this record contributes ZERO to top_tools while being a real
    # dispatch. Counting agent names is the whole difference.
    reset()
    today = date.today().isoformat()
    write_trace(today, [{"agent": "coordinator", "turns": [],
                         "subagents": [{"agent": "home_care", "turns": []}]}])
    counts, days = R.dispatch_counts(PERSONA, days=1)
    assert counts["home_care"] == 1, dict(counts)
    assert days == 1, days


@check("nested specialists are counted — a top-level-only walk reports zero for every one")
def _():
    reset()
    today = date.today().isoformat()
    write_trace(today, [{"agent": "coordinator",
                         "subagents": [{"agent": "home_care"},
                                       {"agent": "logistics",
                                        "subagents": [{"agent": "home_care"}]}]}])
    counts, _days = R.dispatch_counts(PERSONA, days=1)
    assert counts["home_care"] == 2, dict(counts)
    assert counts["logistics"] == 1, dict(counts)


@check("MEASURED days are returned, not days asked for — a stopped VM must not deflate the rate")
def _():
    reset()
    today = date.today()
    write_trace(today.isoformat(), [{"agent": "coordinator",
                                     "subagents": [{"agent": "home_care"}]}])
    write_trace((today - timedelta(days=1)).isoformat(),
                [{"agent": "coordinator", "subagents": [{"agent": "home_care"}]}])
    counts, days = R.dispatch_counts(PERSONA, days=7)
    assert days == 2, f"asked for 7, only 2 files exist, got {days}"
    assert counts["home_care"] == 2, dict(counts)
    land_on("BLD-0919-01", "home_care", (today - timedelta(days=3)).isoformat())
    R.refresh_run_counts(PERSONA, days=7)
    run = R.capabilities(PERSONA)["home_care"]["run"]
    assert run["dispatches_actual_per_day"] == 1.0, run
    assert run["counted_over_days"] == 2, run


@check("refresh is a no-op with nothing landed, and says so")
def _():
    reset()
    assert "nothing landed" in R.refresh_run_counts(PERSONA)


@check("a refresh appends rather than editing — the landing row survives")
def _():
    reset()
    land_on("BLD-0919-01", "home_care",
            (date.today() - timedelta(days=2)).isoformat())
    write_trace(date.today().isoformat(),
                [{"agent": "coordinator", "subagents": [{"agent": "home_care"}]}])
    R.refresh_run_counts(PERSONA, days=1)
    rows = R.read_rows(PERSONA)
    assert len(rows) == 2, rows
    assert rows[0]["run"]["dispatches_actual_per_day"] is None, rows[0]
    assert rows[1]["run"]["dispatches_actual_per_day"] == 1.0, rows[1]


# ---------------------------------------------------------------------------
# REVIEW ROUND 2 — the Fable 5.1 re-check
# ---------------------------------------------------------------------------

@check("REVIEW N3: the LANDING DAY is not a measured day — actual stays None, never 0.0")
def _():
    # On the day a capability lands, the trace file exists because the tick
    # that landed it wrote one. Counting that as a day gave `actual 0.0 over
    # 1d` about a capability nothing had yet had a chance to dispatch — the
    # "it never fires" verdict the contract forbids inferring from an
    # inability to count.
    reset()
    today = date.today().isoformat()
    R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    write_trace(today, [{"agent": "build",
                         "subagents": [{"agent": "build_planner"}]}])
    out = R.refresh_run_counts(PERSONA, days=7)
    assert "no full day of use since landing" in out, out
    run = R.capabilities(PERSONA)["home_care"]["run"]
    assert run["dispatches_actual_per_day"] is None, run
    assert run["counted_over_days"] is None, run


@check("REVIEW N3: a day holding ONLY Build's own ticks does not count as a day")
def _():
    reset()
    today = date.today()
    land_on("BLD-0919-01", "home_care", (today - timedelta(days=4)).isoformat())
    # Yesterday: only the tick. Today: a real exchange that dispatched it.
    write_trace((today - timedelta(days=1)).isoformat(),
                [{"agent": "build", "subagents": [{"agent": "build_inquiry"}]}])
    write_trace(today.isoformat(),
                [{"agent": "coordinator", "subagents": [{"agent": "home_care"}]}])
    counts, measured = R.dispatch_counts(PERSONA, days=7)
    assert measured == 1, f"a tick-only day was counted as a day of use: {measured}"
    assert counts["home_care"] == 1, dict(counts)
    assert counts["build_inquiry"] == 0, dict(counts)
    R.refresh_run_counts(PERSONA, days=7)
    run = R.capabilities(PERSONA)["home_care"]["run"]
    assert run["dispatches_actual_per_day"] == 1.0, run
    assert run["counted_over_days"] == 1, run


@check("REVIEW N3: the window is per capability — a later landing gets its own denominator")
def _():
    reset()
    today = date.today()
    land_on("BLD-0919-01", "old_care", (today - timedelta(days=5)).isoformat())
    land_on("BLD-0919-02", "new_care", (today - timedelta(days=1)).isoformat())
    for back in (3, 2, 1, 0):
        write_trace((today - timedelta(days=back)).isoformat(),
                    [{"agent": "coordinator",
                      "subagents": [{"agent": "old_care"}, {"agent": "new_care"}]}])
    R.refresh_run_counts(PERSONA, days=7)
    live = R.capabilities(PERSONA)
    # old_care: four days of use since it landed. new_care: only today.
    assert live["old_care"]["run"]["counted_over_days"] == 4, live["old_care"]["run"]
    assert live["new_care"]["run"]["counted_over_days"] == 1, live["new_care"]["run"]


# ---------------------------------------------------------------------------
# The tier count
# ---------------------------------------------------------------------------

@check("the tier count is LEAVES under Coord — a themed capability does not count")
def _():
    reset()
    R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    R.record_landing("BLD-0919-02", plan_for("venue_finder", theme="logistics"),
                     [], PERSONA)
    R.record_landing("BLD-0919-03", plan_for("a_policy", kind="policy"), [], PERSONA)
    status = R.tier_status(PERSONA)
    assert status["leaves"] == 1, status      # only home_care: agent, no theme
    assert status["due_at"] == 4 and not status["due"], status


@check("the tier becomes DUE at the fourth leaf")
def _():
    reset()
    for i, name in enumerate(("a_care", "b_care", "c_care", "d_care"), start=1):
        R.record_landing(f"BLD-0919-{i:02d}", plan_for(name), [], PERSONA)
    status = R.tier_status(PERSONA)
    assert status["leaves"] == 4 and status["due"], status


# ---------------------------------------------------------------------------
# The tracked markdown
# ---------------------------------------------------------------------------

@check("the generated markdown carries NO capability description — it becomes a tracked file")
def _():
    reset()
    plan = plan_for("home_care")
    plan["capability"]["one_line"] = "SECRETDESCRIPTION about the household"
    R.record_landing("BLD-0919-01", plan, [], PERSONA)
    body = R.render_markdown(PERSONA)
    assert "SECRETDESCRIPTION" not in body, (
        "one_line is model-written prose about a gap the user filed, and this file "
        "is committed to git")
    assert "home_care" in body and "blocking" in body, body


@check("the markdown reports the tier count against its due figure")
def _():
    reset()
    R.record_landing("BLD-0919-01", plan_for("home_care"), [], PERSONA)
    assert "1 of 4" in R.render_markdown(PERSONA)
    reset()
    assert "Nothing has landed yet" in R.render_markdown(PERSONA)


def main() -> int:
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))
    passed = sum(1 for _n, ok, _d in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
