"""
tests/test_no_user_words_events.py — "user corrected me" events stop being filed from turns
where the user said nothing (Stage 2 #1, [DB-0902-01], D-S2-1 option 3).

On a turn with no user words, USER_CORRECTION, INSTRUCTION_CHANGE_REQUEST, FEATURE_REQUEST and
SELF_APPLIED are refused; ROUTING_MISS is written tagged `"scheduled": true` and skipped by
both readers that count it (the backlog sync and Build's REPAIR count).

Tmp logs dir; no model, no network.

Run:  python3 tests/test_no_user_words_events.py   (or pytest)
"""

from __future__ import annotations

import inspect
import json
import sys
import tempfile
import threading
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import core.orchestrator as orch  # noqa: E402
import core.trace as _tr  # noqa: E402
import tools.logger as logger_mod  # noqa: E402
from tools import turn_context as _turn  # noqa: E402

REFUSED = ("USER_CORRECTION", "INSTRUCTION_CHANGE_REQUEST", "FEATURE_REQUEST", "SELF_APPLIED")


@contextmanager
def logs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with mock.patch.object(logger_mod, "_logs_dir", return_value=tmp_path):
            yield tmp_path / "quality_events.json"


def _events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write(event_type: str):
    return logger_mod.write_quality_event(event_type, "coordinator",
                                          f"a real detail for {event_type.lower()}")


def test_case1_refused_on_no_words_turn():
    with logs() as path, _turn.turn_scope(user_turn=False):
        for t in REFUSED:
            try:
                _write(t)
            except ValueError as exc:
                assert "no words from the user" in str(exc)
            else:
                raise AssertionError(f"{t} was not refused")
        assert _events(path) == []


def test_case2_routing_miss_tagged_scheduled():
    with logs() as path, _turn.turn_scope(user_turn=False):
        _write("ROUTING_MISS")
        ev = _events(path)
    assert len(ev) == 1 and ev[0]["scheduled"] is True


def test_case3_user_turn_writes_all_untagged():
    with logs() as path, _turn.turn_scope(user_turn=True):
        for t in REFUSED + ("ROUTING_MISS",):
            _write(t)
        ev = _events(path)
    assert [e["event_type"] for e in ev] == list(REFUSED) + ["ROUTING_MISS"]
    assert all("scheduled" not in e for e in ev)


def test_case4_no_turn_no_trace_untagged():
    assert _turn.current() is None and _tr.get_trace() is None
    with logs() as path:
        _write("USER_CORRECTION")
        _write("ROUTING_MISS")
        ev = _events(path)
    assert len(ev) == 2 and all("scheduled" not in e for e in ev)


def test_case5_proactive_trace_without_turn():
    _tr.start_request_trace("weekly", None, is_proactive=True)
    try:
        with logs() as path:
            for t in REFUSED:
                try:
                    _write(t)
                    raise AssertionError(f"{t} not refused")
                except ValueError:
                    pass
            _write("ROUTING_MISS")
            ev = _events(path)
    finally:
        _tr.set_trace(None)
    assert len(ev) == 1 and ev[0]["scheduled"] is True


def test_case6_code_written_types_untouched():
    with logs() as path, _turn.turn_scope(user_turn=False):
        _write("CONTEXT_BLOCK_UNPARSED")
        _write("FALSE_ACTION_CLAIM")
        ev = _events(path)
    assert len(ev) == 2 and all("scheduled" not in e for e in ev)


def test_case7_worker_thread_adopts_no_words_turn():
    out: dict = {}
    with logs() as path, _turn.turn_scope(user_turn=False):
        parent = _turn.current()

        def _worker():
            _turn.adopt(parent)
            try:
                _write("USER_CORRECTION")
                out["refused"] = False
            except ValueError:
                out["refused"] = True
            _write("ROUTING_MISS")

        t = threading.Thread(target=_worker)
        t.start()
        t.join()
        ev = _events(path)
    assert out["refused"] is True
    assert len(ev) == 1 and ev[0]["scheduled"] is True


def test_case8_handle_user_correction_no_words():
    pkg = "USER_CORRECTION: the user said the name was wrong\n"
    with logs() as path, mock.patch.object(orch, "_corrected_agents",
                                           side_effect=AssertionError("scanned")), \
            mock.patch.object(orch.logger, "warning") as warn:
        orch._handle_user_correction(pkg, None, user_turn=False)
        assert _events(path) == []
        assert not warn.called


def test_case9_sync_fetch_events_skips_tagged():
    import sync_dev_backlog as S
    lines = [
        json.dumps({"event_type": "ROUTING_MISS", "detail": "missed a health signal",
                    "scheduled": True}),
        json.dumps({"event_type": "ROUTING_MISS", "detail": "missed a calendar signal"}),
    ]
    with mock.patch.object(S, "_get_json", return_value={"content": "\n".join(lines)}):
        got = S.fetch_events("http://stub", "zz_test")
    assert [e["detail"] for e in got] == ["missed a calendar signal"]


def test_case10_build_count_faults_skips_tagged():
    from core.build import tick
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    rows = ([{"timestamp": now, "event_type": "ROUTING_MISS", "source_agent": "zz_cap",
              "detail": "d", "scheduled": True}] * 3
            + [{"timestamp": now, "event_type": "ROUTING_MISS", "source_agent": "zz_cap",
                "detail": "d"}] * 2)
    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = Path(tmp) / "logs"
        logs_dir.mkdir()
        (logs_dir / "quality_events.json").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n")
        with mock.patch("core.persona.persona_data_dir", lambda *a, **k: Path(tmp)):
            counts, _ = tick._count_faults("zz_test", {"zz_cap"}, lambda e: "sig")
    assert counts == Counter({"zz_cap|sig": 2})


def test_case11_both_twins_pass_user_turn():
    for fn in (orch.run_pipeline_session, orch._run_pipeline_session_stream_inner):
        src = inspect.getsource(fn)
        assert "_handle_user_correction(coord_output, persona,\n" in src, fn.__name__
        assert "user_turn=has_real_user_turn(user_input, is_proactive, attachments))" in src


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
