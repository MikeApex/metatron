#!/usr/bin/env python3
"""
tests/test_medication_check.py — #8, the medication check computed in code at every Physical
Health return (Stage 3 plan § 1.1, tests 1–17; archive/plans/
instructions_to_code_stage3_hard_fail_plan_2026-11-23.md).

No model is called. Unit checks monkeypatch `tools.obligations.medication_taken`; the "real
store" checks run on a temporary persona tree (tests/support/stage3_fixtures.sandbox) with a
generic medicine, "lamotrigine"; the pipeline checks drive the REAL twins and the REAL
`_run_single_agent` over a scripted provider (stage3_fixtures.pipeline).

Run:  python tests/test_medication_check.py
"""
from __future__ import annotations

import inspect
import json
import os
import sys
from datetime import date, datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from support.stage3_fixtures import (PERSONA, Script, coordinator_package, collect_stream,  # noqa: E402
                                     linked_habit, patched, pipeline, sandbox)

from core import orchestrator as ORC  # noqa: E402
from tools import clinical_checks as CC  # noqa: E402
from tools import obligations as O  # noqa: E402
from tools import turn_context as T  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name):
    def deco(fn):
        try:
            fn()
            RESULTS.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-900:]}"))
        return fn
    return deco


PROFILE = {"medications": [
    {"name": "lamotrigine", "dose": "100mg", "schedule": "daily, morning",
     "criticality": "required"},
    {"name": "vitamin D", "dose": "1000IU", "schedule": "daily", "criticality": "optional"},
]}
PROFILE_LAM_ONLY = {"medications": [PROFILE["medications"][0]]}
# Today's date (log files are dated by the machine calendar, the view by the ledger clock — the
# two must agree for an unlinked medicine's log entry to be read), at 09:00.
MORNING = datetime.combine(date.today(), time(9, 0))


def _row(name="lamotrigine", linked=True, crit="required", missed=True, in_profile=True,
         needs_link=False, link_broken=False, relink_to=None, task_id="t-0001"):
    r = {"medication": name, "linked": linked, "criticality": crit, "missed": missed,
         "in_profile": in_profile, "needs_link": needs_link, "link_broken": link_broken,
         "task_id": task_id if linked else None}
    if relink_to:
        r["relink_to"] = relink_to
    return r


def _view(*rows, ok=True):
    return {"ok": ok, "day": "2026-11-20", "medications": list(rows),
            **({} if ok else {"reason": "the task store could not be read"})}


def _with_view(view):
    return patched([(O, "medication_taken", lambda persona=None, day=None: view)])


def _h1(result: str, persona: str = PERSONA) -> str:
    return ORC._physical_health_return(result, persona)


PH_PLAIN = "SLEEP: 5 / poor\nFOOD: skipped breakfast\nENERGY: low\nFLAGS: none"


# --- 1–8: the note, from the row fields --------------------------------------------------

@check("1. a required missed row gives the critical flag and MUST_SURFACE; the linked sentence "
       "names update_task and the task id, the unlinked one names no tool")
def _():
    with _with_view(_view(_row())):
        n = CC.medication_note(PERSONA)
    assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in n["text"], n
    assert "MUST_SURFACE: lamotrigine, a required medication, reads missed today." in n["text"]
    assert "update_task, t-0001" in n["text"] and n["critical"] == ["lamotrigine"]
    with _with_view(_view(_row(linked=False, needs_link=True))):
        n = CC.medication_note(PERSONA)
    assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in n["text"]
    assert "MEDICATION_NEEDS_LINK: lamotrigine" in n["text"]
    assert "update_task" not in n["text"] and "offer to link it to a habit" in n["text"], n


@check("2. a model output that already holds the flag is a prefix of H1's result, and the note "
       "adds no second MUST_SURFACE")
def _():
    model = PH_PLAIN.replace("FLAGS: none", "FLAGS: MEDICATION_MISSED_CRITICAL: lamotrigine\n"
                                            "MUST_SURFACE: lamotrigine missed")
    with _with_view(_view(_row())):
        out = _h1(model)
    assert out.startswith(model), out
    note = out[len(model):]
    assert "MUST_SURFACE" not in note, note
    assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in note and "update_task" in note


