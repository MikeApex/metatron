"""
tests/test_routine_pause.py — a routine the user pauses stays paused, and comes back exactly.

Mike asked several times for the virtue review to be dropped "for the time being" and it came
back every evening: no tool could change what `_owned_rituals()` injects. Plan:
archive/plans/routine_pause_plan_2026-10-26.md (and its Fable review, findings 1-4).

What the code puts in front of the model is what is tested — a synthetic persona in a temp
directory, no model call, no network.

Standalone runner (no pytest dependency), matching tests/test_ritual_focus_gate.py.

Usage:
    python3 tests/test_routine_pause.py

Exits 0 if every test passes, 1 otherwise.
"""

import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "routine_pause_test"

EVENING_PROMPT = (
    "How did today go? Anything worth capturing before the day closes? Reference "
    "anything that was left open earlier today rather than asking in the abstract."
)
MORNING_PROMPT = "Good morning. Open with whatever is most time-sensitive today."
VIRTUES = "During the evening close, conduct a Franklin 13-point virtue review. TEMPERANCE-MARKER"
SCHOOL = "School ritual body. SCHOOL-MARKER"

SCHEDULER = f"""
quiet_hours: {{start: "22:00", end: "07:00"}}
schedules:
  morning_brief: {{enabled: true, time: "07:30", agent: coordinator, notification: both,
                  prompt: "{MORNING_PROMPT}"}}
  evening_close: {{enabled: true, time: "20:00", agent: coordinator, notification: push,
                  prompt: "{EVENING_PROMPT}"}}
  manny_school: {{enabled: true, day: sunday, time: "16:00", agent: coordinator,
                 notification: push, prompt: "Manny's school check-in. Go through anything."}}
  weekly_pattern_miner: {{enabled: true, day: sunday, time: "09:00", agent: pattern_miner,
                         notification: terminal, prompt: "Run a full pattern analysis."}}
  weekly_clinical_review: {{enabled: true, day: sunday, time: "11:00",
                           function: tools.escalation.review_clinical_escalations,
                           notification: none}}
"""

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))


