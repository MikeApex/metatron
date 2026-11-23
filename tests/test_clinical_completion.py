#!/usr/bin/env python3
"""
tests/test_clinical_completion.py — M8: a clinical concern's companions completed by code
(Stage 3 plan § 1.4; archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md).

`complete_clinical_flags` adds the MUST_SURFACE a CLINICAL_CONCERN must carry when the specialist
left it out, and writes Mental Wellbeing's journal record when this turn's trace holds none.
`tools.diarist.write_journal` is stubbed throughout; no model, no store.

Run:  python tests/test_clinical_completion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from support.stage3_fixtures import PERSONA, patched  # noqa: E402

from core import orchestrator as ORC  # noqa: E402
from core import trace as TR  # noqa: E402
from tools import clinical_checks as CC  # noqa: E402
import tools.diarist as DI  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
JOURNAL: list[dict] = []


def check(name):
    def deco(fn):
        JOURNAL.clear()
        TR.set_trace(None)
        try:
            with patched([(DI, "write_journal",
                           lambda text, entry_date="", tags=None: JOURNAL.append(
                               {"text": text, "tags": list(tags or [])}) or "Journal entry written")]):
                fn()
            RESULTS.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        finally:
            TR.set_trace(None)
        return fn
    return deco


SI = "MOOD: low\nFLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION\nNOTES: passive ideation"
SI_WITH = SI + "\nMUST_SURFACE: signpost crisis resources warmly"
TWO = "MOOD: low\nFLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION, CLINICAL_CONCERN: ANXIETY_DISORDER"
SAID = "I've been thinking maybe everyone would be better off without me"


def _trace_with_mw_journal(ok: bool | None):
    t = TR.start_request_trace(SAID, PERSONA)
    rec = TR.push_agent("mental_wellbeing", "test", "test")
    if ok is not None:
        TR.record_tool_call(rec, 1, "write_journal", {"text": "x"}, "written", 1.0, ok=ok)
    TR.pop_agent(rec)
    return t


@check("1. a flag without MUST_SURFACE gets one added; a flag with one is unchanged; the "
       "completion is not gated on threads")
def _():
    out = CC.complete_clinical_flags({"mental_wellbeing": SI}, PERSONA, SAID, True)
    added = out["mental_wellbeing"]
    assert added.startswith(SI) and "MUST_SURFACE: SUICIDAL_IDEATION raised by Mental Wellbeing" \
        in added and "added by code" in added, added
    out = CC.complete_clinical_flags({"mental_wellbeing": SI_WITH}, PERSONA, SAID, True)
    assert out["mental_wellbeing"] == SI_WITH
    out = CC.complete_clinical_flags({"mental_wellbeing": SI + "\nMUST_SURFACE: none"},
                                     PERSONA, SAID, True)
    assert "raised by Mental Wellbeing" in out["mental_wellbeing"], "a 'none' MUST_SURFACE is absent"


@check("1a. thread state is ignored (a watch thread still gets the record when the trace has "
       "none); a second raising in the same turn gives no second call")
def _():
    from tools import context_tracker as CT
    watch = {"clinical_threads": [{"flag": "CLINICAL_CONCERN: SUICIDAL_IDEATION", "state": "watch"}]}
    _trace_with_mw_journal(None)
    with patched([(CT, "read_context_tracker", lambda *a, **k: watch)]):
        CC.complete_clinical_flags({"mental_wellbeing": SI}, PERSONA, SAID, True)
        CC.complete_clinical_flags({"mental_wellbeing": SI}, PERSONA, SAID, True)   # a consult
    assert len(JOURNAL) == 1, JOURNAL


@check("2. a scheduled turn: the flag already dropped means nothing added and no journal call")
def _():
    dropped = ORC._drop_unprompted_clinical_flags({"mental_wellbeing": SI_WITH}, False)
    out = CC.complete_clinical_flags(dropped, PERSONA, "", False)
    assert out == dropped and "MUST_SURFACE" not in out["mental_wellbeing"], out
    assert not JOURNAL
    # and with the flag somehow present on a no-words turn, still no journal entry
    CC.complete_clinical_flags({"mental_wellbeing": SI}, PERSONA, "", False)
    assert not JOURNAL


@check("3. Mental Wellbeing's ok write_journal in the trace: no code journal; a failed one or "
       "none: one code journal")
def _():
    _trace_with_mw_journal(True)
    CC.complete_clinical_flags({"mental_wellbeing": SI_WITH}, PERSONA, SAID, True)
    assert not JOURNAL
    _trace_with_mw_journal(False)
    CC.complete_clinical_flags({"mental_wellbeing": SI_WITH}, PERSONA, SAID, True)
    assert len(JOURNAL) == 1
    JOURNAL.clear()
    _trace_with_mw_journal(None)
    CC.complete_clinical_flags({"mental_wellbeing": SI_WITH}, PERSONA, SAID, True)
    assert len(JOURNAL) == 1
    assert JOURNAL[0]["tags"] == ["clinical", "recorded_by_code", "SUICIDAL_IDEATION"], JOURNAL


@check("4. no trace (a direct run) means UNKNOWN: code writes the entry")
def _():
    assert TR.get_trace() is None
    CC.complete_clinical_flags({"mental_wellbeing": SI_WITH}, PERSONA, SAID, True)
    assert len(JOURNAL) == 1


@check("5. the journal text carries no CLINICAL_CONCERN token, and the user's words capped at 600")
def _():
    CC.complete_clinical_flags({"mental_wellbeing": SI}, PERSONA, "x" * 2000, True)
    text = JOURNAL[0]["text"]
    assert "CLINICAL_CONCERN" not in text and "SUICIDAL_IDEATION" not in text, text
    assert "suicidal ideation" in text and text.count("x") <= 600 + 5, len(text)


@check("6. the prefix property: every output is the old text or the old text plus a suffix")
def _():
    outs = {"mental_wellbeing": SI, "physical_health": "FLAGS: none", "finance": "ok"}
    done = CC.complete_clinical_flags(outs, PERSONA, SAID, True)
    for k, v in outs.items():
        assert done[k].startswith(v), k
    assert done["physical_health"] == "FLAGS: none" and done["finance"] == "ok"
    JOURNAL.clear()
    assert CC.complete_clinical_flags({"mental_wellbeing": "prose mentions SUICIDAL_IDEATION on "
                                       "file\nFLAGS: none"}, PERSONA, SAID, True) == {
        "mental_wellbeing": "prose mentions SUICIDAL_IDEATION on file\nFLAGS: none"}
    assert not JOURNAL, "prose is never a flag"


@check("7. two concerns in one output give one journal entry naming both")
def _():
    CC.complete_clinical_flags({"mental_wellbeing": TWO}, PERSONA, SAID, True)
    assert len(JOURNAL) == 1, JOURNAL
    assert "suicidal ideation and anxiety disorder" in JOURNAL[0]["text"], JOURNAL[0]["text"]
    assert {"SUICIDAL_IDEATION", "ANXIETY_DISORDER"} <= set(JOURNAL[0]["tags"])


@check("the item parse is one object shared with _drop_unprompted_clinical_flags")
def _():
    assert ORC._CLINICAL_FLAG_ITEM_RE is CC.CLINICAL_FLAG_ITEM_RE


def main() -> int:
    passed = 0
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"\n     {detail}" if detail else ""))
        passed += ok
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
