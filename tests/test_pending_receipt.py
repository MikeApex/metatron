"""
tests/test_pending_receipt.py — a gated action is never reported as finished.

Live 2026-08-26. `merge_contacts` returned PENDING_CONFIRMATION and merged nothing —
the gate worked exactly as designed — and the Synthesizer then told Mike "That's done.
I've merged the records and kept Marcus Whitfield." He believed the merge had happened
before approving anything. Trace c87a18b2.

This is the mirror of the failure tools/confirm.py names as the worst available
outcome: a user who is told an action landed has no reason to approve it, so the
approval expires unspent at the ten-minute TTL and the action never happens at all.

The model is already out of the CONSENT path. This takes it out of the REPORT path for
the same actions: what is pending is read from the confirmation store — server state —
and a reply that contradicts it is replaced rather than trusted.

Standalone runner (no pytest dependency), matching tests/test_contact_dedup_gate.py.

Usage:
    python tests/test_pending_receipt.py

Exits 0 if every test passes, 1 otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))


def _run() -> None:
    import core.orchestrator as ORC

    PENDING = [{"token": "t1", "action": "merge_contacts",
                "description": "Merge two contacts into one?", "expires_at": 0}]

    # --- the live failure, verbatim ------------------------------------------------
    live = "That's done. I've merged the records and kept Marcus Whitfield."
    out = ORC.enforce_pending_receipt(live, PENDING)
    check("the 2026-08-26 reply is not delivered as written",
          out != live, out[:100])
    check("  and the user is told it is still waiting",
          "waiting for your approval" in out.lower(), out[:100])
    check("  and no trace of the false claim survives",
          "merged the records" not in out, out[:100])
    check("  and the pending action is named",
          "merge_contacts" in out, out[:100])

    # --- an honest reply keeps its content -----------------------------------------
    honest = ("I've put that in front of you to confirm. Separately, did you decide on "
              "Rules or 45 St Martins Lane?")
    out2 = ORC.enforce_pending_receipt(honest, PENDING)
    check("a reply that does not claim completion keeps its text",
          honest.rstrip() in out2, out2[:120])
    check("  and still gains the deterministic waiting line",
          "waiting for your approval" in out2.lower(), out2[:120])

    # --- nothing pending, nothing changes ------------------------------------------
    ordinary = "I've added that to your calendar."
    check("with nothing pending, even a completion claim is left alone",
          ORC.enforce_pending_receipt(ordinary, []) == ordinary,
          "the check must not police ordinary ungated actions")

    # --- the pattern is narrow on purpose ------------------------------------------
    for offer in ("I can merge them if you like.",
                  "Shall I send it?",
                  "Would you like me to add them to your contacts?"):
        out3 = ORC.enforce_pending_receipt(offer, PENDING)
        check(f"an offer is not a completion claim: {offer[:34]!r}",
              offer.rstrip() in out3,
              "a looser pattern would fire on ordinary prose and cost the whole reply")

    for claim in ("Done.",
                  "I have added Stephen to your contacts.",
                  "They're merged now.",
                  "That is sorted."):
        out4 = ORC.enforce_pending_receipt(claim, PENDING)
        check(f"a completion claim is replaced: {claim[:34]!r}",
              claim.rstrip() not in out4, out4[:80])

    # --- an empty reply still reports the pending action ---------------------------
    check("an empty reply is replaced by the waiting line, not left blank",
          "waiting for your approval" in ORC.enforce_pending_receipt("", PENDING).lower())

    # --- the turn boundary ----------------------------------------------------------
    # Only confirmations raised BY this turn are announced. One left outstanding from
    # an earlier turn must not be re-announced on every reply that follows it.
    before = {"t1"}
    check("a confirmation outstanding from an earlier turn is not re-announced",
          ORC._pending_raised_since(before, "test_confirm") == []
          or all(p["token"] != "t1"
                 for p in ORC._pending_raised_since(before, "test_confirm")))

    # An unreadable confirmation store must never take the session down; it fails
    # toward leaving the model's reply exactly as written.
    check("an unreadable confirmation store yields no pending and does not raise",
          isinstance(ORC._pending_tokens("no_such_persona_at_all"), set))


def main() -> int:
    _run()
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail}")
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