@check("3. real store: MEDICATION_TAKEN on a user turn is recorded first and emits no critical "
       "flag; on a non-user turn nothing is recorded and the flag is emitted")
def _():
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
        tid = linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
        text = PH_PLAIN + "\nMEDICATION_TAKEN: lamotrigine"
        with T.turn_scope(user_turn=False):
            out = _h1(text)
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in out, out
        r = next(x for x in O.medication_taken()["medications"] if x["task_id"] == tid)
        assert r["done"] == 0, r
        with T.turn_scope(user_turn=True):
            out = _h1(text)
        assert "MEDICATION_MISSED_CRITICAL" not in out, out
        assert "lamotrigine (1 of 1 today)" in out, out
        r = next(x for x in O.medication_taken()["medications"] if x["task_id"] == tid)
        assert (r["done"], r["missed"]) == (1, False), r


@check("4. ok False gives the UNKNOWN text only, and a model-written flag stays byte for byte")
def _():
    model = PH_PLAIN.replace("FLAGS: none", "FLAGS: MEDICATION_MISSED_CRITICAL: lamotrigine")
    with _with_view(_view(ok=False)):
        n = CC.medication_note(PERSONA)
        out = _h1(model)
    assert n["flags"] == [] and "UNKNOWN" in n["text"] and "MEDICATION_" not in n["text"], n
    assert out.startswith(model) and "could not be read: UNKNOWN" in out[len(model):], out


@check("5. an optional row: MISSED_OPTIONAL, no MUST_SURFACE")
def _():
    with _with_view(_view(_row("vitamin D", crit="optional"))):
        n = CC.medication_note(PERSONA)
    assert "MEDICATION_MISSED_OPTIONAL: vitamin D" in n["text"] and "MUST_SURFACE" not in n["text"]
    assert n["critical"] == []


@check("6. missed None: UNKNOWN for that medicine, no flag")
def _():
    with _with_view(_view(_row(missed=None))):
        n = CC.medication_note(PERSONA)
    assert n["flags"] == [] and "record UNKNOWN" in n["text"], n


@check("7. criticality (ruling C): linked + in profile + none is critical; link_broken gives "
       "LINK_BROKEN only; unlinked + none is a note; relink_to required reads as any row")
def _():
    with _with_view(_view(_row(crit=None))):
        assert CC.medication_note(PERSONA)["critical"] == ["lamotrigine"]
    with _with_view(_view(_row(crit="required", in_profile=False, link_broken=True))):
        n = CC.medication_note(PERSONA)
    assert n["flags"] == ["MEDICATION_LINK_BROKEN: lamotrigine"] and "MUST_SURFACE" not in n["text"], n
    with _with_view(_view(_row(linked=False, crit=None))):
        n = CC.medication_note(PERSONA)
    assert n["flags"] == [] and "no criticality on file" in n["text"], n
    with _with_view(_view(_row(crit="required", in_profile=False, link_broken=True,
                               relink_to="lamotrigine"))):
        n = CC.medication_note(PERSONA)
    assert "MEDICATION_LINK_BROKEN: lamotrigine" in n["flags"] and n["critical"] == ["lamotrigine"]
    # Review item 7: a relinked row is read against the NEW profile entry, which exists, so a
    # criticality-less linked row is critical under ruling C, like any other linked row.
    with _with_view(_view(_row(crit=None, in_profile=False, link_broken=True,
                               relink_to="lamotrigine"))):
        assert CC.medication_note(PERSONA)["critical"] == ["lamotrigine"]


@check("7'. a renamed medicine: a dose reported by its NEW profile name is recorded on the habit "
       "still linked to the old one, not logged as an unlinked dose (review item 7)")
def _():
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
        tid = linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
        renamed = {"medications": [{**PROFILE_LAM_ONLY["medications"][0], "name": "lamotrigine XR"}]}
        (sb["data"] / "config" / "physical_health.json").write_text(
            json.dumps({"medication_profile": json.dumps(renamed)}))
        row = next(r for r in O.medication_taken()["medications"] if r.get("task_id") == tid)
        assert row.get("relink_to") == "lamotrigine XR" and row["missed"] is True, row
        with T.turn_scope(user_turn=True):
            out = _h1(PH_PLAIN + "\nMEDICATION_TAKEN: lamotrigine XR")
        row = next(r for r in O.medication_taken()["medications"] if r.get("task_id") == tid)
        assert (row["done"], row["missed"]) == (1, False), row
        assert "MEDICATION_MISSED_CRITICAL" not in out and "lamotrigine XR (1 of 1 today)" in out, out
        assert not list((sb["data"] / "logs").glob("*.json")) or not any(
            (json.loads(f.read_text()).get("health") or {}).get("medications_logged")
            for f in (sb["data"] / "logs").glob("*.json")), "logged as if unlinked"


