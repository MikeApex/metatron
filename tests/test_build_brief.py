"""
tests/test_build_brief.py — the brief is a spec, and it is redacted by mechanism.

THE CLAIM THAT MATTERS IS THE REDACTION, AND IT IS TESTED IN BOTH DIRECTIONS.
A grep that never matches looks exactly like a clean document, so proving the
brief carries no persona value is worth nothing on its own: the detector has to
be shown FIRING. So every redaction test comes in a pair — a real brief is
clean, and a planted value in the same position is caught and masked. That is
the discipline tests/test_build_manifest.py already uses on the manifest, for
the same reason.

The structural half is tested separately and it is the half that actually holds:
the renderer emits declared fields only, so evidence appears as `tool -> N rows`
and the probe's own arguments never reach the page. The redactor is the proof
that the structural layer worked, not the thing keeping the page clean.

Also here: the brief must be USEFUL WHEN THE JOB IS PARTIAL. A job parked at
needs_interview has a ledger and no plan, and that is exactly the moment a human
is being asked to act — a renderer that required a complete job would produce
nothing precisely when the document is needed.

Standalone runner, no pytest, matching tests/ convention.

Usage:
    python3 tests/test_build_brief.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.brief as BR        # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_brief_test_"))

# A fixed set of "profile values", so the detector is exercised against known
# strings rather than against whatever happens to be in this machine's profile —
# which may be empty, and an empty detector passes everything.
PLANTED = ["Iva Diamond", "Prudential Apex", "Hackney Wick"]
_REAL_PERSONA_VALUES = BR.persona_values
BR.persona_values = lambda persona=None: sorted(PLANTED, key=len, reverse=True)


JOB = {"job_id": "BLD-0919-01", "state": "plan_ready", "mode": "construct",
       "gap": "nothing owns 'is this household thing overdue'", "attempt": 1,
       "trigger": "scheduled prompt went unrouted 3x"}

QUESTION_SET = {"depth": "standard", "disposition": "new",
                "spine": [{"id": "q1", "class": "intent", "text": "What is this for?",
                           "why_it_matters": "it sets the altitude",
                           "candidate_sources": ["log", "user"]}]}

LEDGER = {
    "rows": [{"question_id": "q1", "decision": "treat rain as a watering",
              "decision_options": ["rain counts", "rain does not count"],
              "assumption": "outdoor pots catch enough rain",
              "assumption_falsifier": "a logged watering the day after heavy rain",
              "evidence": [{"tool": "get_log_window", "rows": 12,
                            "data_available": True,
                            "probe": {"query": "Iva Diamond watering"}},
                           {"tool": "get_weather", "rows": 0,
                            "data_available": False, "probe": {}}]}],
    "interview_items": [],
}

PLAN = {
    "capability": {"id": "home_care", "kind": "agent", "one_line": "household upkeep",
                   "disposition": "new", "disposition_evidence": "logistics owns actions",
                   "generalizes_to": "any recurring home obligation",
                   "execution_mode": "blocking", "latency_budget_ms": 8000},
    "surface_map": [{"entity": "watering", "operation": "read", "status": "in_scope",
                     "reason": "the whole job"}],
    "files": ["data/personas/mike/build/overlay/agents/home_care.md"],
    "tests": ["tests/test_home_care.py"],
    "risks": ["reads a log that may be sparse"],
    "registration": [{"routing": {"local": {"allowed_tools": ["get_log_window",
                                                              "get_weather"]}}}],
}


# ---------------------------------------------------------------------------
# Redaction, in both directions
# ---------------------------------------------------------------------------

@check("an ordinary brief carries no planted persona value")
def _():
    body = BR.approval_brief(JOB, QUESTION_SET, LEDGER, PLAN)
    assert not BR.findings(body), BR.findings(body)


@check("a planted value IS caught and masked — the detector fires")
def _():
    # Without this the test above passes trivially on any renderer that produces
    # an empty string. The value goes into the field most likely to carry one in
    # real life: a model-written decision.
    dirty = {**LEDGER, "rows": [{**LEDGER["rows"][0],
                                 "decision": "ask Iva Diamond first"}]}
    body = BR.approval_brief(JOB, QUESTION_SET, dirty, PLAN)
    assert "Iva Diamond" not in body, "the planted value survived redaction"
    assert BR.MASK in body, "it was removed without being marked as masked"
    # findings() runs on the REDACTED body, so it reports clean — which is why
    # write_briefs() computes findings on the pre-redaction render.
    assert BR.findings("ask Iva Diamond first") == ["Iva Diamond"]


@check("masking is case-insensitive and longest-first — no fragment is left behind")
def _():
    assert "Diamond" not in BR.redact("contact IVA DIAMOND today")
    # "Iva Diamond" is longer than nothing else here, but the ordering rule is
    # what stops a shorter overlapping value shredding a longer one first.
    assert BR.redact("Prudential Apex") == BR.MASK


@check("the floor is applied at COLLECTION — a two-letter profile value never becomes a mask")
def _():
    # Tested against the real persona_values() with a fake profile, not against
    # the stub above. The floor lives in collection and NOT in redact(), so a
    # test that stubbed persona_values() would be testing its own stub — which
    # is what the first version of this test did, and it failed for that reason.
    import contextlib

    import core.persona as PZ
    import tools.profile as P

    saved = (BR.persona_values, P._load, PZ.persona_scope, PZ.resolve_persona)
    BR.persona_values = _REAL_PERSONA_VALUES
    P._load = lambda: {"name": "Iva Diamond", "country": "UK",
                       "work": {"employer": "Prudential Apex"},
                       "places": ["Hackney Wick", "ldn"]}
    PZ.persona_scope = lambda persona: contextlib.nullcontext(persona)
    PZ.resolve_persona = lambda explicit=None: "mike"
    try:
        values = BR.persona_values()
        assert "Iva Diamond" in values and "Prudential Apex" in values, values
        assert "UK" not in values and "ldn" not in values, (
            "a value shorter than the floor became maskable — a mask on 'the' "
            "teaches everyone to ignore every mask")
        # Longest first, so a longer value is replaced before a shorter one that
        # is a substring of it.
        assert values == sorted(values, key=len, reverse=True), values
        assert "[redacted]" in BR.redact("ask Iva Diamond")
        assert BR.redact("based in the UK") == "based in the UK"
    finally:
        BR.persona_values, P._load, PZ.persona_scope, PZ.resolve_persona = saved


# ---------------------------------------------------------------------------
# The structural layer — what actually holds
# ---------------------------------------------------------------------------

@check("evidence renders as tool -> N rows, and the PROBE ARGUMENTS never appear")
def _():
    body = BR.approval_brief(JOB, QUESTION_SET, LEDGER, PLAN)
    assert "get_log_window → 12 rows" in body, body
    assert "get_weather → 0 rows (nothing)" in body, body
    # The probe's query is composed from the question text, which is composed
    # from the user's words. It is omitted structurally, not masked.
    assert "query" not in body and "watering\"" not in body


@check("the decisions section carries options, assumption and falsifier — it IS the spec")
def _():
    body = BR.approval_brief(JOB, QUESTION_SET, LEDGER, PLAN)
    for expected in ("treat rain as a watering", "rain does not count",
                     "outdoor pots catch enough rain",
                     "a logged watering the day after heavy rain"):
        assert expected in body, f"missing from the brief: {expected}"


@check("a plan with no tests says so — an empty test list cannot land")
def _():
    body = BR.approval_brief(JOB, QUESTION_SET, LEDGER, {**PLAN, "tests": []})
    assert "cannot land" in body, body


@check("the grants it will hold are listed")
def _():
    body = BR.approval_brief(JOB, QUESTION_SET, LEDGER, PLAN)
    assert "`get_log_window`" in body and "`get_weather`" in body


# ---------------------------------------------------------------------------
# Partial jobs — the moment the brief is most needed
# ---------------------------------------------------------------------------

@check("a job with no plan still renders, and says what it is waiting on")
def _():
    parked = {**JOB, "state": "needs_interview"}
    ledger = {**LEDGER, "interview_items": [
        {"question_id": "q4", "text": "indoor plants too, or only the garden?",
         "why": "only the user can answer this"}]}
    body = BR.approval_brief(parked, QUESTION_SET, ledger, {})
    assert "No plan yet" in body, body
    assert "indoor plants too" in body, body
    assert "Waiting on you" in body, body


@check("an empty job renders rather than raising — nothing here may fail at the gate")
def _():
    body = BR.approval_brief({}, {}, {}, {})
    assert "Build brief" in body and "no gap recorded" in body


@check("no estimate yet is stated, not silently omitted")
def _():
    body = BR.approval_brief(JOB, QUESTION_SET, LEDGER, PLAN)
    assert "has not reached N8" in body, body
    priced = BR.approval_brief(JOB, QUESTION_SET, LEDGER, PLAN,
                               {"usd": 0.12, "spent": 0.4, "limit": 2.5,
                                "limit_source": "placeholder", "notice": "PLACEHOLDER!"})
    assert "$0.1200" in priced and "PLACEHOLDER!" in priced


# ---------------------------------------------------------------------------
# needs_tool briefs
# ---------------------------------------------------------------------------

@check("one brief per TOOL, not one per question")
def _():
    ledger = {"rows": [
        {"question_id": "q1", "needs_tool": ["search_conversations"], "evidence": []},
        {"question_id": "q2", "needs_tool": ["search_conversations"], "evidence": []},
        {"question_id": "q3", "needs_tool": ["read_journal_range"], "evidence": []},
    ]}
    question_set = {"spine": [{"id": "q1", "class": "intent", "text": "a"},
                              {"id": "q2", "class": "surface", "text": "b"},
                              {"id": "q3", "class": "cost", "text": "c"}]}
    briefs = BR.needs_tool_briefs(JOB, question_set, ledger)
    assert sorted(briefs) == ["read_journal_range", "search_conversations"], sorted(briefs)
    assert "2 question(s)" in briefs["search_conversations"]
    assert "1 question(s)" in briefs["read_journal_range"]


@check("a needs_tool brief says it is a READ tool and Mac-side work")
def _():
    briefs = BR.needs_tool_briefs(
        JOB, {"spine": [{"id": "q1", "class": "intent", "text": "a"}]},
        {"rows": [{"question_id": "q1", "needs_tool": ["search_conversations"],
                   "evidence": []}]})
    body = briefs["search_conversations"]
    assert "A **read** tool" in body, body
    assert "nothing on the VM writes code" in body, body
    assert "build_librarian.md" in body, body


@check("no missing tool means no briefs at all")
def _():
    assert BR.needs_tool_briefs(JOB, QUESTION_SET, LEDGER) == {}


def main() -> int:
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))
    passed = sum(1 for _n, ok, _d in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
