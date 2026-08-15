"""
tests/test_crm_placeholders.py — unit tests for the [DB-0815-06] placeholder
guard in tools/crm.py, widened (2026-08-15) from email-only to phone, address,
social handle, and name.

Each placeholder class is checked for refusal, and a matching set of
real-looking values is checked to make sure the guard does not over-refuse —
false positives are the stated risk in the backlog item, not an afterthought.

Standalone runner (no pytest dependency), matching the convention of
tests/test_crm_dedup_guards.py.

Usage:
    python tests/test_crm_placeholders.py

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
    """Point tools.crm at an empty temp directory for the duration of the block,
    so tests never touch a real persona's data. Same pattern as
    tests/test_crm_dedup_guards.py."""
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
# Unit-level checks on the pure matcher functions (no filesystem involved)
# ---------------------------------------------------------------------------

@check("_is_placeholder_phone catches NANP 555-01xx regardless of formatting")
def _():
    for value in ("555-0100", "555 010 0", "(212) 555-0142", "+1-212-555-0199"):
        assert CRM._is_placeholder_phone(value) is not None, value


@check("_is_placeholder_phone catches UK Ofcom 07700 900xxx regardless of formatting")
def _():
    for value in ("07700 900123", "+44 7700 900123", "+44 (0)7700 900123", "0044 7700 900999"):
        assert CRM._is_placeholder_phone(value) is not None, value


@check("_is_placeholder_phone catches sequential and all-zero numbers")
def _():
    for value in ("123-456-7890", "0123456789", "000-000-0000", "0000000000"):
        assert CRM._is_placeholder_phone(value) is not None, value


@check("_is_placeholder_phone passes real-looking numbers")
def _():
    for value in ("+44 7700 800123", "212-555-1234", "312-867-5309", "+1 415 555 2671"):
        assert CRM._is_placeholder_phone(value) is None, value


@check("_is_placeholder_address catches Anytown and bare textbook streets")
def _():
    for value in ("123 Main St", "123 Main Street", "1234 Elm Street",
                  "123 Main St, Anytown, USA", "45 Oak Ave, Anytown"):
        assert CRM._is_placeholder_address(value) is not None, value


@check("_is_placeholder_address passes a real street with a real city attached")
def _():
    for value in ("123 Main Street, Springfield, IL 62704",
                  "1234 Elm Street, Portland, OR 97201",
                  "742 Evergreen Terrace, Springfield, OR"):
        assert CRM._is_placeholder_address(value) is None, value


@check("_is_placeholder_social_handle catches generic stand-in handles")
def _():
    for value in ("@username", "@handle", "@example", "@yourname", "Username", "HANDLE"):
        assert CRM._is_placeholder_social_handle(value) is not None, value


@check("_is_placeholder_social_handle passes a real-looking handle")
def _():
    for value in ("@sarah_chen92", "kathleen.ortiz", "@mikediamond"):
        assert CRM._is_placeholder_social_handle(value) is None, value


@check("_is_placeholder_name catches John Doe / Jane Doe, case-insensitive")
def _():
    for value in ("John Doe", "jane doe", "  John   Doe  "):
        assert CRM._is_placeholder_name(value) is not None, value


@check("_is_placeholder_name passes a real surname 'Doe' and unrelated names")
def _():
    for value in ("Sarah Doe", "John Smith", "Jane Austen", "Doe"):
        assert CRM._is_placeholder_name(value) is None, value


# ---------------------------------------------------------------------------
# write_contact end-to-end: refusal and persistence
# ---------------------------------------------------------------------------

@check("write_contact refuses a placeholder phone and saves nothing")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="Someone", contact_info={"phone": "555-0100"})
        assert result.startswith("Error:"), result
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact refuses a placeholder address and saves nothing")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="Someone", contact_info={"address": "123 Main St"})
        assert result.startswith("Error:"), result
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact refuses a placeholder social handle and saves nothing")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(
            name="Someone", contact_info={"social": {"twitter": "@username"}}
        )
        assert result.startswith("Error:"), result
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact refuses 'John Doe' as a name and saves nothing")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="John Doe")
        assert result.startswith("Error:"), result
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact refuses 'Jane Doe' assembled from first_name/last_name")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="Contact", first_name="Jane", last_name="Doe")
        assert result.startswith("Error:"), result
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact still saves a real contact with real-looking contact_info")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(
            name="Sarah Doe",
            contact_info={
                "phone": "+44 7700 800123",
                "address": "123 Main Street, Springfield, IL 62704",
                "social": {"twitter": "@sarah_chen92"},
            },
        )
        assert not result.startswith("Error:"), result
        cid = result.splitlines()[0]
        contact = json.loads(CRM.read_contact(contact_id=cid))
        assert contact["contact_info"]["phone"] == "+44 7700 800123", contact
        assert contact["contact_info"]["address"] == "123 Main Street, Springfield, IL 62704", contact
        assert contact["contact_info"]["social"]["twitter"] == "@sarah_chen92", contact
        assert contact["name"] == "Sarah Doe", contact


@check("write_contact updating an existing record is checked the same way")
def _():
    with _temp_persona_dir():
        cid = CRM.write_contact(name="Real Person").splitlines()[0]
        result = CRM.write_contact(name="", contact_id=cid, contact_info={"phone": "07700 900123"})
        assert result.startswith("Error:"), result
        contact = json.loads(CRM.read_contact(contact_id=cid))
        assert contact["contact_info"] == {}, contact


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
