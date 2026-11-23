"""
tests/test_pattern_miner_tracker_merge.py — the weekly Pattern Miner run no longer wipes the
session's follow-ups, held items and open threads (Stage 2 M6, 2026-11-23).

The `write_context_tracker` TOOL used to call the replace-semantics writer, so Pattern Miner —
which had to send `open_threads` and `follow_ups` and naturally sent them empty — erased what
the Synthesizer had kept. The tool now maps to `merge_pattern_findings`: it adds to `patterns`
and records clinical threads through the same add-only helper the session writer uses.

Tmp persona dir; no model, no network.

Run:  python3 tests/test_pattern_miner_tracker_merge.py   (or pytest)
"""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import core.trace as _tr  # noqa: E402
import tools.context_tracker as ct  # noqa: E402

OLD = (date.today() - timedelta(days=2)).isoformat()

SEED = {
    "last_session": "2026-01-02",
    "open_threads": [{"text": "chase the plumber quote", "added": OLD},
                     {"text": "bookstore numbers review", "added": OLD}],
    "patterns": ["writing stalls when sleep is short"],
    "follow_ups": ["ask how the chapter went"],
    "held_items": ["Held: SLEEP_POOR — surface when mood lifts"],
    "clinical_threads": [{"flag": "MEDICATION_MISSED_CRITICAL", "tier": 1, "raised": OLD,
                          "status": "watch", "last_surfaced": OLD, "note": "seeded"}],
    "expired_open_threads": [{"text": "old thing", "added": OLD, "expired_on": OLD}],
    "asked_questions": [{"text": "q?", "asks": 1}],
    "scheduled_runs": {"morning_brief": {"last": OLD}},
}


