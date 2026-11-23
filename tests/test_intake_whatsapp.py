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

_REAL_CONSENT_GRANTED = W._consent_granted          # before any check stubs it

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
    # Phase 2 § 4.3: the flag carries its key (chat|second|ordinal, never text) for the missed
    # lookup; the field set is still fixed and holds nothing of the message.
    assert set(flag) == {"id", "native_id", "chat", "sender", "time", "category",
                         "flagged_at"}, flag
    assert flag["native_id"].count("|") == 2 and flag["native_id"].startswith(ANNA + "|"), flag
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
    assert r.status_code == 403 and r.json()["detail"] == "no_consent", r.text
    _state["consent"] = True
    _share()
    assert _client.post("/device/whatsapp/events", headers=h,
                        json={"events": [_ev(text="Lunch tomorrow?")]}).status_code == 200
    _state["consent"] = False
    r = _client.post("/device/whatsapp/events", headers=h, json={"events": [_ev(text="hi")]})
    assert r.status_code == 403 and r.json()["detail"] == "no_consent", r.text
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
# Phase 2 (archive/plans/whatsapp_phase2_build_plan_2026-11-23.md § 4) — the named gate, the run
# report, the stale line, the missed flags
# ---------------------------------------------------------------------------

_DEVICE_ROUTES = (("get", "/device/whatsapp/cursor", None),
                  ("post", "/device/whatsapp/events", {"events": []}),
                  ("post", "/device/whatsapp/share-list", {"chats": []}),
                  ("post", "/device/whatsapp/run", {"report": {}}),
                  ("post", "/device/whatsapp/missed", {"keys": []}))


def _call(h, method, path, body):
    return (_client.get(path, headers=h) if method == "get"
            else _client.post(path, headers=h, json=body))


def _report(**over) -> dict:
    r = {"v": 1, "run_at": _now_s(), "dry_run": 0, "backup_written": _now_s(3),
         "full_backup_written": _now_s(48), "base_received": 40, "base_received_text": 30,
         "inc_received": 6, "inc_received_text": 5, "without_key_id": 0, "without_chat": 0,
         "text_undecodable": 0, "base_key_collisions": 0, "deletions_listed": 0,
         "posted_messages": 3, "posted_updates": 1, "posted_reply_markers": 2,
         "skipped_unchanged": 30, "rejected": 0, "dropped_not_shared": 0,
         "same_second_groups": 0, "error": ""}
    r.update(over)
    return r


def _stale(now) -> list[str]:
    return [l for l in W.context_lines(None, now) if "not reached Metatron" in l]


@check("P1 the closed gate names which gate: no_consent / consented_off, on every device route")
def _():
    cfg = _sandbox(consent=False)
    h = _device()
    for method, path, body in _DEVICE_ROUTES:
        r = _call(h, method, path, body)
        assert r.status_code == 403 and r.json()["detail"] == "no_consent", (path, r.text)
    _state["consent"] = True
    cfg["channels"]["whatsapp"] = False                 # consent recorded, the stanza off
    for method, path, body in _DEVICE_ROUTES:
        r = _call(h, method, path, body)
        assert r.status_code == 403 and r.json()["detail"] == "consented_off", (path, r.text)
    cfg["channels"]["whatsapp"] = True
    cfg["enabled"] = False                              # consent recorded, intake off
    r = _client.get("/device/whatsapp/cursor", headers=h)
    assert r.status_code == 403 and r.json()["detail"] == "consented_off", r.text
    cfg["enabled"] = True                               # all three: open
    for method, path, body in _DEVICE_ROUTES:
        r = _call(h, method, path, body)
        assert r.status_code == 200, (path, r.status_code, r.text)
    # Consent unreadable → fail closed, as no consent — with the stanza off as well.
    import core.consent as consent_mod
    real_is = consent_mod.is_granted
    W._consent_granted = _REAL_CONSENT_GRANTED
    consent_mod.is_granted = lambda *a, **k: (_ for _ in ()).throw(OSError("unreadable"))
    try:
        cfg["channels"]["whatsapp"] = False
        r = _client.get("/device/whatsapp/cursor", headers=h)
        assert r.status_code == 403 and r.json()["detail"] == "no_consent", r.text
    finally:
        consent_mod.is_granted = real_is
    assert W.ChannelOff("channel_off").gate == "no_consent"     # an unknown word fails closed


