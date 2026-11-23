"""
tests/test_coordinator_package_shape.py — the Coordinator stops re-typing the user's whole
message (Stage 2 M10, code side). No code reads ORIGINAL_MESSAGE; the Synthesizer already gets
the user's own words under ORIGINAL USER MESSAGE from `_frame_proactive`.

Run:  python3 tests/test_coordinator_package_shape.py   (or pytest)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.orchestrator as orch  # noqa: E402


def test_nudge_package_has_no_original_message():
    assert "ORIGINAL_MESSAGE" not in orch._NUDGE_PACKAGE
    assert orch._NUDGE_PACKAGE.startswith("RESOLVED_INTENT:")


def test_no_code_reader_of_original_message():
    hits = []
    for tree in ("core", "tools"):
        for path in (ROOT / tree).rglob("*.py"):
            if "ORIGINAL_MESSAGE" in path.read_text(encoding="utf-8", errors="replace"):
                hits.append(str(path.relative_to(ROOT)))
    assert hits == [], hits


def test_synthesizer_label_is_the_users_own_words():
    assert orch._frame_proactive("x", False)[1] == "ORIGINAL USER MESSAGE"


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
