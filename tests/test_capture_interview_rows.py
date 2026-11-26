"""
tests/test_capture_interview_rows.py — the interview path writes a `turn` row for a persona
that is not `mike` (live 2026-11-26: a second user's six interview turns left no outcomes.jsonl).

The REAL `capture.extract` runs; only the model call (`run_session`) and the spend gate are
stubbed, so the extractor's own path — persona scope, trace, data-dir resolution, parse — is
exercised, in a thread, exactly as `core.interview.run_turn` starts it.

Run:
    python -m pytest -q tests/test_capture_interview_rows.py
    python tests/test_capture_interview_rows.py
"""

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core import interview, orchestrator, persona as persona_mod  # noqa: E402
from core import trace as trace_mod  # noqa: E402
from tools import analytics, capture  # noqa: E402

_tmp = Path(tempfile.mkdtemp(prefix="metatron-capture-rows-"))
P = "iva_test"
CFG = {**capture._DEFAULTS, "enabled": True, "holdout_rate": 0.0, "join_bound_s": 0.5,
       "modes": {"synthesizer": "shadow", "goals_interviewer": "on"}}
_REAL_CONFIG = capture.config
DELAY = {"s": 0.0}


def _fake_run_session(agent, user_input="", persona=None, history=None, **kw):
    if agent == capture.AGENT:
        time.sleep(DELAY["s"])
        return "[]"
    return "Thanks, tell me more."


_PATCHES = [
    (persona_mod, "_ROOT", _tmp), (trace_mod, "ROOT", _tmp), (analytics, "ROOT", _tmp),
    (capture, "config", lambda: dict(CFG)),
    (capture, "_within_spend", lambda: True),
    (orchestrator, "run_session", _fake_run_session),
    (orchestrator, "_spend_gate", lambda: None),
]
_SAVED: list = []


def setup_module(module=None):
    for obj, name, value in _PATCHES:
        _SAVED.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)
    (_tmp / "config" / "personas" / P).mkdir(parents=True, exist_ok=True)
    (_tmp / "config" / "personas" / P / "goals.yaml").write_text("quarterly: []\n")
    (_tmp / "data" / "personas" / P).mkdir(parents=True, exist_ok=True)


def teardown_module(module=None):
    while _SAVED:
        obj, name, value = _SAVED.pop()
        setattr(obj, name, value)


def _turn_rows(deadline: float = 3.0) -> list[dict]:
    end = time.monotonic() + deadline
    while True:
        rows = [r for r in capture.read_outcomes(P) if r.get("row") == "turn"]
        if rows or time.monotonic() > end:
            return rows
        time.sleep(0.05)


def _clear():
    cap = _tmp / "data" / "personas" / P / "capture"
    if cap.exists():
        for f in cap.iterdir():
            f.unlink()


def test_row_when_the_extractor_answers_inside_the_bound():
    _clear()
    DELAY["s"] = 0.0
    interview.run_turn(P, "I work Tuesdays and Thursdays from home", [])
    rows = _turn_rows()
    assert len(rows) == 1 and rows[0]["agent"] == "goals_interviewer", rows
    assert rows[0]["outcome"] == "ran", rows


def test_row_when_the_extractor_answers_late():
    _clear()
    DELAY["s"] = 1.2          # past join_bound_s (0.5): the `late` callback must write the row
    interview.run_turn(P, "I swim on Saturday mornings", [])
    rows = _turn_rows(6.0)
    assert len(rows) == 1 and rows[0]["outcome"] == "ran", rows


def test_real_capture_yaml_reads_interview_capture_on():
    # The REAL file through the REAL loader, nothing stubbed: a bare `on` once parsed as True
    # and `mode()` read it as "off" (2026-11-26).
    saved = capture.config
    capture.config = _REAL_CONFIG
    try:
        assert capture.enabled()
        assert capture.mode("goals_interviewer") == "on"
        assert capture.mode("synthesizer") == "shadow"
    finally:
        capture.config = saved


def test_mode_reads_booleans_and_junk():
    def m(v):
        return capture.mode("a", {"enabled": True, "modes": {"a": v}})
    assert (m(True), m(False), m("on"), m("off"), m(None), m("shadow"), m(3)) == \
        ("on", "off", "on", "off", "off", "shadow", "off")


if __name__ == "__main__":
    setup_module()
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_"):
                fn()
                print("PASS", name)
    finally:
        teardown_module()
