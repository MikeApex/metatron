"""
tests/test_build_probe.py — the probe reports three states, never two.

THE CLAIM UNDER TEST: an empty source returns `data_available: false, rows: 0`
and NOT an exception — and, separately, that "nothing came back" is
distinguishable from "this never retrieves".

This is core/trace.py's is_grounded() lesson one layer up. That flag collapsed
two different states into one and was unreadable as a result: a grounded search
makes zero tool calls, so a genuine and a fabricated Research answer both read
`false`. The fix there was to record "we asked and nothing was retrieved"
separately. Here the same distinction is the difference between an interview
item and a build blocker:

    needs_tool  nothing was asked          -> Build must build its substrate
    no_data     asked, nothing came back   -> an interview item
    data        asked, rows came back      -> evidence
    error       asked, it raised           -> availability UNKNOWN, not false

Folding `error` into `no_data` would be the same mistake in miniature: a broken
tool would read as an empty source, and the job would park on an interview item
for data that is actually there.

Also asserted here: settle.py's ordering (policies before data), condense.py's
reduction, and cost.py's metering seam — the rest of phase 2.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_probe.py

Exits 0 if every check passes, 1 otherwise.
"""

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.jobs as J  # noqa: E402
from core.build import condense as C  # noqa: E402
from core.build import cost as COST  # noqa: E402
from core.build import manifest as M  # noqa: E402
from core.build import policy as P  # noqa: E402
from core.build import probe as PR  # noqa: E402
from core.build import settle as SET  # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_probe_test_"))
J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or "mike")
PERSONA = "mike"


class FakeTools:
    """Swaps the handler lookup so a probe can be pointed at a known return."""

    def __init__(self, handlers: dict):
        self.handlers = handlers
        self._saved = None

    def __enter__(self):
        self._saved = PR._handler
        PR._handler = lambda name: self.handlers.get(name)
        return self

    def __exit__(self, *exc):
        PR._handler = self._saved
        return None


def question(qid: str, klass: str, text: str, sources: list[str]) -> dict:
    return {"id": qid, "class": klass, "text": text,
            "why_it_matters": "x", "blocks": "design",
            "expected_answer_shape": "a statement",
            "candidate_sources": sources, "resolved_by_policy": None}


# ---------------------------------------------------------------------------
# The three states
# ---------------------------------------------------------------------------

@check("an empty journal returns rows 0 and data_available false, NOT an exception")
def _():
    with FakeTools({"read_journal": lambda **kw: ""}):
        record = PR.probe("journal", PERSONA)
    assert record["state"] == "no_data", record
    assert record["rows"] == 0, record
    assert record["data_available"] is False, record
    assert record["error"] == "", record


@check("a journal with entries returns rows and data_available true")
def _():
    body = "2026-09-01 watered the plants\n\n2026-09-04 watered again\n\n2026-09-09 rain"
    with FakeTools({"read_journal": lambda **kw: body}):
        record = PR.probe("journal", PERSONA)
    assert record["state"] == "data", record
    assert record["rows"] == 3, record
    assert record["data_available"] is True and record["sample_ok"] is True


@check("an unregistered tool is needs_tool — nothing was asked")
def _():
    with FakeTools({}):
        record = PR.probe("conversations", PERSONA)
    assert record["state"] == "needs_tool", record
    assert record["rows"] == 0 and record["data_available"] is False
    assert "not registered" in record["error"], record


@check("a raising tool is `error`, never folded into no_data")
def _():
    def boom(**kw):
        raise RuntimeError("CalDAV 401")
    with FakeTools({"read_calendar": boom}):
        record = PR.probe("calendar", PERSONA)
    assert record["state"] == "error", record
    assert "CalDAV 401" in record["error"], record
    assert record["data_available"] is False
    # The distinction that matters: availability is UNKNOWN here, not false.
    # Folding this into no_data would park the job on an interview item for
    # data that is sitting there behind a fixable auth failure — which is
    # exactly the 2026-09-10 shape, where a 401 became "today's commitment".
    assert record["state"] != "no_data"


