#!/usr/bin/env python3
"""
Live exercise of the calendar write path — the three branches that have only ever
run against fixtures. Closes the long-standing "never had a live scheduling exchange"
gap without a scheduling exchange: it drives the same functions Logistics calls.

SAFETY, because this writes to a real calendar:
  * every event is dated 2027-11-0X, far outside any view anyone looks at;
  * every title carries the METATRON-SELFTEST marker, so a stray one is unmistakable;
  * cleanup runs in a finally block and re-queries afterwards to PROVE the calendar
    is back to its starting state. The proof is the point — "I deleted them" is a
    claim, a re-query is evidence.

WHY IT IS SEPARATE FROM run_calendar_conflict_tests.py
------------------------------------------------------
That suite is 24 mocked tests and should stay mocked — it is fast, free, offline, and
runs in CI. This one needs real credentials and a real server, so it can never be part
of that run. Keeping them apart is deliberate: a mocked suite that silently skips when
credentials are absent reports green while testing nothing.

VERIFIED LIVE 2026-08-18 on the VM, persona `mike`: 9/9, calendar confirmed clean
afterwards. First live exercise of this write path since it shipped 2026-08-05.

Run ON THE VM (the persona with real calendar credentials lives there):
    gcloud compute scp tests/run_calendar_live_test.py metatron-vm:~/ \
        --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap
    gcloud compute ssh metatron-vm --zone=us-central1-a --tunnel-through-iap \
        --project=metatron-ai-499810 \
        --command="cd ~/multi-model-mcp && source .venv/bin/activate && python3 ~/run_calendar_live_test.py mike"
    # then remove the copy from the VM home directory
"""
from __future__ import annotations

import sys
from datetime import datetime

sys.path.insert(0, "/home/md-homefolder/multi-model-mcp")
sys.path.insert(0, "/Users/md-homefolder/Desktop/multi-model-mcp")

from core.persona import persona_scope  # noqa: E402

MARK = "METATRON-SELFTEST"
DAY = "2027-11-03"
created: list[str] = []
results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"\n          {detail}" if detail else ""))


def main(persona: str) -> int:
    from tools.caldav import (delete_calendar_event, read_calendar,
                              update_calendar_event, write_calendar_event)
    from tools import scheduling

    print(f"Live calendar write-path test — persona={persona}  day={DAY}")
    print("=" * 66)

    try:
        # --- 1. Ordinary create -------------------------------------------------
        print("\n1. A normal event is created")
        r = write_calendar_event(
            title=f"{MARK} alpha", start=f"{DAY}T09:00:00", end=f"{DAY}T10:00:00",
            description="Automated self-test. Safe to delete.",
        )
        ok = isinstance(r, dict) and not r.get("error") and r.get("uid")
        if ok:
            created.append(r["uid"])
        check("event created", bool(ok), str(r)[:200])
        if not ok:
            return 1

        # --- 2. Refuse an exact duplicate ---------------------------------------
        print("\n2. An identical event is refused, not silently duplicated")
        r2 = write_calendar_event(
            title=f"{MARK} alpha", start=f"{DAY}T09:00:00", end=f"{DAY}T10:00:00",
            description="Automated self-test. Safe to delete.",
        )
        dup = isinstance(r2, dict) and r2.get("error") == "duplicate_event"
        if isinstance(r2, dict) and r2.get("uid"):
            created.append(r2["uid"])          # refused wrongly — clean it up anyway
        check("exact duplicate refused", dup, str(r2)[:220])

        # --- 3. The [VERIFY] fail-open marker -----------------------------------
        # Force the conflict check to fail the way a CalDAV outage would, and confirm
        # the write still lands but is marked for re-checking rather than trusted.
        print("\n3. When the conflict check itself fails, the write is marked [VERIFY]")
        # write_calendar_event does `from tools.scheduling import _compute_conflicts`
        # INSIDE the function (circular-import dodge), so patching the module
        # attribute takes effect on the next call. It must RETURN a check_error
        # dict, not raise — raising would abort the write instead of exercising
        # the fail-open branch, which is the opposite of what is being tested.
        original = scheduling._compute_conflicts
        scheduling._compute_conflicts = (
            lambda *a, **k: {"check_error": "simulated CalDAV outage (self-test)"}
        )
        try:
            r3 = write_calendar_event(
                title=f"{MARK} beta", start=f"{DAY}T14:00:00", end=f"{DAY}T15:00:00",
                description="Automated self-test. Safe to delete.",
            )
        finally:
            scheduling._compute_conflicts = original

        if isinstance(r3, dict) and r3.get("uid"):
            created.append(r3["uid"])
        # Read it back — the marker must be on the calendar, not just in the return value.
        back = read_calendar(DAY, DAY)
        blob = str(back)
        marked = "[VERIFY]" in blob and f"{MARK} beta" in blob
        check("failed conflict check still wrote the event", bool(r3 and r3.get("uid")), str(r3)[:200])
        check("and it is marked [VERIFY] on the calendar itself", marked,
              "" if marked else "no [VERIFY] prefix found in the read-back")

        # --- 4. Update ----------------------------------------------------------
        print("\n4. An existing event can be updated")
        r4 = update_calendar_event(uid=created[0], title=f"{MARK} alpha renamed")
        back = str(read_calendar(DAY, DAY))
        check("update returned success", isinstance(r4, dict) and not r4.get("error"), str(r4)[:200])
        check("the new title is on the calendar", "alpha renamed" in back)

        # --- 5. Delete ----------------------------------------------------------
        print("\n5. An event can be deleted")
        first = created[0]
        r5 = delete_calendar_event(uid=first)
        back = str(read_calendar(DAY, DAY))
        gone = "alpha renamed" not in back
        if gone:
            created.remove(first)
        check("delete returned success", isinstance(r5, dict) and not r5.get("error"), str(r5)[:200])
        check("and the event is gone from the calendar", gone)

    finally:
        # --- Cleanup, and prove it ---------------------------------------------
        print("\nCleanup")
        for uid in list(created):
            try:
                delete_calendar_event(uid=uid)
                created.remove(uid)
                print(f"  removed {uid[:24]}...")
            except Exception as e:
                print(f"  !! COULD NOT REMOVE {uid}: {e}")
        try:
            leftover = str(read_calendar(DAY, DAY))
            clean = MARK not in leftover
            print(f"  {'PASS' if clean else 'FAIL'}  calendar re-queried: "
                  f"{'no self-test events remain' if clean else 'SELF-TEST EVENTS STILL PRESENT'}")
            if not clean:
                print("  !! MANUAL CLEANUP NEEDED on " + DAY)
                results.append(("cleanup verified", False, "events remain"))
            else:
                results.append(("cleanup verified", True, ""))
        except Exception as e:
            print(f"  !! could not verify cleanup: {e}")

    print("\n" + "=" * 66)
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
    for label, _, detail in failed:
        print(f"  FAILED: {label}  {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    who = sys.argv[1] if len(sys.argv) > 1 else "mike"
    with persona_scope(who):
        sys.exit(main(who))
