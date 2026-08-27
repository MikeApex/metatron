"""
tests/test_synth_module_injection.py — conduct modules reach only the turns that need them.

2026-08-27 synthesizer audit. Scheduled-session conduct and baseline-interview conduct
moved out of config/agents/synthesizer.md into config/modules/, injected by
_synth_conditional_sections() on the same structural gate as the evening ritual
([DB-0822-10]): text that is not injected cannot be recited on a turn it does not
belong to. Delivered by code rather than a model-initiated tool call because
read_agent_config reads the per-persona data store, not config/modules/ — the ROADMAP
§ D2 loader never existed — and because a model cannot forget to load what it never
has to ask for.

Also covers the session_kind() generalisation: it now returns the matching key for ANY
configured schedule (morning_brief, ambient, …), not just evening_close, with a
20-normalised-char minimum so a short prompt ("Check in.") cannot substring-match
ordinary user speech.

Standalone runner (no pytest dependency), matching tests/test_evening_ritual_gate.py.

Usage:
    python tests/test_synth_module_injection.py

Exits 0 if every test passes, 1 otherwise.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_results: list[tuple[str, bool, str]] = []

EVENING_PROMPT = (
    "How did today go? Anything worth capturing before the day closes? Reference "
    "anything that was left open earlier today rather than asking in the abstract."
)
MORNING_PROMPT = (
    "Good morning — time to look at the day ahead. Open on whatever matters most."
)
SHORT_PROMPT = "Check in."

SCHEDULED_MARKER = "Scheduled session conduct"
ONBOARDING_MARKER = "Onboarding and domain baseline interviews"


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))


def _run() -> None:
    tmp = tempfile.mkdtemp(prefix="synth_modules_")
    cfg_dir = Path(tmp) / "persona_config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    os.environ["METATRON_PERSONA"] = "test_confirm"

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
        "  ambient:\n"
        "    enabled: true\n"
        '    time: "13:00"\n'
        f'    prompt: "{SHORT_PROMPT}"\n'
    )

    import core.orchestrator as ORC
    real_cfg_dir = ORC.persona_config_dir
    ORC.persona_config_dir = lambda persona=None: cfg_dir

    try:
        # --- session_kind generalisation ---------------------------------------------
        check("evening_close still recognised (unchanged behaviour)",
              ORC.session_kind(EVENING_PROMPT, "mike") == "evening_close")
        check("morning_brief prompt returns its own key",
              ORC.session_kind(MORNING_PROMPT, "mike") == "morning_brief")
        check("an ordinary typed turn has no session kind",
              ORC.session_kind("Add Marcus Whitfield to my contacts.", "mike") is None)
        check("a short configured prompt never matches — substring hazard",
              ORC.session_kind("Let me just check in. Also, what's on today?", "mike") is None,
              "'Check in.' inside user speech must not make the turn a scheduled session")
        check("a turn that IS the short prompt verbatim matches by equality",
              ORC.session_kind(SHORT_PROMPT, "mike") == "ambient",
              "exact match is safe at any length — only substring needs the floor")
        check("equality match survives case/whitespace drift",
              ORC.session_kind("  CHECK IN.  ", "mike") == "ambient")
        check("empty input has no session kind",
              ORC.session_kind("", "mike") is None)

        # --- module injection: _synth_conditional_sections ---------------------------
        sched = ORC._synth_conditional_sections("morning_brief", "any package text")
        check("a scheduled turn gets the scheduled-session conduct",
              SCHEDULED_MARKER in sched)
        check("a scheduled turn without BASELINE_INCOMPLETE gets no onboarding conduct",
              ONBOARDING_MARKER not in sched)

        ordinary = ORC._synth_conditional_sections(None, "ordinary package text")
        check("an ordinary turn gets neither module",
              ordinary == "",
              "this is the token/adherence win: interactive turns carry no episodic conduct")

        onboard = ORC._synth_conditional_sections(None, "…BASELINE_INCOMPLETE: finance…")
        check("BASELINE_INCOMPLETE in the package injects onboarding conduct",
              ONBOARDING_MARKER in onboard)
        check("BASELINE_INCOMPLETE alone does not inject scheduled conduct",
              SCHEDULED_MARKER not in onboard)

        both = ORC._synth_conditional_sections("evening_close", "BASELINE_INCOMPLETE: x")
        check("both triggers fire together when both are present",
              SCHEDULED_MARKER in both and ONBOARDING_MARKER in both)

        # --- the moved content is really in the modules, and only there --------------
        agent_file = (Path(__file__).parent.parent / "config" / "agents" / "synthesizer.md").read_text()
        check("synthesizer.md no longer carries the scheduled-session conduct",
              "morning and evening sessions are not interruptible" not in agent_file)
        check("synthesizer.md no longer carries the onboarding interview conduct",
              "baseline interview that establishes" not in agent_file)
        check("synthesizer.md still tells the agent conduct arrives when needed",
              "arrive in your context automatically" in agent_file)
    finally:
        ORC.persona_config_dir = real_cfg_dir


def main() -> int:
    _run()
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
