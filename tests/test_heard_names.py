#!/usr/bin/env python3
"""
tests/test_heard_names.py — misheard names are noted for the Coordinator, never rewritten.

Plan: archive/plans/heard_names_plan_2026-10-23.md. The evidence that motivated it: a contact
"Eva" created for Iva (2026-10-15) and a calendar event "Eva & Benny" for Iva and Manny
(2026-10-22), both saved by Flash-Lite specialists acting on the Coordinator's directive.

What is asserted, in both directions:

  - a contact's name is never noted, and a name that opens a sentence is not checked;
  - a misheard name gets a note — a past correction, a merged-away name, or a sound-alike;
  - ordinary dictated sentences produce NO notes (the flood a design review measured);
  - a correction is never readable by contact lookup, never recordable for a name that is
    somebody's, survives a second correction, and keeps what it replaced;
  - a contact who later takes the corrected name silences the note — the Bonnie case;
  - the wiring is the same in both pipeline twins, and proactive turns get nothing.

Run: python3 tests/test_heard_names.py
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import tools.crm as CRM  # noqa: E402
import tools.heard_names as HN  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:  # noqa: BLE001
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


class _temp_persona_dir:
    """Point tools.crm (which tools.heard_names reads through) at an empty temp directory.
    Same pattern as tests/test_contact_resolution_memory.py."""

    def __init__(self, contacts=None):
        self.contacts = contacts if contacts is not None else CONTACTS

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "data"
        self._orig = CRM.persona_data_dir
        CRM.persona_data_dir = lambda persona=None: self.path
        (self.path / "crm").mkdir(parents=True)
        (self.path / "crm" / "contacts.json").write_text(json.dumps(self.contacts))
        return self.path

    def __exit__(self, *exc):
        CRM.persona_data_dir = self._orig
        self._tmp.cleanup()


# Synthetic people, with the short common-word names a review showed would flood a naive
# matcher (Sam/Same, Ben/Been, Tom/Tomorrow, Kate/Late, Dan/Dad, Mark/Make).
CONTACTS = [
    {"id": "c-iva", "name": "Iva Diamond", "first_name": "Iva", "last_name": "Diamond",
     "relationship_type": "partner", "last_contact": "2026-10-22"},
    {"id": "c-manny", "name": "Manny Diamond", "first_name": "Manny",
     "relationship_type": "family", "last_contact": "2026-10-21"},
    {"id": "c-bella", "name": "Bella Stone", "relationship_type": "friend", "last_contact": "2026-09-01"},
    {"id": "c-sam", "name": "Sam Hart", "last_contact": "2026-08-01"},
    {"id": "c-ben", "name": "Ben Ortiz", "last_contact": "2026-07-01"},
    {"id": "c-tom", "name": "Tom Reyes", "last_contact": "2026-06-01"},
    {"id": "c-kate", "name": "Kate Ng", "last_contact": "2026-05-01"},
    {"id": "c-dan", "name": "Dan Price", "last_contact": "2026-04-01"},
    {"id": "c-mark", "name": "Mark Lowe", "nickname": "Marky", "last_contact": "2026-03-01"},
]


def notes(text: str) -> list[str]:
    out = HN.name_notes(text)
    return re.findall(r'\[Name note: "([^"]+)"', out)


# ---------------------------------------------------------------------------

@check("a contact's own name is never noted — first, last or full")
def _():
    with _temp_persona_dir():
        assert notes("I'm meeting Iva and Manny, then Mark, at the Diamond house.") == [], \
            notes("I'm meeting Iva and Manny, then Mark, at the Diamond house.")


@check("a nickname or referred-to-as name is noted with who it means (the real Eva case)")
def _():
    people = [dict(c) for c in CONTACTS]
    people[0]["referred_to_as"] = ["Eva"]          # as on Mike's record since 2026-10-15
    with _temp_persona_dir(people):
        out = HN.name_notes("Lunch with Eva and Marky on the wharf.")
        assert '"Eva" is what the user calls Iva Diamond' in out, out
        assert '"Marky" is what the user calls Mark Lowe' in out, out


@check("the motivating case: Eva and Benny are noted as sounding like Iva and Manny")
def _():
    with _temp_persona_dir():
        out = HN.name_notes("I need to be on the wharf to meet Eva with Benny by noon.")
        assert '"Eva"' in out and "Iva Diamond" in out, out
        assert '"Benny"' in out and "Manny Diamond" in out, out
        assert "I need to be on the wharf to meet Eva with Benny by noon." not in out, \
            "the note must not restate (or rewrite) the message"


@check("a name that opens a sentence is not checked")
def _():
    with _temp_persona_dir():
        assert notes("Benny called. Eva says hi.") == []


@check("ordinary dictated sentences produce no notes at all")
def _():
    sentences = [
        "I'll take the train from Greenwich to Bank on Monday.",
        "Can you check whether Tesco is open late tomorrow?",
        "We watched The Crown last night and it was good.",
        "Remind me about the Apple keynote in September.",
        "I spoke to the GP at Blackheath about the prescription.",
        "Put the Christmas shopping on Saturday morning.",
        "I'm reading a book by Orwell at the moment.",
        "Send the invoice to Duross before Friday.",
        "Same again for lunch, and many thanks for the reminder.",
        "Maybe we should make it later; been a long day.",
        # Brand/place names between the old 0.6 bar and the 0.8 one, beside contacts
        # Ben and Sam — the band the stricter threshold exists for.
        "Pick up the parcel from the Benson depot on the way.",
        "Book the Samsung repair for next week.",
    ]
    with _temp_persona_dir():
        flagged = {s: notes(s) for s in sentences if notes(s)}
        assert not flagged, f"false hints: {flagged}"


@check("short contact names do not flag ordinary words that share their sound key")
def _():
    people = CONTACTS + [{"id": "c-abel", "name": "Abel Fox"}, {"id": "c-kamal", "name": "Kamal Roy"}]
    with _temp_persona_dir(people):
        found = notes("We should join the Zoom with Tony at Apple, then the Piano class.")
        assert found == [], f"false hints (review, 2026-10-23): {found}"
        # Known residual, kept visible rather than tuned away: "Gmail"~Kamal scores exactly
        # what the real Benny~Manny does (key match, spelling 0.60), so no bar separates them.
        assert notes("Then check Gmail later.") == ["Gmail"]


@check("a name after a title or a colon is still checked")
def _():
    with _temp_persona_dir():
        assert notes("Then Dr. Benny said so.") == ["Benny"], notes("Then Dr. Benny said so.")
        assert notes("Reminder: Benny at three.") == ["Benny"], notes("Reminder: Benny at three.")


@check("a long pasted message is checked quickly (the review measured ~0.65s before)")
def _():
    import time
    para = "We met Eva with Benny at the Wharf and walked to Greenwich. " * 350   # ~21 KB
    with _temp_persona_dir():
        t = time.perf_counter()
        HN.name_notes(para)
        took = time.perf_counter() - t
        assert took < 0.15, f"{took:.3f}s"


@check("a correction produces its note, with the new-person escape in the wording")
def _():
    with _temp_persona_dir():
        assert HN.record_misheard("Benny", "Manny").startswith("recorded"), "not recorded"
        out = HN.name_notes("Please collect Benny at three.")
        assert "corrected it to Manny Diamond" in out, out
        assert "introduces a new or different person" in out, out


@check("a name that belongs to a contact cannot be recorded as a mishearing")
def _():
    with _temp_persona_dir():
        r = HN.record_misheard("Sam", "Manny")
        assert r.startswith("not recorded") and "contact" in r, r


@check("a second correction for the same person keeps the first")
def _():
    with _temp_persona_dir() as d:
        HN.record_misheard("Benny", "Manny")
        HN.record_misheard("Manee", "Manny")
        store = json.loads((d / "crm" / "misheard_names.json").read_text())["misheard"]
        assert {"benny", "manee"} <= set(store), store


@check("a replaced correction is kept in history, not deleted")
def _():
    with _temp_persona_dir() as d:
        HN.record_misheard("Benny", "Manny")
        HN.record_misheard("Benny", "Ben Ortiz")
        entry = json.loads((d / "crm" / "misheard_names.json").read_text())["misheard"]["benny"]
        assert entry["contact_id"] == "c-ben", entry
        assert entry["history"] and entry["history"][0]["contact_id"] == "c-manny", entry


@check("the store file is private to the user (0600)")
def _():
    with _temp_persona_dir() as d:
        HN.record_misheard("Benny", "Manny")
        mode = (d / "crm" / "misheard_names.json").stat().st_mode & 0o777
        assert mode == 0o600, oct(mode)


@check("an unknown or ambiguous correct name is refused, not guessed")
def _():
    people = CONTACTS + [{"id": "c-sam2", "name": "Sam Wu"}]
    with _temp_persona_dir(people):
        assert HN.record_misheard("Benny", "Zed").startswith("not recorded")
        assert "more than one" in HN.record_misheard("Zam", "Sam")


@check("THE BONNIE CASE: once a real Benny is a contact, the old correction is silent")
def _():
    with _temp_persona_dir() as d:
        HN.record_misheard("Benny", "Manny")
        contacts = json.loads((d / "crm" / "contacts.json").read_text())
        contacts.append({"id": "c-benny", "name": "Benny Cole"})
        (d / "crm" / "contacts.json").write_text(json.dumps(contacts))
        assert notes("Please collect Benny at three.") == [], "a real Benny is still noted"


@check("a correction is invisible to contact lookup — read_contact('Benny') is not Manny")
def _():
    with _temp_persona_dir():
        HN.record_misheard("Benny", "Manny")
        found = CRM.read_contact(name="Benny")
        assert "Manny" not in found, found


@check("a merged-away name is noted as a correction to the contact it became")
def _():
    with _temp_persona_dir() as d:
        arch = d / "archive" / "crm"
        arch.mkdir(parents=True)
        (arch / "c-old_2026-10-15.json").write_text(json.dumps(
            {"id": "c-old", "name": "Eva", "merged_into": "c-iva"}))
        out = HN.name_notes("Lunch with Eva on the wharf.")
        assert "corrected it to Iva Diamond" in out, out


@check("a corrupt store or contacts file costs the note, never raises")
def _():
    with _temp_persona_dir() as d:
        (d / "crm" / "misheard_names.json").write_text("{not json")
        assert '"Eva"' in HN.name_notes("Lunch with Eva today.")   # sound-alike still works
        (d / "crm" / "contacts.json").write_text("[not json")
        assert HN.name_notes("Lunch with Eva today.") == ""


@check("one user's corrections never reach another user")
def _():
    with _temp_persona_dir():
        HN.record_misheard("Benny", "Manny")
    with _temp_persona_dir():
        out = HN.name_notes("Please collect Benny at three.")
        assert "corrected" not in out, out


@check("the Coordinator's MISHEARD line is recorded; a filled-in 'None' is not")
def _():
    with _temp_persona_dir() as d:
        HN.handle_coordinator_output("RESOLVED_INTENT: x\nMISHEARD: None\n", None, "It's Manny.")
        assert not (d / "crm" / "misheard_names.json").exists(), "recorded a None"
        res = HN.handle_coordinator_output('RESOLVED_INTENT: x\nMISHEARD: "Benny" -> Manny\n',
                                           None, "It's Manny, not Benny.")
        assert res and res[0].startswith("recorded"), res


@check("a MISHEARD line is not recorded unless the user's own words name both people")
def _():
    # The loop the review found: the Coordinator reads a sound-alike note and fills the
    # slot by reflex; the store would then claim a correction the user never made.
    with _temp_persona_dir() as d:
        res = HN.handle_coordinator_output('MISHEARD: "Benny" -> Manny\n', None,
                                           "Lunch with Benny at noon please.")
        assert res and res[0].startswith("not recorded"), res
        assert not (d / "crm" / "misheard_names.json").exists()


@check("Whisper's vocabulary is contacts only, most recent first, never a correction")
def _():
    with _temp_persona_dir():
        HN.record_misheard("Benny", "Manny")
        vocab = HN.vocabulary()
        assert vocab[:2] == ["Iva", "Manny"], vocab
        assert "Benny" not in vocab and "Marky" in vocab, vocab


@check("the Whisper option is off unless chosen, and carries the names when it is")
def _():
    import core.voice_pipeline as VP
    with _temp_persona_dir():
        assert VP._name_bias_kwargs("someone", "off") == {}
        assert VP._name_bias_kwargs(None, "hotwords") == {}
        kw = VP._name_bias_kwargs("someone", "hotwords")
        assert kw.get("hotwords", "").startswith("Iva Manny"), kw
        kw = VP._name_bias_kwargs("someone", "prompt")
        assert kw.get("initial_prompt", "").startswith("Names: Iva, Manny"), kw
    assert VP.WHISPER_NAME_BIAS == "off" or "METATRON_WHISPER_NAMES" in __import__("os").environ, \
        "the default must stay off until measured"


@check("both pipeline twins carry the note and record MISHEARD; proactive turns get neither")
def _():
    src = (ROOT / "core" / "orchestrator.py").read_text()
    assert src.count("{attach_note}{name_note}") == 4, "a twin's coord_input lacks the note"
    assert src.count("name_note = _name_note(user_input, persona, is_proactive)") == 2
    assert src.count("_handle_misheard(coord_output, persona, is_proactive, user_input)") == 2
    import core.orchestrator as O
    assert O._name_note("Lunch with Eva today.", None, True) == ""


if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            failed += 1
            print(f"        {detail}")
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
