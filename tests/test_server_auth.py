"""
tests/test_server_auth.py — server authentication (roadmap B2, built 2026-08-03).

Covers the gate itself, not the endpoints behind it: that an unauthenticated caller is
refused everywhere except the app shell, that both credential forms work, and that the
WebSocket handshake — the one transport HTTP middleware cannot reach — is closed.

Run:
    python -m pytest tests/test_server_auth.py -q
    python tests/test_server_auth.py            # standalone, no pytest needed

The password is set here before importing core.server, because that import calls
auth.require_configured() and will refuse to load without one. That refusal is itself
the subject of the first test.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_PASSWORD = "test-password-not-the-real-one"
os.environ["METATRON_AUTH_PASSWORD"] = TEST_PASSWORD

from fastapi.testclient import TestClient  # noqa: E402

from core import auth  # noqa: E402
from core.server import app  # noqa: E402

# No `with` — that would run the lifespan handler, which warms Whisper and Kokoro.
# The auth gate is middleware and needs neither.
#
# base_url is https because the session cookie is Secure: over plain http the client
# would silently decline to send it and the cookie test would fail for a reason that
# has nothing to do with the server. Production is HTTPS behind a Tailscale cert.
client = TestClient(app, base_url="https://testserver")


def _login(password: str = TEST_PASSWORD):
    return client.post("/auth/login", json={"password": password})


# --- the guard itself ------------------------------------------------------

def test_missing_password_refuses_to_start():
    """No password set is a startup failure, never a warning."""
    saved = auth.os.environ.pop("METATRON_AUTH_PASSWORD", None)
    try:
        raised = False
        try:
            auth.require_configured()
        except auth.AuthNotConfigured:
            raised = True
        assert raised, "server would have started unauthenticated"
    finally:
        if saved is not None:
            auth.os.environ["METATRON_AUTH_PASSWORD"] = saved


# --- unauthenticated access ------------------------------------------------

def test_health_requires_auth():
    assert client.get("/health").status_code == 401


def test_monitor_file_requires_auth():
    """The endpoint that reads the user's entire data tree."""
    r = client.get("/monitor/file", params={"path": "data/conversations/metatron.db"})
    assert r.status_code == 401


def test_session_stream_requires_auth():
    r = client.post("/session/stream", json={"input": "hello", "agent": "coordinator"})
    assert r.status_code == 401


def test_app_shell_is_open():
    """The PWA has to load before it can offer a login box."""
    assert client.get("/").status_code == 200


# --- login -----------------------------------------------------------------

def test_wrong_password_rejected():
    assert _login("wrong").status_code == 401


def test_login_returns_token_and_sets_cookie():
    r = _login()
    assert r.status_code == 200
    assert r.json()["token"]
    assert auth.COOKIE_NAME in r.cookies
    client.cookies.clear()


def test_bearer_token_grants_access():
    token = _login().json()["token"]
    client.cookies.clear()
    r = client.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_cookie_grants_access():
    _login()  # TestClient retains the Set-Cookie
    assert client.get("/health").status_code == 200
    client.cookies.clear()


# --- token integrity -------------------------------------------------------

def test_tampered_token_rejected():
    token = auth.issue_token()
    payload, _, sig = token.rpartition(".")
    forged = f"{int(payload) + 86400}.{sig}"   # extend the expiry, keep the signature
    assert not auth.verify_token(forged)


def test_expired_token_rejected():
    assert not auth.verify_token(auth.issue_token(ttl_seconds=-1))


def test_token_from_a_different_password_rejected():
    """Changing the password revokes every issued token."""
    token = auth.issue_token()
    auth.os.environ["METATRON_AUTH_PASSWORD"] = "a-different-password"
    try:
        assert not auth.verify_token(token)
    finally:
        auth.os.environ["METATRON_AUTH_PASSWORD"] = TEST_PASSWORD


# --- websocket -------------------------------------------------------------

def test_websocket_first_frame_must_be_auth():
    """A well-formed 'send' as the opening frame is rejected like any other non-auth."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "send", "input": "hello"})
        assert ws.receive_json()["type"] == "auth_failed"


def test_websocket_rejection_closes_the_socket():
    """Rejected sockets are closed, not left open to try again."""
    from starlette.websockets import WebSocketDisconnect
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": "nonsense.deadbeef"})
        assert ws.receive_json()["type"] == "auth_failed"
        closed = False
        try:
            ws.receive_json()
        except WebSocketDisconnect:
            closed = True
        assert closed, "socket stayed open after a failed auth"


def test_websocket_with_valid_token_authenticates():
    token = auth.issue_token()
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": token})
        assert ws.receive_json()["type"] == "auth_ok"


def test_websocket_with_bad_token_is_closed():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": "nonsense.deadbeef"})
        assert ws.receive_json()["type"] == "auth_failed"


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append((name, exc))
                print(f"  FAIL  {name}: {exc}")
    print()
    if failures:
        print(f"{len(failures)} failed")
        sys.exit(1)
    print("all passed")
