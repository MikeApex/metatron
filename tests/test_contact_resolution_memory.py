#!/usr/bin/env python3
"""
tests/test_contact_resolution_memory.py — [DB-0818-05], the second half.

The first half (tests/test_contact_disambiguation.py) proved the tool stops
writing to the wrong Bill: four people share one spoken name, nothing in the
records ranks them, so it refuses and asks. This file is about what happens
*after* the user answers — the answer has to survive the turn it was given in,
or the same question arrives again tomorrow.

What is asserted here, in both directions:

  - a name the user has already resolved is not asked about again, in the read
    path and in the write path;
  - a correction replaces the remembered answer, and the answer it replaced is
    kept rather than deleted (archive-on-merge);
  - and every way the memory could be WRONG falls back to asking: the remembered
    person deleted, the name never actually ambiguous when the pairing was seen,
    a corrupt store, no store at all.

The second group is the one that matters. A remembered answer is only worth
having if it can never be the reason a note lands on the wrong person — the
failure `_ambiguous_match` was built to refuse.

Run: python3 tests/test_contact_resolution_memory.py
Exits 0 if every test passes, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.crm as CRM  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator: run a test, record pass/fail rather than aborting the file."""
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


class _temp_persona_dir:
    """Point tools.crm at an empty temp directory, so no test touches real
    persona data. tools.crm binds persona_data_dir by name at import, so the
    patch goes on the module attribute — patching core.persona would not reach
    this copy. Same pattern as tests/test_crm_dedup_guards.py."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig = CRM.persona_data_dir
        CRM.persona_data_dir = lambda persona=None: self.path / "data"
        return self.path

    def __exit__(self, *exc):
        CRM.persona_data_dir = self._orig
        self._tmp.cleanup()


# The Bills, as stored records. Written straight to contacts.json rather than
# through write_contact: the near-duplicate confirmation gate exists to make
# creating a fourth Bill hard, and that gate is a different test's subject.
#
# Note c3/c4: `_find_by_name` matches the `name` field only, so "Bill" reaches
# c1, c2 and c5 but not the William Harts, whose claim on the name is a
# nickname. That is pre-existing matcher behaviour, untouched here — these two
# are in the fixture so a later widening of the matcher does not quietly change
# what these tests are asserting about.
BILLS = [
    {"id": "c1", "name": "Bill Thompson", "last_name": "Thompson",
     "relationship_type": "colleague", "employer": "Meridian"},
    {"id": "c2", "name": "Bill Reyes", "last_name": "Reyes",
     "relationship_type": "service", "occupation": "plumber"},
    {"id": "c5", "name": "Bill Okafor", "last_name": "Okafor",
     "relationship_type": "acquaintance", "how_met": "cycling club"},
    {"id": "c3", "name": "William Hart", "last_name": "Hart",
     "relationship_type": "friend", "nickname": "Bill"},
    {"id": "c4", "name": "William Hart Sr", "last_name": "Hart",
     "relationship_type": "friend_parent", "how_met": "father of William Hart"},
]


def _seed(contacts: list[dict] | None = None) -> None:
    CRM._save_contacts([dict(c) for c in (contacts if contacts is not None else BILLS)])


def _is_ambiguous(result: str) -> bool:
    try:
        return json.loads(result).get("ambiguous") is True
    except ValueError:
        return False


def _resolved_id(result: str) -> str:
    return json.loads(result).get("id", "")


# ---------------------------------------------------------------------------
# The defect itself: asked once, not asked again
# ---------------------------------------------------------------------------

@check("read_contact asks the first time 'Bill' is used")
def _():
    with _temp_persona_dir():
        _seed()
        assert _is_ambiguous(CRM.read_contact(name="Bill")), "should refuse and ask"


@check("read_contact does not ask again once the user has answered")
def _():
    with _temp_persona_dir():
        _seed()
        assert _is_ambiguous(CRM.read_contact(name="Bill"))
        # The user says "the plumber". The agent repeats the call with the id
        # and the name it asked about — that pairing is the answer.
        CRM.read_contact(contact_id="c2", name="Bill")

        again = CRM.read_contact(name="Bill")
        assert not _is_ambiguous(again), "asked a second time about a settled name"
        assert _resolved_id(again) == "c2", again
        assert "_resolution_note" in json.loads(again), "agent not told why it resolved"


@check("log_interaction does not ask again either, and files against the right Bill")
def _():
    with _temp_persona_dir():
        _seed()
        assert _is_ambiguous(CRM.log_interaction(name="Bill", summary="boiler"))
        CRM.log_interaction(contact_id="c2", name="Bill", summary="boiler quote")

        second = CRM.log_interaction(name="Bill", summary="boiler booked")
        assert not _is_ambiguous(second), second
        assert "Bill Reyes" in second, second
        logs = {c["id"]: c.get("interaction_log", []) for c in CRM._load_contacts()}
        assert len(logs["c2"]) == 2, logs
        assert all(not logs[i] for i in ("c1", "c3", "c4", "c5")), logs


@check("an answer given in one tool is honoured by the other")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.log_interaction(contact_id="c5", name="Bill", summary="pub")
        result = CRM.read_contact(name="Bill")
        assert _resolved_id(result) == "c5", result


@check("the reference is matched on wording, not on a fuzzy guess")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        # Same word, different case — one key.
        assert _resolved_id(CRM.read_contact(name="bill")) == "c2"
        # A different, more specific reference is NOT covered by the answer to
        # "Bill", so it resolves on its own terms.
        assert _resolved_id(CRM.read_contact(name="Bill Thompson")) == "c1"


# ---------------------------------------------------------------------------
# Correcting a remembered answer — and keeping the one it replaced
# ---------------------------------------------------------------------------

@check("a correction replaces the remembered answer")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        assert _resolved_id(CRM.read_contact(name="Bill")) == "c2"
        # "No, the other Bill."
        CRM.read_contact(contact_id="c1", name="Bill")
        assert _resolved_id(CRM.read_contact(name="Bill")) == "c1"


@check("the replaced answer is archived, not deleted")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        CRM.read_contact(contact_id="c1", name="Bill")
        entry = CRM._load_resolutions()["bill"]
        history = entry.get("history", [])
        assert len(history) == 1, entry
        assert history[0]["contact_id"] == "c2", entry
        assert history[0].get("superseded"), "no superseded stamp on the replaced answer"


@check("re-confirming the same answer does not manufacture a correction")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        CRM.read_contact(contact_id="c2", name="Bill")
        entry = CRM._load_resolutions()["bill"]
        assert "history" not in entry, entry


# ---------------------------------------------------------------------------
# Every way the memory could be wrong ends in asking, not in a wrong write
# ---------------------------------------------------------------------------

@check("an unambiguous name is not stored as an answer")
def _():
    """The trap this rule exists for: pairing 'Zoe' with the only Zoe today would
    silently swallow a second Zoe added next month."""
    with _temp_persona_dir():
        _seed([{"id": "z1", "name": "Zoe Adams"}])
        CRM.read_contact(contact_id="z1", name="Zoe")
        assert CRM._load_resolutions() == {}, CRM._load_resolutions()

        _seed([{"id": "z1", "name": "Zoe Adams"}, {"id": "z2", "name": "Zoe Baxter"}])
        assert _is_ambiguous(CRM.read_contact(name="Zoe")), "stale pairing resolved a new Zoe"


@check("a remembered person who no longer exists falls back to asking")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        # c2 gone, two other Bills still there — so the name is still ambiguous
        # and the memory is the only thing that could resolve it. It must not.
        _seed([c for c in BILLS if c["id"] != "c2"])
        assert _is_ambiguous(CRM.read_contact(name="Bill")), "resolved to a deleted record"


@check("a remembered answer follows a merge instead of being stranded")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        # c2 is folded into c1 the way merge_contacts leaves things: the loser
        # archived with a merged_into pointer, gone from contacts.json.
        archive = CRM._crm_archive_dir()
        archive.mkdir(parents=True, exist_ok=True)
        loser = dict(next(c for c in BILLS if c["id"] == "c2"))
        loser["merged_into"] = "c1"
        (archive / "c2_20260827T000000.json").write_text(json.dumps(loser))
        _seed([c for c in BILLS if c["id"] != "c2"])

        result = CRM.read_contact(name="Bill")
        assert _resolved_id(result) == "c1", result


@check("a corrupt resolution store degrades to asking, not to an error")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        CRM._resolutions_path().write_text("{not json at all")
        assert _is_ambiguous(CRM.read_contact(name="Bill")), "corrupt store not survived"


@check("existing persona data with no resolution file behaves exactly as before")
def _():
    with _temp_persona_dir():
        _seed()
        assert not CRM._resolutions_path().exists()
        assert _is_ambiguous(CRM.read_contact(name="Bill"))
        assert _resolved_id(CRM.read_contact(name="Bill Reyes")) == "c2"
        assert not CRM._resolutions_path().exists(), "read path created a store"


@check("the store is written 0600, like contacts.json")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="c2", name="Bill")
        mode = CRM._resolutions_path().stat().st_mode & 0o777
        assert mode == 0o600, oct(mode)


@check("an id that matches nothing is not recorded as an answer")
def _():
    with _temp_persona_dir():
        _seed()
        CRM.read_contact(contact_id="nonexistent", name="Bill")
        assert CRM._load_resolutions() == {}, CRM._load_resolutions()


@check("the ambiguity question tells the agent how to make the answer stick")
def _():
    with _temp_persona_dir():
        _seed()
        instruction = json.loads(CRM.read_contact(name="Bill"))["_instruction"]
        assert "name=" in instruction, instruction
        assert "contact_id" in instruction, instruction


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")
    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
