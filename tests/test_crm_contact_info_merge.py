"""
tests/test_crm_contact_info_merge.py — [DB-1029-02] updating a contact's details can erase
the rest of them, and a contact can hold only one email.

Live 2026-09-07: Mike had Iva's address corrected from her work address to her personal one,
then said "You should have preserved both email addresses in the CRM." Metatron replied that
both were preserved. They were not: `write_contact` replaced `contact_info` wholesale on every
update, so the work address was gone — the model later reached for `social.work_email` as a
place to hide it. The same replacement drops a stored phone or address whenever an update
carries only an email.

Standalone runner (no pytest dependency), matching tests/test_crm_merge_guard.py.

Usage:
    python3 tests/test_crm_contact_info_merge.py

Exits 0 if every test passes, 1 otherwise.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.confirm as CF  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.profile as PR  # noqa: E402

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
    """Same fixture as tests/test_crm_merge_guard.py."""

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


def _iva() -> str:
    out = CRM.write_contact(name="Iva Diamond", contact_info={
        "email": "iva.diamond@bp.com", "phone": "+44 7914 352 618",
        "address": "12 Clarendon Road", "social": {"linkedin": "iva-d"}})
    assert "PENDING_CONFIRMATION" not in out and not out.startswith("Error"), out
    return out.splitlines()[0]


def _info(cid: str) -> dict:
    return next(c for c in CRM._load_contacts() if c["id"] == cid).get("contact_info") or {}


@check("an update carrying only an email keeps the stored phone, address and social")
def _keeps_other_keys():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "iva.stod@gmail.com"})
        info = _info(cid)
        assert info.get("phone") == "+44 7914 352 618", info
        assert info.get("address") == "12 Clarendon Road", info
        assert info.get("social") == {"linkedin": "iva-d"}, info


@check("a new email becomes primary and the previous one is preserved (the 09-07 case)")
def _preserves_old_email():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "iva.stod@gmail.com"})
        info = _info(cid)
        assert info.get("email") == "iva.stod@gmail.com", info
        assert info.get("other_emails") == ["iva.diamond@bp.com"], info


@check("re-writing the same email adds no duplicate")
def _same_email_no_dup():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "IVA.DIAMOND@bp.com"})
        assert "other_emails" not in _info(cid), _info(cid)


@check("swapping back does not list the primary in other_emails")
def _swap_back():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "iva.stod@gmail.com"})
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "iva.diamond@bp.com"})
        info = _info(cid)
        assert info.get("email") == "iva.diamond@bp.com", info
        assert info.get("other_emails") == ["iva.stod@gmail.com"], info


@check("an explicit other_emails list is how an address is dropped")
def _explicit_drop():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "iva.stod@gmail.com"})
        CRM.write_contact(name="", contact_id=cid, contact_info={"other_emails": []})
        info = _info(cid)
        assert info.get("email") == "iva.stod@gmail.com", info
        assert not info.get("other_emails"), info


@check("social handles merge per platform")
def _social_merge():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"social": {"twitter": "@iva"}})
        assert _info(cid).get("social") == {"linkedin": "iva-d", "twitter": "@iva"}, _info(cid)


@check("contact_info={} still clears, as documented")
def _empty_clears():
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={})
        assert _info(cid) == {}, _info(cid)


@check("a preserved address is still a permitted email recipient")
def _recipient_allowlist():
    from tools.mail import _known_recipients
    with _temp_persona_dir():
        cid = _iva()
        CRM.write_contact(name="", contact_id=cid, contact_info={"email": "iva.stod@gmail.com"})
        allowed = _known_recipients()
        assert "iva.stod@gmail.com" in allowed and "iva.diamond@bp.com" in allowed, allowed


if __name__ == "__main__":
    failed = [r for r in _results if not r[1]]
    for name, ok, msg in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {msg}" if msg else ""))
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
