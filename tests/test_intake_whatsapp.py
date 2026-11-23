"""
tests/test_intake_whatsapp.py — WhatsApp Phase 1, the VM side, offline.

Plan: archive/plans/whatsapp_phase1_build_plan_2026-11-23.md § 4 (T1–T31) plus the rulings'
own checks (Bulgarian translated, other scripts held back, opt-in deletion). No network, no
model, no persona data: the persona data tree is redirected into a temp directory, the
translator is a stand-in, the channel's config and consent are set per check.

    python3 tests/test_intake_whatsapp.py

Exits 0 if every check passes, 1 otherwise.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "whatsapp-suite-password")
os.environ.setdefault("METATRON_PERSONA", "danny_park")

from fastapi.testclient import TestClient  # noqa: E402

import core.server as server  # noqa: E402
import tools.intake as intake  # noqa: E402
import tools.intake_whatsapp as W  # noqa: E402
import tools.obligations as O  # noqa: E402
from core import auth  # noqa: E402
from core.persona import persona_scope  # noqa: E402

PERSONA = "danny_park"
_root = Path(tempfile.mkdtemp(prefix="whatsapp-suite-"))
server.DB_PATH = _root / "conversations" / "metatron.db"
O.persona_data_dir = lambda persona=None: _root / "personas" / (persona or PERSONA)
intake.persona_data_dir = O.persona_data_dir
auth.DEVICES_ROOT = _root / "personas"
intake._in_quiet_hours = lambda p=None: False

CFG = {
    "enabled": True,
    "channels": {"whatsapp": True},
    "categories": {
        "action_required": {"disposition": "surface", "domain": "logistics"},
        "correspondence": {"disposition": "surface", "domain": "relationships"},
        "unclear": {"disposition": "surface", "domain": None},
    },
    "digest": {"max_items": 25, "show_reasons": True, "include_silent": True},
    "rules": [],
    "ledger": {"enabled": True, "min_observations": 5},
    "limits": {"max_per_sweep": 50, "seen_retention_days": 90, "max_queue_age_days": 7},
}

ANNA = "447700900111@s.whatsapp.net"
JOANNA = "447700900222@s.whatsapp.net"
GROUP = "120363000000000009@g.us"
BOB = "447700900333@s.whatsapp.net"

_client = TestClient(server.app)
_results: list[tuple[str, bool, str]] = []
_state: dict = {}

FAKE_BG = {
    "Ще вечеряме ли в събота в 19:00?": "Shall we have dinner on Saturday at 19:00?",
    "Здравей, как си": "Hi, how are you",
}


def _sandbox(*, consent: bool = True, stanza: bool = True) -> dict:
    shutil.rmtree(_root / "personas", ignore_errors=True)
    cfg = copy.deepcopy(CFG)
    cfg["channels"]["whatsapp"] = stanza
    intake.load_config = lambda p=None: cfg
    W._consent_granted = lambda p=None: _state.get("consent", consent)
    _state["consent"] = consent
    W.set_translator(lambda t: FAKE_BG.get(t))
    return cfg


def check(name: str):
    def deco(fn):
        try:
            with persona_scope(PERSONA):
                fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(exc).__name__}: {exc}\n"
                                           + traceback.format_exc(limit=5)))
        return fn
    return deco


def _device() -> dict:
    _did, token = auth.issue_device_token(PERSONA, "test phone")
    return {"Authorization": f"Bearer {token}"}


def _admin() -> dict:
    return {"Authorization": f"Bearer {auth.issue_token(persona=PERSONA, role='admin')}"}


def _service() -> dict:
    return {"Authorization": f"Bearer {auth.issue_token()}"}


def _share(*extra) -> None:
    chats = [{"chat": ANNA, "kind": "one_to_one", "label": "Anna Petrova"},
             {"chat": JOANNA, "kind": "one_to_one", "label": "Joanna Smith"},
             {"chat": GROUP, "kind": "group", "label": "Book club", "senders": {BOB: "Bob Jones"}}]
    W.set_share_list(None, {"chats": chats + list(extra)})


def _now_s(hours_ago: float = 0) -> int:
    return int(time.time() - hours_ago * 3600)


def _ev(chat=ANNA, text="hello there", t=None, kind="message", ordinal=0, sender="",
        source="live") -> dict:
    return {"kind": kind, "chat": chat, "time": _now_s() if t is None else t, "ordinal": ordinal,
            "sender": sender, "text": text, "source": source}


def _post(events, headers=None, **body) -> dict:
    return W.handle_events(None, {"events": events, **body})


def _records() -> list[dict]:
    return [r for r in intake.read_records() if r.get("channel") == "whatsapp"]


def _index() -> list[dict]:
    return W._read_jsonl(W._index_path(None))


def _all_files_text() -> str:
    out = ""
    for p in (_root / "personas").rglob("*"):
        if p.is_file():
            try:
                out += p.read_text()
            except Exception:  # noqa: BLE001
                pass
    return out


def _id(msg: str) -> str:
    assert msg.startswith("task "), msg
    return msg.split()[1]


# ---------------------------------------------------------------------------
# V1 — tokens, the user from the token, the cap
# ---------------------------------------------------------------------------

@check("T1 a device token is refused off /device/*")
def _():
    _sandbox()
    h = _device()
    assert _client.get(f"/tasks/today?persona={PERSONA}", headers=h).status_code == 401
    assert _client.post("/whatsapp/device/pair", headers=h, json={}).status_code == 401


@check("T2 session and service tokens are refused on /device/*")
def _():
    _sandbox()
    for h in (_admin(), _service()):
        r = _client.get("/device/whatsapp/cursor", headers=h)
        assert r.status_code == 401, (r.status_code, r.text)
    assert _client.get("/device/whatsapp/cursor", headers=_device()).status_code == 200


@check("T3 the user comes from the token, never the body")
def _():
    _sandbox()
    _share()
    r = _client.post("/device/whatsapp/events", headers=_device(),
                     json={"persona": "someone_else", "events": [_ev(text="Are you free Sat?")]})
    assert r.status_code == 200, r.text
    assert not (_root / "personas" / "someone_else").exists()
    assert len(_records()) == 1


@check("T4 revoked, 31-day-stale and rotated-password device tokens are refused")
def _():
    _sandbox()
    did, token = auth.issue_device_token(PERSONA)
    h = {"Authorization": f"Bearer {token}"}
    assert _client.get("/device/whatsapp/cursor", headers=h).status_code == 200
    assert auth.revoke_device(PERSONA, did)
    assert _client.get("/device/whatsapp/cursor", headers=h).status_code == 401
    did2, token2 = auth.issue_device_token(PERSONA)
    data = auth._read_devices(PERSONA)
    data[did2]["last_used"] = int(time.time()) - 31 * 86400
    auth._write_devices(PERSONA, data)
    assert auth.decode_device_token(token2) is None
    _did3, token3 = auth.issue_device_token(PERSONA)
    old = os.environ["METATRON_AUTH_PASSWORD"]
    os.environ["METATRON_AUTH_PASSWORD"] = old + "-rotated"
    try:
        assert auth.decode_device_token(token3) is None
    finally:
        os.environ["METATRON_AUTH_PASSWORD"] = old
    assert auth.decode_device_token(token3) is not None
    assert auth.decode_token(token3) is None          # never passes as a session token


@check("T5 the body cap: declared over 512 KiB, or chunked past it → 413, nothing written")
def _():
    _sandbox()
    _share()
    h = _device()
    big = json.dumps({"events": [_ev(text="x" * 1000)] * 700}).encode()
    assert len(big) > 512 * 1024
    r = _client.post("/device/whatsapp/events", headers={**h, "Content-Type": "application/json"},
                     content=big)
    assert r.status_code == 413, r.status_code

    def chunks():
        for i in range(0, len(big), 65536):
            yield big[i:i + 65536]
    r = _client.post("/device/whatsapp/events", headers={**h, "Content-Type": "application/json"},
                     content=chunks())
    assert r.status_code == 413, r.status_code
    assert not _records() and not _index()


@check("T6 an event with no chat id is rejected; the rest of the batch is accepted")
def _():
    _sandbox()
    _share()
    out = _post([{"kind": "message", "time": _now_s(), "text": "hi"}, _ev(text="ok see you")])
    assert out["rejected"] == [{"index": 0, "reason": "no chat id"}], out
    assert out["accepted"] == 1, out


@check("T7 a chat not on the share list is dropped — no row, no seen, no index")
def _():
    _sandbox()
    _share()
    out = _post([_ev(chat="447700900999@s.whatsapp.net", text="are you free tomorrow?")])
    assert out["dropped_not_shared"] == 1 and out["accepted"] == 0, out
    assert not _records() and not _index() and not intake._load_seen()


@check("T8 a time in milliseconds is rejected")
def _():
    _sandbox()
    _share()
    out = _post([_ev(t=int(time.time() * 1000))])
    assert out["rejected"][0]["reason"].startswith("time is in milliseconds"), out


@check("T9 a live message and its nightly copy are recorded once")
def _():
    _sandbox()
    _share()
    live_ms = int(time.time() * 1000) - 250
    first = _post([_ev(t=live_ms // 1000, text="Dinner tomorrow?", source="live")])
    second = _post([_ev(t=live_ms // 1000, text="Dinner tomorrow?", source="backup")])
    assert first["accepted"] == 1 and second["duplicates"] == 1, (first, second)
    assert len(_records()) == 1


@check("T10 an update replaces the fact and keeps seen_at")
def _():
    _sandbox()
    _share()
    t = _now_s(1)
    _post([_ev(t=t, text="Dinner tomorrow?")])
    before = _records()[0]
    out = _post([_ev(t=t, kind="update", text="Dinner on Saturday at 19:00 at Dishoom?")])
    assert out["updated"] == 1, out
    rows = _records()
    assert len(rows) == 1, rows
    assert rows[0]["subject"] != before["subject"] and "Dishoom" in rows[0]["subject"], rows[0]
    assert rows[0]["seen_at"] == before["seen_at"]


@check("T11 an update that hits the screen withdraws the fact and adds a flag")
def _():
    _sandbox()
    _share()
    t = _now_s(1)
    _post([_ev(t=t, text="Lunch tomorrow?")])
    out = _post([_ev(t=t, kind="update", text="bring the cocaine tomorrow")])
    assert out["held_back"] == 1, out
    assert not _records() and not _index()
    flags = W._read_jsonl(W._flags_path(None))
    assert len(flags) == 1 and flags[0]["category"] == "drugs", flags


@check("T12 the screen holds back before anything is recorded; the flag has no text")
def _():
    _sandbox()
    _share()
    called = []
    real = intake.ingest
    intake.ingest = lambda *a, **k: called.append(1) or real(*a, **k)
    try:
        out = _post([_ev(text="I will k1ll you tomorrow at 9")])
    finally:
        intake.ingest = real
    assert out["held_back"] == 1 and not called, (out, called)
    flag = W._read_jsonl(W._flags_path(None))[0]
    assert set(flag) == {"id", "chat", "sender", "time", "category", "flagged_at"}, flag
    assert "k1ll" not in _all_files_text() and "tomorrow at 9" not in _all_files_text()


# ---------------------------------------------------------------------------
# V5 — one card per task
# ---------------------------------------------------------------------------

@check("T13 three messages from the expected sender → one card; none after a decline; "
       "'Joanna' never matches 'Anna'")
def _():
    _sandbox()
    _share()
    tid = _id(O.open_task("Hear back from Anna about the venue", kind="waiting",
                          expect_from="Anna"))
    _post([_ev(chat=JOANNA, text="Any news on the venue?")])
    assert not O.pending_proposals(), O.pending_proposals()
    for i, text in enumerate(["The venue said yes", "It's booked", "Deposit paid"]):
        _post([_ev(text=text, t=_now_s(3 - i))])
    props = O.pending_proposals()
    assert len(props) == 1 and props[0]["source"] == "whatsapp", props
    shown = server._proposals_for_display()
    assert shown[0]["sender"] == "Anna Petrova" and "@" not in shown[0]["sender"], shown
    O.resolve_proposal(props[0]["proposal_id"], False)
    _post([_ev(text="Did you see my message?", t=_now_s(0.1))])
    task = O._find(O._load(), tid)
    assert len([p for p in task["proposals"] if p.get("source") == "whatsapp"]) == 1, task


# ---------------------------------------------------------------------------
# V6 — the backstop
# ---------------------------------------------------------------------------

@check("T14 an unanswered one-to-one question re-surfaces once, within one delivery window")
def _():
    _sandbox()
    _share()
    _post([_ev(t=_now_s(25), text="What time is the party?")])
    assert W.backstop(None) == 1
    now = datetime.now()
    first = W.context_lines(None, now)
    again = W.context_lines(None, now + timedelta(minutes=10))
    later = W.context_lines(None, now + timedelta(minutes=31))
    assert first and again and not later, (first, again, later)
    assert "untrusted_content" in first[0]
    assert W.backstop(None) == 0                      # once, ever


@check("T15 a reply marker after the fact clears it")
def _():
    _sandbox()
    _share()
    _post([_ev(t=_now_s(30), text="Are you coming on Friday?")])
    _post([{"kind": "reply_marker", "chat": ANNA, "time": _now_s(29)}])
    assert W.backstop(None) == 0
    assert not W.context_lines(None)


@check("T16 reply markers never reach ingest(), the records or match_envelope")
def _():
    _sandbox()
    _share()
    calls = []
    real_i, real_m = intake.ingest, O.match_envelope
    intake.ingest = lambda *a, **k: calls.append("ingest") or real_i(*a, **k)
    O.match_envelope = lambda *a, **k: calls.append("match") or real_m(*a, **k)
    try:
        out = _post([{"kind": "reply_marker", "chat": ANNA, "time": _now_s()}])
        bad = _post([{"kind": "reply_marker", "chat": ANNA, "time": _now_s(), "text": "secret"}])
    finally:
        intake.ingest, O.match_envelope = real_i, real_m
    assert out["accepted"] == 1 and not calls and not _records(), (out, calls)
    assert bad["rejected"][0]["reason"] == "a reply_marker never carries text"


# ---------------------------------------------------------------------------
# V8 / V9 / decision C
# ---------------------------------------------------------------------------

@check("T17 un-sharing a chat purges it everywhere; other chats and email untouched")
def _():
    _sandbox()
    _share()
    O.open_task("Hear from Anna", kind="waiting", expect_from="Anna")
    _post([_ev(text="Done, all booked"), _ev(chat=JOANNA, text="Lunch tomorrow?"),
           _ev(text="bring the cocaine")])
    _post([{"kind": "reply_marker", "chat": ANNA, "time": _now_s()}])
    intake._append_record({"id": "mail1", "channel": "email", "subject": "s",
                           "seen_at": "2026-11-23T10:00:00"})
    assert O.pending_proposals()
    out = W.set_share_list(None, {"chats": [{"chat": JOANNA, "kind": "one_to_one",
                                             "label": "Joanna Smith"}]})
    assert out["removed"] == 2 and out["purged_facts"] == 1, out
    assert [r["sender"] for r in _records()] == [JOANNA], _records()
    assert {r["chat"] for r in _index()} == {JOANNA}
    assert not W._read_jsonl(W._flags_path(None))
    assert ANNA not in (W._load_state(None).get("last_reply") or {})
    assert not O.pending_proposals()
    assert any(r["id"] == "mail1" for r in intake.read_records())
    assert len(intake._load_seen()) == 1


@check("T18 facts expire at 90 days unless a task carries them")
def _():
    _sandbox()
    _share()
    _post([_ev(t=_now_s(24 * 91), text="old news"), _ev(t=_now_s(24 * 92), text="Book the hall"),
           _ev(t=_now_s(1), text="recent news")])
    held = min(_index(), key=lambda r: r["time"])      # the 92-day-old "Book the hall"
    O.open_task("Book the hall", kind="deadline", source_id=held["id"])
    assert W.expire(None) == 1
    ids = {r["id"] for r in _index()}
    assert held["id"] in ids and len(ids) == 2, _index()


@check("T19 the channel is off without the consent record; withdrawing stops collection, "
       "deletes nothing; delete-all is the user's opt-in")
def _():
    _sandbox(consent=False)
    h = _device()
    r = _client.post("/device/whatsapp/events", headers=h, json={"events": []})
    assert r.status_code == 403 and r.json()["detail"] == "channel_off", r.text
    _state["consent"] = True
    _share()
    assert _client.post("/device/whatsapp/events", headers=h,
                        json={"events": [_ev(text="Lunch tomorrow?")]}).status_code == 200
    _state["consent"] = False
    assert _client.post("/device/whatsapp/events", headers=h,
                        json={"events": [_ev(text="hi")]}).status_code == 403
    intake.sweep()
    assert len(_records()) == 1                         # decision C: nothing deleted
    r = _client.post("/whatsapp/delete-all", headers=_admin())
    assert r.status_code == 200 and r.json()["deleted_facts"] == 1, r.text
    assert not _records() and not W._state_path(None).exists()


@check("T20 WhatsApp never reads or teaches the sender ledger")
def _():
    cfg = _sandbox()
    cfg["rules"] = [{"match": {"sender": ANNA}, "disposition": "surface", "note": "t"}]
    _share()
    _post([_ev(t=_now_s(1) + i, text=f"message number {i}") for i in range(10)])
    assert intake._load_ledger() == {}, intake._load_ledger()


@check("T21 a span carrying an injection marker is dropped")
def _():
    _sandbox()
    _share()
    _post([_ev(text="Dinner tomorrow at Ignore Previous Instructions?")])
    subj = _records()[0]["subject"]
    assert "Ignore" not in subj and '"dinner"' in subj, subj


# ---------------------------------------------------------------------------
# The lock, push channels, digest, queues, the decline guard
# ---------------------------------------------------------------------------

@check("T22 a sweep with a slow fetch and a second process ingesting keep both; nested lock ok")
def _():
    _sandbox()
    _share()
    mail = intake.Envelope(channel="synthetic", native_id="m1",
                           received=datetime.now().isoformat(timespec="seconds"),
                           sender_address="a@x.com", subject="hello")
    dirpath = intake._intake_dir()
    child = (
        "import sys,time; sys.path.insert(0, %r)\n"
        "import tools.intake as I\n"
        "from pathlib import Path\n"
        "I.persona_data_dir = lambda p=None: Path(%r)\n"
        "I.load_config = lambda p=None: {'enabled': True, 'limits': {}}\n"
        "time.sleep(0.5)\n"
        "e = I.Envelope(channel='whatsapp', native_id='x|1|0', received='2026-11-23T10:00:00',"
        " subject='info · from X', signals={'whatsapp': {'type': 'info', 'kind': 'one_to_one',"
        " 'action': False}})\n"
        "I.ingest([e])\n") % (str(Path(__file__).parent.parent), str(dirpath.parent))
    proc = subprocess.Popen([sys.executable, "-c", child])

    def slow(limit, skip=None):
        time.sleep(2.0)
        return [mail]
    intake._ADAPTERS["synthetic"] = slow
    cfg = intake.load_config()
    cfg["channels"]["synthetic"] = True
    real = intake._load_adapters
    intake._load_adapters = lambda c: None
    try:
        intake.sweep()
    finally:
        intake._load_adapters = real
        intake._ADAPTERS.pop("synthetic", None)
    proc.wait(timeout=30)
    assert proc.returncode == 0
    seen = intake._load_seen()
    assert mail.id in seen and intake.envelope_id("whatsapp", "x|1|0") in seen, seen
    assert len(intake.read_records()) == 2
    with intake._state_lock(), intake._state_lock():
        pass


@check("T23 a push channel is never polled: no 'no adapter' warning, no channel-health entry")
def _():
    _sandbox()
    msgs = []
    handler = logging.Handler()
    handler.emit = lambda rec: msgs.append(rec.getMessage())
    intake.logger.addHandler(handler)
    try:
        intake._load_adapters({"channels": {"whatsapp": True}})
        intake.sweep()
    finally:
        intake.logger.removeHandler(handler)
    assert not any("no adapter" in m for m in msgs), msgs
    assert intake._read_json(intake._channel_health_path(), {}) == {}


@check("T24 the digest never holds WhatsApp; an email row still listed")
def _():
    _sandbox()
    _share()
    _post([_ev(text="just saying hi"), _ev(chat=JOANNA, text="Can you call me?", t=_now_s(24 * 8))])
    rows = intake.read_records()
    for r in rows:                                      # age the action fact past escalation
        if r.get("category") == "action_required":
            r["seen_at"] = (datetime.now() - timedelta(days=8)).isoformat(timespec="seconds")
    p = intake._intake_dir() / "records.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    intake._append_record({"id": "mail2", "channel": "email", "subject": "Your invoice",
                           "category": "bill_statement", "disposition": "digest",
                           "seen_at": datetime.now().isoformat(timespec="seconds")})
    d = intake.build_digest()
    assert "Your invoice" in d and "hi" not in d and "call" not in d.lower(), d


@check("T25 an info fact is queued nowhere and not counted as 'unrouted'")
def _():
    _sandbox()
    _share()
    _post([_ev(text="just saying hi")])
    r = _records()[0]
    assert r["domain"] is None and r["disposition"] == "silent", r
    assert intake._queue_rows("relationships") == []
    note = intake._empty_queue("relationships")["note"]
    assert "carry no domain" not in note, note


@check("T26 a WhatsApp info row does not lift a decline; an action row does")
def _():
    from tools.turn_context import _newer_intake_row
    _sandbox()
    _share()
    since = time.time() - 1
    _post([_ev(text="just saying hi")])
    assert not _newer_intake_row(since)
    _post([_ev(chat=JOANNA, text="Can you call me?")])
    assert _newer_intake_row(since)


@check("T27 a same-second clash never loses a message")
def _():
    _sandbox()
    _share()
    t = _now_s(2)
    _post([_ev(t=t, ordinal=0, text="message B", source="live")])
    _post([_ev(t=t, ordinal=0, text="message A", source="backup"),
           _ev(t=t, ordinal=1, text="message B", source="backup")])
    salt = W._salt(W._load_state(None))
    fps = {r["fp"] for r in _index()}
    assert W.fingerprint("message A", salt) in fps and W.fingerprint("message B", salt) in fps, fps


@check("T28 a one-to-one sender is the chat; the display is the user's own label")
def _():
    _sandbox()
    _share()
    _post([_ev(text="see you later", sender="")])
    r = _records()[0]
    assert r["sender"] == ANNA and r["sender_display"] == "Anna Petrova", r
    assert "from Anna Petrova" in r["subject"]


@check("T29 seen is still pruned — after a sweep and after an events post")
def _():
    _sandbox()
    _share()
    intake._save_seen({"old": (datetime.now() - timedelta(days=91)).isoformat()})
    intake.sweep()
    assert "old" not in intake._load_seen()
    intake._save_seen({"old": (datetime.now() - timedelta(days=91)).isoformat()})
    _post([_ev(text="hello")])
    assert "old" not in intake._load_seen()


@check("T30 a group question is info; a group proposal with a time needs the user")
def _():
    _sandbox()
    _share()
    _post([_ev(chat=GROUP, sender=BOB, text="Has anyone read chapter 3?"),
           _ev(chat=GROUP, sender=BOB, text="Shall we meet Saturday at 19:00?", t=_now_s() - 5)])
    cats = {r["subject"].split(" · ")[0]: r["category"] for r in _records()}
    # The type stays what it is; in a group only the proposal needs the user (verify 3).
    assert cats == {"question": "correspondence", "proposal": "action_required"}, cats
    assert all("from Bob Jones" in r["subject"] for r in _records())


@check("T31 rotating the auth password keeps the dedupe")
def _():
    _sandbox()
    _share()
    t = _now_s(1)
    _post([_ev(t=t, text="same words")])
    old = os.environ["METATRON_AUTH_PASSWORD"]
    os.environ["METATRON_AUTH_PASSWORD"] = old + "-rotated"
    try:
        out = _post([_ev(t=t, text="same words", source="backup")])
    finally:
        os.environ["METATRON_AUTH_PASSWORD"] = old
    assert out["duplicates"] == 1 and len(_records()) == 1, out


# ---------------------------------------------------------------------------
# Decision D — languages; the app's own routes
# ---------------------------------------------------------------------------

@check("D1 Bulgarian is translated, then screened and extracted; without a model it is held back")
def _():
    _sandbox()
    _share()
    _post([_ev(text="Ще вечеряме ли в събота в 19:00?")])
    r = _records()[0]
    assert r["category"] == "action_required" and r["subject"].startswith("proposal"), r
    assert "19:00" in r["subject"], r
    W.set_translator(lambda t: None)
    out = _post([_ev(text="Нещо съвсем друго", t=_now_s(1))])
    assert out["held_back"] == 1
    assert W._read_jsonl(W._flags_path(None))[-1]["category"] == "unscreened"
    assert "Нещо" not in _all_files_text() and "вечеряме" not in _all_files_text()


@check("D4 a greeting question is chat; a clock in the original beats the translation's")
def _():
    _sandbox()
    _share()
    FAKE_BG["Ще се видим ли в събота в 19:00?"] = "Shall we meet on Saturday at 7:00 p.m.?"
    _post([_ev(text="Hi, how are you?"), _ev(text="Ще се видим ли в събота в 19:00?", t=_now_s(1)),
           _ev(text="How are you? And can you send me the photos?", t=_now_s(2))])
    subj = {r["subject"].split(" · ")[0]: r for r in _records()}
    assert subj["info"]["category"] == "correspondence", subj
    assert "19:00" in subj["proposal"]["subject"], subj["proposal"]
    assert subj["request"]["category"] == "action_required", subj


@check("D2 another script with no model is held back as unscreened")
def _():
    _sandbox()
    _share()
    out = _post([_ev(text="Θα φάμε μαζί το Σάββατο;")])
    assert out["held_back"] == 1 and not _records(), out


@check("D3 pairing and delete-all refuse a service token; pairing returns a working token")
def _():
    _sandbox()
    assert _client.post("/whatsapp/device/pair", headers=_service(), json={}).status_code == 403
    assert _client.post("/whatsapp/delete-all", headers=_service()).status_code == 403
    r = _client.post("/whatsapp/device/pair", headers=_admin(), json={"label": "Jelly Star"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    assert _client.get("/device/whatsapp/cursor",
                       headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    devs = _client.get("/whatsapp/devices", headers=_admin()).json()["devices"]
    assert devs[0]["label"] == "Jelly Star" and "token" not in devs[0], devs


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    failed = [r for r in _results if not r[1]]
    for name, ok, err in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("        " + err.replace("\n", "\n        "))
    shutil.rmtree(_root, ignore_errors=True)
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
