#!/usr/bin/env python3
"""
tests/test_specialist_requests.py — Stage 5 #19: one FROM THE SPECIALISTS block
(archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md § 1 #19, Revisions 1–2).

Fixtures in each agent's real format; the token-order fixtures pin the clinical rule (a clinical
token stays byte-for-byte in the output and the sign-off veto still fires); the acronym fixtures
pin Revision 2's explicit stop list; the drift guard re-reads the agent files; rotation and
consumption run on a temp persona tree, and consumption runs through the REAL pipeline twins over
a scripted provider (tests/support/stage3_fixtures). No model, no network.

Run:  python tests/test_specialist_requests.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from support.stage3_fixtures import (PERSONA, Script, collect_stream, coordinator_package,  # noqa: E402
                                     pipeline, sandbox)

from core import orchestrator as ORC  # noqa: E402
from tools import specialist_requests as SR  # noqa: E402

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


def _lift(outputs: dict):
    with sandbox():
        return SR.lift(outputs, PERSONA)


@check("1. a Logistics FLAGS: line with two flags: both lifted, the line goes, the block names "
       "the agent")
def _():
    out = ("Booked the 09:12 to Leeds; seat 42.\n"
           "FLAGS: CONSULT_NEEDED: finance — the fare is above the monthly travel line, "
           "RESEARCH_NEEDED: does the off-peak return allow a break of journey?")
    r = _lift({"logistics": out})
    assert r.outputs["logistics"] == "Booked the 09:12 to Leeds; seat 42.", repr(r.outputs)
    assert r.block.startswith(SR.BLOCK_HEAD), r.block
    assert ("- logistics: CONSULT_NEEDED: finance — the fare is above the monthly travel line"
            in r.block), r.block
    assert ("- logistics: RESEARCH_NEEDED: does the off-peak return allow a break of journey?"
            in r.block), r.block


@check("2. a Recreation JSON object whose flags array holds CONSULT_NEEDED and PROFILE_GAP: both "
       "lifted and the object is still valid JSON (inline and pretty-printed; a flag mid-value)")
def _():
    obj = {"summary": "A gig on the 14th.", "follow_up": "Tickets go on sale Friday.",
           "flags": ["HOBBY_LAPSE", "CONSULT_NEEDED: logistics — getting there and back",
                     "PROFILE_GAP: does the user drive to gigs or take the train?"]}
    for text in (json.dumps(obj, ensure_ascii=False), json.dumps(obj, indent=2, ensure_ascii=False)):
        r = _lift({"recreation_hobbies": text})
        parsed = json.loads(r.outputs["recreation_hobbies"])
        assert parsed["flags"] == ["HOBBY_LAPSE"], parsed
        assert parsed["summary"] == obj["summary"]
        assert "- recreation_hobbies: CONSULT_NEEDED: logistics — getting there and back" in r.block
        assert "PROFILE_GAP: does the user drive to gigs or take the train?" in r.block
    only = json.dumps({"flags": ["CONSULT_NEEDED: logistics — parking"]}, ensure_ascii=False)
    assert json.loads(_lift({"r": only}).outputs["r"]) == {"flags": []}
    # Mid-value is prose, not flag position (review item 7): left exactly where it is.
    mid = json.dumps({"follow_up": "Book it soon. CONSULT_NEEDED: logistics — parking", "x": 1},
                     ensure_ascii=False)
    r = _lift({"r": mid})
    assert r.outputs["r"] == mid and not r.block, r


@check("3. Research's CONSULT_NEEDED bullet is lifted")
def _():
    out = ("Interactions between the two are minor at normal doses.\n\n"
           "- CONSULT_NEEDED: physical_health — Physical Health should apply these findings "
           "against the user's medications.")
    r = _lift({"research_agent": out})
    assert r.outputs["research_agent"].strip() == ("Interactions between the two are minor at "
                                                   "normal doses."), repr(r.outputs)
    assert "- research_agent: CONSULT_NEEDED: physical_health — Physical Health should apply" in r.block


# The clinical rule (review item 1): nothing is lifted from a line — or from under a section —
# that holds a clinical token anywhere, before or after the flag.
CLINICAL_LINES = [
    "FLAGS: PROFILE_GAP: x, MEDICATION_MISSED_CRITICAL, CONSULT_NEEDED: finance — y",
    "FLAGS: CONSULT_NEEDED: logistics — z ESCALATION",
    "FLAGS: CLINICAL_CONCERN: low mood for a fortnight, PROFILE_GAP: how is sleep lately?",
    "MUST_SURFACE: CONSULT_NEEDED: physical_health — chest pain",
    "MUST_SURFACE: chest pain on exertion; PROFILE_GAP: does the user have a GP?",
    "MUST_SURFACE:\n- CONSULT_NEEDED: physical_health — chest pain\n  RESEARCH_NEEDED: angina signs",
]


@check("4. the clinical rule (review item 1): a line or section holding a clinical token stays "
       "whole, byte-for-byte; the sign-off veto fires on it (ESCALATION included, item 0)")
def _():
    for text in CLINICAL_LINES:
        r = _lift({"physical_health": text})
        assert r.outputs["physical_health"] == text and not r.block, (text, r)
        assert not ORC._signoff_skip(ORC._spec_bundle({"physical_health": text}),
                                     "over and out", False), text


@check("4b. a clinical token on ANOTHER line does not block a flag of its own line, and is kept")
def _():
    text = "- CONSULT_NEEDED: mental_wellbeing — check in on the week\nMUST_SURFACE: signpost support"
    r = _lift({"physical_health": text})
    assert r.outputs["physical_health"] == "MUST_SURFACE: signpost support", r.outputs
    assert "CONSULT_NEEDED: mental_wellbeing — check in on the week" in r.block
    assert not ORC._signoff_skip(ORC._spec_bundle(r.outputs), "over and out", False)


@check("4c. flag position only (review item 7): prose mentions are never lifted; a known flag "
       "mid-body is a mention; a list separator or a colon cuts; whole-line none-phrases go; an "
       "indented continuation joins its body")
def _():
    for text in ("No CONSULT_NEEDED this turn.", "Nothing to flag; PROFILE_GAP would be premature.",
                 "I would not raise RESEARCH_NEEDED: the answer is on file."):
        r = _lift({"logistics": text})
        assert r.outputs["logistics"] == text and not r.block, (text, r)
    r = _lift({"physical_health": "FLAGS: PROFILE_GAP: has SLEEP_POOR three nights running been "
                                   "raised with a GP?, SLEEP_POOR"})
    assert "PROFILE_GAP: has SLEEP_POOR three nights running been raised with a GP?" in r.block
    assert r.outputs["physical_health"] == "FLAGS: SLEEP_POOR", r.outputs
    r = _lift({"finance": "FLAGS: CONSULT_NEEDED: logistics — fare BUDGET_OVERSPEND: travel"})
    assert "CONSULT_NEEDED: logistics — fare" in r.block, r.block
    assert r.outputs["finance"] == "FLAGS: BUDGET_OVERSPEND: travel", r.outputs
    for none in ("none at this time", "None identified.", "n/a", "none"):
        r = _lift({"finance": f"Summary.\nRESEARCH_NEEDED: {none}"})
        assert r.outputs["finance"] == "Summary." and not r.block, (none, r)
    r = _lift({"logistics": "Booked.\n- PROFILE_GAP: does the user prefer an aisle seat\n"
                            "  on long flights, or the window?\n- HOBBY_LAPSE"})
    assert "PROFILE_GAP: does the user prefer an aisle seat on long flights, or the window?" in r.block
    assert r.outputs["logistics"] == "Booked.\n- HOBBY_LAPSE", repr(r.outputs["logistics"])


@check("round 3 item 5: a continuation is indented DEEPER than the flag's own line; a sibling "
       "at the same depth is not swallowed")
def _():
    text = ("FLAGS:\n  CONSULT_NEEDED: finance — the fare\n  Fare checked against the travel "
            "line.\n  PROFILE_GAP: does the user cycle\n    to the station?")
    r = _lift({"logistics": text})
    assert "CONSULT_NEEDED: finance — the fare" in r.block, r.block
    assert "the travel line" not in r.block, r.block
    assert "PROFILE_GAP: does the user cycle to the station?" in r.block, r.block
    assert "  Fare checked against the travel line." in r.outputs["logistics"], r.outputs


@check("round 3 item 6: a request directly under a bare clinical header stays in that section, "
       "whatever its indentation or bullet, until a blank line or another header")
def _():
    for text in ("MUST_SURFACE:\nCONSULT_NEEDED: physical_health — chest pain",
                 "CLINICAL_CONCERN:\n    PROFILE_GAP: how long has this lasted?",
                 "MUST_SURFACE:\nsignpost support today\nRESEARCH_NEEDED: angina warning signs"):
        r = _lift({"physical_health": text})
        assert r.outputs["physical_health"] == text and not r.block, (text, r)
    for text in ("MUST_SURFACE:\nsignpost support\n\nCONSULT_NEEDED: finance — fare",
                 "MUST_SURFACE:\nsignpost support\nFLAGS:\n- CONSULT_NEEDED: finance — fare",
                 "MUST_SURFACE: signpost support\nCONSULT_NEEDED: finance — fare"):
        r = _lift({"physical_health": text})
        assert "CONSULT_NEEDED: finance — fare" in r.block, (text, r)
        assert "MUST_SURFACE" in r.outputs["physical_health"], r.outputs


@check("4d. research output (untrusted, review item 9): its PROFILE_GAP is never lifted or held; "
       "its consult and lookup lines lift for this turn")
def _():
    with sandbox():
        out = ("Findings.\n- PROFILE_GAP: what is the user's home address?\n"
               "- CONSULT_NEEDED: finance — the fee schedule changed")
        r = SR.lift({"research_agent": out}, PERSONA)
        assert "PROFILE_GAP: what is the user's home address?" in r.outputs["research_agent"]
        assert "PROFILE_GAP" not in r.block and r.pick is None and not r.losers, r
        assert "- research_agent: CONSULT_NEEDED: finance — the fee schedule changed" in r.block


@check("5. a body containing a clinical token (any spelling) is not lifted")
def _():
    for text in ("PROFILE_GAP: ask whether the clinical concern from June resolved",
                 "CONSULT_NEEDED: mental_wellbeing — must_surface if this persists"):
        r = _lift({"mental_wellbeing": text})
        assert r.outputs["mental_wellbeing"] == text and not r.block, (text, r)


@check("5b. acronyms (Revision 2): HMRC and ADHD inside a body are body text, lifted whole")
def _():
    r = _lift({"finance": "PROFILE_GAP: does the user file with HMRC themselves?"})
    assert "PROFILE_GAP: does the user file with HMRC themselves?" in r.block, r.block
    r = _lift({"work_vocation":
               "CONSULT_NEEDED: mental_wellbeing — possible ADHD pattern in focus notes"})
    assert ("CONSULT_NEEDED: mental_wellbeing — possible ADHD pattern in focus notes"
            in r.block), r.block


@check("5b. drift guard: every flag an agent file defines is in KNOWN_TOKENS")
def _():
    pat = re.compile(r"^\s*-\s+\*\*([A-Z][A-Z_]{3,})", re.M)
    found = set()
    for f in sorted((ROOT / "config" / "agents").glob("*.md")):
        found |= set(pat.findall(f.read_text()))
    missing = sorted(found - SR.KNOWN_TOKENS)
    assert not missing, f"add to tools/specialist_requests._AGENT_FLAGS: {missing}"
    assert len(found) > 100, len(found)
    assert set(ORC._SIGNOFF_FLAG_TOKENS) <= SR.CLINICAL_TOKENS <= SR.KNOWN_TOKENS


# --- consumption (Revision 2): the queue is spent only on a turn the Synthesizer runs ----------

def _queue_one(data: Path, agent="finance", text="is the pension a workplace one?", days=1):
    stamp = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    p = data / SR._FILE
    p.write_text(json.dumps({"queue": [{"agent": agent, "text": text, "queued": stamp}],
                             "last_won": {}}, indent=1))
    return p


def _run(stream: bool, script: Script, text: str) -> str:
    with pipeline(script):
        if stream:
            return collect_stream(ORC.run_pipeline_session_stream(
                text, persona=PERSONA, provider="openai"))
        return ORC.run_pipeline_session(text, persona=PERSONA, provider="openai")


def _script(outputs: dict, reply="Done.") -> Script:
    spec = [{"agent": a, "directive": "Look at this."} for a in outputs]
    return Script({"coordinator": coordinator_package(spec), **outputs}, synth_reply=reply)


@check("5c. a sign-off-skipped turn, a nudge, and a turn with no specialist outputs leave the "
       "queue file byte-identical (both twins)")
def _():
    for stream in (False, True):
        with sandbox() as sb:
            p = _queue_one(sb["data"])
            before = p.read_bytes()
            s = _script({"logistics": "Noted.\nFLAGS: PROFILE_GAP: does the user cycle?"})
            out = _run(stream, s, "Thanks, that's all. Over and out")
            assert out == ORC._SIGNOFF_ACK, out
            assert p.read_bytes() == before, "sign-off skip spent the queue"
            s = _script({})
            _run(stream, s, "what's the weather like?")
            assert "FROM THE SPECIALISTS" not in s.last("synthesizer")
            assert p.read_bytes() == before, "an empty-output turn spent the queue"
            # A nudge dispatches no specialists and is never lifted.
            o, lifted = ORC._lift_requests({}, PERSONA, nudge=True)
            assert lifted is None
            o, lifted = ORC._lift_requests({"x": "PROFILE_GAP: y"}, PERSONA, nudge=True)
            assert lifted is None and o == {"x": "PROFILE_GAP: y"}
            assert p.read_bytes() == before


@check("5c. a turn where the Synthesizer runs serves the queued gap (marked held), removes it, "
       "queues this turn's, and the block sits before COORDINATOR ROUTING PACKAGE (both twins)")
def _():
    for stream in (False, True):
        with sandbox() as sb:
            p = _queue_one(sb["data"])
            s = _script({"logistics": "Booked.\nFLAGS: PROFILE_GAP: does the user cycle?"})
            _run(stream, s, "book me a taxi for 9")
            synth_in = s.last("synthesizer")
            head = synth_in.index("FROM THE SPECIALISTS")
            assert head < synth_in.index("COORDINATOR ROUTING PACKAGE:"), synth_in[:400]
            assert ("- finance: PROFILE_GAP (held from an earlier turn): is the pension a "
                    "workplace one?") in synth_in, synth_in[:600]
            assert "does the user cycle?" not in synth_in, "a loser reached the Synthesizer"
            st = json.loads(p.read_text())
            assert [e["agent"] for e in st["queue"]] == ["logistics"], st
            assert "finance" in st["last_won"], st
            assert oct(p.stat().st_mode & 0o777) == "0o600"
            # The veto copy is unlifted; the Synthesizer's SPECIALIST OUTPUTS copy is lifted.
            assert "--- logistics ---\nBooked." in synth_in


# --- rotation -----------------------------------------------------------------------------------

@check("6. rotation: two gaps → one wins, one queued; next turn the queued one is served; the "
       "agent that won last loses a tie; 7-day expiry; cap 10; an unwritable queue still yields "
       "one gap")
def _():
    with sandbox() as sb:
        gaps = {"finance": "PROFILE_GAP: a?", "logistics": "PROFILE_GAP: b?"}
        r = SR.lift(gaps, PERSONA)
        assert r.pick == {"agent": "finance", "text": "a?"}, r.pick
        assert [e["agent"] for e in r.losers] == ["logistics"]
        assert r.block.count("PROFILE_GAP") == 1
        SR.commit_rotation(PERSONA, r.pick, r.losers)
        r = SR.lift({"x": "nothing"}, PERSONA)
        assert r.pick["agent"] == "logistics" and r.pick.get("held"), r.pick
        SR.commit_rotation(PERSONA, r.pick, r.losers)
        assert json.loads((sb["data"] / SR._FILE).read_text())["queue"] == []
        # Logistics won last, so on a fresh tie between the two it loses.
        r = SR.lift(gaps, PERSONA)
        assert r.pick["agent"] == "finance", r.pick
        # Expiry.
        _queue_one(sb["data"], days=8)
        assert SR.lift({"x": "y"}, PERSONA).pick is None
        # Cap.
        stamp = lambda i: (datetime.now() - timedelta(hours=20 - i)).isoformat(timespec="seconds")
        (sb["data"] / SR._FILE).write_text(json.dumps({"queue": [
            {"agent": f"a{i}", "text": f"q{i}", "queued": stamp(i)} for i in range(10)],
            "last_won": {}}))
        r = SR.lift({"z": "PROFILE_GAP: fresh?"}, PERSONA)
        assert r.pick["agent"] == "a0" and len(r.losers) == 10, (r.pick, len(r.losers))
        assert r.losers[-1]["agent"] == "z"
        r2 = SR.lift({"z1": "PROFILE_GAP: 1?", "z2": "PROFILE_GAP: 2?"}, PERSONA)
        assert len(r2.losers) == 10 and "a1" not in [e["agent"] for e in r2.losers], r2.losers
        # Unwritable: the turn still has its gap; nothing raised.
        saved = SR._path
        SR._path = lambda persona: sb["data"] / "no" / "such" / "\x00bad"
        try:
            r = SR.lift({"finance": "PROFILE_GAP: c?"}, PERSONA)
            assert r.pick and "PROFILE_GAP" in r.block
            SR.commit_rotation(PERSONA, r.pick, r.losers)
        finally:
            SR._path = saved


@check("6b. a newer text from the same agent replaces its held entry; 'none' bodies are dropped")
def _():
    with sandbox():
        r = SR.lift({"finance": "PROFILE_GAP: a?", "logistics": "PROFILE_GAP: b?"}, PERSONA)
        SR.commit_rotation(PERSONA, r.pick, r.losers)
        r = SR.lift({"logistics": "PROFILE_GAP: b2?"}, PERSONA)
        assert r.pick == {"agent": "logistics", "text": "b2?", "queued": r.pick["queued"],
                          "held": True}, r.pick
        r = SR.lift({"finance": "Summary.\nRESEARCH_NEEDED: none"}, PERSONA)
        assert r.outputs["finance"] == "Summary." and "RESEARCH_NEEDED" not in r.block


@check("7. no flags at all: outputs unchanged and the block is ''")
def _():
    outs = {"logistics": "Booked the taxi for 9.", "finance": '{"flags": ["BUDGET_ON_TRACK"]}'}
    r = _lift(outs)
    assert r.outputs == outs and r.block == "" and r.pick is None


@check("8. CLARIFICATION_NEEDED is never lifted or put in the block")
def _():
    text = "CLARIFICATION_NEEDED: which Friday?\nFLAGS: CONSULT_NEEDED: finance — fare"
    r = _lift({"logistics": text})
    assert "CLARIFICATION_NEEDED: which Friday?" in r.outputs["logistics"]
    assert "CLARIFICATION" not in r.block and "CONSULT_NEEDED: finance — fare" in r.block


def _run_kw(stream: bool, script: Script, text: str, extra=None, **kw) -> str:
    with pipeline(script, extra=extra):
        if stream:
            return collect_stream(ORC.run_pipeline_session_stream(
                text, persona=PERSONA, provider="openai", **kw))
        return ORC.run_pipeline_session(text, persona=PERSONA, provider="openai", **kw)


@check("review item 8 / 14: a nudge through each twin and a Synthesizer call that fails leave the "
       "queue byte-identical; a sign-off-note turn shows the consult but no profile question, and "
       "queues the fresh gap without spending the held one (round 3 item 7)")
def _():
    for stream in (False, True):
        with sandbox() as sb:
            p = _queue_one(sb["data"])
            before = p.read_bytes()
            s = _script({"logistics": "Booked.\nFLAGS: PROFILE_GAP: does the user cycle?"})
            _run_kw(stream, s, "check the plan", nudge=True, is_proactive=True)
            assert "FROM THE SPECIALISTS" not in s.last("synthesizer"), s.last("synthesizer")[:300]
            assert p.read_bytes() == before, "a nudge spent the queue"

            s = _script({"logistics": "Booked.\nFLAGS: CONSULT_NEEDED: finance — fare, "
                                      "PROFILE_GAP: does the user cycle?"})
            _run_kw(stream, s, "Book me a taxi for nine tomorrow. Over and out")
            synth_in = s.last("synthesizer")
            assert "SIGN-OFF:" in synth_in, synth_in[-600:]
            assert "CONSULT_NEEDED: finance — fare" in synth_in
            assert "PROFILE_GAP" not in synth_in.split("COORDINATOR ROUTING PACKAGE:")[0]
            # Round 3 item 7: nothing spent and nothing lost — the held question keeps its
            # place, this turn's is queued behind it, and no win is recorded.
            held = json.loads(before)["queue"][0]
            st = json.loads(p.read_text())
            assert st["queue"][0] == held, st
            assert [(e["agent"], e["text"]) for e in st["queue"]] == [
                ("finance", held["text"]), ("logistics", "does the user cycle?")], st
            assert st["last_won"] == {}, st
            p.write_bytes(before)

            def boom(*a, **k):
                raise RuntimeError("model down")

            def boom_stream(*a, **k):
                raise RuntimeError("model down")
                yield ""                                   # noqa: unreachable — a generator

            s = _script({"logistics": "Booked.\nFLAGS: PROFILE_GAP: does the user cycle?"})
            s.side_effects["synthesizer"] = boom
            extra = [(ORC, "_openai_compat_stream", boom_stream)] if stream else None
            try:
                _run_kw(stream, s, "book me a taxi for 9", extra=extra)
            except Exception:  # noqa: BLE001 — the failure itself is not under test
                pass
            assert p.read_bytes() == before, "a failed Synthesizer call spent the queue"


@check("wiring by behaviour (review item 14): an 'over and out' turn whose specialist line holds "
       "MUST_SURFACE and a request still runs the Synthesizer, the line reaching it whole")
def _():
    for stream in (False, True):
        with sandbox():
            line = "MUST_SURFACE: CONSULT_NEEDED: physical_health — chest pain"
            s = _script({"physical_health": line})
            out = _run_kw(stream, s, "Thanks, that's all. Over and out")
            assert out != ORC._SIGNOFF_ACK, out
            assert line in s.last("synthesizer")


@check("wiring: both twins build the veto from the pre-lift bundle, lift with `nudge`, build the "
       "block after the sign-off skip, and commit only after the Synthesizer call")
def _():
    src = (ROOT / "core" / "orchestrator.py").read_text()
    for twin, synth in (("def run_pipeline_session(", "synth_result = _run_single_agent("),
                        ("def _run_pipeline_session_stream_inner(", 'complete = "".join(buffer)')):
        body = src[src.index(twin):]
        body = body[: body.index("\ndef ", 10)]
        i_veto = body.index("veto_spec = _spec_bundle(specialist_outputs)")
        i_lift = body.index("_lift_requests(specialist_outputs, persona, nudge)")
        i_skip = body.index("_signoff_skip(veto_text")
        i_text = body.index("_requests_text(requests, signoff_note)")
        i_pkg = body.index("COORDINATOR ROUTING PACKAGE:")
        i_synth = body.index(synth)
        i_commit = body.index("_commit_requests(requests, persona, signoff_note)")
        assert i_veto < i_lift < i_skip < i_text < i_pkg < i_synth < i_commit, twin
        assert 'veto_text = f"{veto_spec}\\n\\n{med_line}" if med_line else veto_spec' in body




if __name__ == "__main__":
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print("      " + detail.replace("\n", "\n      "))
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} passed")
    sys.exit(0 if passed == len(RESULTS) else 1)
