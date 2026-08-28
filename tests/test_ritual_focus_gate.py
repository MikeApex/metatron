"""
tests/test_ritual_focus_gate.py — a scheduled run asks once, stays quiet when nothing is new,
and does not carry another job's ritual.

[DB-0809-02]. Measured 2026-08-27: four different scheduled jobs each re-asked the SAME
unanswered question — five asks, never an answer — the 13-item virtue list went out four times,
and the runs carrying the LEAST new information were the longest. Mike's frame: "Most of these
should be touched upon ONCE if at all. Runs with little information should be short and sweet."

Three halves are covered here, all of them structural rather than instructional, on the same
reasoning as tests/test_evening_ritual_gate.py: an instruction the model already had was the
thing that failed, so what is tested is what the code puts in front of the model.

  1. ASKED-STATE — a question asked by a scheduled run is recorded, is not put again by a
     different job, is re-raisable only under the sparse thresholds, and is cleared by a user
     turn that answers it.
  2. THE FOCUS GATE — an empty context delta switches the run's directive to a short check-in.
     NOT a length cap (that proposal was rejected): a run with something new gets the ordinary
     directive and no cap of any kind.
  3. RITUAL OWNERSHIP — `X_ritual.md` reaches the `X…` job and no other.

Standalone runner (no pytest dependency), matching tests/test_evening_ritual_gate.py.

Usage:
    python3 tests/test_ritual_focus_gate.py

Exits 0 if every test passes, 1 otherwise.
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "ritual_focus_gate_test"

_results: list[tuple[str, bool, str]] = []

EVENING_PROMPT = (
    "How did today go? Anything worth capturing before the day closes? Reference "
    "anything that was left open earlier today rather than asking in the abstract."
)
MORNING_PROMPT = (
    "Good morning — time to look at the day ahead. Open on whatever matters most."
)
EVENING_MARKER = "TEMPERANCE-SILENCE-ORDER-RESOLUTION"
MORNING_MARKER = "MORNING-RITUAL-MARKER"

QUESTION = "Did you ever get the bookstore P&L numbers back from Marcus?"


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))


# ---------------------------------------------------------------------------
# 1 + 2 — asked-state memory and the nothing-new delta (tools/context_tracker.py)
# ---------------------------------------------------------------------------

def _asked_state_and_delta() -> None:
    from core.persona import persona_data_dir, persona_scope
    from tools.context_tracker import (
        _MAX_ASKS_PER_QUESTION,
        _MAX_REASKS_PER_DAY,
        _REASK_MIN_INTERVAL_HOURS,
        clear_answered_questions,
        close_scheduled_run,
        extract_questions,
        note_scheduled_run,
        read_context_tracker,
        record_asked_questions,
        write_context_tracker,
    )

    with persona_scope(PERSONA):
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        tracker_path = persona_data_dir() / "context.json"

        # --- extraction -------------------------------------------------------------
        qs = extract_questions(
            "Morning. Did you ever get the bookstore P&L numbers back from Marcus? "
            "Right? Also the gym membership renews Friday."
        )
        check("a real question is extracted from the reply", qs == [QUESTION],
              f"got {qs!r}")
        check("a rhetorical fragment is not recorded as a question",
              extract_questions("Right? Sure?") == [])

        # --- recording an unanswered ask ---------------------------------------------
        record_asked_questions([QUESTION], kind="morning_brief")
        stored = json.loads(tracker_path.read_text())["asked_questions"]
        check("an unanswered scheduled ask is recorded with its text and count",
              len(stored) == 1 and stored[0]["text"] == QUESTION
              and stored[0]["ask_count"] == 1)
        check("the first-asked stamp is server-side, not model-supplied",
              bool(stored[0]["first_asked"]) and bool(stored[0]["last_asked"]))

        check("the asked list is never loaded into model context",
              "asked_questions" not in read_context_tracker(),
              "handing the model the text of a question it must not repeat is how it repeats it")

        # --- a DIFFERENT job does not re-ask it ---------------------------------------
        state = note_scheduled_run("evening_close")
        texts = [q["text"] for q in state["open_questions"]]
        check("a later job sees the question as already asked",
              texts == [QUESTION])
        check("a later job on the same day may NOT re-ask it",
              state["may_reask"] == [],
              f"within {_REASK_MIN_INTERVAL_HOURS}h of the last ask — this is the measured bug")

        # --- the sparse re-raise ------------------------------------------------------
        # Back-date the ask past the interval; one re-raise becomes available.
        data = json.loads(tracker_path.read_text())
        old = (datetime.now() - timedelta(hours=_REASK_MIN_INTERVAL_HOURS + 1)
               ).isoformat(timespec="seconds")
        data["asked_questions"][0]["last_asked"] = old
        data["scheduled_runs"]["reasks"] = {"date": "1970-01-01", "count": 0}
        tracker_path.write_text(json.dumps(data))

        state = note_scheduled_run("morning_brief")
        check("past the interval, the question may be raised once more",
              state["may_reask"] == [QUESTION])

        state = note_scheduled_run("ambient")
        check("the day's re-ask budget is spent — the next job gets nothing",
              state["may_reask"] == [],
              f"_MAX_REASKS_PER_DAY={_MAX_REASKS_PER_DAY} across ALL jobs, not per job")

        # --- the lifetime cap ---------------------------------------------------------
        data = json.loads(tracker_path.read_text())
        data["asked_questions"][0]["ask_count"] = _MAX_ASKS_PER_QUESTION
        data["asked_questions"][0]["last_asked"] = old
        data["scheduled_runs"]["reasks"] = {"date": "1970-01-01", "count": 0}
        tracker_path.write_text(json.dumps(data))
        state = note_scheduled_run("evening_close")
        check("after the lifetime cap the question is never raised again",
              state["may_reask"] == [] and [q["text"] for q in state["open_questions"]] == [QUESTION],
              "it stays an open item — suppressed, not deleted")

        # --- an ordinary tracker write must not erase the asked state -----------------
        write_context_tracker(["some unrelated thread"], [], [])
        check("an ordinary context write does not wipe the asked state",
              json.loads(tracker_path.read_text()).get("asked_questions"),
              "write_context_tracker rebuilds the file from scratch — the carry-forward is the fix")

        # --- an answered question clears --------------------------------------------
        cleared = clear_answered_questions(
            "Marcus finally sent the bookstore numbers over, P&L looks fine.")
        check("a user turn that answers the question clears it", cleared == [QUESTION])
        after = json.loads(tracker_path.read_text())
        check("the cleared question is archived, not deleted",
              after["asked_questions"] == []
              and after["asked_questions_archive"][-1]["closed_reason"] == "answered",
              "archive-on-merge, same as expired open threads")
        check("a cleared question is gone from the next run's suppression list",
              note_scheduled_run("morning_brief")["open_questions"] == [])

        # --- an unrelated user turn does not clear anything --------------------------
        record_asked_questions([QUESTION], kind="morning_brief")
        check("an unrelated user turn clears nothing",
              clear_answered_questions("What's the weather doing tomorrow?") == [])

        # --- the nothing-new delta ---------------------------------------------------
        close_scheduled_run("morning_brief")
        state = note_scheduled_run("ambient")
        check("with nothing changed since the last run closed, the delta is empty",
              state["nothing_new"] is True)
        check("hours since the last run are reported for the check-in line",
              state["hours_since"] is not None)

        # Something new arrives: a log file the user's day produced.
        logs = persona_data_dir() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"{datetime.now().date().isoformat()}.json").write_text(
            json.dumps({"summary": "went climbing"}))
        state = note_scheduled_run("evening_close")
        check("a new log makes the next run's delta non-empty",
              state["nothing_new"] is False,
              "this is the condition that must NOT trigger the short check-in")

        # The run's OWN writes must not count as news for the next run.
        write_context_tracker(["a thread the evening run itself opened"], [], [])
        close_scheduled_run("evening_close")
        state = note_scheduled_run("morning_brief")
        check("a run's own tracker writes do not make the next run look busy",
              state["nothing_new"] is True,
              "the fingerprint is stamped at close, not at open — the system's own output "
              "is not evidence of news")

        shutil.rmtree(persona_data_dir(), ignore_errors=True)


# ---------------------------------------------------------------------------
# 2b + 3 — the injected directive and ritual ownership (core/orchestrator.py)
# ---------------------------------------------------------------------------

def _directive_and_ritual() -> None:
    from core.persona import persona_data_dir, persona_scope

    tmp = tempfile.mkdtemp(prefix="ritual_focus_")
    cfg_dir = Path(tmp) / "persona_config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    os.environ["METATRON_PERSONA"] = PERSONA

    (cfg_dir / "evening_ritual.md").write_text(
        f"# Evening ritual\n\nReview the thirteen virtues: {EVENING_MARKER}\n")
    (cfg_dir / "morning_ritual.md").write_text(
        f"# Morning ritual\n\nName the day's intention: {MORNING_MARKER}\n")
    (cfg_dir / "scheduler.yaml").write_text(
        "schedules:\n"
        "  evening_close:\n"
        "    enabled: true\n"
        '    time: "20:00"\n'
        f'    prompt: "{EVENING_PROMPT}"\n'
        "  morning_brief:\n"
        "    enabled: true\n"
        '    time: "07:30"\n'
        f'    prompt: "{MORNING_PROMPT}"\n'
    )
    identity = Path(tmp) / "identity.md"
    identity.write_text("Test persona for the ritual focus gate.\n")

    import core.orchestrator as ORC
    real_cfg_dir = ORC.persona_config_dir
    real_persona_md = ORC.persona_md
    ORC.persona_config_dir = lambda persona=None: cfg_dir
    ORC.persona_md = lambda persona=None: identity

    try:
        # --- ritual ownership ---------------------------------------------------------
        evening = ORC.load_config(persona=PERSONA, kind="evening_close")
        check("the evening job still gets its own ritual", EVENING_MARKER in evening)
        check("the evening job does NOT get the morning job's ritual",
              MORNING_MARKER not in evening,
              "a scheduled job does not continue a ritual that is not its own")

        morning = ORC.load_config(persona=PERSONA, kind="morning_brief")
        check("the morning job gets its own ritual and only its own",
              MORNING_MARKER in morning and EVENING_MARKER not in morning)

        other = ORC.load_config(persona=PERSONA, kind="ambient")
        check("a third scheduled job inherits neither ritual",
              EVENING_MARKER not in other and MORNING_MARKER not in other)

        ordinary = ORC.load_config(persona=PERSONA, kind=None)
        check("an ordinary typed turn carries no ritual at all",
              EVENING_MARKER not in ordinary and MORNING_MARKER not in ordinary)
        check("gating rituals keeps real weight out of every other session",
              len(ordinary) < len(evening))

        # --- the focus directive ------------------------------------------------------
        from tools.context_tracker import (
            close_scheduled_run, record_asked_questions,
        )
        with persona_scope(PERSONA):
            shutil.rmtree(persona_data_dir(), ignore_errors=True)

            check("an ordinary typed turn gets no scheduled directive at all",
                  ORC._scheduled_focus_block(None) == "",
                  "ordinary conversation is untouched by any of this")

            first = ORC._scheduled_focus_block("morning_brief")
            check("a scheduled run is told which job it is and what it owns",
                  "morning_brief" in first and "not your own" not in first
                  and ORC._RITUAL_OWNERSHIP_LINE.format(kind="morning_brief") in first)
            check("the first ever run does not claim nothing is new",
                  "NOTHING NEW" not in first,
                  "no prior stamp means no basis for the claim")

            close_scheduled_run("morning_brief")
            quiet = ORC._scheduled_focus_block("ambient")
            check("an empty delta switches the run to a short check-in",
                  "NOTHING NEW SINCE THE LAST SCHEDULED RUN" in quiet
                  and "light check-in" in quiet)
            check("the check-in directive states a condition, not a length limit",
                  "sentence" not in quiet.lower() and "word" not in quiet.lower(),
                  "the <=2-sentence cap was rejected and must not reappear here")

            # Something new arrives — the ordinary directive returns.
            logs = persona_data_dir() / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            (logs / f"{datetime.now().date().isoformat()}.json").write_text(
                json.dumps({"summary": "signed the lease"}))
            busy = ORC._scheduled_focus_block("evening_close")
            check("a non-empty delta gets the ordinary directive",
                  "NOTHING NEW" not in busy)

            # An unanswered question reaches the directive as a suppression.
            record_asked_questions([QUESTION], kind="evening_close")
            close_scheduled_run("evening_close")
            nxt = ORC._scheduled_focus_block("ambient")
            check("the unanswered question reaches the next job as DO NOT ASK",
                  "DO NOT ASK THESE AGAIN" in nxt and QUESTION in nxt)
            check("it is framed as an open item, not an obligation",
                  "open items, not obligations" in nxt)

            shutil.rmtree(persona_data_dir(), ignore_errors=True)
    finally:
        ORC.persona_config_dir = real_cfg_dir
        ORC.persona_md = real_persona_md
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    _asked_state_and_delta()
    _directive_and_ritual()
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail}")
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
