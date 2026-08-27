"""
tests/test_decline_path.py — declining a confirmation actually declines it (`[DB-0827-01]`).

Before this, "No" made no server call: the pending record stayed pending, and the app's
five-second poll put the same card back until the ten-minute TTL. The only exit was to
approve. Mike, on the first decline ever performed: *"If I decline it keeps asking in a
loop. In the end I approved to break the loop."*

What is asserted here is that property, not the plumbing:

  * after a decline, the poll the app makes no longer offers the action
  * the refusal is retained as a fact, with its action fingerprint, not vaporised
  * declining an unknown or expired token reports "no such thing" rather than pretending
  * the approve path is untouched — an approval still executes, still once only

Every test here fails on the pre-change code: `confirm.decline` did not exist.
Nothing here reaches a model, SMTP or the network.

Run:  python3 -m pytest tests/test_decline_path.py -x -q
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")
os.environ["METATRON_PERSONA"] = "test_decline"

from core.persona import persona_data_dir  # noqa: E402
from tools import confirm  # noqa: E402


def _clean() -> None:
    for name in ("pending_confirmations.json", "declined_confirmations.json"):
        p = persona_data_dir() / name
        if p.exists():
            p.unlink()


# --- the loop this exists to end -------------------------------------------

def test_decline_removes_it_from_the_poll():
    """The whole bug: the card came back every five seconds until the user gave in."""
    _clean()
    r = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")
    token = r["confirm_token"]
    assert [p["token"] for p in confirm.pending()] == [token]

    assert confirm.decline(token) is not None
    assert confirm.pending() == []


def test_decline_leaves_other_pending_requests_alone():
    _clean()
    a = confirm.request("send_email", {"to": "a@b.com"}, "Send A")["confirm_token"]
    b = confirm.request("send_email", {"to": "c@d.com"}, "Send B")["confirm_token"]
    confirm.decline(a)
    assert [p["token"] for p in confirm.pending()] == [b]


def test_a_declined_action_cannot_then_be_approved():
    """The record is gone, so the approve path has nothing to spend."""
    _clean()
    token = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")["confirm_token"]
    confirm.decline(token)
    assert confirm.approve(token) is False
    ok, _ = confirm.consume(token, "send_email", {"to": "a@b.com"})
    assert not ok


# --- the refusal is kept ---------------------------------------------------

def test_declined_entry_is_retained_with_status_and_fingerprint():
    """"The user said no to X" is a fact the system keeps — X included."""
    _clean()
    args = {"to": "a@b.com", "subject": "S", "body": "B"}
    r = confirm.request("send_email", args, "Email a@b.com")
    record = confirm.decline(r["confirm_token"])

    assert record["status"] == "declined"
    assert record["action"] == "send_email"
    assert record["args"] == args
    assert record["description"] == "Email a@b.com"
    assert record["declined_at"] > 0

    ledger = confirm.declined()
    assert len(ledger) == 1
    assert ledger[0] == record
    # The fingerprint is what a later re-proposal of the same action is matched against.
    assert ledger[0]["fingerprint"] == confirm._fingerprint("send_email", args)


def test_ledger_accumulates_and_recent_window_filters():
    _clean()
    for i in range(3):
        t = confirm.request("send_email", {"to": f"{i}@b.com"}, f"Send {i}")["confirm_token"]
        confirm.decline(t)
    assert len(confirm.declined()) == 3
    assert len(confirm.declined(within_seconds=60)) == 3
    assert confirm.declined(within_seconds=0) == []


def test_declined_ledger_is_readable_when_absent():
    _clean()
    assert confirm.declined() == []


# --- refusing cleanly ------------------------------------------------------

def test_declining_an_unknown_token_reports_nothing_to_decline():
    _clean()
    assert confirm.decline("not-a-real-token") is None
    assert confirm.declined() == []


def test_declining_an_expired_token_reports_nothing_to_decline():
    _clean()
    token = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")["confirm_token"]
    data = confirm._load()
    data[token]["expires_at"] = time.time() - 1
    confirm._save(data)
    assert confirm.decline(token) is None


def test_declining_twice_is_not_a_second_refusal():
    """The server turns the second call into a 404; nothing double-files the ledger."""
    _clean()
    token = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")["confirm_token"]
    assert confirm.decline(token) is not None
    assert confirm.decline(token) is None
    assert len(confirm.declined()) == 1


def test_tampered_record_is_still_removed_but_not_filed_as_a_clean_refusal():
    """If the args no longer match the fingerprint, what was refused is not known."""
    _clean()
    token = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")["confirm_token"]
    data = confirm._load()
    data[token]["args"] = {"to": "attacker@evil.com"}     # edited on disk
    confirm._save(data)

    record = confirm.decline(token)
    assert record is not None
    assert confirm.pending() == []                       # the loop still ends
    assert record["args"] is None and record["fingerprint"] is None


# --- the approve path is unchanged -----------------------------------------

def test_approve_path_still_works():
    _clean()
    args = {"to": "a@b.com"}
    token = confirm.request("send_email", args, "Send a test")["confirm_token"]
    assert confirm.approve(token) is True
    ok, reason = confirm.consume(token, "send_email", args)
    assert ok, reason
    ok_again, _ = confirm.consume(token, "send_email", args)
    assert not ok_again                                   # still single-use
    assert confirm.declined() == []                       # an approval is not a refusal


# --- the endpoint the app actually calls -----------------------------------
#
# No `with TestClient(...)` — that runs the lifespan handler, which warms Whisper and
# Kokoro. Nothing here needs either. `base_url` is https because the session cookie is
# Secure and would otherwise be silently withheld.

TEST_PASSWORD = "test-password-not-the-real-one"

from fastapi.testclient import TestClient  # noqa: E402
from core import server as srv  # noqa: E402

_client = TestClient(srv.app, base_url="https://testserver")


def _login() -> None:
    _client.post("/auth/login", json={"password": TEST_PASSWORD})


def _with_temp_db(fn):
    """Point the exchange store at a scratch file — a decline writes a conversation row."""
    import asyncio
    import tempfile

    saved = srv.DB_PATH
    tmp = Path(tempfile.mkdtemp()) / "exchanges.db"
    srv.DB_PATH = tmp
    try:
        asyncio.run(srv._init_db())
        return fn()
    finally:
        srv.DB_PATH = saved


def test_decline_endpoint_requires_auth():
    """Same gate as every other endpoint — a tap has to come from a signed-in client."""
    _client.cookies.clear()
    assert _client.post("/decline", json={"token": "nope"}).status_code == 401


def test_decline_endpoint_404s_on_an_unknown_token():
    _clean()
    _login()
    res = _client.post("/decline", json={"token": "not-a-real-token",
                                         "persona": "test_decline"})
    assert res.status_code == 404


def test_decline_endpoint_stops_the_poll_returning_it():
    """End to end: what the app polls no longer offers the action it just refused."""
    _clean()
    _login()

    def body():
        token = confirm.request("send_email", {"to": "a@b.com"}, "Send a test")["confirm_token"]
        before = _client.get("/pending-confirmations?persona=test_decline").json()
        assert [p["token"] for p in before["pending"]] == [token]

        res = _client.post("/decline", json={"token": token, "persona": "test_decline"})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "declined"

        after = _client.get("/pending-confirmations?persona=test_decline").json()
        assert after["pending"] == []
        # A second tap on a stale card is refused rather than filing a second refusal.
        assert _client.post("/decline", json={"token": token,
                                              "persona": "test_decline"}).status_code == 404
        assert len(confirm.declined()) == 1

    _with_temp_db(body)


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
