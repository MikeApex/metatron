"""
tests/test_ws_send_idempotent.py — a resent message is answered, never run twice.

The client now keeps every message until its reply arrives and resends whatever is
unconfirmed after a reconnect (static/index.html, the outbox). That is only safe if
the server recognises a resend: without the guard each one re-ran the whole pipeline,
a median ~26k input tokens, and the second reply was dropped by INSERT OR IGNORE, so
the duplicate was paid for and never seen.

Runs the REAL /ws handler. Two things are replaced, and both are meters: the pipeline
(a stub that counts its calls — the count is the whole point) and the conversation
log (which writes into data/personas/). The database is a temp file, so nothing in
data/ is read or written.

Both sockets share one blocking portal, and therefore one event loop. The default
TestClient gives every websocket its own loop, which would make the cross-socket
broadcast in the second test a cross-loop call that production never makes.

    python tests/test_ws_send_idempotent.py
    python -m pytest tests/test_ws_send_idempotent.py -q
"""

import asyncio
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["METATRON_AUTH_PASSWORD"] = "test-password-not-the-real-one"

import anyio.from_thread  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core import auth  # noqa: E402
from core import server  # noqa: E402

PERSONA = "idempotency_test"

_tmp = tempfile.TemporaryDirectory()
server.DB_PATH = Path(_tmp.name) / "metatron.db"
asyncio.run(server._init_db())

server._log_conversation = lambda *a, **k: None

CALLS: list[str] = []
MODE = {"kind": "ok"}
GATE = threading.Event()


def _fake_stream(user_input, **kwargs):
    CALLS.append(user_input)
    if MODE.get("block"):
        GATE.wait(10)
    kind = MODE["kind"]
    if kind == "ok":
        yield "hello "
        yield "world"
    elif kind == "retract":
        yield "[RETRACT]"
    elif kind == "error":
        raise RuntimeError("boom")


server.run_pipeline_session_stream = _fake_stream


def _reset(kind="ok", block=False):
    CALLS.clear()
    MODE.clear()
    MODE.update(kind=kind, block=block)
    GATE.clear()


def _open(client):
    ws = client.websocket_connect(f"/ws?persona={PERSONA}").__enter__()
    ws.send_json({"type": "auth", "token": auth.issue_token()})
    assert ws.receive_json()["type"] == "auth_ok"
    # A turn starting on another socket can broadcast its stream_start into the gap
    # between joining the group and the history read — production has the same gap.
    while ws.receive_json()["type"] != "history":
        pass
    return ws


def _close(ws):
    """
    Exit the session, not just close the socket: an un-exited session leaves its
    server task running, and the shared portal then waits on it forever.

    Waits for every claim to clear first. Exiting a TestClient session CANCELS the
    server task — production's handler is never cancelled by a disconnect — and the
    row is saved after `done` goes out, so an early exit would kill the save and make
    the stored-reply test pass or fail on timing.
    """
    deadline = time.monotonic() + 5
    while server._inflight_exchanges and time.monotonic() < deadline:
        time.sleep(0.02)
    ws.__exit__(None, None, None)


def _send(ws, exchange_id, text="what's on today"):
    ws.send_json({"type": "send", "exchange_id": exchange_id, "input": text,
                  "agent": "coordinator", "source": "ui"})


def _until(ws, terminal=("done", "retract", "error")):
    """Frames up to and including the first terminal one, skipping heartbeats."""
    frames = []
    while True:
        f = ws.receive_json()
        if f.get("type") == "ping":
            continue
        frames.append(f)
        if f.get("type") in terminal:
            return frames


def _types(frames):
    return [f["type"] for f in frames]


def _with_client(fn):
    with anyio.from_thread.start_blocking_portal() as portal:
        client = TestClient(server.app, base_url="https://testserver")
        client.portal = portal
        fn(client)


# ---------------------------------------------------------------------------

def test_a_send_is_acknowledged_before_it_runs():
    _reset()

    def body(client):
        ws = _open(client)
        _send(ws, "idem-ack")
        frames = _until(ws)
        assert frames[0] == {"type": "accepted", "exchange_id": "idem-ack"}, frames[0]
        assert _types(frames)[-1] == "done"
        assert "".join(f["text"] for f in frames if f["type"] == "chunk") == "hello world"
        _close(ws)
    _with_client(body)
    assert CALLS == ["what's on today"], CALLS


def test_a_resend_of_a_running_turn_is_acknowledged_not_rerun():
    """The socket that sent it is gone; the new one receives the reply by broadcast."""
    _reset(block=True)

    def body(client):
        first = _open(client)
        _send(first, "idem-inflight")
        assert first.receive_json() == {"type": "accepted", "exchange_id": "idem-inflight"}

        second = _open(client)
        _send(second, "idem-inflight")
        assert second.receive_json() == {"type": "accepted", "exchange_id": "idem-inflight"}

        GATE.set()
        frames = _until(second)
        assert _types(frames)[-1] == "done", frames
        assert "".join(f["text"] for f in frames if f["type"] == "chunk") == "hello world"
        _until(first)
        _close(first)
        _close(second)
    _with_client(body)
    assert len(CALLS) == 1, f"the pipeline ran {len(CALLS)} times for one message"


def test_a_resend_of_an_answered_turn_replays_the_stored_reply():
    _reset()

    def body(client):
        ws = _open(client)
        _send(ws, "idem-stored")
        _until(ws)
        _close(ws)

        again = _open(client)
        _send(again, "idem-stored")
        frames = _until(again)
        assert _types(frames) == ["accepted", "chunk", "done"], _types(frames)
        assert frames[1]["text"] == "hello world"
        _close(again)
    _with_client(body)
    assert len(CALLS) == 1, f"the pipeline ran {len(CALLS)} times for one message"


def test_a_resend_of_a_retracted_turn_replays_the_retract():
    """Re-running it would be re-rolling against the output filter."""
    _reset(kind="retract")

    def body(client):
        ws = _open(client)
        _send(ws, "idem-retract")
        assert _types(_until(ws))[-1] == "retract"
        _send(ws, "idem-retract")
        frames = _until(ws)
        assert _types(frames) == ["accepted", "retract"], _types(frames)
        _close(ws)
    _with_client(body)
    assert len(CALLS) == 1, f"the pipeline ran {len(CALLS)} times for one message"


def test_a_failed_turn_can_be_retried():
    """An error is not an answer; the user's Retry must actually run it again."""
    _reset(kind="error")

    def body(client):
        ws = _open(client)
        _send(ws, "idem-error")
        assert _types(_until(ws))[-1] == "error"
        MODE["kind"] = "ok"
        _send(ws, "idem-error")
        assert _types(_until(ws))[-1] == "done"
        _close(ws)
    _with_client(body)
    assert len(CALLS) == 2, CALLS


def test_no_claim_outlives_its_turn():
    """A leaked claim would make that message unsendable until the server restarts."""
    assert not server._inflight_exchanges, server._inflight_exchanges


if __name__ == "__main__":
    failures = 0
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures} passed, {failures} failed, {len(tests)} total")
    sys.exit(1 if failures else 0)
