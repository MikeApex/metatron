"""
tests/test_interview_mode.py — the first interview, in the app (plan § 6.1 item 9).

The whole persona tree (config and data) is a temporary directory, the account store and the
conversation DB are temporary, and no model is called: the interviewer's single-agent run
(`_run_single_agent`) and the pipeline are both stubbed and counted, and the spend gate is
stubbed so no meter file is touched.

Run:
    python -m pytest -q tests/test_interview_mode.py
    python tests/test_interview_mode.py
"""

import asyncio
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-interview")

from fastapi.testclient import TestClient  # noqa: E402

from core import accounts, auth, interview, persona as persona_mod  # noqa: E402
from core import orchestrator, server  # noqa: E402

from core import trace as trace_mod  # noqa: E402

_tmp = Path(tempfile.mkdtemp(prefix="metatron-interview-"))
CONSENT = {"scope": "base_configuration", "text_version": "v1"}

client = TestClient(server.app, base_url="https://testserver")

# --- the stubs ------------------------------------------------------------------------

CALLS: list[dict] = []          # every interviewer run: agent, input, history
NEXT_REPLY = {"text": "Tell me about your days.", "side_effect": None}
PIPELINE_CALLS: list[str] = []


def _fake_single_agent(agent_name, user_input, persona=None, history=None, **kw):
    CALLS.append({"agent": agent_name, "input": user_input, "history": list(history or [])})
    if NEXT_REPLY["side_effect"]:
        NEXT_REPLY["side_effect"](persona)
    return NEXT_REPLY["text"]


def _fake_pipeline(user_input, **kw):
    PIPELINE_CALLS.append(user_input)
    yield "pipeline reply"


# Every module that builds a persona path from its own idea of the repo root is pointed at
# the temp tree — persona helpers, the trace writer, the account store's name check — and the
# model and pipeline are stubbed. Applied when this file's tests start and undone when they
# end: done at import, these leaked into every other test file in one pytest process.
_PATCHES = [
    (persona_mod, "_ROOT", _tmp), (trace_mod, "ROOT", _tmp), (accounts, "_ROOT", _tmp),
    (accounts, "ACCOUNTS_PATH", _tmp / "accounts" / "accounts.json"),
    (orchestrator, "_run_single_agent", _fake_single_agent),
    (orchestrator, "_spend_gate", lambda: None),
    (server, "run_pipeline_session_stream", _fake_pipeline),
]
_SAVED: list = []


def setup_module(module=None):
    for obj, name, value in _PATCHES:
        _SAVED.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)


def teardown_module(module=None):
    while _SAVED:
        obj, name, value = _SAVED.pop()
        setattr(obj, name, value)


def _own_db():
    server.DB_PATH = _tmp / "metatron.db"
    asyncio.run(server._init_db())


def _new_user(name: str) -> str:
    """An approved account with a not_started interview — what `approve` leaves behind."""
    accounts.register(name, name.title(), f"{name}-password-1", "Europe/London", CONSENT)
    entry = accounts.update(name, status="active")
    cfg = _tmp / "config" / "personas" / name
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "goals.yaml").write_text("quarterly: []\nweekly: []\ndaily: []\n")
    for f in ("mission.md", "prime_directive.md"):
        (cfg / f).write_text("<!-- Populated by the Goals Interview. Do not fill in speculatively. -->\n")
    state = _tmp / "data" / "personas" / name / "interview" / "state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"status": "not_started"}))
    return auth.issue_token(persona=name, role="user", cred_version=entry["cred_version"])


def _drain(ws, until: str, limit: int = 20) -> list[dict]:
    seen = []
    for _ in range(limit):
        msg = ws.receive_json()
        seen.append(msg)
        if msg.get("type") == until:
            return seen
    raise AssertionError(f"never saw {until}: {seen}")


def _connect(token: str):
    ws = client.websocket_connect("/ws").__enter__()
    ws.send_json({"type": "auth", "token": token})
    assert ws.receive_json()["type"] == "auth_ok"
    return ws


def _wait_for_interview_calls(n: int, timeout: float = 5.0):
    import time
    end = time.time() + timeout
    while time.time() < end and len(CALLS) < n:
        time.sleep(0.02)