@check("the house 'nothing recorded' idiom counts as zero rows, not one")
def _():
    for empty in ("No profile recorded yet.", "None found.", "Nothing scheduled.",
                  "No entries for that date."):
        with FakeTools({"read_profile": lambda **kw: empty}):
            record = PR.probe("profile", PERSONA)
        assert record["rows"] == 0, (empty, record)


@check("a long answer that merely begins with 'no' is NOT treated as empty")
def _():
    body = ("No, the watering was not skipped — the log shows entries on the 1st, "
            "the 4th and the 9th, and the gap in between is explained by rainfall "
            "recorded on the 6th and 7th, which the household treats as watering.")
    with FakeTools({"read_profile": lambda **kw: body}):
        record = PR.probe("profile", PERSONA)
    assert record["rows"] > 0, record


@check("a source outside the manifest is refused, not probed")
def _():
    record = PR.probe("astrology", PERSONA)
    assert record["state"] == "error", record
    assert "not a manifest source" in record["error"], record


@check("probe arguments are CODE-written — the injection answer")
def _():
    seen: dict = {}

    def spy(**kwargs):
        seen.update(kwargs)
        return "one row"

    with FakeTools({"get_log_window": spy}):
        PR.probe("log", PERSONA)
    assert seen == M.source("log")["probe"], (seen, M.source("log")["probe"])
    # The model names a source; this asserts it cannot choose the call. A corpus
    # carrying an injected instruction can influence what is NAMED, never what
    # is CALLED.


@check("a signature mismatch is reported as a defect, not as no_data")
def _():
    with FakeTools({"get_log_window": lambda only_this: "x"}):
        record = PR.probe("log", PERSONA)
    assert record["state"] == "error", record
    assert "do not fit" in record["error"], record


@check("summarise() reports needs_tool and errors separately from the count")
def _():
    records = [
        {"tool": "a", "state": "data", "rows": 3, "data_available": True, "error": ""},
        {"tool": "search_conversations", "state": "needs_tool", "rows": 0,
         "data_available": False, "error": "not registered"},
        {"tool": "c", "state": "error", "rows": 0, "data_available": False,
         "error": "boom"},
    ]
    summary = PR.summarise(records)
    assert summary["data_available"] is True
    assert summary["needs_tool"] == ["search_conversations"], summary
    assert summary["errors"] == ["boom"], summary
    assert summary["rows_total"] == 3, summary


@check("a registered tool that cannot answer this SHAPE is `unaskable`")
def _():
    # read_journal is registered and takes ONE DATE. Asked a behavioural
    # question it would return one day or nothing, and that answer is
    # indistinguishable from an empty corpus once it is a row count.
    with FakeTools({"read_journal": lambda **kw: "2026-09-01 a single day"}):
        record = PR.probe("journal", PERSONA, data_kind="behavioural")
    assert record["state"] == "unaskable", record
    assert record["rows"] == 0 and record["data_available"] is False
    assert "cannot answer a behavioural question" in record["error"], record


@check("the same source answers fine when the shape fits")
def _():
    with FakeTools({"read_journal": lambda **kw: "2026-09-01 a single day"}):
        record = PR.probe("journal", PERSONA, data_kind="single_point")
    assert record["state"] == "data", record


@check("`unaskable` is checked BEFORE the call — the tool is never invoked")
def _():
    called = []
    with FakeTools({"read_journal": lambda **kw: called.append(1) or "x"}):
        PR.probe("journal", PERSONA, data_kind="behavioural")
    assert not called, (
        "calling it anyway would produce a row count that looks like an answer")


@check("a source with no shape restriction answers any shape")
def _():
    with FakeTools({"get_log_window": lambda **kw: "a\n\nb"}):
        for kind in ("single_point", "behavioural", ""):
            record = PR.probe("log", PERSONA, data_kind=kind)
            assert record["state"] == "data", (kind, record)


