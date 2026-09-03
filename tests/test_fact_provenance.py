"""
tests/test_fact_provenance.py — [DB-0818-08], the two halves built 2026-09-03.

Job 1 — THE CHECKED-DETAIL GATE (`tools/crm.py`). A contact detail Python read out of a
real artefact is not silently replaced by one a model concluded. Covers: the gate fires
on a marked detail, stays quiet on an unmarked one, stays quiet on filling a blank, stays
quiet on a no-op rewrite, and — the one that keeps the mark honest — CLEARS the mark once
an approved correction lands, so the same correction is never questioned twice.

Job 2 — THE HEDGE (`core/orchestrator._knowledge_block`). An inferred fact is rendered as
a sentence about the inference, not as a fact with a marker beside it. The marker-plus-
rule shape it replaces had already failed live on 2026-08-18 (`[RETRIEVAL: NONE]`), which
is why the assertion here is that the hedge is INSIDE the claim rather than that a label
is present somewhere.

Also asserts the tagging-authority ruling (Mike, 2026-09-03): a model may declare
stated/observed; only Python may set `verified`, so neither `verified` in the wisdom
enum nor `_verified_source` in a tool schema is reachable by a model.

Standalone runner, matching tests/test_crm_dedup_guards.py.

Usage:
    python tests/test_fact_provenance.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.confirm as CF  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.profile as PR  # noqa: E402
import tools.wisdom as WIS  # noqa: E402
from core.orchestrator import _knowledge_block  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
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
    """Same patch set and same reasoning as tests/test_crm_dedup_guards.py."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig = (CRM.persona_data_dir, PR.persona_config_dir, CF.persona_data_dir)
        CRM.persona_data_dir = lambda persona=None: self.path / "data"
        PR.persona_config_dir = lambda persona=None: self.path / "config"
        CF.persona_data_dir = lambda persona=None: self.path / "data"
        return self.path

    def __exit__(self, *exc):
        CRM.persona_data_dir, PR.persona_config_dir, CF.persona_data_dir = self._orig
        self._tmp.cleanup()


def _imported(email: str = "kathleen.jermyn@dovercourt.co.uk") -> str:
    """Create a contact the way tools/contacts_import.py does — from the artefact."""
    return CRM.write_contact(
        name="Kathleen Jermyn",
        contact_info={"email": email},
        _bulk=True,
        _verified_source="google_contacts",
    ).splitlines()[0]


# --- Job 1: the checked-detail gate ----------------------------------------

@check("an imported detail is marked as read from the address book")
def _():
    with _temp_persona_dir():
        cid = _imported()
        rec = next(c for c in CRM._load_contacts() if c["id"] == cid)
        mark = rec["verified_details"]["email"]
        assert mark["source"] == "google_contacts", mark
        assert mark["value"] == "kathleen.jermyn@dovercourt.co.uk", mark


@check("replacing a checked email asks instead of overwriting")
def _():
    with _temp_persona_dir():
        cid = _imported()
        result = CRM.write_contact(
            name="Kathleen Jermyn", contact_id=cid,
            contact_info={"email": "k.jermyn@dovercourt.com"},
        )
        assert "PENDING_CONFIRMATION" in result, result
        # Nothing was written while the question is outstanding.
        rec = next(c for c in CRM._load_contacts() if c["id"] == cid)
        assert rec["contact_info"]["email"] == "kathleen.jermyn@dovercourt.co.uk", rec


@check("the card says where the value on file came from, in plain language")
def _():
    with _temp_persona_dir():
        cid = _imported()
        result = CRM.write_contact(
            name="Kathleen Jermyn", contact_id=cid,
            contact_info={"email": "k.jermyn@dovercourt.com"},
        )
        desc = json.loads(result)["description"]
        assert "Google address book" in desc, desc
        # Architecture-opaque: the card names the record, never the code that read it.
        for leak in ("contacts_import", "write_contact", "_verified_source", "tool"):
            assert leak not in desc, f"{leak!r} leaked into the card: {desc}"


@check("approving the correction saves it AND clears the mark")
def _():
    with _temp_persona_dir():
        cid = _imported()
        result = CRM.write_contact(
            name="Kathleen Jermyn", contact_id=cid,
            contact_info={"email": "k.jermyn@dovercourt.com"},
        )
        token = json.loads(result)["confirm_token"]
        CF.approve(token)
        outcome = CF.execute(token)
        assert outcome.get("status") == "executed", outcome
        rec = next(c for c in CRM._load_contacts() if c["id"] == cid)
        assert rec["contact_info"]["email"] == "k.jermyn@dovercourt.com", rec
        # The new value was never checked against an artefact, so nothing claims it was.
        assert "email" not in rec.get("verified_details", {}), rec.get("verified_details")