@check("P2 the run report is stored whole-and-only: unknown keys dropped, received_at the VM's")
def _():
    _sandbox()
    h = _device()
    planted = "PLANTED-RUN-TEXT see you at the usual place"
    r = _client.post("/device/whatsapp/run", headers=h,
                     json={"report": _report(note=planted, extra_field=7), "also": planted})
    assert r.status_code == 200 and r.json() == {"stored": True}, r.text
    stored = W._load_state(None)["run_report"]
    assert set(stored) == set(W.RUN_INT_FIELDS) | {"error", "received_at"}, sorted(stored)
    assert stored["posted_messages"] == 3 and stored["error"] == ""
    datetime.fromisoformat(stored["received_at"])
    assert planted not in _all_files_text() and "extra_field" not in _all_files_text()
    # A second report overwrites the first.
    _client.post("/device/whatsapp/run", headers=h, json={"report": _report(posted_messages=9)})
    assert W._load_state(None)["run_report"]["posted_messages"] == 9


@check("P3 the run report refuses wrong types and bad codes (400), and stores nothing then")
def _():
    _sandbox()
    h = _device()
    bad = [_report(posted_messages=True), _report(base_received="40"),
           _report(inc_received=1.5), _report(rejected=-1), _report(dry_run=2),
           _report(run_at=int(time.time() * 1000)), _report(error="Schema changed"),
           _report(error="a" * 49), _report(error="9lives"), _report(error=None),
           _report(error="PLANTED-CODE-TEXT")]
    for rep in bad:
        r = _client.post("/device/whatsapp/run", headers=h, json={"report": rep})
        assert r.status_code == 400, (rep, r.status_code, r.text)
    for body in ({}, {"report": "text"}, {"report": [1, 2]}):
        assert _client.post("/device/whatsapp/run", headers=h, json=body).status_code == 400
    assert "run_report" not in W._load_state(None)
    assert "PLANTED-CODE-TEXT" not in _all_files_text()
    ok = _client.post("/device/whatsapp/run", headers=h,
                      json={"report": _report(error="share_out_of_step", dry_run=1)})
    assert ok.status_code == 200, ok.text


@check("P4 stale line, 52 h: raised once per onset, cleared by a clean report, raised again")
def _():
    _sandbox()
    t0 = datetime.now().replace(microsecond=0)
    W.record_run(None, {"report": _report()}, now=t0)
    assert not _stale(t0 + timedelta(hours=51))
    first = _stale(t0 + timedelta(hours=53))
    assert len(first) == 1 and t0.strftime("%Y-%m-%d %H:%M") in first[0], first
    assert _stale(t0 + timedelta(hours=53, minutes=10))           # same delivery window
    assert not _stale(t0 + timedelta(hours=53, minutes=31))       # window over
    assert not _stale(t0 + timedelta(hours=80))                   # same onset: never again
    t1 = t0 + timedelta(hours=81)
    W.record_run(None, {"report": _report()}, now=t1)             # clean → the onset ends
    assert not _stale(t1 + timedelta(minutes=1))
    again = _stale(t1 + timedelta(hours=53))                      # a new onset
    assert len(again) == 1 and t1.strftime("%Y-%m-%d %H:%M") in again[0], again
    # Only code-written words: nothing of the report's own values.
    assert "untrusted_content" not in again[0]


