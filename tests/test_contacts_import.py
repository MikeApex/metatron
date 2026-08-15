"""
tests/test_contacts_import.py — unit tests for tools/contacts_import.py [DB-0810-17]:

  - import_google_contacts: pulls from a stubbed read_google_contacts (no live
    Google API calls), writes/updates CRM records, idempotent on re-run.
  - import_contacts_file: vCard and CSV parsing (Google-shaped and Outlook-shaped
    headers), tolerant of unrecognized columns, idempotent on re-run.
  - dedup: identity match (email/phone/exact-name) updates in place; a soft name
    resemblance is surfaced as evidence via write_contact, not auto-merged.

Standalone runner (no pytest dependency), matching tests/test_crm_dedup_guards.py.

Usage:
    python3 tests/test_contacts_import.py

Exits 0 if every test passes, 1 otherwise.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.crm as CRM  # noqa: E402
import tools.profile as PR  # noqa: E402
import tools.contacts_import as CI  # noqa: E402

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
    """Point tools.crm at an empty temp directory for the duration of the block,
    same pattern as tests/test_crm_dedup_guards.py. tools.contacts_import calls
    tools.crm's public functions directly (crm.write_contact, crm.list_contacts),
    so patching CRM.persona_data_dir is the only patch needed — contacts_import
    holds no persona-dir state of its own. write_contact also lazily imports
    tools.profile._load (for the own-identity email/phone check), which resolves
    through tools.profile's own persona_config_dir — patched here too, same as
    tests/test_crm_dedup_guards.py's _temp_persona_dir."""
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
# import_google_contacts — stubbed read_google_contacts, no live API calls
# ---------------------------------------------------------------------------

def _stub_google(contacts):
    """Patch tools.google_contacts.read_google_contacts for the duration of a
    `with` block via unittest.mock, so import_google_contacts's lazy
    `from tools.google_contacts import read_google_contacts` picks up the stub."""
    return mock.patch("tools.google_contacts.read_google_contacts", return_value={"contacts": contacts})


@check("import_google_contacts creates new records from a stubbed pull")
def _():
    with _temp_persona_dir():
        with _stub_google([
            {"name": "Sarah Chen", "emails": ["sarah@example-contact.net"], "phones": []},
            {"name": "Bob Jenkins", "emails": [], "phones": ["415-282-9134"]},
        ]):
            report = CI.import_google_contacts()
        assert "2 created, 0 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        assert {c["name"] for c in contacts} == {"Sarah Chen", "Bob Jenkins"}, contacts


@check("import_google_contacts propagates a not-connected error without creating anything")
def _():
    with _temp_persona_dir():
        with mock.patch("tools.google_contacts.read_google_contacts", return_value={"error": "not connected"}):
            report = CI.import_google_contacts()
        assert report.startswith("Error:"), report
        assert "not connected" in report, report
        assert json.loads(CRM.list_contacts()) == [], CRM.list_contacts()


@check("import_google_contacts is idempotent on re-run (matched by email)")
def _():
    with _temp_persona_dir():
        source = [{"name": "Sarah Chen", "emails": ["sarah@example-contact.net"], "phones": []}]
        with _stub_google(source):
            CI.import_google_contacts()
        with _stub_google(source):
            report = CI.import_google_contacts()
        assert "0 created, 1 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        assert len(contacts) == 1, contacts


@check("import_google_contacts is idempotent on re-run (matched by exact name, no email/phone)")
def _():
    with _temp_persona_dir():
        source = [{"name": "No Contact Info Person", "emails": [], "phones": []}]
        with _stub_google(source):
            CI.import_google_contacts()
        with _stub_google(source):
            report = CI.import_google_contacts()
        assert "0 created, 1 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        assert len(contacts) == 1, contacts


@check("import_google_contacts matches an existing CRM contact by phone even if the name differs")
def _():
    with _temp_persona_dir():
        CRM.write_contact(name="Bob", contact_info={"phone": "4152829134"})
        with _stub_google([{"name": "Robert Jenkins", "emails": [], "phones": ["(415) 282-9134"]}]):
            report = CI.import_google_contacts()
        assert "0 created, 1 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        assert len(contacts) == 1, contacts
        assert contacts[0]["name"] == "Robert Jenkins", contacts


@check("import_google_contacts surfaces a soft name near-miss as evidence, does not auto-merge")
def _():
    with _temp_persona_dir():
        CRM.write_contact(name="Iva Diamond")
        with _stub_google([{"name": "Eva", "emails": [], "phones": []}]):
            report = CI.import_google_contacts()
        assert "1 created, 0 updated" in report, report
        assert "Possible existing match" in report or "evidence" in report.lower(), report
        contacts = json.loads(CRM.list_contacts())
        assert len(contacts) == 2, contacts


@check("import_google_contacts skips a contact with no usable name")
def _():
    with _temp_persona_dir():
        with _stub_google([{"name": "", "emails": ["noone@example-contact.net"], "phones": []}]):
            report = CI.import_google_contacts()
        assert "0 created, 0 updated, 1 skipped" in report, report
        assert json.loads(CRM.list_contacts()) == [], CRM.list_contacts()


# ---------------------------------------------------------------------------
# import_contacts_file — vCard
# ---------------------------------------------------------------------------

_VCARD_FIXTURE = """BEGIN:VCARD
VERSION:3.0
FN:Jane Okonkwo
N:Okonkwo;Jane;;;
EMAIL;TYPE=INTERNET:jane@example-contact.net
TEL;TYPE=CELL:415-282-9155
ORG:Acme Corp
NOTE:Met at a conference
END:VCARD
BEGIN:VCARD
VERSION:3.0
N:Smith;John;;;
TEL;TYPE=HOME:212-774-3018
END:VCARD
"""