@check("3'. MUST_SURFACE (review item 3): a model 'MUST_SURFACE: none' does not withhold code's; "
       "a consult storing into the open slot keeps code's MUST_SURFACE even when the model had one")
def _():
    model = PH_PLAIN.replace("FLAGS: none", "FLAGS: MEDICATION_MISSED_CRITICAL: lamotrigine\n"
                                            "MUST_SURFACE: none")
    with _with_view(_view(_row())):
        out = _h1(model)
        assert "MUST_SURFACE: lamotrigine, a required medication" in out[len(model):], out
        surfaced = model.replace("MUST_SURFACE: none", "MUST_SURFACE: lamotrigine missed")
        with T.turn_scope(user_turn=True) as turn:
            turn["medication"] = {}
            assert _h1(surfaced) == surfaced
            assert "MUST_SURFACE: lamotrigine, a required medication" in turn["medication"]["note"]


@check("8. the prefix property: every view above leaves the model's text a prefix of H1's result")
def _():
    views = [_view(_row()), _view(ok=False), _view(_row(crit="optional")), _view(_row(missed=None)),
             _view(_row(linked=False, crit=None)), _view(), _view(_row(missed=False))]
    for v in views:
        with _with_view(v):
            for model in ("", PH_PLAIN, "FLAGS: MEDICATION_MISSED_CRITICAL: lamotrigine"):
                assert _h1(model).startswith(model)
    with _with_view(_view(_row(missed=False))):
        assert _h1(PH_PLAIN) == PH_PLAIN, "nothing to say adds nothing"
    with patched([(O, "medication_taken", lambda **k: 1 / 0)]):
        assert _h1(PH_PLAIN) == PH_PLAIN, "a failing view never raises and adds nothing"


# --- 9–13: the pipeline and every path ---------------------------------------------------

def _run_twin(stream: bool, text: str, script: Script) -> str:
    with pipeline(script):
        if stream:
            return collect_stream(ORC.run_pipeline_session_stream(text, persona=PERSONA,
                                                                  provider="openai"))
        return ORC.run_pipeline_session(text, persona=PERSONA, provider="openai")


def _run_twin_ff(stream: bool, text: str, script: Script) -> None:
    """A twin with a fire-and-forget Physical Health. Its background thread calls run_session;
    that is replaced for the whole run, and the test WAITS for the thread's call inside the
    patch (review item 10c), so no thread can outlive the stub and reach a real session."""
    import threading
    called = threading.Event()
    with patched([(ORC, "run_session", lambda *a, **k: called.set() or "")]):
        _run_twin(stream, text, script)
        assert called.wait(10), "the fire-and-forget thread never ran"


def _ph_script(ff: bool = False, ph_reply=PH_PLAIN, synth="All good. [CONTEXT]{}[/CONTEXT]"):
    spec = {"agent": "physical_health", "directive": "Check in on health."}
    if ff:
        spec["fire_and_forget"] = True
    return Script({"coordinator": coordinator_package([spec]), "physical_health": ph_reply},
                  synth_reply=synth)


@check("9. both twins: Physical Health's text is unchanged in the bundle, MEDICATION CHECK "
       "(from code) is its own line, and the sign-off veto sees it")
def _():
    for stream in (False, True):
        with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
            linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
            s = _ph_script()
            _run_twin(stream, "rough night, heading in", s)
            synth_in = s.last("synthesizer")
            assert f"--- physical_health ---\n{PH_PLAIN}\n" in synth_in + "\n", synth_in[-1500:]
            assert "MEDICATION (from code" not in synth_in, "H1 appended in the pipeline"
            assert "MEDICATION CHECK (from code):" in synth_in
            assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in synth_in
            assert T.current() is None or "medication" not in (T.current() or {})
            s2 = _ph_script()
            _run_twin(stream, "thanks, over and out", s2)
            assert s2.inputs.get("synthesizer"), f"stream={stream}: sign-off skipped despite the flag"


