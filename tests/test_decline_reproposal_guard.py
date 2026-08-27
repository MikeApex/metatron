"""
tests/test_decline_reproposal_guard.py — [DB-0827-01] a refusal has to stand.

`0f8f528` gave "No" somewhere to land: the pending record is removed, so the app's
five-second poll stops putting the same card straight back. It did not stop the NEXT turn
proposing the identical action off the same carried context — the same loop one turn slower,
and with the same escape hatch, which is approving the thing you just refused.

What is under test: a declined action is not raised again from carried context, and IS
allowed back when something genuinely new happens — the user asking, or a new item arriving.
The judgement of "genuinely new" lives in tools/turn_context.py; tools/confirm.py only asks.

Run:  python3 tests/test_decline_reproposal_guard.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.persona import persona_data_dir, persona_scope  # noqa: E402
from tools import confirm, turn_context  # noqa: E402

PERSONA = "decline_reproposal_test"
FAILURES: list[str] = []

ACTION = "send_email"
ARGS = {"to": "sarah@example.com", "subject": "Itinerary", "body": "Attached."}
OTHER_ARGS = {"to": "sarah@example.com", "subject": "Address", "body": "12 Elm St."}
DESC = "Email Sarah the itinerary"


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


def fresh() -> None:
    shutil.rmtree(persona_data_dir(), ignore_errors=True)
    persona_data_dir().mkdir(parents=True, exist_ok=True)


def decline_once(args=ARGS, desc=DESC) -> dict:
    """Propose and then refuse, through the real path — no hand-written ledger rows."""
    with turn_context.turn_scope(user_turn=True):
        payload = confirm.request(ACTION, args, desc, persona=PERSONA)
    token = payload["confirm_token"]
    return confirm.decline(token, persona=PERSONA)


with persona_scope(PERSONA):
    print("A refusal stands against a scheduled run re-reading the same context:")
    fresh()
    record = decline_once()
    check("the decline was filed with its fingerprint", bool(record and record.get("fingerprint")))

    with turn_context.turn_scope(user_turn=False):
        again = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("no card is raised", again["status"] == "DECLINED_RECENTLY", str(again)[:200])
    check("nothing is left waiting for the user",
          not confirm.pending(persona=PERSONA), str(confirm.pending(persona=PERSONA)))
    check("no token is issued to be spent later", "confirm_token" not in again)
    check("the payload states the user's decision, not the mechanism",
          "declined" in again["instruction"].lower()
          and not any(w in json.dumps(again).lower()
                      for w in ("fingerprint", "guard", "suppress", "ledger", "token")),
          json.dumps(again))

    print("\nThe user asking again is a new trigger, and is never blocked:")
    fresh()
    decline_once()
    with turn_context.turn_scope(user_turn=True):
        allowed = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("the card is raised", allowed["status"] == "PENDING_CONFIRMATION", str(allowed)[:200])
    check("it says the user turned this down before",
          allowed.get("previously_declined_at") is not None)
    check("the pending record remembers it follows a refusal",
          any(e.get("after_decline") for e in
              json.loads((persona_data_dir() / "pending_confirmations.json").read_text()).values()))

    print("\nA turn that began BEFORE the refusal cannot resurrect it:")
    fresh()
    decline_once()
    with turn_context.turn_scope(user_turn=True, started_at=time.time() - 3600):
        stale = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("an hour-old turn is not new evidence", stale["status"] == "DECLINED_RECENTLY")

    print("\nA new item arriving is a new trigger:")
    fresh()
    decline_once()
    intake_dir = persona_data_dir() / "intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    (intake_dir / "records.jsonl").write_text(json.dumps({
        "id": "m1", "domain": "logistics", "category": "email",
        "seen_at": (datetime.now() + timedelta(seconds=5)).isoformat(),
    }) + "\n")
    with turn_context.turn_scope(user_turn=False):
        after_mail = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("a message that arrived after the refusal reopens it",
          after_mail["status"] == "PENDING_CONFIRMATION", str(after_mail)[:200])

    (intake_dir / "records.jsonl").write_text(json.dumps({
        "id": "m0", "domain": "logistics", "category": "email",
        "seen_at": (datetime.now() - timedelta(days=2)).isoformat(),
    }) + "\n")
    fresh()
    intake_dir.mkdir(parents=True, exist_ok=True)
    (intake_dir / "records.jsonl").write_text(json.dumps({
        "id": "m0", "domain": "logistics", "category": "email",
        "seen_at": (datetime.now() - timedelta(days=2)).isoformat(),
    }) + "\n")
    decline_once()
    with turn_context.turn_scope(user_turn=False):
        old_mail = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("a message that predates the refusal is not new evidence",
          old_mail["status"] == "DECLINED_RECENTLY")

    print("\nThe refusal is of one action, not of a subject:")
    fresh()
    decline_once()
    with turn_context.turn_scope(user_turn=False):
        different = confirm.request(ACTION, OTHER_ARGS, "Email Sarah the address",
                                    persona=PERSONA)
    check("a different action to the same person still goes through",
          different["status"] == "PENDING_CONFIRMATION")

    print("\nFail closed when nothing bound a turn:")
    fresh()
    decline_once()
    turn_context.adopt(None)
    unbound = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("an unbound path suppresses rather than re-proposes",
          unbound["status"] == "DECLINED_RECENTLY")

    print("\nA record that failed the tamper check suppresses nothing:")
    fresh()
    decline_once()
    ledger_path = persona_data_dir() / "declined_confirmations.json"
    rows = json.loads(ledger_path.read_text())
    rows[-1]["fingerprint"] = None
    rows[-1]["args"] = None
    ledger_path.write_text(json.dumps(rows))
    with turn_context.turn_scope(user_turn=False):
        tampered = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("what the user said no to is not known, so nothing is blocked on it",
          tampered["status"] == "PENDING_CONFIRMATION")

    print("\nThe window releases the suppression and keeps the record:")
    fresh()
    decline_once()
    rows = json.loads(ledger_path.read_text())
    rows[-1]["declined_at"] = time.time() - confirm._REPROPOSE_WINDOW_SECONDS - 60
    ledger_path.write_text(json.dumps(rows))
    with turn_context.turn_scope(user_turn=False):
        expired = confirm.request(ACTION, ARGS, DESC, persona=PERSONA)
    check("past the window it can be proposed again",
          expired["status"] == "PENDING_CONFIRMATION")
    check("the refusal itself is still on record — nothing is deleted",
          len(confirm.declined(persona=PERSONA)) == 1)

    print("\nThe session is told, not only prevented:")
    fresh()
    check("nothing declined means no block and no tokens spent",
          confirm.context_block(PERSONA) == "")
    decline_once()
    block = confirm.context_block(PERSONA)
    check("the refused thing is named in the user's own terms", DESC in block, block)
    check("their answer is stated as standing", "stands" in block.lower(), block)
    check("no tool or argument names leak into a user-facing layer",
          ACTION not in block and "sarah@example.com" not in block, block)

    shutil.rmtree(persona_data_dir(), ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All decline re-proposal guard checks passed.")
sys.exit(0)
