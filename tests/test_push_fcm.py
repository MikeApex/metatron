"""
tests/test_push_fcm.py — the Android app's push channel (day planner Stage C, plan § 14 D1 b).

FCM is stubbed (`core.push._FCM_SEND`) — the standing rule: every live meter a test ends in is
stubbed. The stores point at a temp directory; nothing under data/ is touched.

What must hold:
  - the ping that goes through Google carries the message id and nothing else
  - one persona's phone never receives another's ping, and cannot fetch another's message
  - a token FCM reports dead is pruned; a 400 (possibly our own bad request) is not
  - messages expire; a phone moved to another account stops receiving the first one's pings

    python3 tests/test_push_fcm.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.push as P  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="push_fcm_"))
_SENT: list[tuple[str, dict]] = []
_REPLY = {"status": 200, "text": "{}"}
_LOG: list[tuple[str, str, dict]] = []


def _fake_send(token, data):
    _SENT.append((token, data))
    status = _REPLY.get(token, _REPLY["status"]) if isinstance(_REPLY.get(token), int) else _REPLY["status"]
    return status, _REPLY["text"] if status == 200 else _REPLY.get("dead_text", "")


def _fresh(name: str) -> None:
    d = _TMP / name
    d.mkdir(parents=True, exist_ok=True)
    P._FCM_TOKENS_FILE = d / "fcm_tokens.json"
    P._OUTBOX_FILE = d / "push_outbox.json"
    P._LOCK_FILE = d / ".push.lock"
    P._SUBSCRIPTIONS_FILE = d / "push_subscriptions.json"   # no browsers: FCM only
    P._FCM_SEND = _fake_send
    P._log_delivery = lambda persona, event, **f: _LOG.append((persona, event, f))
    _SENT.clear()
    _LOG.clear()
    _REPLY.clear()
    _REPLY.update(status=200, text="{}")


def check(name: str):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


@check("the ping through Google carries the message id only — never the title, body or a task")
def _():
    _fresh("content_free")
    P.save_fcm_token("tok-mike", "mike")
    out = P.send_push("Metatron", "Leave for physio now", persona="mike",
                      tasks=[{"id": "t1", "title": "Physio exercises"}])
    assert out["sent"] == 1 and not out["errors"], out
    (token, data), = _SENT
    assert token == "tok-mike" and set(data) == {"m"}, data
    wire = json.dumps(data)
    assert "physio" not in wire.lower() and "t1" not in wire, wire
    msg = P.fetch_message(data["m"], "mike")
    assert msg == {"title": "Metatron", "body": "Leave for physio now",
                   "tasks": [{"id": "t1", "title": "Physio exercises"}]}, msg
    assert [e for _, e, _ in _LOG] == ["fcm_sent", "fcm_fetched"], _LOG
    assert "physio" not in json.dumps(_LOG).lower(), _LOG          # the log is content-free


@check("one persona's phone never receives another's ping, nor fetches another's message")
def _():
    _fresh("isolation")
    P.save_fcm_token("tok-mike", "mike")
    P.save_fcm_token("tok-iva", "iva")
    P.send_push("Metatron", "Mike's check-in", persona="mike")
    assert [t for t, _ in _SENT] == ["tok-mike"], _SENT
    msg_id = _SENT[0][1]["m"]
    assert P.fetch_message(msg_id, "iva") is None
    assert P.fetch_message("not-an-id", "mike") is None
    assert P.fetch_message(msg_id, "mike")["body"] == "Mike's check-in"


@check("a phone that signs in as someone else moves to them; sign-out stops its pings")
def _():
    _fresh("move")
    P.save_fcm_token("tok-phone", "mike")
    P.save_fcm_token("tok-phone", "iva")
    P.send_push("Metatron", "for mike", persona="mike")
    assert not _SENT, _SENT
    assert P.remove_fcm_token("tok-phone", "mike") == "Not registered"   # not his to remove
    assert P.remove_fcm_token("tok-phone", "iva") == "Removed"
    P.send_push("Metatron", "for iva", persona="iva")
    assert not _SENT, _SENT


@check("a token FCM reports dead is pruned; a 400 is not")
def _():
    _fresh("prune")
    P.save_fcm_token("tok-dead", "mike")
    P.save_fcm_token("tok-live", "mike")
    _REPLY["tok-dead"] = 404
    out = P.send_push("Metatron", "x", persona="mike")
    assert out["sent"] == 1, out
    left = [t["token"] for t in json.loads(P._FCM_TOKENS_FILE.read_text())]
    assert left == ["tok-live"], left
    _REPLY["tok-live"] = 400
    out = P.send_push("Metatron", "y", persona="mike")
    assert out["sent"] == 0 and out["errors"] == ["fcm: HTTP 400"], out
    assert [t["token"] for t in json.loads(P._FCM_TOKENS_FILE.read_text())] == ["tok-live"]
    # FCM's own word for a rotated token arrives on a 400 too, and that one IS pruned.
    _REPLY["dead_text"] = '{"error": {"details": [{"errorCode": "UNREGISTERED"}]}}'
    P.send_push("Metatron", "z", persona="mike")
    assert json.loads(P._FCM_TOKENS_FILE.read_text()) == []


@check("messages expire after a day, and every send prunes the outbox")
def _():
    _fresh("expiry")
    P.save_fcm_token("tok-mike", "mike")
    P.send_push("Metatron", "old", persona="mike")
    old_id = _SENT[-1][1]["m"]
    box = json.loads(P._OUTBOX_FILE.read_text())
    box[old_id]["created"] = int(time.time()) - P._OUTBOX_TTL_S - 5
    P._OUTBOX_FILE.write_text(json.dumps(box))
    assert P.fetch_message(old_id, "mike") is None
    P.send_push("Metatron", "new", persona="mike")
    assert old_id not in json.loads(P._OUTBOX_FILE.read_text())


@check("no devices at all still says so; an FCM failure never raises out of send_push")
def _():
    _fresh("none")
    assert P.send_push("Metatron", "x", persona="mike") == {
        "sent": 0, "errors": ["No registered subscriptions"]}
    P.save_fcm_token("tok-mike", "mike")

    def boom(token, data):
        raise ConnectionError("down")
    P._FCM_SEND = boom
    out = P.send_push("Metatron", "x", persona="mike")
    assert out == {"sent": 0, "errors": ["fcm: ConnectionError"]}, out


@check("browser subscriptions: re-sent on every load without piling up; a replacement drops only its own")
def _():
    _fresh("web_subs")
    sub = lambda e: {"endpoint": e, "keys": {"p256dh": "k", "auth": "a"}}
    P.save_subscription(sub("https://web.push.apple.com/A"), "mike")
    for _ in range(5):                                    # five page loads, same subscription
        P.save_subscription(sub("https://web.push.apple.com/A"), "mike")
    P.save_subscription(sub("https://web.push.apple.com/X"), "iva")
    assert len(P._load_subscriptions()) == 2, P._load_subscriptions()
    # The key changed: the browser replaces A with B and says so.
    P.save_subscription(sub("https://web.push.apple.com/B"), "mike",
                        replaces="https://web.push.apple.com/A")
    eps = sorted((s["persona"], s["endpoint"].rsplit("/", 1)[1]) for s in P._load_subscriptions())
    assert eps == [("iva", "X"), ("mike", "B")], eps
    # Naming someone else's endpoint as "replaced" removes nothing of theirs.
    P.save_subscription(sub("https://web.push.apple.com/C"), "mike",
                        replaces="https://web.push.apple.com/X")
    assert ("iva", "https://web.push.apple.com/X") in {
        (s["persona"], s["endpoint"]) for s in P._load_subscriptions()}


@check("a phone's fetch-failure report is logged, stripped to short safe tokens")
def _():
    _fresh("phone_failure")
    P.note_phone_failure("mike", "SocketTimeoutException|xrbRZPY-|2026-10-28T15:38:41")
    P.note_phone_failure("mike", "<script>alert(1)</script>" + "x" * 200 + "|id\nwith\nlines|now")
    (p1, e1, f1), (p2, e2, f2) = _LOG
    assert (p1, e1) == ("mike", "fcm_fetch_failed"), _LOG
    assert f1 == {"reason": "SocketTimeoutException", "id": "xrbRZPY-",
                  "phone_at": "2026-10-28T15:38:41"}, f1
    assert "<" not in f2["reason"] and len(f2["reason"]) <= 60 and "\n" not in f2["id"], f2


@check("send_push still refuses a call that names no persona")
def _():
    _fresh("no_persona")
    try:
        P.send_push("Metatron", "x", persona="")
    except ValueError:
        return
    raise AssertionError("send_push accepted an empty persona")


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
