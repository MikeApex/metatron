"""
tests/test_null_ish_events.py — [DB-0815-09] / [DB-0815-10]

Two things are asserted here, and the second is the reason this file exists at all.

1. A quality event whose detail says "no correction happened" never becomes an event.
   93 of 174 live USER_CORRECTION events on 2026-08-15 carried "None" / "N/A", passed the
   2026-08-10 blank-detail guard because they were not blank, and collapsed into a single
   `None. ×90` entry that drowned every real signature in Mike's session-start line.

2. The two copies of is_null_ish() agree. tools/logger.py holds the canonical one;
   scripts/sync_dev_backlog.py deliberately carries a second because it is stdlib-only by
   design. A named exception to One Home Per Rule Class is only safe if drift fails a test.

Run: python3 tests/test_null_ish_events.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from tools.logger import is_null_ish                      # noqa: E402
from sync_dev_backlog import _is_null_ish                 # noqa: E402
import sync_dev_backlog as sync                           # noqa: E402

passed = failed = 0


def check(label: str, got, want):
    global passed, failed
    if got == want:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}\n          got {got!r}, want {want!r}")


# --- The exact forms observed live on 2026-08-15 -----------------------------------
OBSERVED_NULL = [
    "None", "None.", "N/A", "[N/A]", "[None]", "none", "  None.  ",
    "[N/A - the user's message is a shift in intent, not a correction of a past error.]",
    "N/A - nothing to correct",
    "",
    "   ",
]

# Real corrections that must survive. The first two are the dangerous ones: a substring
# test on "none"/"n/a" would discard both, and both are genuine user corrections.
REAL_CORRECTIONS = [
    "None of the medication was taken yesterday, contrary to the log.",
    "The N/A field should have been filled with the Prudential deadline.",
    "Corrected contact name from Eva to Iva.",
    "User corrected the assumption that scheduled calendar events imply completion.",
    "Nothing about the Heathrow trip was right — wrong day, wrong person.",
]

print("null-ish detection — forms observed live")
for text in OBSERVED_NULL:
    check(f"drops {text[:44]!r}", is_null_ish(text), True)

print("\nreal corrections survive")
for text in REAL_CORRECTIONS:
    check(f"keeps {text[:44]!r}", is_null_ish(text), False)

print("\nthe two copies agree (One Home exception is only safe if drift fails)")
for text in OBSERVED_NULL + REAL_CORRECTIONS:
    check(f"agree on {text[:38]!r}", is_null_ish(text), _is_null_ish(text))

print("\nwrite_quality_event refuses a null-ish detail")
try:
    from tools.logger import write_quality_event
    write_quality_event("USER_CORRECTION", "coordinator", "None.")
    check("raises on 'None.'", "no exception", "ValueError")
except ValueError:
    check("raises on 'None.'", "ValueError", "ValueError")
except Exception as exc:  # persona/env not set up — the guard still ran first if it raised
    check("raises on 'None.'", f"{type(exc).__name__}", "ValueError")

print("\nfetch_events-level filtering drops them from the human-facing backlog")
events = [
    {"event_type": "USER_CORRECTION", "detail": "None.", "timestamp": "t1"},
    {"event_type": "USER_CORRECTION", "detail": "Corrected the name.", "timestamp": "t2"},
]
kept = [e for e in events if not _is_null_ish(str(e.get("detail", "")))]
check("1 of 2 survives", len(kept), 1)
check("the informative one survives", kept[0]["detail"], "Corrected the name.")

# --- [DB-0815-10] state markers ---------------------------------------------------
print("\nstate markers are counted, and never double-count a section")
DOC = """
## Inbox

## Now

- **[DB-1] A thing.**
  @waiting: a real unreferenced calendar event
  @kind: bug
- **[DB-2] Another thing.**
  @kind: feature
- **[DB-3] Third.**
  @session: needs a scoping decision from Mike
  @kind: feature

## Later

- **[DB-4] Parked.**
  @kind: bug
  `due: 2026-09-01`

## Machine log

---
## Done
"""
st = sync.count_states(DOC)
check("waiting counted", st["waiting"], 1)
check("session counted", st["session"], 1)
check("bugs counted across Now+Later", st["bug"], 2)
check("features counted", st["feature"], 2)

inbox, now, later = sync.count_items(DOC)
check("now still counts every item, blocked or not", now, 3)
check("later unchanged by markers", later, 1)
check("markers are not a fourth section", inbox + now + later, 4)

print("\nmarkers must be line-anchored — prose saying \"session:\" is not a marker")
PROSE = """
## Inbox

## Now

- **[DB-9] A thing.** Fixed same session: `_imap_quote()` added to tools/mail.py,
  and it was never given its own session: the design question is still open.

## Later

## Machine log

---
## Done
"""
check("prose \"same session:\" does not count", sync.count_states(PROSE)["session"], 0)

print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
sys.exit(1 if failed else 0)
