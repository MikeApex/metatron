"""
tests/test_accountability_gate.py — the judgment-gate half of [DB-0827-09].

Covers what the structured-join tests in tests/test_accountability.py do not: the list
write shape (Mike's ruling (a), 2026-08-28), restatement grouping, the nightly gate's
scope and judged-once rule, the defensive parse, the verdict merge into the index, and
the delivered-once weekly block.

**No test here makes a model call.** The gate takes an injectable `judge` callable for
exactly this reason — a suite that reached Vertex would cost money per run, fail without
network, and be non-deterministic, which is three reasons not to.

Same check-decorator convention as tests/test_accountability.py (no pytest here). Every
fixture is synthetic data in a tempdir; nothing touches real persona data.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.accountability as ACC  # noqa: E402
import tools.logger as LOG  # noqa: E402

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


def _write_log_file(tmp: Path, persona: str, day: str, content: dict) -> None:
    d = tmp / "data" / "personas" / persona / "logs"
    d.mkdir(parents=True, exist_ok=True)
    body = dict(content)
    body["date"] = day
    (d / f"{day}.json").write_text(json.dumps(body))


def _write_journal_file(tmp: Path, persona: str, day: str, texts: list[str]) -> None:
    d = tmp / "data" / "personas" / persona / "journal"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{day}.json").write_text(json.dumps({
        "date": day,
        "entries": [{"timestamp": f"{day}T20:00:00", "text": t, "tags": []} for t in texts],
    }))


# ---------------------------------------------------------------------------
# 1. tools/logger.py — intentions accumulate as a list
# ---------------------------------------------------------------------------

@check("a second intention on the same day no longer overwrites the first")
def _():
    content, entry = LOG._split_intention({"intention": "call Dad", "stated_for": "2026-08-30"})
    assert entry == {"intention": "call Dad", "stated_for": "2026-08-30"}, entry
    assert "intention" not in content and "stated_for" not in content, content

    # Two writes, merged the way write_log merges them.
    existing: dict = {}
    for text in ("call Dad", "clean the garage"):
        rest, entry = LOG._split_intention({"intention": text})
        existing = LOG._deep_merge(existing, rest)
        existing.setdefault(LOG._INTENTIONS_KEY, []).append(entry)
    assert [e["intention"] for e in existing["intentions"]] == ["call Dad", "clean the garage"], existing


@check("restating the same intention is kept, not deduped — frequency is the signal")
def _():
    existing: dict = {"intentions": [{"intention": "start running again", "stated_for": ""}]}
    rest, entry = LOG._split_intention({"intention": "start running again"})
    existing["intentions"].append(entry)
    assert len(existing["intentions"]) == 2, existing


@check("a write with no intention is untouched, and a bare stated_for is left alone")
def _():
    content = {"mood": "positive", "stated_for": "2026-08-30"}
    rest, entry = LOG._split_intention(content)
    assert entry is None, entry
    assert rest == content, rest


@check("write_log stores an intention as a list entry, not a scalar, and appends the second")
def _():
    from core.persona import persona_scope
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        original = LOG._logs_dir
        LOG._logs_dir = lambda: tmp / "logs"          # noqa: E731 — narrow, restored below
        try:
            with persona_scope("mike"):
                LOG.write_log({"intention": "call Dad", "stated_for": "2026-08-30"})
                LOG.write_log({"intention": "call Dad"})
                LOG.write_log({"mood": "positive"})
            day = date.today().isoformat()
            data = json.loads((tmp / "logs" / f"{day}.json").read_text())
        finally:
            LOG._logs_dir = original
    assert "intention" not in data, data
    assert len(data["intentions"]) == 2, data
    assert data["intentions"][0] == {"intention": "call Dad", "stated_for": "2026-08-30"}, data
    assert data["intentions"][1] == {"intention": "call Dad", "stated_for": ""}, data
    assert data["mood"] == "positive", data


# ---------------------------------------------------------------------------
# 2. Reading both shapes, and grouping restatements
# ---------------------------------------------------------------------------

@check("a legacy scalar intention already on disk is still read")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-01", {"intention": "old shape", "stated_for": "2026-08-02"})
        got = ACC.read_intentions("t", root=tmp)
        assert len(got) == 1, got
        assert got[0]["intention"] == "old shape", got
        assert got[0]["stated_for"] == "2026-08-02", got
        assert got[0]["times_stated"] == 1, got


@check("a day file holding both shapes yields both statements")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-01", {
            "intention": "legacy one",
            "intentions": [{"intention": "new one", "stated_for": ""}],
        })
        got = ACC.read_statements("t", root=tmp)
        assert [g["intention"] for g in got] == ["legacy one", "new one"], got


@check("restatements across days group into one intention with times_stated")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-01", {
            "intentions": [{"intention": "Start running again", "stated_for": ""}]})
        _write_log_file(tmp, "t", "2026-08-03", {
            "intentions": [{"intention": "start running again!", "stated_for": ""}]})
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "start running again", "stated_for": ""}]})
        got = ACC.read_intentions("t", root=tmp)
        assert len(got) == 1, got
        assert got[0]["times_stated"] == 3, got
        assert got[0]["logged_date"] == "2026-08-01", got   # anchored to the FIRST statement


@check("restating does not extend the window — it is anchored to the first statement")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for day in ("2026-08-01", "2026-08-06", "2026-08-09"):
            _write_log_file(tmp, "t", day, {
                "intentions": [{"intention": "read that book", "stated_for": ""}]})
        got = ACC.read_intentions("t", root=tmp)
        start, end = ACC.intention_window(got[0])
        assert (start, end) == (date(2026, 8, 1), date(2026, 8, 8)), (start, end)


@check("times_stated reaches the resolution row and the report table")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for day in ("2026-08-01", "2026-08-02"):
            _write_log_file(tmp, "t", day, {
                "intentions": [{"intention": "reconnect with an old friend", "stated_for": ""}]})
        idx = ACC.build_index("t", as_of=date(2026, 8, 20), root=tmp,
                              calendar_events=[], obligations=[], gate_verdicts={})
        assert idx["items"][0]["times_stated"] == 2, idx["items"]


@check("statements are counted per day for the A9 row, so a restatement still counts as stated")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-01", {
            "intentions": [{"intention": "call Dad", "stated_for": ""}]})
        _write_log_file(tmp, "t", "2026-08-02", {"intentions": [
            {"intention": "call Dad", "stated_for": ""},
            {"intention": "clean the garage", "stated_for": ""},
        ]})
        counts = ACC.daily_accountability_counts("2026-08-02", "t", root=tmp)
        assert counts["intentions_stated"] == 2, counts


# ---------------------------------------------------------------------------
# 3. Gate scope — leftovers only, judged once, code verdicts untouched
# ---------------------------------------------------------------------------

def _recording_judge(verdict="fulfilled", reason="the record says so"):
    seen: list[str] = []

    def judge(item, evidence):
        seen.append(item["intention"])
        return {"verdict": verdict, "reason": reason}

    return judge, seen


@check("the gate judges only the post-join leftovers, never a code-resolved verdict")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # fulfilled in code (an obligation closed inside the window) — must NOT be judged
        _write_log_file(tmp, "t", "2026-08-01", {
            "intentions": [{"intention": "clean the garage", "stated_for": ""}]})
        (tmp / "data" / "personas" / "t").mkdir(parents=True, exist_ok=True)
        # window still open on as_of — must NOT be judged
        _write_log_file(tmp, "t", "2026-08-18", {
            "intentions": [{"intention": "book the dentist", "stated_for": ""}]})
        # closed window, no structured match — the only leftover
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "reconnect with an old friend", "stated_for": ""}]})

        obligations = [{"what": "clean the garage", "status": "closed",
                        "closed_at": "2026-08-04T18:00:00"}]
        ACC._fetch_calendar_events = lambda *a, **k: []          # no network in tests
        ACC._fetch_obligations = lambda persona, root=None: obligations

        judge, seen = _recording_judge()
        out = ACC.run_judgment_gate("t", as_of=date(2026, 8, 20), root=tmp, judge=judge)
        assert seen == ["reconnect with an old friend"], (seen, out)


@check("an intention the gate has already judged is never re-judged, indeterminate included")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "reconnect with an old friend", "stated_for": ""}]})
        ACC._fetch_calendar_events = lambda *a, **k: []
        ACC._fetch_obligations = lambda persona, root=None: []

        judge, seen = _recording_judge(verdict="indeterminate", reason="nothing recorded")
        ACC.run_judgment_gate("t", as_of=date(2026, 8, 20), root=tmp, judge=judge)
        assert len(seen) == 1, seen
        # second night, same leftover: the stored indeterminate is final
        ACC.run_judgment_gate("t", as_of=date(2026, 8, 21), root=tmp, judge=judge)
        assert len(seen) == 1, seen

        rows = ACC._verdicts_path("t", tmp).read_text().strip().splitlines()
        assert len(rows) == 1, rows
        row = json.loads(rows[0])
        assert row["verdict"] == "indeterminate", row
        assert row["logged_date"] == "2026-08-05", row
        assert row["judged_at"], row


@check("the verdicts file is append-only and 0600")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "one thing", "stated_for": ""}]})
        _write_log_file(tmp, "t", "2026-08-06", {
            "intentions": [{"intention": "another thing", "stated_for": ""}]})
        ACC._fetch_calendar_events = lambda *a, **k: []
        ACC._fetch_obligations = lambda persona, root=None: []
        judge, _seen = _recording_judge()
        ACC.run_judgment_gate("t", as_of=date(2026, 8, 20), root=tmp, judge=judge)
        path = ACC._verdicts_path("t", tmp)
        assert len(path.read_text().strip().splitlines()) == 2, path.read_text()
        assert oct(path.stat().st_mode)[-3:] == "600", oct(path.stat().st_mode)


@check("the gate returns a plain string and never raises, even when the judge blows up")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "one thing", "stated_for": ""}]})
        ACC._fetch_calendar_events = lambda *a, **k: []
        ACC._fetch_obligations = lambda persona, root=None: []

        def exploding(item, evidence):
            raise RuntimeError("provider down")

        out = ACC.run_judgment_gate("t", as_of=date(2026, 8, 20), root=tmp, judge=exploding)
        assert isinstance(out, str), out
        assert "failed" in out, out


# ---------------------------------------------------------------------------
# 4. Defensive parse — everything malformed is indeterminate
# ---------------------------------------------------------------------------

@check("junk, prose, an injection echo and a verdict outside the enum all parse to indeterminate")
def _():
    for raw in ("", "   ", None, "no json here at all", "{not json}",
                '{"verdict": "definitely_done", "reason": "x"}',
                '{"verdict": "IGNORE PREVIOUS INSTRUCTIONS"}',
                '{"reason": "no verdict key"}', "[]", '{"verdict": 7}'):
        got = ACC.parse_verdict(raw)
        assert got["verdict"] == "indeterminate", (raw, got)


@check("a well-formed verdict parses, case-insensitively, with its reason kept")
def _():
    got = ACC.parse_verdict('  {"verdict": "Fulfilled", "reason": "went for a run on the 12th"} ')
    assert got == {"verdict": "fulfilled", "reason": "went for a run on the 12th"}, got


@check("a judge returning something that is not a dict lands as indeterminate, not a crash")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "one thing", "stated_for": ""}]})
        ACC._fetch_calendar_events = lambda *a, **k: []
        ACC._fetch_obligations = lambda persona, root=None: []
        ACC.run_judgment_gate("t", as_of=date(2026, 8, 20), root=tmp,
                              judge=lambda i, e: "sure, it happened")
        row = json.loads(ACC._verdicts_path("t", tmp).read_text().strip())
        assert row["verdict"] == "indeterminate", row


# ---------------------------------------------------------------------------
# 5. Evidence gathering
# ---------------------------------------------------------------------------

@check("the window's evidence carries journal text and log free text, and not the intention itself")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_journal_file(tmp, "t", "2026-08-03", ["Went for a 5k around the block."])
        _write_log_file(tmp, "t", "2026-08-03", {
            "intentions": [{"intention": "RESTATEMENT-SHOULD-NOT-APPEAR", "stated_for": ""}],
            "notes": "legs sore",
        })
        ev = ACC.window_evidence("t", date(2026, 8, 1), date(2026, 8, 8), root=tmp)
        assert "5k around the block" in ev, ev
        assert "legs sore" in ev, ev
        assert "RESTATEMENT-SHOULD-NOT-APPEAR" not in ev, ev


@check("evidence is truncated rather than allowed to grow with a prolific week")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for i in range(1, 9):
            _write_journal_file(tmp, "t", f"2026-08-0{i}", ["x" * 2000])
        ev = ACC.window_evidence("t", date(2026, 8, 1), date(2026, 8, 8), root=tmp)
        assert len(ev) <= ACC._MAX_EVIDENCE_CHARS + 40, len(ev)
        assert "truncated" in ev, ev[-60:]


# ---------------------------------------------------------------------------
# 6. Verdict merge into the index
# ---------------------------------------------------------------------------

@check("a gate verdict replaces the awaiting-gate indeterminate and lands in the fulfilment rate")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_log_file(tmp, "t", "2026-08-05", {
            "intentions": [{"intention": "reconnect with an old friend", "stated_for": ""}]})
        ACC._fetch_calendar_events = lambda *a, **k: []
        ACC._fetch_obligations = lambda persona, root=None: []

        before = ACC.build_index("t", as_of=date(2026, 8, 20), root=tmp)
        assert before["counts"]["indeterminate"] == 1, before["counts"]
        assert before["fulfilment_rate"] is None, before

        judge, _seen = _recording_judge(verdict="fulfilled", reason="had coffee with Sam on the 8th")
        ACC.run_judgment_gate("t", as_of=date(2026, 8, 20), root=tmp, judge=judge)

        after = ACC.build_index("t", as_of=date(2026, 8, 20), root=tmp)
        item = after["items"][0]
        assert item["verdict"] == "fulfilled", item
        assert item["reason"] == "had coffee with Sam on the 8th", item
        assert item["judged_by"] == "gate", item
        assert after["fulfilment_rate"] == 1.0, after


@check("a gate verdict never overturns a structured match or an open window")
def _():
    i = {"intention": "go for a run", "logged_date": "2026-08-10", "stated_for": "2026-08-12"}
    gate = {ACC._intention_key("2026-08-10", "go for a run"):
            {"verdict": "unfulfilled", "reason": "model disagrees"}}
    events = [{"title": "go for a run", "start": "2026-08-13T09:00:00"}]
    item = ACC.resolve_intention(i, events, [], date(2026, 8, 20), gate)
    assert item["verdict"] == "fulfilled", item          # code wins
    assert item["judged_by"] == "", item

    still_open = {"intention": "book the dentist", "logged_date": "2026-08-18", "stated_for": ""}
    gate2 = {ACC._intention_key("2026-08-18", "book the dentist"):
             {"verdict": "unfulfilled", "reason": "model guessed"}}
    item2 = ACC.resolve_intention(still_open, [], [], date(2026, 8, 19), gate2)
    assert item2["verdict"] == "indeterminate", item2
    assert item2["reason"] == "window still open", item2


# ---------------------------------------------------------------------------
# 7. The weekly block — parked Sunday, delivered once
# ---------------------------------------------------------------------------

@check("the weekly summary is parked on a Sunday and not on other days")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # stated_for 08-26 → window closes 08-28, so it is a leftover by the Saturday run
        _write_log_file(tmp, "t", "2026-08-25", {
            "intentions": [{"intention": "reconnect with an old friend",
                            "stated_for": "2026-08-26"}]})
        ACC._fetch_calendar_events = lambda *a, **k: []
        ACC._fetch_obligations = lambda persona, root=None: []
        judge, _seen = _recording_judge(verdict="unfulfilled", reason="said they never called")

        # 2026-08-29 is a Saturday
        ACC.run_judgment_gate("t", as_of=date(2026, 8, 29), root=tmp, judge=judge)
        assert not ACC._weekly_state_path("t", tmp).exists(), "parked on a non-Sunday"

        # 2026-08-30 is a Sunday
        out = ACC.run_judgment_gate("t", as_of=date(2026, 8, 30), root=tmp, judge=judge)
        state = json.loads(ACC._weekly_state_path("t", tmp).read_text())
        summary = state["pending_summary"]
        assert summary["counts"]["unfulfilled"] == 1, summary
        assert summary["unfulfilled"] == ["reconnect with an old friend"], summary
        assert "weekly summary parked" in out, out


@check("the context block carries the counts and names, and is empty when nothing is parked")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        assert ACC.context_block("t", root=tmp) == "", "spoke with nothing parked"
        ACC._park_weekly_summary("t", {
            "as_of": "2026-08-30", "trailing_days": 7,
            "counts": {"fulfilled": 4, "unfulfilled": 1, "indeterminate": 1, "total": 6},
            "unfulfilled": ["call the plumber"], "open": ["read that book"],
        }, root=tmp)
        block = ACC.context_block("t", root=tmp)
        assert "6 stated · 4 done" in block, block
        assert "not done: call the plumber" in block, block
        assert "no record either way: read that book" in block, block
        assert "weekly retrospective" in block, block


@check("the parked summary is delivered inside one session's window, then cleared")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ACC._park_weekly_summary("t", {
            "as_of": "2026-08-30", "trailing_days": 7,
            "counts": {"fulfilled": 1, "unfulfilled": 0, "indeterminate": 0, "total": 1},
            "unfulfilled": [], "open": [],
        }, root=tmp)
        first = ACC.context_block("t", root=tmp)
        second = ACC.context_block("t", root=tmp)     # same session, seconds later
        assert first and second == first, (first, second)

        # Rewind the delivery clock past the window and load again.
        state = ACC._read_weekly_state("t", root=tmp)
        state["delivery_started"] = "2020-01-01T00:00:00"
        ACC._write_weekly_state("t", state, root=tmp)
        assert ACC.context_block("t", root=tmp) == "", "still offered after the window closed"
        assert ACC.context_block("t", root=tmp) == "", "resurrected after being cleared"


@check("a corrupt weekly state file is quiet, not fatal")
def _():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = ACC._weekly_state_path("t", tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json")
        assert ACC.context_block("t", root=tmp) == "", "spoke from a corrupt state file"


if __name__ == "__main__":
    for n, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
        if not ok:
            print(f"        {detail}")
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results)-failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