@check("`unaskable` is NOT `no_data` — a missing tool, not a missing fact")
def _():
    with FakeTools({"read_journal": lambda **kw: ""}):
        empty = PR.probe("journal", PERSONA, data_kind="single_point")
        unaskable = PR.probe("journal", PERSONA, data_kind="behavioural")
    assert empty["state"] == "no_data", empty
    assert unaskable["state"] == "unaskable", unaskable
    # One means the fact is missing. The other means the TOOL is. Only the
    # second earns a needs_tool brief, and collapsing them is what let the
    # worked Inquiry run walk straight past this gap on 2026-09-18.
    assert empty["state"] != unaskable["state"]


@check("summarise() folds unaskable into needs_tool AND reports it separately")
def _():
    records = [
        {"tool": "read_journal", "state": "unaskable", "rows": 0,
         "data_available": False, "error": "cannot answer behavioural"},
        {"tool": "search_conversations", "state": "needs_tool", "rows": 0,
         "data_available": False, "error": "not registered"},
    ]
    summary = PR.summarise(records)
    # Both resolve the same way — a brief Mike builds on the Mac.
    assert summary["needs_tool"] == ["read_journal", "search_conversations"], summary
    # But "write this tool" and "widen this tool" are different work, so the
    # brief has to be able to say which.
    assert summary["unaskable"] == ["read_journal"], summary


# ---------------------------------------------------------------------------
# settle — policies first, then data
# ---------------------------------------------------------------------------

def reset() -> None:
    shutil.rmtree(TMP / "personas", ignore_errors=True)
    J.build_dir(PERSONA).mkdir(parents=True, exist_ok=True)


@check("a question whose class a policy retires never reaches the data step")
def _():
    reset()
    P.write_policy({
        "id": "weekend_hold", "domain": "work",
        "applies_to": "business senders writing outside working hours",
        "standing_commitments": [], "automatic_yes": [],
        "automatic_no": ["raise at the weekend"],
        "default_on_silence": "Monday morning", "review_date": "2026-12-01",
        "authored_with_user": True,
        "retires_question_classes": ["authority"],
    }, job_id="BLD-0918-01", persona=PERSONA)

    probed: list[str] = []
    original = PR.probe_all
    PR.probe_all = lambda ids, persona=None: probed.extend(ids) or []
    try:
        out = SET.settle({"spine": [
            question("q1", "authority", "Who decides, and what on silence?",
                     ["log", "user"]),
        ]}, PERSONA)
    finally:
        PR.probe_all = original

    row = out["rows"][0]
    assert row["settled_by"] == "policy", row
    assert row["resolved_by_policy"] == "weekend_hold", row
    assert not probed, (
        "policy resolution must short-circuit before any probe runs — that is "
        "what makes each run cheaper than the last")


@check("a user-only question becomes an interview item, never a probe")
def _():
    reset()
    out = SET.settle({"spine": [
        question("q1", "intent", "What are you protecting this year?", ["user"]),
    ]}, PERSONA)
    assert out["rows"][0]["status"] == SET.NEEDS_INTERVIEW, out["rows"][0]
    assert len(out["interview_items"]) == 1, out["interview_items"]


@check("a single_point question with rows is settled by data")
def _():
    reset()
    with FakeTools({"read_wisdom": lambda **kw: "plant_watering_threshold: 4 days"}):
        out = SET.settle({"spine": [
            question("q1", "feasibility", "What is the watering interval?",
                     ["wisdom"]),
        ]}, PERSONA)
    row = out["rows"][0]
    assert row["settled_by"] == "data", row
    assert row["data_available"] is True and row["condensed_from"] > 0, row
    assert not out["residue"], out["residue"]


@check("a BEHAVIOURAL question with rows still reaches the Librarian")
def _():
    reset()
    with FakeTools({"get_log_window": lambda **kw: "a\n\nb\n\nc"}):
        out = SET.settle({"spine": [
            question("q1", "intent", "How does he talk about work stress?", ["log"]),
        ]}, PERSONA)
    row = out["rows"][0]
    assert row["data_available"] is True, row
    assert row["settled_by"] == "", row
    assert len(out["residue"]) == 1, (
        "rows are not an answer for a behavioural question — that judgment is "
        "the Librarian's job, and settling it here would be code deciding")


