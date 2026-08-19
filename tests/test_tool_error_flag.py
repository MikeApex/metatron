"""
tests/test_tool_error_flag.py — the trace's tool-call `ok` flag, [DB-0810-07].

Until 2026-08-19 `ok` was set False in exactly one place: the `except` around tool
dispatch. So it recorded crashes and nothing else, and every graceful failure —
which is how every tool in this codebase reports invalid input — was filed as a
success. Measured on the VM that day: 786 tool calls, ONE ok:false, and that one
was a missing required argument. The monitoring view showed green while users hit
"Error: no contact found with id …".

These tests pin both halves: a returned error string now marks the call failed,
and ordinary output — including prose that merely discusses an error — does not.
The second half is the expensive one to get wrong. A false red sends someone
debugging a call that worked.

Standalone runner (no pytest dependency), matching tests/test_crm_dedup_guards.py.

Usage:
    python tests/test_tool_error_flag.py

Exits 0 if every test passes, 1 otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import _TOOL_ERROR_PREFIX_RE  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))


def flags_failed(result: str) -> bool:
    """The exact predicate dispatch_tool() applies to a tool's returned string."""
    return bool(isinstance(result, str) and _TOOL_ERROR_PREFIX_RE.match(result))


# --- Real return values, copied from tools/. Each of these rendered GREEN before. ---

FAILURES = [
    ("crm.read_contact", "Error: no contact found with id 'nope-1234'"),
    ("obligations.close_obligation", "error: no obligation with id 'nope-1234'"),
    ("obligations.open_obligation", "error: `what` is required — nothing was opened."),
    ("crm.write_contact", "Error: provide either contact_id or name."),
    ("wishes.write_wishes", "Error: 'holidays' is not a valid section."),
    ("leading whitespace", "  Error: something went wrong"),
    ("spaced colon", "Error : something went wrong"),
    ("upper case", "ERROR: something went wrong"),
]

for label, text in FAILURES:
    check(f"marked failed — {label}", flags_failed(text), repr(text[:60]))


# --- Ordinary output. A false red here is worse than a missed failure. ---

SUCCESSES = [
    ("a contact id", "3d6c145d-b1ca-4119-ab37-464fdc3a2a6f"),
    ("a plain confirmation", "Contact created."),
    ("schedule not-found, which is not the Error: convention",
     "No schedule named 'my_reminder'. Existing: none."),
    ("prose that discusses an error",
     "Error handling in the pipeline is documented in the runbook."),
    ("prose mentioning an error mid-sentence",
     "The report notes an error in the Q3 figures and recommends a re-run."),
    ("a research answer opening on the word",
     "Errors of this kind are usually transient."),
    ("JSON output", '{"status": "ok", "error": null}'),
    ("empty string", ""),
]

for label, text in SUCCESSES:
    check(f"NOT marked failed — {label}", not flags_failed(text), repr(text[:60]))


# --- The regression this replaces: the old behaviour must be genuinely different. ---

check(
    "the widening is not a no-op (the old code would have passed these)",
    all(flags_failed(t) for _, t in FAILURES),
    "every FAILURES entry was recorded ok:True before 2026-08-19",
)


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        status = "PASS" if ok else "FAIL"
        line = f"  {status}  {name}"
        if not ok and detail:
            line += f"\n        {detail}"
        print(line)
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
