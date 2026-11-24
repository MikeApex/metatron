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
    mid = json.dumps({"follow_up": "Book it soon. CONSULT_NEEDED: logistics — parking", "x": 1}, ensure_ascii=False)
    r = _lift({"r": mid})
    assert json.loads(r.outputs["r"])["x"] == 1 and "parking" in r.block, r.outputs


@check("3. Research's CONSULT_NEEDED bullet is lifted")
def _():
    out = ("Interactions between the two are minor at normal doses.\n\n"
           "- CONSULT_NEEDED: physical_health — Physical Health should apply these findings "
           "against the user's medications.")
    r = _lift({"research_agent": out})
    assert r.outputs["research_agent"].strip() == ("Interactions between the two are minor at "
                                                   "normal doses."), repr(r.outputs)
    assert "- research_agent: CONSULT_NEEDED: physical_health — Physical Health should apply" in r.block


TOKEN_ORDER = [
    ("FLAGS: PROFILE_GAP: x, MEDICATION_MISSED_CRITICAL, CONSULT_NEEDED: finance — y",
     "MEDICATION_MISSED_CRITICAL"),
    ("FLAGS: CONSULT_NEEDED: logistics — z ESCALATION", "ESCALATION"),
    ("FLAGS: CLINICAL_CONCERN: low mood for a fortnight, PROFILE_GAP: how is sleep lately?",
     "CLINICAL_CONCERN: low mood for a fortnight"),
    ("- CONSULT_NEEDED: mental_wellbeing — check in on the week\nMUST_SURFACE: signpost support",
     "MUST_SURFACE: signpost support"),
]


@check("4. token order (review L1): each clinical token stays byte-for-byte in the output, and "
       "the sign-off veto, reading the pre-lift text, still fires — and would on the lifted text. "
       "(ESCALATION is not a veto token at HEAD; for it the lift leaves the decision unchanged.)")
def _():
    for text, kept in TOKEN_ORDER:
        r = _lift({"physical_health": text})
        assert kept in r.outputs["physical_health"], (text, r.outputs)
        assert r.block, text            # something was lifted
        veto_text = ORC._spec_bundle({"physical_health": text})
        pre = ORC._signoff_skip(veto_text, "over and out", False)
        post = ORC._signoff_skip(ORC._spec_bundle(r.outputs), "over and out", False)
        assert pre == post, text
        if any(t in text for t in ORC._SIGNOFF_FLAG_TOKENS):
            assert not pre, text
    r = _lift({"physical_health": TOKEN_ORDER[0][0]})
    assert r.outputs["physical_health"] == "FLAGS: MEDICATION_MISSED_CRITICAL", r.outputs
    assert "PROFILE_GAP: x" in r.block and "CONSULT_NEEDED: finance — y" in r.block, r.block


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


@check("wiring: both twins build the veto from the pre-lift bundle, lift with `nudge`, and commit "
       "only after the sign-off skip")
def _():
    src = (ROOT / "core" / "orchestrator.py").read_text()
    for twin in ("def run_pipeline_session(", "def _run_pipeline_session_stream_inner("):
        body = src[src.index(twin):]
        body = body[: body.index("\ndef ", 10)]
        i_veto = body.index("veto_spec = _spec_bundle(specialist_outputs)")
        i_lift = body.index("_lift_requests(specialist_outputs, persona, nudge)")
        i_skip = body.index("_signoff_skip(veto_text")
        i_commit = body.index("_commit_requests(requests, persona)")
        i_pkg = body.index("COORDINATOR ROUTING PACKAGE:")
        assert i_veto < i_lift < i_skip < i_commit < i_pkg, twin
        assert 'veto_text = f"{veto_spec}\\n\\n{med_line}" if med_line else veto_spec' in body


if __name__ == "__main__":
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print("      " + detail.replace("\n", "\n      "))
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} passed")
    sys.exit(0 if passed == len(RESULTS) else 1)
