"""
tests/test_med_critical_scheduled_thread.py — Mike's ruling (2026-11-24, Stage 5 review round 3):
on a scheduled turn (no user words) a MEDICATION_MISSED_CRITICAL clinical thread may open and
escalate; every other clinical-thread write on such a turn stays refused (the 10-29 rule and
Mental Wellbeing's re-raise protection unchanged). tools/context_tracker._clinical_merge_for_write.

Offline: a temp tracker, the escalation inbox stubbed.

    python3 tests/test_med_critical_scheduled_thread.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import core.trace as _tr  # noqa: E402
import tools.context_tracker as ct  # noqa: E402


@contextmanager
def tracker():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        path = tmp_path / "context.json"
        path.write_text(json.dumps({"last_session": "2026-01-02", "clinical_threads": []}))
        with mock.patch.object(ct, "persona_data_dir", lambda *a, **k: tmp_path), \
                mock.patch("tools.obligations.consult_index", lambda *a, **k: []):
            yield path


@contextmanager
def scheduled():
    _tr.start_request_trace("morning brief", None, is_proactive=True)
    try:
        yield
    finally:
        _tr.set_trace(None)
        _tr._set_current_agent(None)


def _flags(path):
    return {t["flag"]: t for t in json.loads(path.read_text()).get("clinical_threads") or []}


def test_scheduled_med_critical_opens_and_escalates():
    calls = []
    with tracker() as path, scheduled(), \
            mock.patch.object(ct, "_thread_tier",
                              lambda flag: 2 if flag.startswith("MEDICATION_MISSED_CRITICAL") else 1), \
            mock.patch("tools.escalation.raise_escalation", lambda flag, **kw: calls.append(flag)):
        out = ct.merge_pattern_findings(patterns=[], clinical_threads=[
            {"flag": "MEDICATION_MISSED_CRITICAL: Lithium", "status": "active", "note": "missed"}])
        flags = _flags(path)
    assert "MEDICATION_MISSED_CRITICAL: Lithium" in flags, flags
    assert flags["MEDICATION_MISSED_CRITICAL: Lithium"]["raised"] == date.today().isoformat()
    assert calls == ["MEDICATION_MISSED_CRITICAL: Lithium"], calls
    assert "scheduled session" not in out, out


def test_scheduled_bare_med_critical_opens_through_the_session_writer_too():
    with tracker() as path, scheduled():
        ct.write_context_tracker(open_threads=[], patterns=[], follow_ups=[], clinical_threads=[
            {"flag": "MEDICATION_MISSED_CRITICAL", "status": "active"}])
        assert "MEDICATION_MISSED_CRITICAL" in _flags(path)


def test_scheduled_clinical_concern_from_mental_wellbeing_still_refused():
    calls = []
    with tracker() as path, scheduled(), \
            mock.patch("tools.escalation.raise_escalation", lambda flag, **kw: calls.append(flag)):
        out = ct.merge_pattern_findings(patterns=[], clinical_threads=[
            {"flag": "CLINICAL_CONCERN: LOW_MOOD", "status": "active"}])
        flags = _flags(path)
    assert flags == {}, flags
    assert not calls and "scheduled session" in out, (calls, out)


def test_scheduled_mixed_write_keeps_only_the_med_critical_thread():
    with tracker() as path, scheduled():
        out = ct.merge_pattern_findings(patterns=[], clinical_threads=[
            {"flag": "MEDICATION_MISSED_CRITICAL: Insulin", "status": "active"},
            {"flag": "CLINICAL_CONCERN: LOW_MOOD", "status": "active"},
            {"flag": "MUST_SURFACE: X", "status": "active"}])
        flags = _flags(path)
    assert set(flags) == {"MEDICATION_MISSED_CRITICAL: Insulin"}, flags
    assert "scheduled session" in out


def test_a_user_turn_is_unchanged():
    with tracker() as path, mock.patch("tools.escalation.raise_escalation", lambda *a, **k: None):
        ct.merge_pattern_findings(patterns=[], clinical_threads=[
            {"flag": "CLINICAL_CONCERN: LOW_MOOD", "status": "active"}])
        assert "CLINICAL_CONCERN: LOW_MOOD" in _flags(path)


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures.append(name)
                print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print("\n" + (f"{len(failures)} failed" if failures else "all passed"))
    sys.exit(1 if failures else 0)