# --- tests ----------------------------------------------------------------------------

def test_no_state_file_means_no_interview_ever():
    """Every existing persona — Mike, the test personas — has no file and is never held."""
    assert interview.status("zz_nobody") is None
    assert not interview.holds_proactive("zz_nobody")


def test_start_claimed_once_across_a_reconnect_race():
    _own_db()
    _new_user("zz_race")
    results = []
    threads = [threading.Thread(target=lambda: results.append(interview.claim_start("zz_race")))
               for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1 and interview.status("zz_race") == "active"


def test_first_connection_opens_the_interview_once():
    _own_db()
    CALLS.clear()
    token = _new_user("zz_open")
    ws1 = _connect(token)
    ws2 = _connect(token)                 # a second device / a reconnect
    _wait_for_interview_calls(1)
    seen = _drain(ws1, "message")
    opening = [m for m in seen if m.get("type") == "message"][0]
    assert opening["proactive"] is True and opening["user"] == ""
    assert len(CALLS) == 1 and CALLS[0]["agent"] == "goals_interviewer"
    assert interview.OPENING_PROMPT in CALLS[0]["input"]
    assert "INTERVIEW COVERAGE" in CALLS[0]["input"]
    ws1.__exit__(None, None, None)
    ws2.__exit__(None, None, None)


def test_active_message_goes_to_the_interviewer_with_full_history():
    _own_db()
    CALLS.clear()
    PIPELINE_CALLS.clear()
    token = _new_user("zz_talk")
    ws = _connect(token)
    _wait_for_interview_calls(1)
    _drain(ws, "message")                 # the opening
    for i, text in enumerate(("I'm up at six", "I work until five")):
        ws.send_json({"type": "send", "exchange_id": f"x{i}", "input": text})
        _drain(ws, "done")
    assert PIPELINE_CALLS == [], "an active interview must never reach the pipeline"
    last = CALLS[-1]
    contents = [m["content"] for m in last["history"]]
    assert "I'm up at six" in contents, "the interviewer gets the whole interview as history"
    assert "I work until five" in last["input"]
    ws.__exit__(None, None, None)


def test_pause_routes_back_to_the_pipeline_and_resume_returns():
    _own_db()
    CALLS.clear()
    PIPELINE_CALLS.clear()
    token = _new_user("zz_pause")
    ws = _connect(token)
    _wait_for_interview_calls(1)
    _drain(ws, "message")
    r = client.post("/interview/pause", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and interview.status("zz_pause") == "paused"
    ws.send_json({"type": "send", "exchange_id": "p1", "input": "what's the weather"})
    _drain(ws, "done")
    assert PIPELINE_CALLS == ["what's the weather"]
    n = len(CALLS)
    r = client.post("/interview/resume", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and interview.status("zz_pause") == "active"
    _wait_for_interview_calls(n + 1)
    assert len(CALLS) == n + 1, "resuming lets the interviewer speak first"
    ws.__exit__(None, None, None)


def test_pause_tool_and_another_users_routes():
    _own_db()
    token_a = _new_user("zz_ta")
    _new_user("zz_tb")
    interview.claim_start("zz_ta")
    with persona_mod.persona_scope("zz_ta"):
        assert "Paused" in interview.pause_interview()
    assert interview.status("zz_ta") == "paused"
    r = client.post("/interview/resume", json={"persona": "zz_tb"},
                    headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 403


def test_coverage_reflects_what_is_stored():
    _new_user("zz_cov")
    block = interview.coverage_block("zz_cov")
    assert "Mission: not yet" in block and "Prime directive: not yet" in block
    (_tmp / "config/personas/zz_cov/mission.md").write_text("To build things that last.\n")
    (_tmp / "config/personas/zz_cov/goals.yaml").write_text(
        "quarterly:\n  - {shareable_what: run a 10k}\nweekly: []\ndaily: []\n")
    block = interview.coverage_block("zz_cov")
    assert "Mission: written" in block and "quarterly 1" in block
    assert "location_sharing" not in block, "plain words only — see _SHAPE_SECTIONS"


def test_filter_suppresses_a_leak_in_an_interviewer_reply():
    _new_user("zz_leak")
    interview.claim_start("zz_leak")
    NEXT_REPLY["text"] = "Sure — I'll call write_config and run_subagent for that."
    try:
        reply = interview.run_turn("zz_leak", "hello", [])
    finally:
        NEXT_REPLY["text"] = "Tell me about your days."
    assert "write_config" not in reply and "run_subagent" not in reply


def _raise_mission_card(persona):
    from tools.config_writer import write_config
    with persona_mod.persona_scope(persona):
        result = write_config("mission.md", "To live deliberately.")
    assert "PENDING" in json.dumps(result).upper() or "confirm" in json.dumps(result).lower()


def test_pending_write_is_never_reported_as_done():
    """Review L1: a card she has never seen is not 'recorded'."""
    _new_user("zz_pend")
    interview.claim_start("zz_pend")
    NEXT_REPLY.update(text="Lovely — I've recorded your mission.", side_effect=_raise_mission_card)
    try:
        reply = interview.run_turn("zz_pend", "my mission is to live deliberately", [])
    finally:
        NEXT_REPLY.update(text="Tell me about your days.", side_effect=None)
    assert "Waiting for your approval in the app" in reply
    assert "I've recorded your mission" not in reply
    assert "awaiting her confirmation" in interview.coverage_block("zz_pend")
    with persona_mod.persona_scope("zz_pend"):
        refusal = interview.finish_interview()
    assert refusal.startswith("Not finished") and interview.status("zz_pend") == "active"


def test_finish_completes_and_routes_back():
    _new_user("zz_done")
    interview.claim_start("zz_done")
    with persona_mod.persona_scope("zz_done"):
        assert "complete" in interview.finish_interview().lower()
    assert interview.status("zz_done") == "complete"
    assert not interview.holds_proactive("zz_done")


def test_config_words_count_only_for_a_config_card():
    """Stage 2 review F3: an honest draft reply to a send_email card is kept, not replaced."""
    honest = "I've written the email — it's waiting for your approval."
    out = orchestrator.enforce_pending_receipt(honest, [{"action": "send_email"}])
    assert out.startswith(honest), out
    false = "Lovely — I've recorded your mission."
    out = orchestrator.enforce_pending_receipt(false, [{"action": "write_config"}])
    assert "recorded your mission" not in out


def test_failed_opening_is_released_for_a_retry():
    """Stage 2 review F4: no active interview left with no first message."""
    _new_user("zz_fail")
    assert interview.claim_start("zz_fail")
    assert interview.release_start("zz_fail") and interview.status("zz_fail") == "not_started"
    assert interview.claim_start("zz_fail")
    interview.count_turn("zz_fail")
    assert not interview.release_start("zz_fail"), "never rewinds a conversation under way"


def test_old_session_routes_are_not_a_side_door():
    """Stage 2 review F2."""
    token = _new_user("zz_side")
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/session", json={"input": "hi", "agent": "tone_profiler"}, headers=h)
    assert r.status_code == 403
    interview.claim_start("zz_side")
    for path in ("/session", "/session/stream"):
        r = client.post(path, json={"input": "hi", "agent": "coordinator"}, headers=h)
        assert r.status_code == 409, (path, r.status_code)


def test_only_the_account_holder_grants_a_permission():
    """Stage 2 review F6: a record that says she tapped cannot be written by an admin token."""
    token = _new_user("zz_grant")
    admin = auth.issue_token(persona="zz_grant", role="admin")
    body = {"text_version": "v1"}
    r = client.post("/consents/tone_profile", json=body, headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 403
    r = client.post("/consents/tone_profile", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_history_is_trimmed_to_budget_on_whole_pairs():
    big = "x" * 100_000
    pairs = []
    for i in range(6):
        pairs += [{"role": "user", "content": big}, {"role": "assistant", "content": f"a{i}"}]
    kept = interview.trim_history(pairs)
    assert sum(len(m["content"]) for m in kept) <= interview.HISTORY_CHAR_BUDGET
    assert kept[0]["role"] == "user" and kept[-1]["content"] == "a5"


if __name__ == "__main__":
    setup_module()
    failures = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc!r}")
    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    sys.exit(1 if failures else 0)
