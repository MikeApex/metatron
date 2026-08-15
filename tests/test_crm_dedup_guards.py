"""
tests/test_crm_dedup_guards.py — unit tests for the [DB-0815-07]/[DB-0815-06]/
[DB-0815-05] guards added to tools/crm.py and tools/profile.py:

  - merge_contacts: folds a duplicate contact into another, archives the loser
    with a merged_into pointer, never deletes it.
  - read_contact / search_contacts: follow that merged_into pointer, so an old
    id or an old (corrected-away) name still resolves.
  - write_contact: surfaces near-duplicate names (voice-transcription near-misses
    like "Eva"/"Iva" and "Kathaleen"/"Kathleen") as evidence, not a verdict, and
    refuses a reserved/placeholder email domain (example.com and friends) outright.
  - write_profile: refuses a value that reads as a correction to someone else's
    contact record rather than a fact about the user, without over-refusing
    ordinary name/other writes.

Standalone runner (no pytest dependency), matching the convention of
tests/test_profile_language.py.

Usage:
    python tests/test_crm_dedup_guards.py

Exits 0 if every test passes, 1 otherwise.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.crm as CRM  # noqa: E402
import tools.profile as PR  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator: run a test function, record pass/fail rather than aborting."""
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
    """
    Point tools.crm and tools.profile at an empty temp directory for the
    duration of the block, so tests never touch a real persona's data. Both
    modules bind their persona_*_dir function by name at import time, so each
    needs its own patch — patching core.persona itself would not reach either
    copy. tools.crm's write_contact also imports tools.profile._load lazily
    inside the function body, which resolves through tools.profile's own
    patched persona_config_dir, so the own-identity checks in crm tests keep
    working under this same patch.
    """
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig_crm_data = CRM.persona_data_dir
        self._orig_pr_config = PR.persona_config_dir
        CRM.persona_data_dir = lambda persona=None: self.path / "data"
        PR.persona_config_dir = lambda persona=None: self.path / "config"
        return self.path

    def __exit__(self, *exc):
        CRM.persona_data_dir = self._orig_crm_data
        PR.persona_config_dir = self._orig_pr_config
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# merge_contacts: preserves data, archives with merged_into, never deletes
# ---------------------------------------------------------------------------

@check("merge_contacts folds fields, unions lists, and archives the loser")
def _():
    with _temp_persona_dir():
        keep_id = CRM.write_contact(name="Iva Diamond", relationship_type="family",
                                     tags=["family"]).splitlines()[0]
        merge_id = CRM.write_contact(name="Eva", occupation="Retired teacher",
                                      tags=["needs_follow_up"]).splitlines()[0]

        result = CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id)
        assert "Merged" in result, result

        kept = json.loads(CRM.read_contact(contact_id=keep_id))
        # Field empty on keep, present on merge: filled in.
        assert kept["occupation"] == "Retired teacher", kept
        # Field already set on keep: left alone (not overwritten by merge's absence).
        assert kept["relationship_type"] == "family", kept
        # Lists unioned.
        assert set(kept["tags"]) == {"family", "needs_follow_up"}, kept

        # Loser is gone from the live list.
        contacts = CRM._load_contacts()
        assert all(c["id"] != merge_id for c in contacts), contacts

        # Loser is archived, not deleted, with a merged_into pointer.
        archive_dir = CRM._crm_archive_dir()
        archived_files = list(archive_dir.glob(f"{merge_id}_*.json"))
        assert len(archived_files) == 1, archived_files
        archived = json.loads(archived_files[0].read_text())
        assert archived["merged_into"] == keep_id, archived
        assert archived["name"] == "Eva", archived
        assert archived["occupation"] == "Retired teacher", archived


@check("read_contact(contact_id=old_id) resolves through merged_into to the survivor")
def _():
    with _temp_persona_dir():
        keep_id = CRM.write_contact(name="Iva Diamond").splitlines()[0]
        merge_id = CRM.write_contact(name="Eva").splitlines()[0]
        CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id)

        result = json.loads(CRM.read_contact(contact_id=merge_id))
        assert result["id"] == keep_id, result
        assert result["name"] == "Iva Diamond", result
        assert "_merged_note" in result, result


@check("read_contact(name=old_name) resolves the corrected-away name to the survivor")
def _():
    with _temp_persona_dir():
        keep_id = CRM.write_contact(name="Iva Diamond").splitlines()[0]
        merge_id = CRM.write_contact(name="Eva").splitlines()[0]
        CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id)

        result = json.loads(CRM.read_contact(name="Eva"))
        assert result["id"] == keep_id, result
        assert result["name"] == "Iva Diamond", result


