"""
tests/test_analytics_rollup.py — A9 rollup (tools/analytics.py).

The two that matter most are the content-free assertion and the cohort pin: both
are schema properties that cannot be repaired retroactively, unlike the metric
definitions, which are re-derivable from retained traces.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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


def _fixture(tmp: Path, day: str, records: list[dict]) -> None:
    d = tmp / "data" / "personas" / "t" / "traces"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{day}.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")


def _rec(proactive: bool, tools: list[str], dur=60000):
    return {
        "ts": "2026-08-18T09:00:00", "is_proactive": proactive, "duration_ms": dur,
        "user_input": "SECRET-INPUT", "synth_response": "SECRET-RESPONSE",
        "pipeline": [{"agent": "coordinator", "turns": [
            {"turn": 1, "input_tokens": 10, "output_tokens": 5,
             "output_text": "SECRET-OUTPUT",
             "tool_calls": [{"name": t, "args": {"to": "SECRET@example.com"},
                             "ok": True, "result_preview": "SECRET-PREVIEW"} for t in tools]}]}],
    }


@check("a world-affecting call in a proactive trace counts as T3 autonomous")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18", [_rec(True, ["send_email"])])
        row = A.rollup_day("2026-08-18", "t")
        assert row["absorbed_t3_autonomous"] == 1, row
        assert row["absorbed_user_present"] == 0, row
        assert row["absorbed_total"] == 1, row


@check("the same call in a user-initiated trace is not counted autonomous")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18", [_rec(False, ["send_email"])])
        row = A.rollup_day("2026-08-18", "t")
        assert row["absorbed_t3_autonomous"] == 0, row
        assert row["absorbed_user_present"] == 1, row


@check("internal bookkeeping is NOT absorbed work — the headline must not inflate")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18",
                 [_rec(False, ["write_log", "write_journal", "write_wisdom", "read_log"])])
        row = A.rollup_day("2026-08-18", "t")
        assert row["absorbed_total"] == 0, row
        assert row["tool_calls"] == 4, row


@check("attention is recorded as a denominator, not as absorbed work")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18",
                 [_rec(False, ["send_email"]), _rec(False, []), _rec(True, [])])
        row = A.rollup_day("2026-08-18", "t")
        assert row["user_sessions"] == 2 and row["proactive_sessions"] == 1, row
        assert row["absorbed_per_user_session"] == 0.5, row


@check("EVERY row is content-free — no input, response, args or previews leak")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18", [_rec(False, ["send_email"]), _rec(True, ["write_log"])])
        blob = json.dumps(A.rollup_day("2026-08-18", "t"))
        for secret in ("SECRET-INPUT", "SECRET-RESPONSE", "SECRET-OUTPUT",
                       "SECRET-PREVIEW", "SECRET@example.com"):
            assert secret not in blob, f"{secret} leaked into the rollup row: {blob}"


@check("cohort anchor is pinned once and survives losing older traces")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-01", [_rec(False, [])])
        _fixture(tmp, "2026-08-18", [_rec(False, [])])
        assert A.rollup_day("2026-08-18", "t")["cohort_day"] == 17
        # prune the earliest trace — the anchor must NOT move forward
        (tmp / "data/personas/t/traces/2026-08-01.jsonl").unlink()
        again = A.rollup_day("2026-08-18", "t")
        assert again["first_use"] == "2026-08-01", again
        assert again["cohort_day"] == 17, again


@check("write_rollup is idempotent per day — a rerun replaces, never duplicates")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18", [_rec(False, ["send_email"])])
        A.write_rollup("2026-08-18", "t")
        A.write_rollup("2026-08-18", "t")
        rows = [json.loads(l) for l in
                (tmp / "data/personas/t/analytics/daily.jsonl").read_text().splitlines() if l.strip()]
        assert len(rows) == 1, rows


@check("a day with no traces yields no row rather than a fake zero row")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); A.ROOT = tmp
        _fixture(tmp, "2026-08-18", [_rec(False, [])])
        assert A.rollup_day("2026-08-17", "t") is None


@check("the scheduler entry point never raises, even with no persona resolvable")
def _():
    with tempfile.TemporaryDirectory() as td:
        A.ROOT = Path(td)
        out = A.rollup_yesterday()
        assert isinstance(out, str) and out, out


if __name__ == "__main__":
    for n, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
        if not ok:
            print(f"        {detail}")
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results)-failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
