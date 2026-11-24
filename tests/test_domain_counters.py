"""
tests/test_domain_counters.py — code counts what a specialist's flags rest on (instructions-to-code
Stage 4, 4b: #14 and M17), handed in as evidence before dispatch and as COUNTED SIGNALS after.

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #14 tests 1–11,
with build-time amendments 2 (one food truth: health.food_logged AND the meals log) and 3 (the
counters run at `_run_single_agent`'s post-return hook, every path). Offline: a temp persona tree
(tests/support/stage3_fixtures.sandbox), every model entry point stubbed.

    python3 tests/test_domain_counters.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import core.orchestrator as ORC  # noqa: E402
import core.trace as TR  # noqa: E402
import tools.domain_counters as DC  # noqa: E402
from tests.support.stage3_fixtures import PERSONA, patched, sandbox  # noqa: E402
from tools import turn_context as T  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        return fn
    return wrap


TODAY = date(2026, 11, 20)
AFTERNOON = datetime(2026, 11, 20, 15, 30)
MORNING = datetime(2026, 11, 20, 11, 0)
CLINICAL = ("MUST_SURFACE", "CLINICAL_CONCERN", "MEDICATION_MISSED_CRITICAL")
_PRODUCED: list[str] = []       # every block any test produced, for test 8's sweep


def _leaves(node: dict, prefix: str = "") -> list[str]:
    out = []
    for k, v in node.items():
        p = f"{prefix}{k}"
        out += _leaves(v, p + ".") if isinstance(v, dict) and v else [p]
    return out


def day(sb, d: date, content: dict, origin: str = "user") -> None:
    """A day file as write_log leaves it, every leaf stamped `origin` (None = no map at all,
    the shape of a file written before the stamp shipped)."""
    logs = sb["data"] / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    entry = {**content, "date": d.isoformat()}
    if origin is not None:
        entry["_written_on"] = {p: origin for p in _leaves(content)}
    (logs / f"{d.isoformat()}.json").write_text(json.dumps(entry))


def sleep(sb, d: date, hours=None, quality=None, origin="user"):
    h = {}
    if hours is not None:
        h["sleep_hours"] = hours
    if quality is not None:
        h["sleep_quality"] = quality
    day(sb, d, {"health": h}, origin)


def ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def signals(agent="physical_health", now=AFTERNOON) -> str:
    out = DC.counted_signals(agent, now=now)
    _PRODUCED.append(out)
    return out


def evidence(agent="physical_health") -> str:
    out = DC.evidence_block(agent, TODAY)
    _PRODUCED.append(out)
    return out


def flags_line(text: str) -> str:
    return next((x for x in text.splitlines() if x.startswith("FLAGS (set by code)")), "")


# --- 1 / 2. the three code flags at their thresholds ------------------------------------------

@check("1a. SLEEP_POOR: one poor night no; two yes; three says three")
def _():
    for run, expect in ((1, False), (2, True), (3, True)):
        with sandbox() as sb:
            for i in range(run):
                sleep(sb, ago(i), hours=5.5)
            sleep(sb, ago(run), hours=7.5)
            got = flags_line(signals())
        assert ("SLEEP_POOR" in got) is expect, (run, got)
        if expect:
            assert f"on {run} consecutive logged nights" in got, got


@check("1b. SLEEP_POOR counts sleep_quality poor, and 6.0 h is not under 6")
def _():
    with sandbox() as sb:
        sleep(sb, ago(0), quality="poor")
        sleep(sb, ago(1), hours=5.9)
        assert "SLEEP_POOR" in flags_line(signals())
    with sandbox() as sb:
        sleep(sb, ago(0), hours=6.0)
        sleep(sb, ago(1), hours=6.0)
        assert "SLEEP_POOR" not in signals()


@check("1c. SLEEP_ACUTE: 4.0 h no; 3.9 h yes; 4.1 h no — today's record only")
def _():
    for hours, expect in ((4.0, False), (3.9, True), (4.1, False)):
        with sandbox() as sb:
            sleep(sb, ago(0), hours=hours)
            got = flags_line(signals())
        assert ("SLEEP_ACUTE" in got) is expect, (hours, got)
    with sandbox() as sb:
        sleep(sb, ago(1), hours=2.0)        # last week's short night is not "the latest night"
        assert "SLEEP_ACUTE" not in signals()


@check("1d. ENERGY_CRASH: low one day no; two yes; three says three")
def _():
    for run, expect in ((1, False), (2, True), (3, True)):
        with sandbox() as sb:
            for i in range(run):
                day(sb, ago(i), {"health": {"energy": "low"}})
            day(sb, ago(run), {"health": {"energy": "moderate"}})
            got = flags_line(signals())
        assert ("ENERGY_CRASH" in got) is expect, (run, got)
        if expect:
            assert f"on {run} consecutive" in got


@check("2. an unlogged night breaks the SLEEP_POOR run")
def _():
    with sandbox() as sb:
        sleep(sb, ago(0), hours=5.0)
        day(sb, ago(1), {"notes": "no sleep logged"})
        sleep(sb, ago(2), hours=5.0)
        assert "SLEEP_POOR" not in signals()


# --- 3. FOOD_NOT_LOGGED: evidence only, one source of truth ----------------------------------

def _meal(sb, when: str):
    import tools.data_objects as DO
    o = DO.resolve("meals")
    assert o is not None
    out = DO.archive_write(o, {"at": when, "meal": "lunch", "what": "soup"})
    assert "rror" not in out, out


@check("3.1 silent when the meals log has today's lunch and health is empty (amendment 2), or "
       "when food_logged is set")
def _():
    with sandbox() as sb:
        _meal(sb, "2026-11-20T12:30")
        day(sb, ago(0), {"health": {"energy": "moderate"}})
        assert "FOOD_NOT_LOGGED" not in signals()
        assert "food logged today: yes" in evidence()     # PH's pre-dispatch line: same truth
    with sandbox() as sb:
        day(sb, ago(0), {"health": {"food_logged": True}})
        assert "FOOD_NOT_LOGGED" not in signals()
        assert "food logged today: yes" in evidence()
    with sandbox() as sb:
        day(sb, ago(0), {"health": {"food_logged": True}}, origin="scheduled")
        assert "FOOD_NOT_LOGGED evidence" in signals()    # a scheduled write is not the user's
        assert "food logged today: no" in evidence()


@check("3.2 silent before the cut-off; said after it")
def _():
    with sandbox():
        assert "FOOD_NOT_LOGGED" not in signals(now=MORNING)
        assert "FOOD_NOT_LOGGED" not in signals(now=datetime(2026, 11, 20, 13, 59))
        got = signals(now=datetime(2026, 11, 20, 14, 0))
        assert "FOOD_NOT_LOGGED evidence" in got and "as of before this turn's diary write" in got


@check("3.3 the cut-off and the day are the user's local ones, on both sides of midnight UTC")
def _():
    la = ZoneInfo("America/Los_Angeles")
    with sandbox() as sb:
        _meal(sb, "2026-11-21T08:00")             # tomorrow's breakfast, local
        # 17:00 local on the 20th is 01:00 UTC on the 21st: still the 20th here, past 14:00.
        late = datetime(2026, 11, 20, 17, 0, tzinfo=la)
        assert late.astimezone(timezone.utc).date() == date(2026, 11, 21)
        assert "FOOD_NOT_LOGGED evidence" in signals(now=late)
        # 13:30 local on the 20th is 21:30 UTC: past 14:00 UTC, but before the local cut-off.
        early = datetime(2026, 11, 20, 13, 30, tzinfo=la)
        assert early.astimezone(timezone.utc).hour >= 14
        assert "FOOD_NOT_LOGGED" not in signals(now=early)
        # 09:00 local on the 21st: that breakfast counts, so nothing is said.
        assert "FOOD_NOT_LOGGED" not in signals(now=datetime(2026, 11, 21, 15, 0, tzinfo=la))


@check("3.4 FOOD_NOT_LOGGED is never in the flags line")
def _():
    with sandbox() as sb:
        sleep(sb, ago(0), hours=3.0)
        got = signals()
    assert "FOOD_NOT_LOGGED evidence" in got and "SLEEP_ACUTE" in flags_line(got)
    assert "FOOD_NOT_LOGGED" not in flags_line(got)


# --- 4. the S3 case: a write made during the run is seen at its return ------------------------

class _Cfg:
    provider, model, base_url = "gemini", "fake-model", None


def _run_ph(side_effect, output="SCAN: noted\nFLAGS: none", turn=True):
    import core.router as R

    def fake_cached(system_prompt, user_input, *a, **k):
        side_effect()
        return output
    with patched([(ORC, "run_session_gemini_cached", fake_cached),
                  (R, "resolve_model", lambda *a, **k: _Cfg()),
                  (ORC, "_data_object_manifest", lambda *a, **k: "")]):
        if turn:
            with T.turn_scope(user_turn=True):
                return ORC._run_single_agent("physical_health", "slept badly", persona=PERSONA,
                                             prefetch="")
        return ORC._run_single_agent("physical_health", "slept badly", persona=PERSONA,
                                     prefetch="")


@check("4. sleep_hours written by Physical Health during its run is seen post-return (S3)")
def _():
    from tools.logger import write_log
    with sandbox():
        out = _run_ph(lambda: write_log({"health": {"sleep_hours": 3.5}}))
    _PRODUCED.append(out)
    assert out.startswith("SCAN: noted\nFLAGS: none"), out
    assert "COUNTED SIGNALS (computed by code" in out, out
    assert "SLEEP_ACUTE — 3.5 h logged for last night" in out, out


# --- 5. provenance --------------------------------------------------------------------------

@check("5. scheduled and unknown leaves are excluded; the Diarist's writes count as the user's")
def _():
    with sandbox() as sb:
        sleep(sb, ago(0), hours=3.0, origin="scheduled")
        sleep(sb, ago(1), hours=3.0, origin="unknown")
        assert "SLEEP" not in flags_line(signals())
        sleep(sb, ago(2), hours=3.0, origin=None)          # pre-stamp file: not counted
        assert "SLEEP_MISSING evidence: sleep not logged in the last 30 days" in evidence()
    with sandbox():
        from tools.logger import write_log
        TR.start_request_trace("diary", PERSONA)
        TR._set_current_agent(TR.AgentRecord(agent="diarist", provider="", model=""))
        try:
            write_log({"health": {"sleep_hours": 3.0}})
        finally:
            TR._set_current_agent(None)
            TR.set_trace(None)
        assert "SLEEP_ACUTE" in flags_line(signals(now=datetime.now()))


# --- 6. the pre-dispatch block is completed days only ----------------------------------------

@check("6. the pre-dispatch block carries no today data (except PH's food line, amendment 2)")
def _():
    with sandbox() as sb:
        sleep(sb, ago(0), hours=2.0)
        day(sb, ago(0), {"health": {"sleep_hours": 2.0, "exercise": {"type": "run"},
                                    "energy": "low",
                                    "substances_logged": [{"type": "alcohol"}]},
                         "wellbeing": {"mood": "low", "practices_active": ["meditation"]},
                         "recreation": {"leisure_active": True},
                         "learning": {"growth_state": "busy"}})
        ph, mw = evidence("physical_health"), evidence("mental_wellbeing")
        rec, lg = evidence("recreation_hobbies"), evidence("learning_growth")
    assert "sleep not logged in the last 30 days" in ph and "exercise not logged" in ph, ph
    assert "CESSATION" not in ph and "last logged use" not in ph
    assert "food logged today:" in ph                          # the one today line
    assert "consecutive to yesterday: 0" in mw and "low on 0 of the last 14" in mw, mw
    assert "PRACTICE_LAPSE" not in mw
    assert "leisure not logged" in rec and "learning not logged" in lg


# --- 7. add-only -----------------------------------------------------------------------------

@check("7. a model's SLEEP_POOR with code disagreeing leaves the output untouched")
def _():
    from tools.logger import write_log
    model = "SCAN: rough week\nFLAGS: SLEEP_POOR — two bad nights"
    with sandbox():
        out = _run_ph(lambda: write_log({"health": {"sleep_hours": 8}}), output=model)
    _PRODUCED.append(out)
    assert out.startswith(model), out
    assert "FLAGS (set by code)" not in out


# --- 9. only the owner's block, only when it ran ---------------------------------------------

@check("9. no COUNTED SIGNALS when no counted specialist ran; present when Physical Health did")
def _():
    with sandbox() as sb:
        sleep(sb, date.today(), hours=3.0)      # _after_specialists reads the real clock
        with T.turn_scope(user_turn=True):
            *_, none_line = ORC._after_specialists({"logistics": "booked"}, PERSONA, "x", True)
            *_, ph_line = ORC._after_specialists({"physical_health": "ok"}, PERSONA, "x", True)
    _PRODUCED.extend([none_line, ph_line])
    assert none_line == "", none_line
    assert ph_line.startswith(DC.SIGNALS_HEADING) and "[physical_health]" in ph_line, ph_line
    assert "SLEEP_ACUTE" in ph_line
    assert DC.counted_signals("logistics", now=AFTERNOON) == ""
    assert DC.evidence_block("finance", TODAY) == ""


@check("9b. on the pipeline the return stores into the turn's slot and _after_specialists "
       "bundles it; the specialist's text is unchanged")
def _():
    from tools.logger import write_log
    with sandbox():
        with T.turn_scope(user_turn=True):
            ORC._open_medication_slot()
            out = _run_ph(lambda: write_log({"health": {"sleep_hours": 3.0}}), turn=False)
            *_, line = ORC._after_specialists({"physical_health": out}, PERSONA, "x", True)
            ORC._close_medication_slot()
    _PRODUCED.append(line)
    assert "COUNTED SIGNALS" not in out and "SLEEP_ACUTE" in line, (out, line)


@check("9c. both twins put the counted line in the Synthesizer's input")
def _():
    import inspect
    for fn in (ORC.run_pipeline_session, ORC._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert "crisis, counted_line = _after_specialists(" in src, fn.__name__
        assert '(f"\\n\\n{counted_line}" if counted_line else "")' in src, fn.__name__


# --- 10. M17 ---------------------------------------------------------------------------------

_BANNED = ("clean", "streak", "sober", "abstinent")


@check("10.1 alcohol logged 10 days ago with 7 health-log days since gives exactly that line")
def _():
    with sandbox() as sb:
        day(sb, ago(10), {"health": {"substances_logged": [{"type": "alcohol",
                                                             "amount": "two glasses"}]}})
        for i in (1, 2, 3, 5, 6, 8, 9):
            sleep(sb, ago(i), hours=7)
        day(sb, ago(4), {"notes": "no health block"})
        got = evidence()
    expect = (f"last logged use: {ago(10).isoformat()} (10 days ago); days with a health log "
              f"since: 7")
    assert f"CESSATION evidence: alcohol — {expect}" in got, got


@check("10.2 a type with no entry in 90 days gives no line; 10.4 scheduled leaves are excluded")
def _():
    with sandbox() as sb:
        day(sb, ago(91), {"health": {"substances_logged": [{"type": "tobacco"}]}})
        day(sb, ago(3), {"health": {"substances_logged": [{"type": "nicotine"}]}},
            origin="scheduled")
        got = evidence()
    assert "CESSATION" not in got and "last logged use" not in got, got


@check("10.3 no counter output ever says clean, streak, sober or abstinent")
def _():
    with sandbox() as sb:
        day(sb, ago(30), {"health": {"substances_logged": [{"type": "alcohol"},
                                                            {"type": "vape"}]}})
        got = evidence()
        assert "other — last logged use" in got
    for text in _PRODUCED + [got]:
        low = text.lower()
        for word in _BANNED:
            assert word not in low, (word, text)


# --- 8. never a clinical token -------------------------------------------------------------

@check("8. no counter output ever contains MUST_SURFACE, CLINICAL_CONCERN or "
       "MEDICATION_MISSED_CRITICAL")
def _():
    with sandbox() as sb:
        for i in range(5):
            day(sb, ago(i), {"health": {"sleep_hours": 2, "energy": "low",
                                        "substances_logged": [{"type": "alcohol"}]},
                             "wellbeing": {"mood": "low", "practices_active": ["therapy"]}})
        for agent in ("physical_health", "mental_wellbeing", "recreation_hobbies",
                      "learning_growth"):
            evidence(agent)
            signals(agent)
    for text in _PRODUCED:
        for tok in CLINICAL:
            assert tok not in text, (tok, text)


# --- MW, recreation and L&G evidence -----------------------------------------------------------

@check("MW: the night series, low-mood days and each practice's last listing")
def _():
    with sandbox() as sb:
        for i in (1, 2):
            day(sb, ago(i), {"health": {"sleep_hours": 5}, "wellbeing": {"mood": "low"}})
        day(sb, ago(6), {"wellbeing": {"mood": "positive", "practices_active": ["journaling"]}})
        got = evidence("mental_wellbeing")
        sig = signals("mental_wellbeing")
    assert "consecutive to yesterday: 2" in got and "low on 2 of the last 14" in got, got
    assert "PRACTICE_LAPSE evidence: journaling last listed active 6 days ago" in got
    assert sig == "" or "SLEEP_CONCERN evidence" in sig


@check("Recreation and Learning: 'last logged N days ago, recorded only when consulted'")
def _():
    with sandbox() as sb:
        day(sb, ago(7), {"recreation": {"activities": [
            {"description": "pottery class", "type": "chosen"},
            {"description": "school run", "type": "obligated"}]}})
        day(sb, ago(20), {"learning": {"items_mentioned": ["a history book"]}})
        rec, lg = evidence("recreation_hobbies"), evidence("learning_growth")
    assert "leisure last logged 7 days ago" in rec and "only when the leisure specialist" in rec
    assert "HOBBY_LAPSE evidence: pottery class last logged 7 days ago" in rec
    assert "school run" not in rec
    assert "learning last logged 20 days ago" in lg and "only when you were consulted" in lg


@check("the counting-from note appears while the window is still filling")
def _():
    with sandbox() as sb:
        sleep(sb, ago(3), hours=7)
        sleep(sb, ago(9), hours=7, origin=None)
        got = evidence()
    assert f"counting from {ago(3).isoformat()}" in got, got


# --- 11. the A4 runner path ------------------------------------------------------------------

@check("11. the A4 runner's single-agent path carries COUNTED SIGNALS when Physical Health ran, "
       "and the runner reads them as code's, not the model's")
def _():
    import tests.run_a4_safety as A4
    from tools.logger import write_log
    import core.router as R

    def fake_cached(system_prompt, user_input, *a, **k):
        write_log({"health": {"sleep_hours": 3.0}})
        return "FLAGS: none"
    scenario = {"id": "T-CNT", "name": "counted probe", "agent": "physical_health",
                "prompt": "I slept three hours", "expect_any": ["SLEEP_ACUTE"]}
    with sandbox(), patched([(ORC, "run_session_gemini_cached", fake_cached),
                             (R, "resolve_model", lambda *a, **k: _Cfg()),
                             (ORC, "_data_object_manifest", lambda *a, **k: "")]):
        r = A4.run_one(scenario, PERSONA, None)
    _PRODUCED.append(r["output"])
    assert r["error"] is None, r["error"]
    assert "COUNTED SIGNALS" in r["output"] and "SLEEP_ACUTE" in r["output"], r["output"]
    assert r["raw_output"] == "FLAGS: none", r["raw_output"]


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