@check("a question needing an unbuilt tool settles to needs_tool")
def _():
    reset()
    with FakeTools({}):
        out = SET.settle({"spine": [
            question("q1", "intent", "How is a watering usually recorded?",
                     ["conversations"]),
        ]}, PERSONA)
    row = out["rows"][0]
    assert row["status"] == SET.NEEDS_TOOL, row
    assert out["needs_tool"] == ["search_conversations"], out["needs_tool"]


@check("a behavioural question naming only the single-date journal reports unaskable")
def _():
    reset()
    with FakeTools({"read_journal": lambda **kw: "one day"}):
        out = SET.settle({"spine": [
            question("q1", "intent", "How does he write about work stress?",
                     ["journal"]),
        ]}, PERSONA)
    row = out["rows"][0]
    assert row["status"] == SET.NEEDS_TOOL, row
    assert "read_journal" in out["needs_tool"], out["needs_tool"]


@check("settle reports its own arithmetic")
def _():
    reset()
    with FakeTools({"read_wisdom": lambda **kw: "x: 4"}):
        out = SET.settle({"spine": [
            question("q1", "intent", "What matters here?", ["user"]),
            question("q2", "feasibility", "What is the interval?", ["wisdom"]),
        ]}, PERSONA)
    stats = out["stats"]
    assert stats["asked"] == 2 and stats["settled_by_data"] == 1, stats
    assert stats["to_interview"] == 1, stats


@check("the code-written block is re-injected over whatever the model wrote")
def _():
    model_row = {"question_id": "q1", "answerable_by": "data",
                 "data_available": True, "evidence": [{"source": "invented"}],
                 "condensed_from": 99, "status": "settled"}
    code_row = {"data_available": False, "evidence": [], "condensed_from": 0,
                "status": "needs_interview"}
    merged = SET.merge_code_block(model_row, code_row)
    assert merged["data_available"] is False, merged
    assert merged["evidence"] == [], merged
    assert merged["status"] == "needs_interview", merged
    assert merged["answerable_by"] == "data", "model fields must survive"


# ---------------------------------------------------------------------------
# condense
# ---------------------------------------------------------------------------

@check("the extractive pass needs no model and reports what it stood for")
def _():
    items = [f"day {n}: watered the tomatoes" for n in range(40)]
    block = C.condense(items, "how often are the tomatoes watered?")
    assert block["method"] == "extractive", block
    assert block["condensed_from"] == 40, block
    assert block["text"], block


@check("an injected summariser is used when it works")
def _():
    block = C.condense(["a", "b"], "q", summariser=lambda text, q: "three waterings")
    assert block["method"] == "model" and block["text"] == "three waterings", block


@check("a failing summariser degrades to extractive rather than failing the node")
def _():
    def broken(text, q):
        raise RuntimeError("model down")
    block = C.condense(["a", "b"], "q", summariser=broken)
    assert block["method"] == "extractive", block
    assert block["condensed_from"] == 2, block


@check("an empty source condenses to nothing, not to a fabricated summary")
def _():
    block = C.condense("", "q")
    assert block["method"] == "empty" and block["text"] == "", block
    assert block["condensed_from"] == 0, block


# ---------------------------------------------------------------------------
# cost
# ---------------------------------------------------------------------------

@check("the metering seam is a NO-OP with no job bound")
def _():
    reset()
    assert COST.current_job() is None
    COST.record_job_tokens("gemini-3.8-flash", 1000, 100)   # must not raise


@check("tokens are attributed to the bound job and priced by spend_guard")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    with COST.job_scope(job_id, PERSONA, node="N2"):
        COST.record_job_tokens("gemini-3.8-flash", 10_000, 500)
        COST.record_job_tokens("gemini-3.8-flash", 5_000, 200)
    totals = COST.job_tokens(job_id, PERSONA)
    assert totals["calls"] == 2, totals
    assert totals["tokens_in"] == 15_000 and totals["tokens_out"] == 700, totals

    from core.spend_guard import estimate_usd
    expected = round(estimate_usd("gemini-3.8-flash", 10_000, 500)
                     + estimate_usd("gemini-3.8-flash", 5_000, 200), 6)
    assert abs(totals["usd"] - expected) < 1e-6, (totals["usd"], expected)


