"""
tests/test_empty_template_label_events.py — [DB-0827-07] empty CLARIFICATION_NEEDED events.

33 quality events on the VM since 2026-08-18 carry a detail that is exactly
`CLARIFICATION_NEEDED:` — the Coordinator filled the USER_CORRECTION slot of its output
template with the label of the adjacent template line and nothing else. That is the
[DB-0815-09] "None ×90" failure one slot along, and is_null_ish() did not catch it because
a label is not one of the observed null words.

The two directions that matter are both asserted here. A bare label is dropped; a label
carrying real content ("CLARIFICATION_NEEDED: which Bill?") is genuine signal and is kept
INTACT, label included — the fix must not become a stripper.

Run:  python3 tests/test_empty_template_label_events.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools.logger import is_null_ish  # noqa: E402

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'' if ok else f' — got {got!r}, want {want!r}'}")
    if not ok:
        FAILURES.append(name)


# The live shape, plus the variants of it a template-filling model produces.
BARE_LABELS = [
    "CLARIFICATION_NEEDED:",
    "CLARIFICATION_NEEDED: ",
    "  CLARIFICATION_NEEDED:  ",
    "[CLARIFICATION_NEEDED:]",
    "USER_CORRECTION:",
    "ROUTING_MISS:",
    "MUST_SURFACE:",
    "CLARIFICATION NEEDED:",
    "CLARIFICATION_NEEDED: None",
    "CLARIFICATION_NEEDED: N/A",
    "CLARIFICATION_NEEDED: -",
]

# Content after the label is the whole point of the event — none of these may be dropped.
REAL_SIGNAL = [
    "CLARIFICATION_NEEDED: which Bill?",
    "CLARIFICATION_NEEDED: the user said 'the Tuesday one' and there are two.",
    "USER_CORRECTION: the run was Thursday, not Wednesday.",
    "Corrected contact name from Eva to Iva.",
    "None of the medication was taken yesterday, contrary to the log.",
    "NOTE: this is shouted but it says something.",
]

print("bare template labels are dropped:")
for text in BARE_LABELS:
    check(f"drops {text!r}", is_null_ish(text), True)

print("\nlabels carrying content are kept:")
for text in REAL_SIGNAL:
    check(f"keeps {text!r}", is_null_ish(text), False)

print("\nthe 2026-08-15 forms still behave (no regression):")
for text in ["None", "None.", "N/A", "[None]", "", "   ",
             "[N/A - the user's message is a shift in intent, not a correction.]"]:
    check(f"drops {text[:40]!r}", is_null_ish(text), True)

print("\nwrite_quality_event refuses a bare label, keeps a labelled correction intact:")
from tools.logger import write_quality_event  # noqa: E402

try:
    write_quality_event("USER_CORRECTION", "coordinator", "CLARIFICATION_NEEDED:")
    check("raises on a bare label", "no exception", "ValueError")
except ValueError:
    check("raises on a bare label", "ValueError", "ValueError")
except Exception as exc:   # persona/env not bound — the detail guard still ran first
    check("raises on a bare label", type(exc).__name__, "ValueError")

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All empty-template-label checks passed.")
sys.exit(0)
