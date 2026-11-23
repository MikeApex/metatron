"""
tests/test_routing_miss_block.py — reporting a routing miss no longer costs the Synthesizer an
extra model round (Stage 2 M11): it rides the [CONTEXT] block as `routing_miss`, parsed in code.

Tmp logs and tracker dirs; no model, no network.

Run:  python3 tests/test_routing_miss_block.py   (or pytest)
"""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as orch  # noqa: E402
import core.trace as _tr  # noqa: E402
import tools.context_tracker as ct  # noqa: E402
import tools.logger as logger_mod  # noqa: E402
from tools import turn_context as _turn  # noqa: E402


@contextmanager
def dirs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with mock.patch.object(logger_mod, "_logs_dir", return_value=tmp_path), \
                mock.patch.object(ct, "persona_data_dir", lambda *a, **k: tmp_path), \
                mock.patch("tools.obligations.consult_index", lambda *a, **k: []):
            yield tmp_path


def _events(tmp: Path) -> list[dict]:
    p = tmp / "quality_events.json"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def _block(routing_miss, **extra) -> dict:
    return {"open_threads": [], "patterns": [], "follow_ups": [],
            "routing_miss": routing_miss, **extra}


def test_case1_dict_writes_one_event():
    with dirs() as tmp:
        orch.persist_context_block(_block({"agent": "Physical Health",
                                           "detail": "chest tightness was not routed"}))
        ev = _events(tmp)
    assert len(ev) == 1 and ev[0]["event_type"] == "ROUTING_MISS"
    assert ev[0]["source_agent"] == "physical_health"
    assert ev[0]["detail"] == "chest tightness was not routed"


def test_case2_list_becomes_one_joined_event():
    with dirs() as tmp:
        orch.persist_context_block(_block([
            {"agent": "logistics", "detail": "the train time"},
            {"agent": "finance", "detail": "the refund amount"}]))
        ev = _events(tmp)
    assert len(ev) == 1
    assert ev[0]["source_agent"] == "logistics,finance"
    assert ev[0]["detail"] == "the train time; the refund amount"


def test_case3_empty_shapes_write_nothing():
    with dirs() as tmp:
        for value in (None, {}, "none", {"agent": "logistics"}, {"agent": "x", "detail": "N/A"}):
            orch.persist_context_block(_block(value))
        assert _events(tmp) == []


def test_case4_success_claim_refused_without_escaping():
    with dirs() as tmp:
        orch.persist_context_block(_block({
            "agent": "logistics", "detail": "Routed the calendar request correctly."}))
        assert _events(tmp) == []


def test_case5_no_words_turn_tagged():
    with dirs() as tmp, _turn.turn_scope(user_turn=False):
        orch.persist_context_block(_block({"agent": "logistics", "detail": "missed the trip"}))
        ev = _events(tmp)
    assert len(ev) == 1 and ev[0]["scheduled"] is True


def test_case5b_clarify_hold_writes_nothing():
    with dirs() as tmp, _turn.turn_scope(user_turn=True) as turn:
        turn["clarify_hold"] = True
        orch.persist_context_block(_block({"agent": "logistics", "detail": "missed the trip"}))
        assert _events(tmp) == []


def test_case6_deduped_against_coordinator_event():
    _tr.start_request_trace("x", None)
    try:
        with dirs() as tmp:
            logger_mod.write_quality_event("ROUTING_MISS", "coordinator", "coordinator caught it")
            orch.persist_context_block(_block({"agent": "logistics", "detail": "same signal"}))
            ev = _events(tmp)
    finally:
        _tr.set_trace(None)
    assert [e["detail"] for e in ev] == ["coordinator caught it"]


def test_case7_salvaged_from_malformed_block():
    raw = ('{"open_threads": ["a", "b",}, "patterns": [oops], '
           '"routing_miss": {"agent": "logistics", "detail": "the ferry"}')
    parsed, how = orch._repair_context_json(raw)
    assert parsed and parsed.get("routing_miss") == {"agent": "logistics", "detail": "the ferry"}
    with dirs() as tmp:
        orch.persist_context_block(parsed)
        ev = _events(tmp)
    assert len(ev) == 1 and ev[0]["detail"] == "the ferry"
    assert "routing_miss" in orch._CONTEXT_KEYS


def test_case8_tracker_and_dev_request_unaffected_by_failure():
    with dirs() as tmp, mock.patch.object(logger_mod, "write_quality_event",
                                          side_effect=_explode_on_routing_miss):
        orch.persist_context_block(_block(
            {"agent": "logistics", "detail": "x"}, follow_ups=["keep me"],
            dev_request={"type": "FEATURE_REQUEST", "detail": "a real feature"}))
        tracker = json.loads((tmp / "context.json").read_text())
    assert tracker["follow_ups"] == ["keep me"]
    assert _DEV_SEEN == ["FEATURE_REQUEST"]


_DEV_SEEN: list[str] = []


def _explode_on_routing_miss(event_type="", **kw):
    if event_type == "ROUTING_MISS":
        raise RuntimeError("boom")
    _DEV_SEEN.append(event_type)
    return "ok"


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