@check("10. fire-and-forget Physical Health: med_line is still in the Synthesizer input")
def _():
    for stream in (False, True):
        with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
            linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
            s = _ph_script(ff=True)
            _run_twin_ff(stream, "rough night, heading in", s)
            synth_in = s.last("synthesizer")
            assert "MEDICATION CHECK (from code):" in synth_in and \
                "MEDICATION_MISSED_CRITICAL: lamotrigine" in synth_in, synth_in[-800:]


@check("11. a failed Physical Health (_unavailable_notice): med_line present")
def _():
    def boom():
        raise RuntimeError("provider down")
    for stream in (False, True):
        with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
            linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
            s = _ph_script(ph_reply=boom)
            _run_twin(stream, "rough night, heading in", s)
            synth_in = s.last("synthesizer")
            assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in synth_in, synth_in[-800:]


@check("12. twin parity: both open and close the slot, call _after_specialists once, and no "
       "longer call _record_reported_doses")
def _():
    for fn in (ORC.run_pipeline_session, ORC._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert src.count("_open_medication_slot()") == 1, fn.__name__
        assert src.count("_close_medication_slot()") == 2, fn.__name__   # skip path + normal
        assert src.count("_after_specialists(") == 1, fn.__name__
        assert "_record_reported_doses(" not in src, fn.__name__
        assert src.index("_open_medication_slot()") < src.index("_dispatch_from_coordinator(")
        assert src.index("_drop_unprompted_clinical_flags(") < src.index("_after_specialists(")
        assert src.index("synthesizer_input = (") < src.rindex("_close_medication_slot()")


@check("13. every path: the flag reaches the consumer — (a) pipeline dispatch, (b) run_subagent in "
       "a bound turn after the slot closed, (c) run_session with no turn, (d) fire-and-forget, "
       "(e) a direct _run_single_agent")
def _():
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
        linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
        # (a)
        s = _ph_script()
        _run_twin(True, "rough night", s)
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in s.last("synthesizer")
        # (b) a consult from the Synthesizer's pass: the slot is closed by then
        s = Script({"physical_health": PH_PLAIN})
        with pipeline(s), T.turn_scope(user_turn=True):
            from tools.subagent import run_subagent
            out = run_subagent("physical_health", "check the medicines")
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in out, out
        # (c) the weekly review: run_session, no turn bound
        assert T.current() is None
        with pipeline(s):
            out = ORC.run_session("physical_health", "weekly review", persona=PERSONA,
                                  provider="openai")
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in out, out
        # (d)
        s = _ph_script(ff=True)
        _run_twin_ff(False, "rough night", s)
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in s.last("synthesizer")
        # (e) the A4 runner's path
        s = Script({"physical_health": PH_PLAIN})
        with pipeline(s):
            out = ORC._run_single_agent("physical_health", "rough night", persona=PERSONA,
                                        provider="openai")
        assert out.startswith(PH_PLAIN) and "MEDICATION_MISSED_CRITICAL: lamotrigine" in out


@check("13f. a Physical Health consult made by another specialist while the slot is open (no "
       "Physical Health dispatched): its check still reaches the Synthesizer input (both twins)")
def _():
    from tools.subagent import run_subagent
    got = {}
    for stream in (False, True):
        with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
            linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
            spec = [{"agent": "work_vocation", "directive": "Plan the day."}]
            s = Script({"coordinator": coordinator_package(spec), "physical_health": PH_PLAIN,
                        "work_vocation": "WORK: busy day"},
                       side_effects={"work_vocation": lambda: got.update(
                           consult=run_subagent("physical_health", "any health limits today?"))})
            _run_twin(stream, "what's on today", s)
            assert got["consult"] == PH_PLAIN, "the slot was open: the consult's text is unchanged"
            synth_in = s.last("synthesizer")
            assert "MEDICATION CHECK (from code):" in synth_in and \
                "MEDICATION_MISSED_CRITICAL: lamotrigine" in synth_in, (stream, synth_in[-600:])


# --- 14–17: same-turn doses -------------------------------------------------------------

@check("14. linked, the MEDICATION_TAKEN line omitted (prose only): flag with the linked "
       "sentence, nothing recorded")
def _():
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
        tid = linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
        text = PH_PLAIN + "\nNOTES: user says they took my lamotrigine with breakfast"
        with T.turn_scope(user_turn=True):
            out = _h1(text)
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in out and f"update_task, {tid}" in out
        r = next(x for x in O.medication_taken()["medications"] if x["task_id"] == tid)
        assert r["done"] == 0


def _log_entries(data_dir: Path) -> list[dict]:
    out = []
    for f in sorted((data_dir / "logs").glob("*.json")):
        d = json.loads(f.read_text())
        out += list((d.get("health") or {}).get("medications_logged") or [])
    return [e for e in out if O._med_key(e.get("name")) == "lamotrigine"]


@check("15. unlinked, same turn, Physical Health wrote medications_logged: no critical flag, "
       "NEEDS_LINK still emitted")
def _():
    from tools.logger import write_log
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING):
        write_log({"health": {"medications_logged": [{"name": "lamotrigine", "taken": True}]}})
        with T.turn_scope(user_turn=True):
            out = _h1(PH_PLAIN)
        assert "MEDICATION_MISSED_CRITICAL" not in out, out
        assert "MEDICATION_NEEDS_LINK: lamotrigine" in out, out