@check("import_contacts_file parses a vCard fixture and creates records")
def _():
    with _temp_persona_dir():
        with tempfile.NamedTemporaryFile("w", suffix=".vcf", delete=False) as f:
            f.write(_VCARD_FIXTURE)
            path = f.name
        try:
            report = CI.import_contacts_file(path)
        finally:
            Path(path).unlink()
        assert "2 created, 0 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        names = {c["name"] for c in contacts}
        assert names == {"Jane Okonkwo", "John Smith"}, contacts
        jane = next(c for c in contacts if c["name"] == "Jane Okonkwo")
        assert jane["contact_info"]["email"] == "jane@example-contact.net", jane
        assert jane["employer"] == "Acme Corp", jane
        assert jane["notes"] == "Met at a conference", jane
        # N-only record (no FN) falls back to "First Last" from structured name.
        john = next(c for c in contacts if c["name"] == "John Smith")
        assert john["first_name"] == "John" and john["last_name"] == "Smith", john


@check("import_contacts_file (vCard) is idempotent on re-run")
def _():
    with _temp_persona_dir():
        with tempfile.NamedTemporaryFile("w", suffix=".vcf", delete=False) as f:
            f.write(_VCARD_FIXTURE)
            path = f.name
        try:
            CI.import_contacts_file(path)
            report = CI.import_contacts_file(path)
        finally:
            Path(path).unlink()
        assert "0 created, 2 updated, 0 skipped" in report, report
        assert len(json.loads(CRM.list_contacts())) == 2


@check("vCard unescaping handles comma/semicolon/newline escapes")
def _():
    parsed = CI._parse_vcard(
        "BEGIN:VCARD\nFN:O\\, Brien\\; Jr.\nNOTE:Line one\\nLine two\nEND:VCARD\n"
    )
    assert len(parsed) == 1, parsed
    assert parsed[0]["name"] == "O, Brien; Jr.", parsed
    assert parsed[0]["notes"] == "Line one\nLine two", parsed


# ---------------------------------------------------------------------------
# import_contacts_file — CSV
# ---------------------------------------------------------------------------

_GOOGLE_CSV_FIXTURE = (
    "Name,Given Name,Family Name,E-mail 1 - Value,Phone 1 - Value,Organization Name,Notes\n"
    "Sarah Chen,Sarah,Chen,sarah@example-contact.net,415-282-9134,Acme Inc,Old friend\n"
)

_OUTLOOK_CSV_FIXTURE = (
    "First Name,Last Name,E-mail Address,Business Phone,Company,Weird Custom Field\n"
    "Bob,Jenkins,bob@example-contact.net,212-774-3062,Initech,some-value\n"
)


@check("import_contacts_file (CSV) parses Google-export-shaped headers")
def _():
    with _temp_persona_dir():
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(_GOOGLE_CSV_FIXTURE)
            path = f.name
        try:
            report = CI.import_contacts_file(path)
        finally:
            Path(path).unlink()
        assert "1 created, 0 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        assert len(contacts) == 1, contacts
        c = contacts[0]
        assert c["name"] == "Sarah Chen", c
        assert c["contact_info"]["email"] == "sarah@example-contact.net", c
        assert c["employer"] == "Acme Inc", c
        assert c["notes"] == "Old friend", c


@check("import_contacts_file (CSV) parses Outlook-export-shaped headers and keeps unmapped columns")
def _():
    with _temp_persona_dir():
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(_OUTLOOK_CSV_FIXTURE)
            path = f.name
        try:
            report = CI.import_contacts_file(path)
        finally:
            Path(path).unlink()
        assert "1 created, 0 updated, 0 skipped" in report, report
        contacts = json.loads(CRM.list_contacts())
        c = contacts[0]
        assert c["name"] == "Bob Jenkins", c
        assert c["employer"] == "Initech", c
        # Unrecognized column preserved in notes, not dropped.
        assert "Weird Custom Field" in c["notes"], c
        assert "some-value" in c["notes"], c


@check("import_contacts_file (CSV) is idempotent on re-run")
def _():
    with _temp_persona_dir():
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(_GOOGLE_CSV_FIXTURE)
            path = f.name
        try:
            CI.import_contacts_file(path)
            report = CI.import_contacts_file(path)
        finally:
            Path(path).unlink()
        assert "0 created, 1 updated, 0 skipped" in report, report
        assert len(json.loads(CRM.list_contacts())) == 1


@check("import_contacts_file errors cleanly on a missing file")
def _():
    with _temp_persona_dir():
        report = CI.import_contacts_file("/no/such/file.vcf")
        assert report.startswith("Error:"), report


@check("import_contacts_file errors cleanly on an unsupported source_format")
def _():
    with _temp_persona_dir():
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(_GOOGLE_CSV_FIXTURE)
            path = f.name
        try:
            report = CI.import_contacts_file(path, source_format="excel")
        finally:
            Path(path).unlink()
        assert report.startswith("Error:"), report


# ---------------------------------------------------------------------------
# _find_exact_contact — matching precedence directly
# ---------------------------------------------------------------------------

@check("_find_exact_contact prefers email match over name mismatch")
def _():
    contacts = [{"id": "1", "name": "Old Name", "contact_info": {"email": "x@example-contact.net"}}]
    match = CI._find_exact_contact(contacts, "New Name", ["x@example-contact.net"], [])
    assert match is not None and match["id"] == "1"


@check("_find_exact_contact returns None when nothing matches")
def _():
    contacts = [{"id": "1", "name": "Someone Else", "contact_info": {}}]
    match = CI._find_exact_contact(contacts, "Nobody", ["a@b.com"], ["2829134"])
    assert match is None


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