@check("P5 stale line, text gone: ≥ 20 received and none with text — once per onset")
def _():
    _sandbox()
    t0 = datetime.now().replace(microsecond=0)
    W.record_run(None, {"report": _report(base_received=19, base_received_text=0,
                                          inc_received=0, inc_received_text=0)}, now=t0)
    assert not _stale(t0 + timedelta(minutes=1))                  # under 20: not a signal
    gone = _report(base_received=15, base_received_text=0, inc_received=5, inc_received_text=0)
    W.record_run(None, {"report": gone}, now=t0 + timedelta(hours=1))
    n1 = t0 + timedelta(hours=1, minutes=1)
    assert _stale(n1) and _stale(n1 + timedelta(minutes=20))
    assert not _stale(n1 + timedelta(minutes=40))
    W.record_run(None, {"report": gone}, now=t0 + timedelta(hours=25))   # still gone: same onset
    assert not _stale(t0 + timedelta(hours=25, minutes=1))
    W.record_run(None, {"report": _report()}, now=t0 + timedelta(hours=26))   # text back
    assert not _stale(t0 + timedelta(hours=26, minutes=1))
    W.record_run(None, {"report": gone}, now=t0 + timedelta(hours=50))
    assert _stale(t0 + timedelta(hours=50, minutes=1))            # a new onset raises again


@check("P6 stale line, a refusal: raised once per onset; the retry-later codes are not refusals")
def _():
    _sandbox()
    t0 = datetime.now().replace(microsecond=0)
    for code in ("being_written", "no_backup_found", "io_error"):
        W.record_run(None, {"report": _report(error=code)}, now=t0)
        assert not _stale(t0 + timedelta(minutes=1)), code
    W.record_run(None, {"report": _report(error="schema_changed")}, now=t0 + timedelta(hours=1))
    n1 = t0 + timedelta(hours=1, minutes=1)
    line = _stale(n1)
    assert len(line) == 1 and t0.strftime("%Y-%m-%d %H:%M") in line[0], line   # since the last clean
    assert not _stale(n1 + timedelta(minutes=31))
    W.record_run(None, {"report": _report(error="post_failed")}, now=t0 + timedelta(hours=25))
    assert not _stale(t0 + timedelta(hours=25, minutes=1))       # another refusal, same onset
    W.record_run(None, {"report": _report()}, now=t0 + timedelta(hours=26))
    assert not _stale(t0 + timedelta(hours=26, minutes=1))
    assert "run_stale" not in W._load_state(None)
    W.record_run(None, {"report": _report(error="key_refused")}, now=t0 + timedelta(hours=30))
    assert _stale(t0 + timedelta(hours=30, minutes=1))


@check("P7 the stale line is silent while the channel is closed (switched off, consent withdrawn)")
def _():
    cfg = _sandbox()
    t0 = datetime.now().replace(microsecond=0)
    W.record_run(None, {"report": _report()}, now=t0)
    cfg["channels"]["whatsapp"] = False
    assert not _stale(t0 + timedelta(hours=60))
    cfg["channels"]["whatsapp"] = True
    _state["consent"] = False
    assert not _stale(t0 + timedelta(hours=60))
    assert "run_stale" not in W._load_state(None)                # nothing consumed meanwhile
    _state["consent"] = True
    assert _stale(t0 + timedelta(hours=60))


@check("P8 any successful revoke and delete-all remove the report: nothing is raised")
def _():
    _sandbox()
    t0 = datetime.now().replace(microsecond=0)
    d1, _t1 = auth.issue_device_token(PERSONA, "phone one")
    d2, _t2 = auth.issue_device_token(PERSONA, "phone two")
    W.record_run(None, {"report": _report(error="schema_changed")}, now=t0)
    assert _stale(t0 + timedelta(minutes=1))                     # the onset is raised
    # A revoke that fails keeps the report.
    r = _client.post("/whatsapp/device/revoke", headers=_admin(), json={"device_id": "no-such"})
    assert r.status_code == 404, r.text
    assert "run_report" in W._load_state(None)
    # Any successful revoke — here with another device still live, as after a re-pair, whose old
    # token is still unrevoked — removes the report and its onset state (F8).
    r = _client.post("/whatsapp/device/revoke", headers=_admin(), json={"device_id": d1})
    assert r.status_code == 200, r.text
    state = W._load_state(None)
    assert not any(k in state for k in W._RUN_KEYS), state
    assert not _stale(t0 + timedelta(hours=60))
    # A genuinely live device re-posts its report at its next run; the line works again.
    W.record_run(None, {"report": _report()}, now=t0)
    assert "run_report" in W._load_state(None)
    r = _client.post("/whatsapp/device/revoke", headers=_admin(), json={"device_id": d2})
    assert r.status_code == 200, r.text
    assert "run_report" not in W._load_state(None)
    # delete-all.
    W.record_run(None, {"report": _report(error="schema_changed")}, now=t0)
    assert _client.post("/whatsapp/delete-all", headers=_admin()).status_code == 200
    assert not W._state_path(None).exists()
    assert not _stale(t0 + timedelta(hours=60))