def run() -> None:
    import core.orchestrator as ORC
    import core.scheduler as SCH
    import tools.routines as R
    from core.persona import persona_data_dir, persona_scope
    from tools.turn_context import turn_scope

    tmp = Path(tempfile.mkdtemp(prefix="routine_pause_"))
    cfg_dir = tmp / "cfg"
    cfg_dir.mkdir()
    identity = tmp / f"{PERSONA}.md"
    identity.write_text("Synthetic test persona.")
    (cfg_dir / "evening_ritual.md").write_text(VIRTUES)
    (cfg_dir / "manny_school_ritual.md").write_text(SCHOOL)
    (cfg_dir / "scheduler.yaml").write_text(SCHEDULER)
    originals = {p.name: p.read_bytes() for p in cfg_dir.iterdir()}

    saved = (ORC.persona_config_dir, ORC.persona_md, R.persona_config_dir, SCH._load_config)
    ORC.persona_config_dir = lambda persona=None: cfg_dir
    ORC.persona_md = lambda persona=None: identity
    R.persona_config_dir = lambda persona=None: cfg_dir
    import yaml
    SCH._load_config = lambda persona=None: yaml.safe_load(SCHEDULER)
    try:
        with persona_scope(PERSONA):
            shutil.rmtree(persona_data_dir(), ignore_errors=True)

            before = ORC.load_config(kind="evening_close")
            check("baseline: evening close carries the virtue review", "TEMPERANCE-MARKER" in before)

            # -- what can be paused --------------------------------------------------------
            listing = R.list_routines()
            for rid in ("evening_ritual", "manny_school_ritual", "morning_brief",
                        "evening_close", "manny_school"):
                check(f"list shows {rid}", f"- {rid} " in listing, listing)
            for rid in ("weekly_pattern_miner", "weekly_clinical_review", "daily_analytics_rollup"):
                check(f"list omits machinery {rid}", f"- {rid} " not in listing, listing)
            out = R.pause_routine("weekly_clinical_review", evidence="stop the clinical thing")
            check("machinery cannot be paused", out.startswith("error:"), out)
            out = R.pause_routine("franklin", evidence="drop it")
            check("unknown id refused with the real list",
                  out.startswith("error:") and "evening_ritual" in out, out)
            check("evidence required", R.pause_routine("evening", "").startswith("error:"))

            # -- only the user's words -----------------------------------------------------
            with turn_scope(user_turn=False):
                out = R.pause_routine("evening", evidence="scheduler said so")
            check("a scheduled turn's pause is refused", out.startswith("error:"), out)
            check("refused pause stored nothing", not R.paused_routines())

            past = (date.today() - timedelta(days=1)).isoformat()
            check("revisit in the past refused",
                  R.pause_routine("evening", "drop it", revisit=past).startswith("error:"))

            revisit = (date.today() + timedelta(days=92)).isoformat()
            with turn_scope(user_turn=True) as turn:
                turn["user_text"] = "drop the virtue review for three months"
                out = R.pause_routine("evening", evidence="drop the virtue review",
                                      revisit=revisit)
            check("user turn pauses; 'evening' resolves to evening_ritual",
                  R.paused_routines() == {"evening_ritual"}, out)
            rec = R._load(None)["paused"]["evening_ritual"]
            check("the user's real words are stored", rec.get("user_said", "").startswith("drop the"))

            # -- the ritual is gone, everywhere ----------------------------------------------
            during = ORC.load_config(kind="evening_close")
            check("paused: evening close carries no virtue review", "TEMPERANCE-MARKER" not in during)
            school = ORC.load_config(kind="manny_school")
            check("manny_school_ritual untouched", "SCHOOL-MARKER" in school)
            morning = ORC._scheduled_focus_block("morning_brief")
            check("morning brief is told the ritual is paused (no catch-up)",
                  "PAUSED BY THE USER" in morning and "evening_ritual" in morning, morning)
            check("no check-back before the date", "CHECK BACK, ONCE" not in morning)
            check("no paused line on a user-typed turn", ORC._scheduled_focus_block(None) == "")

            # -- scheduler gate --------------------------------------------------------------
            cfg = yaml.safe_load(SCHEDULER)
            with turn_scope(user_turn=True):
                R.pause_routine("manny_school", evidence="skip the school check-in")
            got = SCH._gates_block("manny_school", cfg["schedules"]["manny_school"], cfg, PERSONA)
            check("paused check-in is held by the scheduler", got == "paused by the user", str(got))
            got = SCH._gates_block("evening_close", cfg["schedules"]["evening_close"], cfg, PERSONA)
            check("unpaused check-in is not held for a pause", got != "paused by the user", str(got))
            with turn_scope(user_turn=True):
                R.resume_routine("manny_school", evidence="bring the school check-in back")

            # -- the revisit: once, and only after a delivered reply --------------------------
            doc = R._load(None)
            doc["paused"]["evening_ritual"]["revisit"] = date.today().isoformat()
            R._save(None, doc)
            due = ORC._scheduled_focus_block("morning_brief")
            check("check-back raised on its date", "CHECK BACK, ONCE" in due, due)
            check("check-back not on the quiet check-in",
                  "CHECK BACK, ONCE" not in ORC._scheduled_focus_block("manny_school"))
            ORC._stamp_routine_revisits("morning_brief", "", "")
            check("blank reply does not spend the check-back",
                  "CHECK BACK, ONCE" in ORC._scheduled_focus_block("morning_brief"))
            reply = "Morning. Want the virtue review back?"
            ORC._stamp_routine_revisits("morning_brief", reply, ORC._CANNED_FALLBACK)
            check("a reply the filter suppressed does not spend it (review finding 1)",
                  "CHECK BACK, ONCE" in ORC._scheduled_focus_block("morning_brief"))

            # Both fixed points paused: the question moves to a check-in still running (finding 2).
            with turn_scope(user_turn=True):
                R.pause_routine("morning_brief", evidence="no morning briefs for now")
                R.pause_routine("evening_close", evidence="no evening close for now")
            check("both fixed points paused: asked on a running check-in",
                  "CHECK BACK, ONCE" in ORC._scheduled_focus_block("manny_school"))
            with turn_scope(user_turn=True):
                R.resume_routine("morning_brief", evidence="morning briefs back")
                R.resume_routine("evening_close", evidence="evening close back")

            # A ritual stem in the store never holds a scheduler job of that name (finding 5).
            got = SCH._gates_block("evening_ritual", cfg["schedules"]["evening_close"], cfg, PERSONA)
            check("a paused ritual's id does not hold a job", got != "paused by the user", str(got))

            ORC._stamp_routine_revisits("morning_brief", reply, reply)
            check("delivered reply spends it", "CHECK BACK, ONCE" not in ORC._scheduled_focus_block("morning_brief"))
            check("still paused afterwards", "evening_ritual" in R.paused_routines())

            # -- re-pause replaces the date (finding 3) --------------------------------------
            with turn_scope(user_turn=True):
                R.pause_routine("evening_ritual", evidence="keep it off for good")
            rec = R._load(None)["paused"]["evening_ritual"]
            check("re-pause with no date clears the revisit",
                  rec.get("revisit") is None and rec.get("revisit_raised") is None, str(rec))
            check("re-pause records the latest words (finding 3)",
                  rec.get("evidence") == "keep it off for good", str(rec))
            check("no check-back after 'for good'",
                  "CHECK BACK, ONCE" not in ORC._scheduled_focus_block("morning_brief"))

            # -- resume restores exactly -----------------------------------------------------
            with turn_scope(user_turn=True):
                out = R.resume_routine("evening_ritual", evidence="bring the virtues back")
            after = ORC.load_config(kind="evening_close")
            check("resume restores the evening config byte-identical", after == before, out)
            check("ritual and scheduler files never modified",
                  {p.name: p.read_bytes() for p in cfg_dir.iterdir()} == originals)
            shutil.rmtree(persona_data_dir(), ignore_errors=True)
    finally:
        ORC.persona_config_dir, ORC.persona_md, R.persona_config_dir, SCH._load_config = saved
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    run()
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail[:400]}")
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
