"""
tests/test_quality_event_reconciliation.py — every write_quality_event() event_type
literal in the codebase is either collected by scripts/sync_dev_backlog.py's WANTED
set, or explicitly named as intentionally excluded.

Why this exists ([DB-0810-09]): tools/logger.py's write_quality_event() will accept
any event_type string a caller passes it — nothing ties that to what
scripts/sync_dev_backlog.py actually reads. USER_CORRECTION and CALENDAR_DUPLICATE
were both emitted live and both silently discarded for weeks because nothing
reconciled the two sides. A shared import isn't the fix here: sync_dev_backlog.py is
deliberately standard-library-only (it runs from a Claude Code SessionStart hook with
no virtualenv), and tools/logger.py pulls in core.persona / core.background at import
time, so importing it there would break that constraint. This test is the
reconciliation instead — it greps for event_type literals rather than importing the
package that defines them, so it costs nothing at runtime and catches the next type
the same way this one was caught: by looking for the gap directly.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_quality_event_reconciliation.py

Exits 0 if every check passes, 1 otherwise.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import sync_dev_backlog as S  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator: run a test function, record pass/fail rather than aborting."""
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


# Matches `write_quality_event(event_type="X", ...)` — the keyword form every call
# site but one uses.
_KEYWORD_RE = re.compile(r"""event_type\s*=\s*["']([A-Z][A-Z0-9_]*)["']""")

# Matches `write_quality_event("X", ...)` — the one positional call site
# (core/orchestrator.py's _handle_user_correction).
_POSITIONAL_RE = re.compile(r"""write_quality_event\(\s*["']([A-Z][A-Z0-9_]*)["']""")

# Scanned rather than imported: tools/ and core/ are the only trees that call
# write_quality_event today (grepped 2026-08-15). If a future call site lands
# outside both, this test silently stops covering it — that is a known limit of
# grepping over importing, accepted for the reason in the module docstring above.
_SCAN_DIRS = ("core", "tools")


def _literal_event_types() -> set[str]:
    found: set[str] = set()
    for dirname in _SCAN_DIRS:
        for path in sorted((ROOT / dirname).glob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "write_quality_event" not in text:
                continue
            found.update(_KEYWORD_RE.findall(text))
            found.update(_POSITIONAL_RE.findall(text))
    return found


# ---------------------------------------------------------------------------

@check("every literal event_type is collected or explicitly excluded")
def _():
    literal_types = _literal_event_types()
    assert literal_types, "found no event_type literals at all — scan is broken"
    accounted_for = S.WANTED | S.KNOWN_DEAD_TYPES
    unaccounted = literal_types - accounted_for
    assert not unaccounted, (
        f"{sorted(unaccounted)} are emitted (grep of core/*.py, tools/*.py) but are "
        f"in neither WANTED nor KNOWN_DEAD_TYPES in scripts/sync_dev_backlog.py — "
        f"add the type to WANTED if it should be collected, or to KNOWN_DEAD_TYPES "
        f"with a note if it is emitted deliberately but should stay excluded."
    )


@check("USER_CORRECTION and CALENDAR_DUPLICATE are collected ([DB-0810-09])")
def _():
    assert "USER_CORRECTION" in S.WANTED
    assert "CALENDAR_DUPLICATE" in S.WANTED


@check("ROUTING_MISS is collected, not marked dead ([DB-0827-05])")
def _():
    # Was classed dead 2026-08-13 on a code-only grep; the emitter is the
    # Synthesizer's agent instructions (config/agents/synthesizer.md), not Python,
    # so the grep missed it and 5 events were silently discarded on the live VM
    # since 08-11 before this was caught.
    assert "ROUTING_MISS" in S.MACHINE_TYPES
    assert "ROUTING_MISS" not in S.KNOWN_DEAD_TYPES


@check("the dynamic dev-request path (_DEV_REQUEST_TYPES) is fully covered")
def _():
    # core/orchestrator.py's _record_dev_request() passes event_type=req_type, a
    # variable, so the grep above cannot see its members. They are hardcoded here
    # instead — cheaper than parsing orchestrator.py's AST for one set literal,
    # and this only needs to catch a type being ADDED to that set without also
    # being added to WANTED, not track the set's membership over time.
    dev_request_types = {"SELF_APPLIED", "INSTRUCTION_CHANGE_REQUEST", "FEATURE_REQUEST"}
    assert dev_request_types <= S.WANTED, dev_request_types - S.WANTED


@check("WANTED and KNOWN_DEAD_TYPES do not overlap")
def _():
    overlap = S.WANTED & S.KNOWN_DEAD_TYPES
    assert not overlap, f"types marked both collected and dead: {overlap}"


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed

    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")

    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