def _missed(body, h=None):
    return _client.post("/device/whatsapp/missed", headers=h or _device(), json=body)


def _missed_setup() -> dict:
    """One key per outcome: recorded (and re-surfaced, delivered), held back, never received,
    and a clash where the key holds a recorded fact and a re-keyed held-back one."""
    _share()
    t = {"rec": _now_s(25), "held": _now_s(5), "never": _now_s(4), "clash": _now_s(3)}
    _post([_ev(t=t["rec"], text="What time is the party?")])
    _post([_ev(t=t["held"], text="bring the cocaine")])
    _post([_ev(chat=JOANNA, t=t["clash"], text="see you there", source="live")])
    _post([_ev(chat=JOANNA, t=t["clash"], text="bring the cocaine", source="backup")])
    assert W.backstop(None) == 1
    assert W.context_lines(None)
    return {"rec": W.native_key(ANNA, t["rec"], 0), "held": W.native_key(ANNA, t["held"], 0),
            "never": W.native_key(ANNA, t["never"], 0),
            "clash": W.native_key(JOANNA, t["clash"], 0)}


@check("P9 missed: what the VM did with each key — recorded, held back, never received, both")
def _():
    _sandbox()
    k = _missed_setup()
    h = _device()
    out = {}
    for name in ("rec", "held", "never", "clash"):
        r = _missed({"keys": [k[name]]}, h)
        assert r.status_code == 200 and r.json() == {"recorded": 1}, r.text
        out[name] = W._read_jsonl(W._missed_path(None))[-1]["outcomes"][0]
    assert out["rec"]["outcome"] == "recorded", out["rec"]
    rec = out["rec"]["recorded"][0]
    assert rec["category"] == "action_required" and rec["type"] == "question", rec
    assert rec["resurfaced"] and rec["delivered"], rec
    assert out["held"]["outcome"] == "held_back" and out["held"]["held_back"] == ["drugs"], out
    assert out["never"]["outcome"] == "never_received", out["never"]
    assert out["clash"]["outcome"] == "both", out["clash"]             # re-keyed key|fp8 found
    assert out["clash"]["held_back"] == ["drugs"] and len(out["clash"]["recorded"]) == 1
    rep = W.missed_report(None)
    s = rep["single"]
    assert rep["flags"] == 4 and s["never_received"] == 1 and s["both"] == 1, rep
    assert s["held_back"] == {"drugs": 1} and s["recorded"] == {"action_required": 1}, rep
    assert s["resurfaced"] == 1 and s["delivered"] == 1, rep


@check("P10 missed: ambiguous counted once, ambiguous_over and empty apart; > 5 keys and bad "
       "keys → 400; the report prints counts only")
