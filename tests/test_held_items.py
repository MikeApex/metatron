"""
tests/test_held_items.py — held items get a date, are shown back, and are merged, never replaced
(instructions-to-code Stage 4, 4e: M4, with build-time amendment 1).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 M4 tests 1–6, as
amended: an incoming list is MERGED (deduplicated by text, each keeping its first `held_since`);
an item leaves only through an explicit `held_dropped` list; `[]` and an omitted key change
nothing. Tmp persona dir; no model, no network.

    python3 tests/test_held_items.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import core.orchestrator as ORC  # noqa: E402
import tools.context_tracker as CT  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        return fn
    return wrap


TODAY = date.today().isoformat()
PERSONA = "sarah_chen"


def ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


A = "Held: SLEEP_POOR flag — user was already stressed, surface when mood lifts"
B = "Held: the gym membership renewal — raise after the deadline week"
STORED = [{"text": A, "held_since": ago(9)}, {"text": B, "held_since": ago(3)}]


@contextmanager
def tracker(seed: dict | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        path = tmp_path / "context.json"
        if seed is not None:
            path.write_text(json.dumps(seed))
        with mock.patch.object(CT, "persona_data_dir", lambda *a, **k: tmp_path), \
                mock.patch.object(ORC, "persona_data_dir", lambda *a, **k: tmp_path), \
                mock.patch("tools.obligations.consult_index", lambda *a, **k: []):
            yield path


def _seed(**extra) -> dict:
    return {"last_session": ago(1), "open_threads": [{"text": "chase the quote", "added": ago(1)}],
            "patterns": ["p"], "follow_ups": ["f"], "held_items": list(STORED),
            "clinical_threads": [], **extra}


def _write(**kw):
    CT.write_context_tracker(kw.pop("open_threads", ["chase the quote"]),
                             kw.pop("patterns", ["p"]), kw.pop("follow_ups", ["f"]), **kw)


def _held(path: Path) -> list[dict]:
    return json.loads(path.read_text())["held_items"]


@check("amendment 1: an explicit [] and an omitted key both leave the stored items and dates")
def _():
    with tracker(_seed()) as path:
        _write(held_items=[])
        assert _held(path) == STORED, _held(path)
        _write()                                   # key omitted → None
        assert _held(path) == STORED, _held(path)
        ORC.persist_context_block({"open_threads": ["chase the quote"], "follow_ups": ["f"]})
        assert _held(path) == STORED, _held(path)
        ORC.persist_context_block({"open_threads": [], "patterns": [], "follow_ups": [],
                                   "held_items": []})
        assert _held(path) == STORED, _held(path)


@check("amendment 1: [new] on top of two stored items keeps both, each with its first date; the "
       "new one is stamped today")
def _():
    new = "Held: the spending dip this month — mention at the weekly review"
    with tracker(_seed()) as path:
        _write(held_items=[new])
        got = _held(path)
    assert got == STORED + [{"text": new, "held_since": TODAY}], got


@check("M4.1 re-sent text keeps its held_since (also with the rendered '(held N days)' suffix); "
       "reworded text inherits it; genuinely new text is stamped today")
def _():
    reworded = "Held: SLEEP_POOR flag — user stressed today, raise when mood improves"
    with tracker(_seed()) as path:
        _write(held_items=[A, f"{B} (held 3 days)", reworded])
        got = _held(path)
    assert got[:2] == STORED, got
    assert got[2] == {"text": reworded, "held_since": ago(9)}, got
    assert len(got) == 3


@check("amendment 1: held_dropped is the only way out — exact, suffixed or reworded-unique; an "
       "ambiguous drop removes nothing; dropped items are archived, never loaded")
def _():
    with tracker(_seed()) as path:
        _write(held_dropped=[f"{B} (held 3 days)"])
        assert _held(path) == STORED[:1], _held(path)
        raw = json.loads(path.read_text())
        assert raw["dropped_held_items"][0]["text"] == B
        assert raw["dropped_held_items"][0]["dropped_on"] == TODAY
        assert "dropped_held_items" not in CT.read_context_tracker()
        # Raised and dropped in the same block: the drop wins.
        new = "Held: a note about the weekend plans — raise on Friday"
        ORC.persist_context_block({"held_items": [new], "held_dropped": [new]})
        assert _held(path) == STORED[:1], _held(path)
        # A reworded drop that matches exactly one stored item drops it.
        _write(held_items=[B])
        _write(held_dropped=["SLEEP_POOR flag: user was stressed, surface when mood lifts"])
        assert [h["text"] for h in _held(path)] == [B], _held(path)
        # Ambiguous: shares anchors with two items → nothing is removed.
        _write(held_items=["Held: gym membership renewal — second note after deadline week"])
        before = _held(path)
        _write(held_dropped=["gym membership renewal deadline week"])
        assert _held(path) == before, _held(path)
        assert len(json.loads(path.read_text())["dropped_held_items"]) == 3


@check("M4.2 a legacy bare string is normalised on read, with no date invented")
def _():
    with tracker(_seed(held_items=["Held: an old bare string"])) as path:
        got = CT.read_context_tracker()["held_items"]
        assert got == [{"text": "Held: an old bare string", "held_since": None}], got
        _write(held_items=["Held: an old bare string"])
        assert _held(path) == [{"text": "Held: an old bare string", "held_since": None}]


@check("M4.3 rendered for the Synthesizer only, every entry, with its age")
def _():
    seed = _seed(held_items=STORED + ["Held: legacy entry"] +
                 [{"text": f"Held: item {i}", "held_since": TODAY} for i in range(6)])
    from core.persona import persona_scope
    with tracker(seed), persona_scope(PERSONA), \
            mock.patch("tools.ambient.load_ambient_context", lambda *a, **k: ""):
        synth = ORC.load_recent_context(PERSONA, audience="synthesizer")
        coord = ORC.load_recent_context(PERSONA, audience="coordinator")
        plain = ORC.load_recent_context(PERSONA)
    line = [x for x in synth.splitlines() if x.startswith("**Held back (not yet raised):**")]
    assert len(line) == 1, synth
    assert f"{A} (held 9 days)" in line[0] and f"{B} (held 3 days)" in line[0], line
    assert "Held: legacy entry (held, start not recorded)" in line[0]
    assert all(f"Held: item {i} (held since today)" in line[0] for i in range(6)), line
    assert "Held back" not in coord and "Held back" not in plain
    # The render, sent back verbatim, is the same items — nothing is added.
    texts = [p.strip() for p in line[0].split(":**", 1)[1].split(" | ")]
    with tracker(seed) as path:
        before = _held(path)
        _write(held_items=texts)
        after = _held(path)
    assert len(after) == len(CT._normalize_held_items(before)), after


@check("M4.4 the fingerprint reads text only: shape and age changes are not 'something new'")
def _():
    base = {"open_threads": [], "patterns": [], "follow_ups": [], "clinical_threads": []}
    with tracker():
        f1 = CT._context_fingerprint({**base, "held_items": [A, B]})
        f2 = CT._context_fingerprint({**base, "held_items": STORED})
        f3 = CT._context_fingerprint({**base, "held_items": [{"text": A, "held_since": TODAY},
                                                             {"text": B, "held_since": ago(1)}]})
        f4 = CT._context_fingerprint({**base, "held_items": STORED + ["Held: new"]})
    assert f1 == f2 == f3 and f4 != f1


@check("M4.6 a merge_pattern_findings call leaves dated held items byte-identical")
def _():
    with tracker(_seed()) as path:
        before = json.dumps(_held(path))
        CT.merge_pattern_findings(patterns=["a new finding"], held_items=[], follow_ups=[],
                                  open_threads=[])
        assert json.dumps(_held(path)) == before


@check("no data loss: an unreadable tracker recovers held items from the last good copy")
def _():
    with tracker(_seed()) as path:
        _write(held_items=["Held: one more"])
        kept = _held(path)
        _write()               # .lastgood is the OUTGOING tracker, so it now holds "one more"
        path.write_text("{ not json")
        _write()
        assert _held(path) == kept, _held(path)


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
