"""
tests/test_confirmation_gate.py — the human-in-the-loop gate (roadmap B2 / item 5).

These test the properties that make the gate worth having, not that it runs:

  * a first call does not act
  * an unapproved token does not act
  * an approval is single-use
  * an approval cannot be spent on different arguments than the ones shown
  * approvals expire
  * recipients outside the known set are refused in code, whatever the model was told

Nothing here sends mail: SMTP is never reached, because every test stops at the gate.

Run:  python tests/test_confirmation_gate.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")
os.environ["METATRON_PERSONA"] = "test_confirm"

from core.persona import persona_data_dir  # noqa: E402
from tools import confirm  # noqa: E402


def _clean():
    p = persona_data_dir() / "pending_confirmations.json"
    if p.exists():
        p.unlink()


# --- the gate itself -------------------------------------------------------

def test_request_does_not_act():
    _clean()
    r = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")
    assert r["status"] == "PENDING_CONFIRMATION"
    assert r["confirm_token"]
    assert "NOT been performed" in r["instruction"]


def test_unapproved_token_is_refused():
    _clean()
    r = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")
    ok, reason = confirm.consume(r["confirm_token"], "send_email", {"to": "a@b.com"})
    assert not ok and "not approved" in reason.lower()


def test_approved_token_works_once_only():
    _clean()
    args = {"to": "a@b.com"}
    r = confirm.request("send_email", args, "Send a test")
    assert confirm.approve(r["confirm_token"])
    ok, _ = confirm.consume(r["confirm_token"], "send_email", args)
    assert ok, "approved token was refused"
    ok2, reason = confirm.consume(r["confirm_token"], "send_email", args)
    assert not ok2, "token was reusable — one approval authorised a second send"


def test_approval_cannot_be_spent_on_different_arguments():
    """The dangerous one: approve something harmless, spend it on something else."""
    _clean()
    shown = {"to": "a@b.com", "subject": "Itinerary", "body": "here it is"}
    r = confirm.request("send_email", shown, "Send the itinerary")
    confirm.approve(r["confirm_token"])
    swapped = {"to": "attacker@evil.com", "subject": "Itinerary", "body": "here it is"}
    ok, reason = confirm.consume(r["confirm_token"], "send_email", swapped)
    assert not ok, "approval for one message was spent on another"
    assert "changed" in reason.lower()


def test_no_token_is_refused():
    assert confirm.consume(None, "send_email", {})[0] is False
    assert confirm.consume("", "send_email", {})[0] is False


def test_forged_token_is_refused():
    _clean()
    ok, _ = confirm.consume("not-a-real-token", "send_email", {"to": "a@b.com"})
    assert not ok


def test_expiry():
    _clean()
    saved = confirm.TTL_SECONDS
    confirm.TTL_SECONDS = 1
    try:
        r = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")
        confirm.approve(r["confirm_token"])
        time.sleep(1.2)
        ok, reason = confirm.consume(r["confirm_token"], "send_email", {"to": "a@b.com"})
        assert not ok and "expired" in reason.lower()
    finally:
        confirm.TTL_SECONDS = saved


def test_pending_lists_only_unapproved():
    _clean()
    a = confirm.request("send_email", {"to": "a@b.com"}, "First")
    confirm.request("send_email", {"to": "c@d.com"}, "Second")
    assert len(confirm.pending()) == 2
    confirm.approve(a["confirm_token"])
    assert [p["description"] for p in confirm.pending()] == ["Second"]


# --- send_email's own guards -----------------------------------------------

def test_unknown_recipient_refused_in_code():
    _clean()
    from tools.mail import send_email
    r = send_email("stranger@evil.com", "Hi", "body")
    assert "error" in r and "not a known recipient" in r["error"]
    assert "confirm_token" not in r, "an unknown recipient still opened a confirmation"


def test_first_call_returns_pending_not_sent(monkeypatch=None):
    _clean()
    import tools.mail as mail
    mail._known_recipients = lambda: {"me@example.com": "you"}
    r = mail.send_email("me@example.com", "Subject", "Body")
    assert r.get("status") == "PENDING_CONFIRMATION"
    assert "Subject" in r["description"] and "Body" in r["description"]


def test_empty_message_refused():
    _clean()
    import tools.mail as mail
    mail._known_recipients = lambda: {"me@example.com": "you"}
    assert "error" in mail.send_email("me@example.com", "", "")


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc}")
    _clean()
    print()
    print(f"{len(failures)} failed" if failures else "all passed")
    sys.exit(1 if failures else 0)