def _():
    _sandbox()
    k = _missed_setup()
    h = _device()
    r = _missed({"keys": [k["rec"], k["held"], k["never"]], "ambiguous": True}, h)
    assert r.json() == {"recorded": 3}, r.text
    row = W._read_jsonl(W._missed_path(None))[-1]
    assert [o["outcome"] for o in row["outcomes"]] == ["recorded", "held_back", "never_received"]
    assert _missed({"keys": [], "ambiguous_over": 9}, h).json() == {"recorded": 0}
    assert _missed({"keys": []}, h).json() == {"recorded": 0}
    for body in ({"keys": [k["never"]] * 2 + [W.native_key(ANNA, _now_s(i), 0)
                                                for i in range(10, 14)]},
                 {"keys": "x"}, {}, {"keys": ["hello there"]}, {"keys": ["a|b|c"]},
                 {"keys": [f"{ANNA}|{int(time.time() * 1000)}|0"]}, {"keys": [7]},
                 {"keys": [k["rec"]], "ambiguous": "yes"},
                 {"keys": [], "ambiguous_over": True}, {"keys": [], "ambiguous_over": -1}):
        r = _missed(body, h)
        assert r.status_code == 400, (body, r.status_code, r.text)
    rep = W.missed_report(None)
    assert (rep["flags"], rep["ambiguous"], rep["ambiguous_over"], rep["not_found"]) == (3, 1, 1, 1)
    assert rep["single"]["never_received"] == 0, rep             # the ambiguous keys not counted
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert W._main(["--missed-report", "--persona", PERSONA]) == 0
    text = buf.getvalue()
    assert "ambiguous (several matches, counted once): 1" in text, text
    assert "more than 5 matches: 1" in text and "no sent copy found on the phone: 1" in text, text
    assert "@" not in text and "|" not in text and "447700" not in text, text


@check("P11 missed flags expire at 90 days, go with purge_chat for that chat, and with delete-all")
def _():
    _sandbox()
    k = _missed_setup()
    h = _device()
    _missed({"keys": [k["rec"]]}, h)                              # Anna only
    _missed({"keys": [k["held"], k["clash"]], "ambiguous": True}, h)   # Anna and Joanna
    _missed({"keys": []}, h)                                      # no chat
    _missed({"keys": [k["clash"]]}, h)                            # Joanna, to be aged out
    rows = W._read_jsonl(W._missed_path(None))
    rows[-1]["at"] = (datetime.now() - timedelta(days=91)).isoformat(timespec="seconds")
    W._write_jsonl(W._missed_path(None), rows)
    W.expire(None)
    rows = W._read_jsonl(W._missed_path(None))
    assert len(rows) == 3, rows
    W.set_share_list(None, {"chats": [{"chat": JOANNA, "kind": "one_to_one",
                                       "label": "Joanna Smith"}]})            # Anna un-shared
    rows = W._read_jsonl(W._missed_path(None))
    assert len(rows) == 2, rows
    assert rows[0]["keys"] == [k["clash"]] and [o["key"] for o in rows[0]["outcomes"]] == [k["clash"]]
    assert rows[1]["keys"] == []
    assert ANNA not in W._missed_path(None).read_text()
    # A merge moves a hidden id's missed keys to the canonical chat, so its purge finds them.
    hidden = "100000000000001@lid"
    _missed({"keys": [W.native_key(hidden, _now_s(1), 0)]}, h)
    W.set_share_list(None, {"chats": [{"chat": JOANNA, "kind": "one_to_one", "label": "Joanna Smith"}],
                            "merges": [{"from": hidden, "to": JOANNA}]})
    assert hidden not in W._missed_path(None).read_text()
    W.set_share_list(None, {"chats": []})
    assert all(not r["keys"] for r in W._read_jsonl(W._missed_path(None)))
    assert _client.post("/whatsapp/delete-all", headers=_admin()).status_code == 200
    assert not W._missed_path(None).exists()


@check("P12 a planted text never appears in any file the channel writes")
def _():
    _sandbox()
    _share()
    h = _device()
    words = ["PLANTED-ALPHA lunch on the terrace?", "PLANTED-BRAVO bring the cocaine",
             "PLANTED-CHARLIE quiet note", "PLANTED-DELTA report", "PLANTED-ECHO missed"]
    t = _now_s(2)
    _client.post("/device/whatsapp/events", headers=h, json={"events": [
        _ev(t=t, text=words[0]), _ev(t=t + 1, text=words[1]),
        _ev(chat=GROUP, sender=BOB, t=t + 2, text=words[2])]})
    _client.post("/device/whatsapp/run", headers=h,
                 json={"report": _report(comment=words[3]), "text": words[3]})
    _client.post("/device/whatsapp/missed", headers=h,
                 json={"keys": [W.native_key(ANNA, t, 0)], "text": words[4], "note": words[4]})
    blob = _all_files_text()
    assert W._missed_path(None).exists() and W._load_state(None).get("run_report")
    for w in words:
        assert w not in blob and w.split()[0] not in blob, w