@check("a second correction after an approved one passes without a tap")
def _():
    with _temp_persona_dir():
        cid = _imported()
        first = CRM.write_contact(name="Kathleen Jermyn", contact_id=cid,
                                  contact_info={"email": "k.jermyn@dovercourt.com"})
        token = json.loads(first)["confirm_token"]
        CF.approve(token)
        CF.execute(token)
        second = CRM.write_contact(name="Kathleen Jermyn", contact_id=cid,
                                   contact_info={"email": "kj@dovercourt.com"})
        assert "PENDING_CONFIRMATION" not in second, second
        rec = next(c for c in CRM._load_contacts() if c["id"] == cid)
        assert rec["contact_info"]["email"] == "kj@dovercourt.com", rec


@check("filling a blank detail on an imported contact is never gated")
def _():
    with _temp_persona_dir():
        cid = _imported()
        result = CRM.write_contact(
            name="Kathleen Jermyn", contact_id=cid,
            contact_info={"email": "kathleen.jermyn@dovercourt.co.uk",
                          "phone": "+44 7911 123456"},
        )
        assert "PENDING_CONFIRMATION" not in result, result


@check("re-writing the same checked value is not a change and is not gated")
def _():
    with _temp_persona_dir():
        cid = _imported()
        result = CRM.write_contact(
            name="Kathleen Jermyn", contact_id=cid,
            contact_info={"email": "KATHLEEN.JERMYN@dovercourt.co.uk"},
        )
        assert "PENDING_CONFIRMATION" not in result, result


@check("an unmarked detail still overwrites freely")
def _():
    with _temp_persona_dir():
        cid = CRM.write_contact(name="Ravi Chandran",
                                contact_info={"email": "ravi@chandran-associates.co.uk"}).splitlines()[0]
        result = CRM.write_contact(name="Ravi Chandran", contact_id=cid,
                                   contact_info={"email": "r.chandran@chandran-associates.co.uk"})
        assert "PENDING_CONFIRMATION" not in result, result
        rec = next(c for c in CRM._load_contacts() if c["id"] == cid)
        assert rec["contact_info"]["email"] == "r.chandran@chandran-associates.co.uk", rec


@check("enriching a marked contact with a non-detail field is never gated")
def _():
    with _temp_persona_dir():
        cid = _imported()
        result = CRM.write_contact(name="Kathleen Jermyn", contact_id=cid,
                                   employer="Dovercourt", occupation="Surveyor")
        assert "PENDING_CONFIRMATION" not in result, result


# --- Job 2: the hedge ------------------------------------------------------

@check("an inferred fact is rendered as an inference, not as a fact")
def _():
    block = _knowledge_block([
        {"domain": "work", "key": "morning_focus",
         "provenance": "observed", "value": "sharpest between 6am and 9am"},
    ])
    assert "you inferred this, and have not confirmed it" in block, block
    # The hedge is in the same sentence as the claim, not on a separate rule line.
    line = next(ln for ln in block.splitlines() if "morning_focus" in ln)
    assert "sharpest between 6am and 9am" in line, line
    assert "you inferred this" in line, line


@check("a stated fact is rendered bare, with no hedge")
def _():
    block = _knowledge_block([
        {"domain": "food", "key": "standard_oatmeal",
         "provenance": "stated", "value": "oats with berries, no sugar"},
    ])
    line = next(ln for ln in block.splitlines() if "standard_oatmeal" in ln)
    assert line.endswith("oats with berries, no sugar"), line
    assert "inferred" not in line, line


@check("the negotiable rule the hedge replaces is gone from the header")
def _():
    block = _knowledge_block([
        {"domain": "work", "key": "k", "provenance": "observed", "value": "v"},
    ])
    header = block.splitlines()[0]
    assert "tentativ" not in header.lower(), header
    assert "(observed)" not in block, block


@check("a missing provenance hedges rather than asserting")
def _():
    block = _knowledge_block([{"domain": "other", "key": "k", "value": "v"}])
    assert "you inferred this" in block, block


# --- The tagging-authority ruling ------------------------------------------

@check("no schema lets a model claim a value was verified")
def _():
    assert "verified" not in WIS.PROVENANCE, WIS.PROVENANCE
    assert WIS.DEFAULT_PROVENANCE == "observed", WIS.DEFAULT_PROVENANCE
    props = CRM.WRITE_CONTACT_SCHEMA["input_schema"]["properties"]
    for hidden in ("_verified_source", "_bulk", "verified_details"):
        assert hidden not in props, f"{hidden} is model-settable"


@check("an unrecognised provenance falls back to the tentative register")
def _():
    assert WIS.resolve_provenance("verified") == "observed"
    assert WIS.resolve_provenance("") == "observed"
    assert WIS.resolve_provenance("stated") == "stated"


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