@contextmanager
def tracker(seed: dict | None = SEED, raw: str | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        path = tmp_path / "context.json"
        if raw is not None:
            path.write_text(raw)
        elif seed is not None:
            path.write_text(json.dumps(seed))
        with mock.patch.object(ct, "persona_data_dir", lambda *a, **k: tmp_path), \
                mock.patch("tools.obligations.consult_index", lambda *a, **k: []):
            yield path


@contextmanager
def trace(proactive: bool):
    _tr.start_request_trace("x", None, is_proactive=proactive)
    try:
        yield
    finally:
        _tr.set_trace(None)
        _tr._set_current_agent(None)


def _handler():
    _, handlers = orch.register_tools()
    return handlers["write_context_tracker"]


def _wipe_call(**extra):
    return dict(open_threads=[], follow_ups=[], held_items=[], patterns=["p-new"], **extra)


def test_registered_handler_is_merge():
    assert _handler() is ct.merge_pattern_findings


def test_case1_session_fields_survive():
    with tracker() as path:
        out = _handler()(**_wipe_call())
        data = json.loads(path.read_text())
    for key in ("open_threads", "follow_ups", "held_items", "clinical_threads"):
        assert data[key] == SEED[key], key
    assert data["patterns"] == SEED["patterns"] + ["p-new"]
    assert "1 added" in out and "not changed" in out


def test_case1b_clinical_thread_added_and_escalated():
    calls = []
    with tracker() as path, trace(proactive=False), \
            mock.patch("tools.escalation.raise_escalation",
                       lambda flag, **kw: calls.append(flag)):
        _handler()(**_wipe_call(clinical_threads=[
            {"flag": "CLINICAL_CONCERN: TEST_SIGNAL", "status": "active", "note": "n"}]))
        data = json.loads(path.read_text())
    flags = {t["flag"]: t for t in data["clinical_threads"]}
    assert "CLINICAL_CONCERN: TEST_SIGNAL" in flags
    assert flags["CLINICAL_CONCERN: TEST_SIGNAL"]["raised"] == date.today().isoformat()
    assert "MEDICATION_MISSED_CRITICAL" in flags          # carried forward
    assert calls == ["CLINICAL_CONCERN: TEST_SIGNAL"]


def test_case1c_scheduled_turn_writes_no_thread():
    with tracker() as path, trace(proactive=True):
        out = _handler()(**_wipe_call(clinical_threads=[
            {"flag": "CLINICAL_CONCERN: TEST_SIGNAL", "status": "active"}]))
        data = json.loads(path.read_text())
    assert data["clinical_threads"] == SEED["clinical_threads"]
    assert "scheduled session" in out


def test_case1d_same_clinical_result_both_writers():
    incoming = [{"flag": "MUST_SURFACE: TEST", "status": "active", "note": "x"},
                {"flag": "MEDICATION_MISSED_CRITICAL", "status": "resolved"}]
    with tracker() as path:
        ct.merge_pattern_findings(patterns=[], clinical_threads=incoming)
        merged = json.loads(path.read_text())["clinical_threads"]
    with tracker() as path:
        ct.write_context_tracker(open_threads=[], patterns=[], follow_ups=[],
                                 clinical_threads=incoming)
        replaced = json.loads(path.read_text())["clinical_threads"]
    assert merged == replaced


def test_case1e_held_items_dict_shape_byte_identical():
    seed = {**SEED, "held_items": [{"text": "Held: a thing", "held_since": OLD}]}
    with tracker(seed) as path:
        _handler()(**_wipe_call())
        data = json.loads(path.read_text())
    assert json.dumps(data["held_items"]) == json.dumps(seed["held_items"])


def test_case2_duplicate_pattern_not_added():
    with tracker() as path:
        ct.merge_pattern_findings(patterns=["  Writing   stalls when SLEEP is short "])
        data = json.loads(path.read_text())
    assert data["patterns"] == SEED["patterns"]


def test_case3_last_session_unchanged():
    with tracker() as path:
        ct.merge_pattern_findings(patterns=["p"])
        assert json.loads(path.read_text())["last_session"] == SEED["last_session"]


def test_case4_carried_keys_survive():
    with tracker() as path:
        ct.merge_pattern_findings(patterns=["p"])
        data = json.loads(path.read_text())
    assert data["asked_questions"] == SEED["asked_questions"]
    assert data["scheduled_runs"] == SEED["scheduled_runs"]
    assert data["expired_open_threads"] == SEED["expired_open_threads"]


def test_case5_corrupt_file_not_overwritten():
    with tracker(raw="{not json") as path:
        out = ct.merge_pattern_findings(patterns=["p"])
        assert path.read_text() == "{not json"
    assert "unreadable" in out and "nothing written" in out


def test_case6_schema_requires_patterns_only():
    schema = ct.WRITE_CONTEXT_TRACKER_SCHEMA["input_schema"]
    assert schema["required"] == ["patterns"]
    for key in ("open_threads", "follow_ups", "held_items", "clinical_threads"):
        assert key in schema["properties"]


def test_case7_session_writer_still_replaces():
    with tracker() as path:
        orch.persist_context_block({"open_threads": [], "patterns": [],
                                    "follow_ups": ["new follow-up"]})
        data = json.loads(path.read_text())
    assert data["follow_ups"] == ["new follow-up"]


def test_case8_through_dispatch_tool_as_pattern_miner():
    rec = _tr.AgentRecord(agent="pattern_miner", provider="", model="")
    _, handlers = orch.register_tools()
    with tracker() as path:
        orch.dispatch_tool("write_context_tracker", _wipe_call(), handlers, _agent_rec=rec)
        data = json.loads(path.read_text())
    for key in ("open_threads", "follow_ups", "held_items", "clinical_threads"):
        assert data[key] == SEED[key], key
    assert data["patterns"] == SEED["patterns"] + ["p-new"]
    assert rec.turns[0].tool_calls[0].ok is True


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"  FAIL  {name} — {type(exc).__name__}: {exc}")
    print(f"\n{'all passed' if not failures else f'{failures} failed'}")
    sys.exit(1 if failures else 0)
