"""
tests/test_research_check.py — Stage 5 #17: a Research query carrying a known identifier is
refused before it leaves (archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md
§ 1 #17, Revision 2 and the build-time amendments).

The check is `tools/lookup_guard.check_research`, called at the one choke point every Research
call passes — `core/orchestrator._run_single_agent`'s research branch — before any provider. It
refuses, never rewrites; fail-closed on an unreadable store; the trace carries the kind only.

EVERY METER IS STUBBED: `run_session_gemini_grounded` records calls and returns a canned answer;
the spend gate is a no-op. Profile and contacts are temp files. Generic names only.

    python3 tests/test_research_check.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import yaml  # noqa: E402

import core.orchestrator as ORC  # noqa: E402
import core.persona as P  # noqa: E402
import core.spend_guard as SG  # noqa: E402
import core.trace as TR  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.day_plan as D  # noqa: E402
import tools.lookup_guard as LG  # noqa: E402
import tools.profile as PR  # noqa: E402
import tools.ranking as RK  # noqa: E402

_PERSONA = "research_check"
_TMP = Path(tempfile.mkdtemp(prefix="research_check_"))
_PROFILE = _TMP / "config" / "profile.yaml"
_CONTACTS = _TMP / "crm" / "contacts.json"
_PROFILE.parent.mkdir(parents=True)
_CONTACTS.parent.mkdir(parents=True)
PR._profile_path = lambda: _PROFILE
CRM._crm_path = lambda: _CONTACTS
D.persona_data_dir = lambda persona=None: _TMP

_SENT: list[str] = []


def _grounded(system_prompt, user_input, *a, **k):
    _SENT.append(user_input)
    return "Term starts on the 5th."


ORC.run_session_gemini_grounded = _grounded
SG.check_before_session = lambda: None

_TRACES: list[str] = []
_real_trace = ORC._trace
ORC._trace = lambda msg: (_TRACES.append(msg), _real_trace(msg))[-1]

_PROFILE_DATA = {
    "name": "Alex Morgan",
    "contact": {"email": "amorgan@example.com", "phone": "07700900123",
                "address": "14 Elm Grove Road, Westbury, London, SW1A 2AA"},
}
_CONTACT_DATA = [
    {"id": "c1", "first_name": "Jordan", "last_name": "Pike", "name": "Jordan Pike",
     "relationship_type": "friend",
     "contact_info": {"email": "jpike@example.org", "phone": "+33 6 12 34 56 78",
                      "address": "8 Rue des Lilas, 75011 Paris, France"}},
    {"id": "c2", "first_name": "Grace", "relationship_type": "family"},
    {"id": "c3", "name": "Sam Rivers", "relationship_type": "family",
     "referred_to_as": ["my wife", "the boss"]},
    {"id": "c4", "name": "Riverside Dental", "relationship_type": "professional",
     "referred_to_as": ["the dentist"]},
    {"id": "c5", "first_name": "Ruth", "relationship_type": "family",
     "referred_to_as": ["Aunt Ruth", "my aunt"]},
    {"id": "c6", "first_name": "Kim", "last_name": "Hale", "relationship_type": "colleague",
     "contact_info": {"phone": "07700 900456", "address": "Flat 3, 22 Mill Lane, Hove, BN3 1AB"}},
]


def _seed(profile=None, contacts=None) -> None:
    _PROFILE.write_text(yaml.safe_dump(_PROFILE_DATA if profile is None else profile))
    _CONTACTS.write_text(json.dumps(_CONTACT_DATA if contacts is None else contacts))


def _research(q: str) -> str:
    return ORC._run_single_agent("research_agent", q, persona=_PERSONA, provider="gemini",
                                 model_override="stub-model")


_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        try:
            _seed()
            _SENT.clear()
            _TRACES.clear()
            with P.persona_scope(_PERSONA):
                fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(exc).__name__}: {exc}\n"
                             + "".join(traceback.format_exc().splitlines(True)[-5:])))
        return fn
    return deco


@check("1: each known identifier is refused at the choke point and the provider is never called "
       "— the user's full name; a contact's First Last, First M. Last, Last, First; the email; the "
       "phone written another way; the postcode without its space; the street segment; and a "
       "contact's email, phone and street (amendment 1)")
def _():
    refused = {
        "Is Alex Morgan on the parish council?": "full name",
        "Jordan Pike marathon results": "full name",
        "Jordan T. Pike marathon results": "full name",
        "Pike, Jordan — marathon results": "full name",
        "Who is amorgan@EXAMPLE.com registered to?": "email address",
        "Whose number is +44 7700 900123?": "phone number",
        "Bin collection days for SW1A2AA": "postcode",
        "Parking permits on 14 Elm Grove Road": "street address",
        "Is jpike@example.org a real address?": "email address",
        "Who owns 06 12 34 56 78?": "phone number",
        "Street parking on 8 rue des Lilas": "street address",
        "Is 07700 900456 a mobile?": "phone number",
        "Noise rules at 22 Mill Lane": "street address",
    }
    for q, kind in refused.items():
        out = _research(q)
        assert out.startswith(LG.RESEARCH_REFUSED), (q, out)
        assert kind in out, (q, kind, out)
    assert not _SENT, _SENT


@check("1b: the refusal names the matched contact so the writer can rephrase (amendment 2)")
def _():
    out = _research("Riverside Dental Saturday opening hours")
    assert out.startswith(LG.RESEARCH_REFUSED) and "Riverside Dental" in out, out
    out = _research("Hale, Kim conference talk")
    assert "Kim Hale" in out, out
    assert not _SENT


@check("2: a single first name passes ('Grace School term dates' with a contact named Grace)")
def _():
    out = _research("Grace School term dates")
    assert out == "Term starts on the 5th." and _SENT == ["Grace School term dates"], (out, _SENT)


@check("3: the city or district alone passes — London, Westbury, Paris, Hove")
def _():
    for q in ("Best museums in London", "Westbury library hours", "Paris metro strike news",
              "Hove seafront parking"):
        assert not _research(q).startswith("refused"), q
    assert len(_SENT) == 4


@check("4: a public organisation name passes when nobody saved it; aliases are read per alias "
       "and only an all-capitalised one is a name — 'my wife', 'the dentist', 'the boss' pass, "
       "'Aunt Ruth' is refused (amendment 3)")
def _():
    for q in ("When does HMRC open its phone lines?", "Is the NHS dentist backlog improving?",
              "Gift ideas for my wife", "How often should the dentist see a child?",
              "What does the boss of a council do?"):
        out = _research(q)
        assert not out.startswith("refused"), (q, out)
    out = _research("Aunt Ruth recipes from the 1950s")
    assert out.startswith(LG.RESEARCH_REFUSED) and "full name" in out, out
    assert LG.check("Gift ideas for my wife") is None    # the public lookup's guard too


@check("5: dosages, prices and public addresses pass — check()'s pattern and figure refusals are "
       "not applied to Research")
def _():
    for q in ("Is a 200 mg dose of ibuprofen safe for adults?", "Is £640 fair for brakes on a Golf?",
              "Opening hours at 10 Downing Street", "Visa office at 1 Main Street, Dublin",
              "What is the 2025-2026 tax year deadline?"):
        out = _research(q)
        assert not out.startswith("refused"), (q, out)


@check("5b: a non-UK stored number and postcode match on digits and as a normalised string "
       "(amendment 4)")
def _():
    assert _research("Bakeries near 75011").startswith(LG.RESEARCH_REFUSED)
    assert _research("call 0033612345678 back?").startswith(LG.RESEARCH_REFUSED)
    assert LG._phone_key("+44 (0)7700 900123") == LG._phone_key("07700900123") == "700900123"
    assert LG._postcode_key("1 Hauptstrasse, 10115 Berlin") == "10115"
    assert LG._postcode_key("1 High St, Leeds, ls1 4ap") == "LS14AP"
    assert LG._street_key("Flat 3, 22 Mill Lane, Hove") == " 22 mill lane "
    assert LG._street_key("Westbury, London") == ""


@check("6: a corrupt contacts file refuses; so does a corrupt profile; a missing file passes")
def _():
    _CONTACTS.write_text("{not json")
    out = _research("Grace School term dates")
    assert out.startswith(LG.RESEARCH_REFUSED) and "could not be read" in out, out
    _seed()
    _PROFILE.write_text("name: [unclosed")
    out = _research("Grace School term dates")
    assert out.startswith(LG.RESEARCH_REFUSED) and "could not be read" in out, out
    assert not _SENT
    _PROFILE.unlink()
    _CONTACTS.unlink()
    out = _research("Grace School term dates")
    assert out == "Term starts on the 5th.", out


@check("7: the trace carries the kind and never the value")
def _():
    _research("Who is amorgan@example.com?")
    _research("Jordan Pike marathon results")
    hits = [t for t in _TRACES if t.startswith("[RESEARCH] refused")]
    assert hits == ["[RESEARCH] refused: an email address",
                    "[RESEARCH] refused: the full name of someone the user knows"], hits
    joined = "\n".join(_TRACES)
    assert "amorgan" not in joined and "Jordan" not in joined and "Pike" not in joined, joined


@check("8/9: lookup_public_fact on a question the Research check refuses keeps the day's count, "
       "returns the plain refusal with no untrusted wrapper; a clean question still works end to "
       "end and is wrapped")
def _():
    saved = ORC.run_session
    ORC.run_session = lambda agent, user_input="", persona=None, **k: _research(user_input)
    RK._OVERRIDE = {"lookups": {"enabled": True, "per_day": 5}}
    try:
        # Passes check() (no street-type word, a 5-digit code), refused by check_research.
        prof = dict(_PROFILE_DATA, contact={"address": "7 Kingsmead, Little Fernham, 75011"})
        _seed(profile=prof)
        q = "Is the recycling day for 7 Kingsmead a Tuesday?"
        assert LG.check(q) is None, LG.check(q)
        out = LG.lookup_public_fact(q)
        assert out.startswith(LG.RESEARCH_REFUSED), out
        assert "<untrusted_content" not in out, out
        st = RK.load_state(_PERSONA).get("lookups") or {}
        assert int(st.get("n") or 0) == 0, st
        assert not _SENT
        out = LG.lookup_public_fact("When does the autumn school term start?")
        assert "<untrusted_content" in out and "Term starts on the 5th." in out, out
        assert int(RK.load_state(_PERSONA)["lookups"]["n"]) == 1
    finally:
        ORC.run_session = saved
        RK._OVERRIDE = None


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print("      " + detail.replace("\n", "\n      "))
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
