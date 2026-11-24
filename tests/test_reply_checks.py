"""
tests/test_reply_checks.py — Stage 5 M19: a quality event when a reply opens a sentence with a
listed filler phrase (archive/plans/instructions_to_code_stage5_one_channel_plan_2026-11-23.md
§ 1 M19). Detection only. The quality-event writer is stubbed.

    python3 tests/test_reply_checks.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import tools.logger as LOG  # noqa: E402
import tools.reply_checks as RC  # noqa: E402

_EVENTS: list[dict] = []
LOG.write_quality_event = lambda **k: _EVENTS.append(k) or "ok"

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        _EVENTS.clear()
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


@check("1. 'Enjoy the museum.' fires, once, with the sentence as detail")
def _():
    reply = "The V&A is open until 22:00 on Fridays. Enjoy the museum."
    assert RC.check_filler(reply) == "Enjoy the museum.", RC.check_filler(reply)
    _EVENTS.clear()
    RC.check_filler(reply)
    assert [e["event_type"] for e in _EVENTS] == ["FILLER_PHRASE"], _EVENTS
    assert _EVENTS[0]["detail"] == "Enjoy the museum." and _EVENTS[0]["source_agent"] == "synthesizer"


@check("2. 'You'd enjoy the quieter route.' does not fire — advice, not a sentence start")
def _():
    assert RC.check_filler("You'd enjoy the quieter route. It adds four minutes.") is None
    assert RC.check_filler("Take the 9:12 — you will enjoy the view.") is None
    assert not _EVENTS


@check("3. one event for two matches in one reply; a line start and the other phrases match")
def _():
    reply = "Booked for 7.\nHave a great time! Hope it goes well."
    assert RC.check_filler(reply) == "Have a great time!", RC.check_filler(reply)
    assert len(_EVENTS) == 1, _EVENTS
    assert RC.check_filler("Have fun.") and RC.check_filler('Done. "Enjoy your trip."')


@check("4. the reply text is unchanged")
def _():
    reply = "Enjoy it."
    copy = str(reply)
    RC.check_filler(reply)
    assert reply == copy


@check("the list lives in config, and the module points at the rule's home")
def _():
    text = (ROOT / "config" / "modules" / "filler_phrases.yaml").read_text()
    assert "synthesizer.md" in text and "sentence_starts" in text


@check("both pipeline twins run the detector beside check_false_action_claims")
def _():
    src = (ROOT / "core" / "orchestrator.py").read_text()
    assert src.count("check_false_action_claims(visible)\n") == 2
    assert src.count("_check_filler(visible)") == 2


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
