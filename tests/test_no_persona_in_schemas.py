"""
tests/test_no_persona_in_schemas.py — no model-facing tool schema offers a `persona` slot.

Review 2026-11-05, finding 3. Six schemas in tools/pattern_miner.py and tools/baselines.py
carried a dev-testing `persona` property — three of them REQUIRED it — so a model running the
weekly Pattern Miner for one user had to name a persona, and an existing name reached that
user's logs, insights and baselines. `tests/test_build_doors.py:581-599` already asserted
"NO schema declares a `persona` property" for the Build read doors only; this is the same
assertion over everything `register_tools()` advertises.

The Python parameter is kept on every function, for tests. The second check is what keeps
that honest: a call carrying only what the schema asks for must bind to the real signature,
or dropping the property would turn into a TypeError on the next Sunday run.

No model is called; `register_tools()` only builds the schema list and handler map.

Usage:
    python3 tests/test_no_persona_in_schemas.py
"""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_results: list[tuple[str, bool, str]] = []

# The six named by the finding — checked by name as well as by the sweep, so a rename that
# drops one out of register_tools() cannot make this pass vacuously.
_NAMED = ("get_log_window", "write_insight_report", "read_recent_insights",
          "write_aspirational_baseline", "shuffled_null_score", "score_against_anchors")


def check(name: str):
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


def _registered():
    from core.orchestrator import register_tools
    return register_tools()


@check("NO schema in register_tools() declares or requires a `persona` property")
def _():
    schemas, _handlers = _registered()
    names = {s["name"] for s in schemas}
    missing = [n for n in _NAMED if n not in names]
    assert not missing, f"named tools absent from register_tools(): {missing}"
    offenders = []
    for s in schemas:
        spec = s.get("input_schema") or {}
        if "persona" in (spec.get("properties") or {}) or "persona" in (spec.get("required") or []):
            offenders.append(s["name"])
    assert not offenders, f"schemas still offering persona: {sorted(offenders)}"


@check("a call with only the schema's required arguments binds to each of the six handlers")
def _():
    schemas, handlers = _registered()
    by_name = {s["name"]: s for s in schemas}
    for name in _NAMED:
        required = by_name[name]["input_schema"].get("required") or []
        sig = inspect.signature(handlers[name])
        try:
            sig.bind(**{arg: None for arg in required})
        except TypeError as e:
            raise AssertionError(f"{name}{sig}: a schema-conforming call fails to bind — {e}")
        assert "persona" in sig.parameters, f"{name}: the test-only parameter was removed"


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
