"""
tests/test_tone_validation.py — Stage 5 #21: a tone profile is checked against the correspondence
it was built from (archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md
§ 1 #21, Revision 2 and build-time amendment 2).

A pet name or shared phrase used fewer than five times is dropped; a value naming another person
the user knows is dropped or blanked; a name "they use for the user" must appear in what they
wrote. All pure-Python over a canned sample in tools/mail.search_correspondence's format, plus one
`_extract` run with the mailbox, the model and the CRM write stubbed. Generic names only.

    python3 tests/test_tone_validation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.tone as T  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(exc).__name__}: {exc}\n"
                             + "".join(traceback.format_exc().splitlines(True)[-4:])))
        return fn
    return deco


def _sample(user: list[str], them: list[str]) -> str:
    blocks = []
    for i in range(max(len(user), len(them))):
        if i < len(user):
            blocks.append(f"[user] {user[i]}")
        if i < len(them):
            blocks.append(f"[them] {them[i]}")
    return "<untrusted_content source=\"mail\">\n" + "\n\n---\n\n".join(blocks) + "\n</untrusted_content>"


CONTACT = {"id": "c1", "name": "Dana Kerr", "first_name": "Dana", "last_name": "Kerr",
           "nickname": "Dee", "referred_to_as": ["my sister"]}
OTHERS = [CONTACT,
          {"id": "c2", "name": "Tobias Lund", "first_name": "Tobias"},
          {"id": "c3", "name": "School Office", "relationship_type": "other"},
          {"id": "c4", "first_name": "Will", "last_name": "Ash"},
          {"id": "c5", "first_name": "May", "last_name": "Ford"},
          {"id": "c6", "first_name": "Mark", "last_name": "Oakes"},
          {"id": "c7", "name": "Dana Kerr", "first_name": "Dana"},          # a duplicate record
          {"id": "c8", "name": "Dee Marsh", "first_name": "Dee"}]           # a namesake

USER = ["Hi Dee, the long one again on Friday? cheers sis",
        "Dee — the long one went fine. cheers sis",
        "cheers sis, the long one is booked. Will do the shopping.",
        "the long one tomorrow? cheers sis. mark my words, it will rain",
        "Tobias says hi. the long one at 6. cheers sis, will do",
        "May the force be with you, Dee"]
THEM = ["Morning Bun! Sounds good. Tobias is coming too.",
        "Bun, Friday works. Will often signs off first, ha.",
        "ok Bun", "Tobias asked after you", "Fine by me, Bun", "Yes Bun"]
SAMPLE = _sample(USER, THEM)


def _parse(obj: dict, contacts=OTHERS, contact=CONTACT, user_name="Alex Morgan") -> dict:
    return T._parse_profile(json.dumps(obj), sample=SAMPLE, contact=contact, contacts=contacts,
                            user_name=user_name)


@check("1. a phrase seen 4 times is dropped, 5 times kept")
def _():
    four = _sample(["hey you"] * 4, ["x"])
    five = _sample(["hey you"] * 5, ["x"])
    obj = json.dumps({"shared_phrases": ["hey you"], "pet_names": ["hey you"]})
    assert T._parse_profile(obj, sample=four, contact={}, contacts=[]) == {}
    out = T._parse_profile(obj, sample=five, contact={}, contacts=[])
    assert out == {"shared_phrases": ["hey you"], "pet_names": ["hey you"]}, out


@check("2. a quoted phrase is counted by its quote, not the whole description")
def _():
    out = _parse({"shared_phrases": ["calls Fridays 'the long one'", "says 'once in a blue moon'"]})
    assert out.get("shared_phrases") == ["calls Fridays 'the long one'"], out


@check("3. a third party's name is blanked from register_notes and dropped from shared_phrases")
def _():
    out = _parse({"register_notes": "mentions Tobias often", "formality": "casual",
                  "shared_phrases": ["Tobias says hi", "cheers sis"]})
    assert "register_notes" not in out and out["formality"] == "casual", out
    assert out["shared_phrases"] == ["cheers sis"], out


@check("4. a nickname seen only in [user] blocks is dropped from names_they_use_for_user")
def _():
    out = _parse({"names_they_use_for_user": ["Bun", "sis"]})
    assert out["names_they_use_for_user"] == ["Bun"], out


@check("5/6. the contact's own name and nickname are kept in every field — with a duplicate "
       "record of the same person and a namesake on file")
def _():
    out = _parse({"names_user_uses_for_them": ["Dee", "Dana"], "greeting_style": "Hi Dee",
                  "register_notes": "Dana is addressed as Dee"})
    assert out["names_user_uses_for_them"] == ["Dee", "Dana"], out
    assert out["greeting_style"] == "Hi Dee" and out["register_notes"].startswith("Dana"), out


@check("7. Revision 2: an organisation contact 'School Office', and contacts named Will, May and "
       "Mark, never cost a value — lower-case tokens or stoplisted words")
def _():
    out = _parse({"register_notes": "writes like a school office memo",
                  "formality": "warm but Office-formal",
                  "shared_phrases": ["will do", "May the force", "mark my words"],
                  "typical_length": "Will often signs off first"})
    assert out.get("register_notes") == "writes like a school office memo", out
    assert out.get("formality") == "warm but Office-formal", out
    assert out.get("typical_length") == "Will often signs off first", out
    # 'May the force' and 'mark my words' recur only once each, so they fall to the count —
    # not to the name check. Seen five times, both survive the name check.
    many = _sample(["will do. May the force. mark my words"] * 5, ["ok"])
    out = T._parse_profile(json.dumps({"shared_phrases": ["will do", "May the force",
                                                         "mark my words"]}),
                           sample=many, contact=CONTACT, contacts=OTHERS)
    assert out["shared_phrases"] == ["will do", "May the force", "mark my words"], out


@check("7b. a name the sample never capitalises contributes nothing (amendment 2)")
def _():
    out = _parse({"register_notes": "mentions Lund at times"})
    assert out.get("register_notes") == "mentions Lund at times", out


@check("validation runs before the 6-item truncation, so one-offs do not use up the slots")
def _():
    many = _sample(["cheers sis"] * 5, ["x"])
    phrases = [f"one-off {i}" for i in range(8)] + ["cheers sis"]
    out = T._parse_profile(json.dumps({"shared_phrases": phrases}), sample=many,
                           contact={}, contacts=[])
    assert out["shared_phrases"] == ["cheers sis"], out


@check("no sample: _parse_profile behaves exactly as before")
def _():
    obj = json.dumps({"shared_phrases": ["x"], "register_notes": "mentions Tobias"})
    assert T._parse_profile(obj) == {"shared_phrases": ["x"], "register_notes": "mentions Tobias"}


@check("_extract passes the sample and the profiled record — a third party never reaches the "
       "stored profile")
def _():
    import core.orchestrator as ORC
    import tools.crm as CRM
    import tools.mail as M
    import tools.profile as PR
    written = {}
    saved = (T._permitted, M.search_correspondence, ORC.run_session, CRM._load_contacts,
             CRM.write_contact, PR._load)
    T._permitted = lambda persona: True
    M.search_correspondence = lambda address: {"sent_folder_found": True,
                                               "counts": {"sampled": 12},
                                               "correspondence": SAMPLE}
    ORC.run_session = lambda *a, **k: json.dumps({"formality": "casual",
                                                 "register_notes": "mentions Tobias often",
                                                 "names_they_use_for_user": ["Bun", "sis"]})
    CRM._load_contacts = lambda: OTHERS
    CRM.write_contact = lambda **k: written.update(k) or "c1"
    PR._load = lambda: {"name": "Alex Morgan"}
    try:
        res = T._extract("dana@example.com", "c1", persona="tone_test")
    finally:
        (T._permitted, M.search_correspondence, ORC.run_session, CRM._load_contacts,
         CRM.write_contact, PR._load) = saved
    assert res["status"] == "written", res
    shape = written["tone_shape"]
    assert "Tobias" not in shape and "Bun" in shape and "sis" not in shape, shape


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print("      " + detail.replace("\n", "\n      "))
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
