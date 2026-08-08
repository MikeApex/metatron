"""
tests/test_clinical_threads.py — clinical thread lifecycle in tools/context_tracker.py.

Covers the B1a red-team finding (2026-08-04): a MUST_SURFACE/SUICIDAL_IDEATION thread left in
sarah_chen's context.json hijacked 15 unrelated later turns, with no expiry or resolution path.

The rules under test are the ones enforced in Python rather than trusted to an instruction file:
tier derivation, the refusal to resolve a clinical thread from a session, the immovable `raised`
date, carry-forward on omission, and the conditional protocol injection.

Run:  python3 tests/test_clinical_threads.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "clinical_thread_test"
SI = "CLINICAL_CONCERN: SUICIDAL_IDEATION"
MED = "MEDICATION_MISSED_CRITICAL"

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def main() -> int:
    from core.persona import persona_data_dir, persona_scope
    from tools.context_tracker import read_context_tracker, write_context_tracker

    today = date.today().isoformat()

    with persona_scope(PERSONA):
        shutil.rmtree(persona_data_dir(), ignore_errors=True)

        # --- Baseline: no clinical thread, no protocol overhead ------------------------
        write_context_tracker(["thread a"], ["pattern a"], ["follow up a"])
        state = read_context_tracker()
        check(
            "clean session carries no clinical_threads",
            state["clinical_threads"] == [],
        )
        check(
            "protocol text is absent when no thread is open",
            "_clinical_protocol" not in state,
            "the protocol must cost nothing in the common case",
        )

        # --- A clinical flag fires ------------------------------------------------------
        write_context_tracker(
            ["safety check"], [], [],
            clinical_threads=[{"flag": SI, "status": "active", "note": "expressed SI"}],
        )
        state = read_context_tracker()
        thread = state["clinical_threads"][0]
        check("thread is recorded", thread["flag"] == SI)
        check("CLINICAL_CONCERN derives tier 2", thread["tier"] == 2, str(thread))
        check("raised is stamped today", thread["raised"] == today)
        check(
            "protocol is injected once a thread is open",
            "_clinical_protocol" in state and "active" in state["_clinical_protocol"],
        )

        # --- The bug: an unrelated turn must not keep it leading ------------------------
        result = write_context_tracker(
            ["unrelated: weather"], [], [],
            clinical_threads=[{"flag": SI, "status": "watch", "note": "surfaced, acknowledged"}],
        )
        thread = read_context_tracker()["clinical_threads"][0]
        check("active -> watch is permitted", thread["status"] == "watch")
        check("the status change is reported back", "active -> watch" in result, result)

        # --- Tier 2 cannot be closed from a session -------------------------------------
        result = write_context_tracker(
            ["unrelated: weather"], [], [],
            clinical_threads=[{"flag": SI, "status": "resolved"}],
        )
        thread = read_context_tracker()["clinical_threads"][0]
        check("tier-2 resolve is refused, coerced to watch", thread["status"] == "watch")
        check(
            "the refusal is reported, not silent",
            "cannot be resolved" in result,
            result,
        )

        # --- The clock cannot be reset --------------------------------------------------
        check("raised survives later writes", thread["raised"] == today)
        stale = {"flag": SI, "tier": 2, "status": "watch", "raised": "2020-01-01", "note": ""}
        import json

        p = persona_data_dir() / "context.json"
        data = json.loads(p.read_text())
        data["clinical_threads"] = [stale]
        p.write_text(json.dumps(data))
        write_context_tracker(
            ["x"], [], [],
            clinical_threads=[{"flag": SI, "status": "active", "raised": today}],
        )
        thread = read_context_tracker()["clinical_threads"][0]
        check(
            "a model-supplied raised date cannot overwrite the stored one",
            thread["raised"] == "2020-01-01",
            str(thread),
        )

        # --- Omission carries forward; it does not delete --------------------------------
        write_context_tracker(["y"], [], [])
        live = read_context_tracker()["clinical_threads"]
        check("omitted thread is carried, not dropped", len(live) == 1 and live[0]["flag"] == SI)

        # --- Tier 1 behaves differently ---------------------------------------------------
        write_context_tracker(
            ["z"], [], [],
            clinical_threads=[{"flag": MED, "status": "active", "note": "missed dose"}],
        )
        live = {t["flag"]: t for t in read_context_tracker()["clinical_threads"]}
        check("tier-1 flag derives tier 1", live[MED]["tier"] == 1, str(live.get(MED)))
        write_context_tracker(
            ["z"], [], [],
            clinical_threads=[{"flag": MED, "status": "resolved"}],
        )
        live = {t["flag"]: t for t in read_context_tracker()["clinical_threads"]}
        check("tier-1 thread CAN be resolved and drops out of context", MED not in live)
        check("resolving a tier-1 thread leaves the tier-2 one open", SI in live)

        # --- Legacy trackers written before this field existed ----------------------------
        p.write_text('{"last_session": "2026-08-01", "open_threads": [], "patterns": [], '
                     '"follow_ups": []}')
        state = read_context_tracker()
        check(
            "a pre-existing tracker without the field still reads",
            state["clinical_threads"] == [] and state["held_items"] == [],
        )

        shutil.rmtree(persona_data_dir(), ignore_errors=True)

    print()
    if _failures:
        print(f"{len(_failures)} failure(s): {', '.join(_failures)}")
        return 1
    print("All clinical thread lifecycle checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
