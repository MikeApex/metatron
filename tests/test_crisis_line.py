#!/usr/bin/env python3
"""
tests/test_crisis_line.py — M9: the crisis line in every reply to a suicide disclosure
(Stage 3 plan § 1.5, tests 1–7, 4a, 4b, and build-time amendment 2's prose fixture;
archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md).

Config resolution and the append are unit-tested; the trigger, the bundle line, the post-reply
append and the suppressed-reply branch are driven through the REAL twins over a scripted provider
(tests/support/stage3_fixtures.pipeline) on a temporary persona tree. No model, no network.

Run:  python tests/test_crisis_line.py
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from support.stage3_fixtures import (PERSONA, Script, collect_stream, coordinator_package,  # noqa: E402
                                     patched, pipeline, sandbox)

from core import orchestrator as ORC  # noqa: E402
from tools import clinical_checks as CC  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name):
    def deco(fn):
        try:
            fn()
            RESULTS.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-700:]}"))
        return fn
    return deco


SI_OUT = ("MOOD: very low\nFLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION\n"
          "MUST_SURFACE: signpost crisis resources warmly")
PROSE_OUT = ("MOOD: tired\nNOTES: the SUICIDAL_IDEATION concern on file from last month was not "
             "raised again; nothing today suggests it.\nFLAGS: none")
REPLY_NO_LINE = "I'm really glad you told me. You matter, and I'm here with you."
SAID = "I've been thinking maybe everyone would be better off without me"


def _script(mw_out: str, synth: str) -> Script:
    spec = [{"agent": "mental_wellbeing", "directive": "The user disclosed something heavy."}]
    return Script({"coordinator": coordinator_package(spec), "mental_wellbeing": mw_out},
                  synth_reply=synth)


def _run(stream: bool, script: Script, text: str = SAID, proactive: bool = False,
         history: list | None = None, extra: list | None = None) -> str:
    with pipeline(script, extra=extra):
        if stream:
            return collect_stream(ORC.run_pipeline_session_stream(
                text, persona=PERSONA, provider="openai", is_proactive=proactive, history=history))
        return ORC.run_pipeline_session(text, persona=PERSONA, provider="openai",
                                        is_proactive=proactive, history=history)


@check("1. config: alias match, unmatched country and no profile resolve correctly")
def _():
    for country, key in (("United Kingdom", "GB"), ("uk", "GB"), ("USA", "US"),
                         ("France", "default")):
        with sandbox(location_country=country):
            got = CC.crisis_line_for(PERSONA)
        assert got["key"] == key, (country, got)
    with sandbox():
        got = CC.crisis_line_for(PERSONA)
    assert got["key"] == "default" and "116 123" in got["line"], got
    with sandbox(location_country="usa"):
        assert "988" in CC.crisis_line_for(PERSONA)["line"]


@check("2 / 4b. a reply with '116 123', '116-123' or '116123' (or 'Samaritans') is returned "
       "byte for byte")
def _():
    with sandbox():
        for r in ("Call 116 123 any time.", "Call 116-123.", "Call 116123 now.",
                  "The Samaritans are there for you."):
            assert CC.ensure_crisis_line(r, PERSONA) is r or CC.ensure_crisis_line(r, PERSONA) == r
        assert CC.ensure_crisis_line("Call 1161234 for pizza.", PERSONA) != "Call 1161234 for pizza."


@check("3. a missing line is appended once at the end; the reply prefix is identical")
def _():
    with sandbox():
        line = CC.crisis_line_for(PERSONA)["line"]
        out = CC.ensure_crisis_line(REPLY_NO_LINE + "\n", PERSONA)
        assert out == REPLY_NO_LINE + "\n\n" + line, out
        assert CC.ensure_crisis_line(out, PERSONA) == out, "appended once only"
        assert CC.ensure_crisis_line("", PERSONA) == line


@check("4. no flag, a scheduled turn, or a flag already dropped: reply unchanged, no bundle line "
       "(both twins); amendment 2: prose naming a concern is not a flag")
def _():
    for stream in (False, True):
        with sandbox():
            s = _script("MOOD: fine\nFLAGS: none", REPLY_NO_LINE)
            assert _run(stream, s, "had a nice walk today") == REPLY_NO_LINE
            assert "CRISIS LINE (from code)" not in s.last("synthesizer")
            s = _script(SI_OUT, REPLY_NO_LINE)        # scheduled: the flag is dropped first
            assert _run(stream, s, "Good morning — the morning brief.", proactive=True) == REPLY_NO_LINE
            assert "CRISIS LINE (from code)" not in s.last("synthesizer")
            s = _script(PROSE_OUT, REPLY_NO_LINE)
            assert _run(stream, s, "just tired today") == REPLY_NO_LINE, "prose is never the trigger"
            assert "CRISIS LINE (from code)" not in s.last("synthesizer")


@check("4a. a user with a watch-state SI thread who discloses again: bundle line present, and a "
       "reply without the number gets it appended (both twins)")
def _():
    # REAL state (review item 10a): the persona's own context tracker holds a watch-state SI
    # thread on disk, read back through tools.context_tracker before the turn runs.
    import json as _json
    from tools import context_tracker as CT
    watch = {"clinical_threads": [{"flag": "CLINICAL_CONCERN: SUICIDAL_IDEATION",
                                   "status": "watch", "first_seen": "2026-11-01",
                                   "last_seen": "2026-11-10"}]}
    for stream in (False, True):
        with sandbox() as sb:
            (sb["data"] / "context.json").write_text(_json.dumps(watch))
            threads = CT.read_context_tracker().get("clinical_threads") or []
            assert any(t.get("status") == "watch" and "SUICIDAL_IDEATION" in str(t.get("flag"))
                       for t in threads), threads
            line = CC.crisis_line_for(PERSONA)["line"]
            s = _script(SI_OUT, REPLY_NO_LINE)
            out = _run(stream, s)
            assert f"CRISIS LINE (from code): {line} — include it in this reply." in s.last("synthesizer")
            assert out == REPLY_NO_LINE + "\n\n" + line, (stream, out)


ARMS = [
    "**FLAGS:** CLINICAL_CONCERN: SUICIDAL_IDEATION",
    "- FLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION, ESCALATION",
    "## FLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION",
    "> FLAGS: CLINICAL_CONCERN: SUICIDAL_IDEATION",
    "FLAGS:\n- CLINICAL_CONCERN: SUICIDAL_IDEATION\n- ESCALATION",
    "FLAGS:\n  * ESCALATION\n  * **CLINICAL_CONCERN: SUICIDAL_IDEATION**",
    "FLAGS:\n1. CLINICAL_CONCERN: SUICIDAL_IDEATION",
    "FLAGS: CLINICAL_CONCERN - SUICIDAL_IDEATION",
    "FLAGS: CLINICAL_CONCERN — suicidal ideation",
    "FLAGS: CLINICAL_CONCERN SUICIDAL_IDEATION",
    "FLAGS: CLINICAL_CONCERN: DEPRESSION / SUICIDAL_IDEATION",
    "FLAGS: CLINICAL_CONCERN: Suicidal Ideation (passive)",
    "flags: clinical_concern: suicidal_ideation",
]
NOT_ARMS = [
    "NOTES: CLINICAL_CONCERN: SUICIDAL_IDEATION was raised last month; nothing new today.",
    "FLAGS: none\nNOTES: suicidal ideation is on file from October.",
    "FLAGS: SLEEP_POOR\n\nThe user shows no SUICIDAL_IDEATION today.",
    "FLAGS:\n- SLEEP_POOR\nNOTES:\n- CLINICAL_CONCERN: SUICIDAL_IDEATION history, not current",
    "FLAGS: CLINICAL_CONCERN: DEPRESSION\nNOTES: earlier suicidal ideation resolved",
    "MOOD: low, and earlier SUICIDAL_IDEATION was discussed in therapy",
]


@check("item 2: every FLAGS form arms the crisis trigger (markup, bullets, any separator, "
       "'DEPRESSION / SUICIDAL_IDEATION'); prose outside a FLAGS item never does")
def _():
    for text in ARMS:
        assert CC.raises_suicidal_ideation({"mental_wellbeing": text}), f"did not arm: {text!r}"
        assert "SUICIDAL_IDEATION" in CC.clinical_concerns(text), text
    for text in NOT_ARMS:
        assert not CC.raises_suicidal_ideation({"mental_wellbeing": text}), f"armed on prose: {text!r}"
    assert CC.clinical_concerns(NOT_ARMS[4]) == ["DEPRESSION"]


@check("item 2 end to end: a bulleted '**FLAGS:**' form gets the line appended on both twins")
def _():
    out_mw = "MOOD: very low\n**FLAGS:**\n- CLINICAL_CONCERN — suicidal ideation\n"
    for stream in (False, True):
        with sandbox():
            line = CC.crisis_line_for(PERSONA)["line"]
            s = _script(out_mw, REPLY_NO_LINE)
            assert _run(stream, s) == REPLY_NO_LINE + "\n\n" + line, stream
            assert "CRISIS LINE (from code)" in s.last("synthesizer")
            assert "MUST_SURFACE: SUICIDAL_IDEATION raised by Mental Wellbeing" in s.last("synthesizer")


@check("item 9: the append failing on a suppressed (empty) reply still delivers the built-in line")
def _():
    def broken(*a, **k):
        raise RuntimeError("config gone")
    with sandbox(), patched([(CC, "crisis_line_for", broken)]):
        assert ORC._ensure_crisis("", True, PERSONA) == CC.BUILTIN_CRISIS_LINE
        assert CC.ensure_crisis_line("", PERSONA) == CC.BUILTIN_CRISIS_LINE
        assert ORC._ensure_crisis("hello", True, PERSONA) == "hello"
    import tools.clinical_checks as mod
    with sandbox(), patched([(mod, "ensure_crisis_line", broken)]):
        assert ORC._ensure_crisis("", True, PERSONA) == CC.BUILTIN_CRISIS_LINE
        assert "116 123" in CC.BUILTIN_CRISIS_LINE


@check("4b (pipeline). a reply already carrying the configured number is delivered unchanged")
def _():
    for stream in (False, True):
        with sandbox():
            for reply in ("Please call Samaritans on 116 123.", "Ring 116-123 now.", "Try 116123."):
                assert _run(stream, _script(SI_OUT, reply)) == reply, (stream, reply)


@check("5. a suppressed reply on a crisis turn becomes the crisis line alone (both twins)")
def _():
    real = ORC.filter_output
    fallback = "I'm here to help you manage your life. What can I help you with today?"
    extra = [(ORC, "filter_output", lambda text, agent, user_text=None:
              fallback if "LEAKS" in text else real(text, agent, user_text=user_text))]
    for stream in (False, True):
        with sandbox():
            line = CC.crisis_line_for(PERSONA)["line"]
            out = _run(stream, _script(SI_OUT, "This reply LEAKS an internal name."), extra=extra)
            assert out == line, (stream, out)
            # and without the flag, suppression is unchanged
            s = _script("FLAGS: none", "This reply LEAKS an internal name.")
            got = _run(stream, s, "hello", extra=extra)
            assert got == ("" if stream else fallback), (stream, got)


@check("6. twin parity: both twins ensure the line after the reply and carry the bundle line")
def _():
    for fn in (ORC.run_pipeline_session, ORC._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert src.count("_ensure_crisis(") == 2, fn.__name__        # suppressed + normal
        assert "crisis_text = _crisis_bundle_line(crisis, persona)" in src
        assert '(f"\\n\\n{crisis_text}" if crisis_text else "")' in src
        assert src.index("_offer_receipt(") < src.rindex("_ensure_crisis(")


@check("7. streaming: [RETRACT_WITH] text ends in the line, and history holds the amended text")
def _():
    with sandbox():
        line = CC.crisis_line_for(PERSONA)["line"]
        history: list = []
        s = _script(SI_OUT, REPLY_NO_LINE)
        with pipeline(s):
            chunks = list(ORC.run_pipeline_session_stream(SAID, persona=PERSONA, provider="openai",
                                                          history=history))
        retract = [c for c in chunks if c.startswith("[RETRACT_WITH]")]
        assert retract and retract[-1].endswith(line), chunks[-3:]
        assert chunks[-1] == "[DONE]"
        assert history[-1]["content"] == REPLY_NO_LINE + "\n\n" + line, history


def main() -> int:
    passed = 0
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"\n     {detail}" if detail else ""))
        passed += ok
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
