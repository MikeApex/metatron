"""
tests/test_context_audit_line.py — [DB-0814-02] context-tracker writes leave no history.

Thread expiry shipped 2026-08-14. Twelve days later the live `context.json` read
`expired_open_threads: 0` with four threads open — which is equally consistent with "grace
is legitimately keeping everything alive" and "expiry has silently never fired", because the
file is overwritten in place and records a state, never a change.

`context_audit.jsonl` is the data source that settles it: one append-only line per write,
beside the file it describes. Asserted here: exactly one line per write, the fields are
present, and an expiry is distinguishable from a thread the model merely stopped sending.

Run:  python3 tests/test_context_audit_line.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import shutil
import stat
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.persona import persona_data_dir, persona_scope  # noqa: E402
from tools.context_tracker import (  # noqa: E402
    _OPEN_THREAD_EXPIRY_DAYS,
    write_context_tracker,
)

PERSONA = "context_audit_test"
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


def _lines(audit: Path) -> list[dict]:
    return [json.loads(ln) for ln in audit.read_text().splitlines() if ln.strip()]


def _age_thread(tracker: Path, text: str, days_ago: int) -> None:
    data = json.loads(tracker.read_text())
    old = (date.today() - timedelta(days=days_ago)).isoformat()
    for t in data["open_threads"]:
        if t.get("text") == text:
            t["added"] = old
    tracker.write_text(json.dumps(data))


with persona_scope(PERSONA):
    data_dir = persona_data_dir()
    shutil.rmtree(data_dir, ignore_errors=True)
    tracker_path = data_dir / "context.json"
    audit_path = data_dir / "context_audit.jsonl"

    print("one line per write:")
    write_context_tracker(["bookstore P&L review"], [], [])
    check("a write produces exactly one audit line", len(_lines(audit_path)) == 1)
    first = _lines(audit_path)[0]
    check("the line names what was added", first["added"] == ["bookstore P&L review"], str(first))
    check("nothing removed or expired on a first write",
          first["removed"] == [] and first["expired"] == [], str(first))
    check("the line carries a timestamp and the open count",
          bool(first.get("ts")) and first["open_count"] == 1, str(first))

    write_context_tracker(["bookstore P&L review"], [], [])
    check("a second write appends rather than replaces", len(_lines(audit_path)) == 2)
    check("an unchanged resend records no change",
          _lines(audit_path)[1]["added"] == [] and _lines(audit_path)[1]["expired"] == [])

    print("\nexpiry is distinguishable from a thread the model simply stopped sending:")
    write_context_tracker([], [], [])          # dropped by omission, not by age
    dropped = _lines(audit_path)[-1]
    check("an omitted thread is recorded as removed, not expired",
          dropped["removed"] == ["bookstore P&L review"] and dropped["expired"] == [],
          str(dropped))

    shutil.rmtree(data_dir, ignore_errors=True)
    write_context_tracker(["post-travel recovery"], [], [])
    _age_thread(tracker_path, "post-travel recovery", _OPEN_THREAD_EXPIRY_DAYS + 1)
    write_context_tracker(["post-travel recovery"], [], [],
                          user_text="what's on my calendar today")
    aged = _lines(audit_path)[-1]
    check("an expiry is recorded as expired",
          aged["expired"] == ["post-travel recovery"], str(aged))
    check("the expired thread is not double-counted as removed",
          aged["removed"] == [], str(aged))
    check("the audit answers the question context.json cannot: expiry has fired",
          any(ln["expired"] for ln in _lines(audit_path)))

    print("\npermissions match the file it sits beside:")
    check("audit file is 600",
          stat.S_IMODE(audit_path.stat().st_mode) == 0o600,
          oct(stat.S_IMODE(audit_path.stat().st_mode)))
    check("it sits in the same directory as context.json",
          audit_path.parent == tracker_path.parent)

    shutil.rmtree(data_dir, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All context-audit checks passed.")
sys.exit(0)