@check("search_contacts(old_name) finds the survivor, not a stub or nothing")
def _():
    with _temp_persona_dir():
        keep_id = CRM.write_contact(name="Iva Diamond").splitlines()[0]
        merge_id = CRM.write_contact(name="Eva").splitlines()[0]
        CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id)

        results = json.loads(CRM.search_contacts("Eva"))
        assert len(results) == 1, results
        assert results[0]["id"] == keep_id, results


@check("merge_contacts refuses when either id doesn't resolve")
def _():
    with _temp_persona_dir():
        keep_id = CRM.write_contact(name="Iva Diamond").splitlines()[0]
        result = CRM.merge_contacts(keep_id=keep_id, merge_id="not-a-real-id")
        assert result.startswith("Error:"), result


@check("merge_contacts refuses merging a record into itself")
def _():
    with _temp_persona_dir():
        keep_id = CRM.write_contact(name="Iva Diamond").splitlines()[0]
        result = CRM.merge_contacts(keep_id=keep_id, merge_id=keep_id)
        assert result.startswith("Error:"), result


# ---------------------------------------------------------------------------
# write_contact: dedup evidence on the write path (Item B)
# ---------------------------------------------------------------------------

@check("write_contact surfaces the Eva/Iva near-miss as evidence, still creates the record")
def _():
    with _temp_persona_dir():
        CRM.write_contact(name="Iva Diamond")
        result = CRM.write_contact(name="Eva")
        lines = result.splitlines()
        new_id = lines[0]
        # Still created — evidence, not a refusal.
        assert CRM._load_contacts()[-1]["id"] == new_id, result
        assert "Possible existing match" in result, result
        assert "Iva Diamond" in result, result


@check("write_contact surfaces the Kathaleen/Kathleen transcription near-miss")
def _():
    with _temp_persona_dir():
        CRM.write_contact(name="Kathleen Ortiz")
        result = CRM.write_contact(name="Kathaleen Ortiz")
        assert "Possible existing match" in result, result
        assert "Kathleen Ortiz" in result, result


@check("write_contact does not flag unrelated names as duplicates")
def _():
    with _temp_persona_dir():
        CRM.write_contact(name="Sarah Chen")
        result = CRM.write_contact(name="Bob Jenkins")
        assert "Possible existing match" not in result, result


@check("updating an existing contact via contact_id is unaffected by dedup evidence")
def _():
    with _temp_persona_dir():
        cid = CRM.write_contact(name="Iva Diamond").splitlines()[0]
        result = CRM.write_contact(name="Iva Diamond", occupation="Retired", contact_id=cid)
        assert result == cid, result


# ---------------------------------------------------------------------------
# write_contact: reserved/placeholder email domain refusal (Item C)
# ---------------------------------------------------------------------------

@check("write_contact refuses example.com outright")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="Eva", contact_info={"email": "eva@example.com"})
        assert result.startswith("Error:"), result
        assert "example.com" in result, result
        # Nothing was saved.
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact refuses other RFC 2606 reserved domains (.test, .invalid, localhost)")
def _():
    with _temp_persona_dir():
        for addr in ("a@b.test", "a@b.invalid", "a@localhost"):
            result = CRM.write_contact(name="Someone", contact_info={"email": addr})
            assert result.startswith("Error:"), (addr, result)


@check("write_contact still writes a legitimate email address")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="Eva", contact_info={"email": "eva.diamond@gmail.com"})
        assert not result.startswith("Error:"), result
        cid = result.splitlines()[0]
        contact = json.loads(CRM.read_contact(contact_id=cid))
        assert contact["contact_info"]["email"] == "eva.diamond@gmail.com", contact


# ---------------------------------------------------------------------------
# write_profile: third-party-correction guard (Item D)
# ---------------------------------------------------------------------------

@check("write_profile refuses the exact recorded failure text in 'name'")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("name", "Contact name updated from Eva to Iva.")
        assert result.startswith("Error:"), result
        assert PR._load().get("name") is None, PR._load()


@check("write_profile refuses a similarly-shaped correction in 'other'")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("other", "Contact name was changed from Kathaleen to Kathleen.")
        assert result.startswith("Error:"), result
        assert PR._load().get("other") in (None, []), PR._load()


@check("write_profile still accepts an ordinary name")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("name", "Mike Diamond")
        assert "Profile updated" in result, result
        assert PR._load().get("name") == "Mike Diamond", PR._load()


@check("write_profile still accepts an ordinary 'other' fact with 'from'/'to' in it")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("other", "Prefers to work from home on Fridays.")
        assert "Profile updated" in result, result
        assert "Prefers to work from home on Fridays." in PR._load().get("other", []), PR._load()


@check("write_profile still accepts a longer legitimate name with a suffix")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("name", "Robert Smith Jr.")
        assert "Profile updated" in result, result
        assert PR._load().get("name") == "Robert Smith Jr.", PR._load()


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