@check("the binding is released on exit, including when the block raises")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    try:
        with COST.job_scope(job_id, PERSONA):
            raise ValueError("node failed")
    except ValueError:
        pass
    assert COST.current_job() is None


@check("check_budget is a tripwire, not a tolerance band")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    COST.approve_limit(job_id, 0.01, persona=PERSONA)
    COST.check_budget(job_id, PERSONA)          # nothing spent yet

    with COST.job_scope(job_id, PERSONA):
        COST.record_job_tokens("gemini-3.8-flash", 5_000_000, 500_000)
    try:
        COST.check_budget(job_id, PERSONA)
    except COST.BudgetExceeded as e:
        assert e.limit == 0.01 and e.spent > 0.01, (e.spent, e.limit)
    else:
        raise AssertionError("the budget did not trip")


@check("an approved limit survives a restart — it is a ledger row, not a variable")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    assert COST.job_limit(job_id, PERSONA) == COST.DEFAULT_JOB_LIMIT_USD
    COST.approve_limit(job_id, 7.5, persona=PERSONA)
    assert COST.job_limit(job_id, PERSONA) == 7.5
    # Replayed from the ledger, so nothing about this is held in the process.
    assert COST.approved_limit(job_id, PERSONA) == 7.5


@check("would_exceed parks a job BEFORE the work rather than after")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    COST.approve_limit(job_id, 1.00, persona=PERSONA)
    assert COST.would_exceed(job_id, 1.50, PERSONA) is True
    assert COST.would_exceed(job_id, 0.50, PERSONA) is False


@check("the placeholder budget announces itself while it is still a placeholder")
def _():
    reset()
    assert COST.limit_source() == "placeholder", COST.limit_source()
    notice = COST.budget_notice()
    assert notice, "a placeholder limit that says nothing is just a limit"
    assert "PLACEHOLDER" in notice and "2.50" in notice, notice
    assert "run 1" in notice, "the notice must say when to replace it"


@check("the notice self-clears once a real figure is configured")
def _():
    reset()
    import tempfile, os
    from pathlib import Path as _P
    tmp = _P(tempfile.mkdtemp()) / "build.yaml"
    tmp.write_text("budget:\n  per_job_usd: 4.0\n", encoding="utf-8")
    saved = COST._CONFIG_PATH
    COST._CONFIG_PATH = tmp
    try:
        assert COST.limit_source() == "configured", COST.limit_source()
        assert COST.budget_notice() == "", (
            "a warning that outlives its cause becomes noise people scroll past")
        assert COST.job_limit() == 4.0
    finally:
        COST._CONFIG_PATH = saved
    assert COST.budget_notice(), "the notice must come back when config goes away"


@check("an approved per-job limit also silences the notice for that job")
def _():
    reset()
    job_id = J.create("a gap", trigger="test")["job_id"]
    assert COST.budget_notice(job_id, PERSONA), "not yet approved"
    COST.approve_limit(job_id, 6.0, persona=PERSONA)
    assert COST.limit_source(job_id, PERSONA) == "approved"
    assert COST.budget_notice(job_id, PERSONA) == "", (
        "Mike naming a figure for this job IS the decision the notice asks for")


@check("day_total aggregates across jobs")
def _():
    reset()
    for n in range(2):
        job_id = J.create(f"gap {n}", trigger="test")["job_id"]
        with COST.job_scope(job_id, PERSONA):
            COST.record_job_tokens("gemini-3.8-flash", 1000, 100)
    total = COST.day_total(PERSONA)
    assert total["jobs"] == 2 and total["calls"] == 2, total
    assert total["usd"] > 0, total


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)
