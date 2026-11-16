"""
tests/test_health_notes_feed.py — a health note is never lost to the next one.

`health.symptoms` and `health.medical_notes` are scalars, so each write replaced the one
before; 2026-11-13 to 11-16 that lost four of six cardiac events Mike logged for his
cardiologist. tools/logger.py now also appends every value to the day's `health_notes`
feed, with the write time and — where the client stamped them — the spoken times, which
tools/turn_context.py lifts from the message and carries to the Diarist's thread.

Same check-decorator convention as tests/test_accountability_gate.py (no pytest here). Every
fixture is synthetic, in a tempdir. The memory index that write_log starts in the background
is stubbed: it embeds, and a test must not end in a live meter.
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.logger as LOG  # noqa: E402
import tools.turn_context as TURN  # noqa: E402
from core.persona import persona_scope  # noqa: E402

_results = []


def check(name):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


def _with_logs(fn):
    """Run `fn(logs_dir)` with write_log pointed at a tempdir and the index stubbed."""
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td) / "logs"
        orig_dir, orig_bg = LOG._logs_dir, LOG.run_background
        LOG._logs_dir = lambda: logs                  # noqa: E731 — restored below
        LOG.run_background = lambda *a, **k: None     # noqa: E731
        try:
            with persona_scope("mike"):
                fn(logs)
        finally:
            LOG._logs_dir, LOG.run_background = orig_dir, orig_bg


def _day(logs: Path) -> dict:
    return json.loads(next(logs.glob("*.json")).read_text())


@check("two writes to the same day keep both notes; the scalar still holds the latest")
def _():
    def body(logs):
        LOG.write_log({"health": {"medical_notes": "11:42 irregular heartbeat, just ate"}})
        LOG.write_log({"health": {"medical_notes": "13:42 reclined in bed, not supine"}})
        day = _day(logs)
        assert day["health"]["medical_notes"] == "13:42 reclined in bed, not supine"
        texts = [e["text"] for e in day["health_notes"]]
        assert texts == ["11:42 irregular heartbeat, just ate",
                         "13:42 reclined in bed, not supine"], texts
        assert all(e["field"] == "medical_notes" and e["written_at"]
                   for e in day["health_notes"])
    _with_logs(body)


@check("an identical restatement is not appended twice; a different field still is")
def _():
    def body(logs):
        LOG.write_log({"health": {"symptoms": "irregular heartbeat"}})
        LOG.write_log({"health": {"symptoms": "irregular heartbeat",
                                  "medical_notes": "on the train"}})
        fields = [(e["field"], e["text"]) for e in _day(logs)["health_notes"]]
        assert fields == [("symptoms", "irregular heartbeat"),
                          ("medical_notes", "on the train")], fields
    _with_logs(body)


@check("a write with no health note leaves the day without a feed")
def _():
    def body(logs):
        LOG.write_log({"mood": "steady", "health": {"sleep_hours": 7}})
        LOG.write_log({"health": {"symptoms": None, "medical_notes": "  "}})
        assert "health_notes" not in _day(logs)
    _with_logs(body)


@check("an existing log written before the feed reads and merges as before")
def _():
    def body(logs):
        logs.mkdir(parents=True)
        today = __import__("datetime").date.today().isoformat()
        (logs / f"{today}.json").write_text(json.dumps(
            {"date": today, "health": {"medical_notes": "old note"}}))
        LOG.write_log({"health": {"sleep_hours": 6}})
        day = _day(logs)
        assert day["health"] == {"medical_notes": "old note", "sleep_hours": 6}
        assert "health_notes" not in day
    _with_logs(body)


@check("spoken stamps from the turn are recorded beside the note")
def _():
    msg = ("[Sun, Nov 15, 4:48 PM] Council tax is paid, cardiac monitor, at the computer.\n\n"
           "[Sun, Nov 15, 5:09 PM] Bupa request is in.")
    def body(logs):
        with TURN.turn_scope(user_turn=True, spoken=TURN.spoken_stamps(msg)):
            LOG.write_log({"health": {"medical_notes": "event at the computer"}})
        entry = _day(logs)["health_notes"][0]
        assert entry["spoken"] == ["Sun, Nov 15, 4:48 PM", "Sun, Nov 15, 5:09 PM"], entry
    _with_logs(body)


@check("no stamp in the message means no `spoken` key, not an empty one")
def _():
    def body(logs):
        with TURN.turn_scope(user_turn=True, spoken=TURN.spoken_stamps("cardiac monitor, couch")):
            LOG.write_log({"health": {"medical_notes": "on the couch"}})
        assert "spoken" not in _day(logs)["health_notes"][0]
    _with_logs(body)


@check("spoken_stamps reads 12- and 24-hour client stamps and ignores other brackets")
def _():
    text = ("[Mon 16 Nov, 13:48] standing on the train\n\n"
            "[Sun, Nov 15, 4:48 PM] at the computer\n\n"
            "[Pre-loaded context] not a stamp\n"
            "mid-line [Sun, Nov 15, 4:48 PM] not at a line start")
    assert TURN.spoken_stamps(text) == ["Mon 16 Nov, 13:48", "Sun, Nov 15, 4:48 PM"]
    assert TURN.spoken_stamps(None) == []


@check("adopt_spoken carries stamps to a thread without binding a turn")
def _():
    seen = {}
    def worker():
        TURN.adopt_spoken(["Sun, Nov 15, 3:08 PM"])
        seen["turn"] = TURN.current()
        seen["spoken"] = TURN.current_spoken()
        seen["trigger"] = TURN.new_trigger_since(0.0)
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen["turn"] is None                       # the decline guard's input is untouched
    assert seen["trigger"] is False                   # ...so it still fails closed
    assert seen["spoken"] == ["Sun, Nov 15, 3:08 PM"]


if __name__ == "__main__":
    for n, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {n}" + (f"  — {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results)-failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