@check("16. unlinked, MEDICATION_TAKEN present, write_log omitted: code records it (one entry); "
       "16a: PH also wrote it — still one entry, its fields kept; 16b: no line, no write — flag")
def _():
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
        with T.turn_scope(user_turn=True):
            out = _h1(PH_PLAIN + "\nMEDICATION_TAKEN: lamotrigine")
        row = next(r for r in O.medication_taken()["medications"] if r["medication"] == "lamotrigine")
        assert row["missed"] is False, row
        assert len(_log_entries(sb["data"])) == 1, _log_entries(sb["data"])
        assert "lamotrigine (logged as taken today)" in out and "MISSED_CRITICAL" not in out, out
    from tools.logger import write_log
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:   # 16a
        write_log({"health": {"medications_logged": [
            {"name": "lamotrigine", "taken": True, "dose": "100mg", "time": "08:10",
             "notes": "with breakfast"}]}})
        with T.turn_scope(user_turn=True):
            out = _h1(PH_PLAIN + "\nMEDICATION_TAKEN: lamotrigine")
        entries = _log_entries(sb["data"])
        assert len(entries) == 1 and entries[0]["dose"] == "100mg" and \
            entries[0]["time"] == "08:10" and entries[0]["notes"] == "with breakfast", entries
        assert "already logged" in out, out
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:   # 16a': a taken:false entry
        write_log({"health": {"medications_logged": [
            {"name": "lamotrigine", "taken": False, "dose": "100mg", "notes": "forgot"}]}})
        with T.turn_scope(user_turn=True):
            _h1(PH_PLAIN + "\nMEDICATION_TAKEN: lamotrigine")
        entries = _log_entries(sb["data"])
        assert len(entries) == 1 and entries[0]["taken"] is True and \
            entries[0]["dose"] == "100mg" and entries[0]["notes"] == "forgot", entries
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:   # 16b
        with T.turn_scope(user_turn=True):
            out = _h1(PH_PLAIN)
        assert "MEDICATION_MISSED_CRITICAL: lamotrigine" in out and not _log_entries(sb["data"])


@check("17. no double count: a consult in a turn whose pipeline Physical Health already recorded "
       "the dose says 'already recorded'")
def _():
    with sandbox(profile=PROFILE_LAM_ONLY, clock=MORNING) as sb:
        tid = linked_habit(sb["state"], "Take lamotrigine", "lamotrigine")
        text = PH_PLAIN + "\nMEDICATION_TAKEN: lamotrigine"
        with T.turn_scope(user_turn=True):
            first = _h1(text)
            sb["state"]["clock"] = MORNING.replace(minute=5)
            again = _h1(text)
        assert "lamotrigine (1 of 1 today)" in first
        assert "already recorded" in again, again
        r = next(x for x in O.medication_taken()["medications"] if x["task_id"] == tid)
        assert r["done"] == 1


def main() -> int:
    passed = 0
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"\n     {detail}" if detail else ""))
        passed += ok
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