HIDDEN = "900000000077@lid"


def _merge_setup() -> tuple[int, int]:
    """A chat shared under its hidden id, two messages recorded under it, then the merge night:
    the hidden id posted once more beside the phone-number id, with the merge."""
    W.set_share_list(None, {"chats": [{"chat": HIDDEN, "kind": "one_to_one", "label": ""}]})
    t1, t2 = _now_s(5), _now_s(4)
    out = _post([_ev(chat=HIDDEN, t=t1, text="Dinner tomorrow?"),
                 _ev(chat=HIDDEN, t=t2, text="Lunch on Friday?")])
    assert out["accepted"] == 2, out
    W.set_share_list(None, {"chats": [{"chat": ANNA, "kind": "one_to_one", "label": "Anna Petrova"},
                                      {"chat": HIDDEN, "kind": "one_to_one", "label": ""}],
                            "merges": [{"from": HIDDEN, "to": ANNA}]})
    assert W._load_state(None).get("aliases") == {ANNA: [HIDDEN]}
    return t1, t2


@check("P13 after a merge, the same messages under the new id are duplicates; a change updates")
def _():
    _sandbox()
    t1, t2 = _merge_setup()
    before = {r["id"]: r for r in _records()}
    out = _post([_ev(chat=ANNA, t=t1, text="Dinner tomorrow?"),
                 _ev(chat=ANNA, t=t2, text="Lunch on Friday?")])
    assert out["duplicates"] == 2 and out["accepted"] == 0, out
    assert len(_records()) == 2
    # A changed text, sent as an update under the new id, rewrites the original fact.
    out = _post([_ev(chat=ANNA, t=t2, kind="update", text="Dinner on Saturday at 19:00 at Dishoom?")])
    assert out["updated"] == 1, out
    rows = _records()
    assert len(rows) == 2 and set(r["id"] for r in rows) == set(before), rows
    assert any("Dishoom" in r["subject"] for r in rows), rows
    # The next night the retiring hidden id drops off the list: its alias stays with the chat.
    W.set_share_list(None, {"chats": [{"chat": ANNA, "kind": "one_to_one", "label": "Anna Petrova"}],
                            "merges": []})
    assert W._load_state(None).get("aliases") == {ANNA: [HIDDEN]}
    out = _post([_ev(chat=ANNA, t=t1, text="Dinner tomorrow?")])
    assert out["duplicates"] == 1 and len(_records()) == 2, out
    # Merging the same pair again lists it once.
    state = W._load_state(None)
    W._apply_merges(None, state, [{"from": HIDDEN, "to": ANNA}])
    assert state["aliases"] == {ANNA: [HIDDEN]}, state["aliases"]


@check("P14 a purge of either id clears the alias; delete-all removes it")
def _():
    _sandbox()
    _merge_setup()
    W.purge_chat(None, HIDDEN)                                   # the merged-from id
    assert not (W._load_state(None).get("aliases") or {}), W._load_state(None)
    _sandbox()
    _merge_setup()
    W.set_share_list(None, {"chats": [], "merges": []})          # un-ticking the chat: both ids go
    assert not (W._load_state(None).get("aliases") or {}), W._load_state(None)
    assert not _records()
    _sandbox()
    _merge_setup()
    W.purge_chat(None, ANNA)                                     # the merged-into id
    assert ANNA not in (W._load_state(None).get("aliases") or {})
    _merge_setup()
    W.delete_all(None)
    assert not W._state_path(None).exists()


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
