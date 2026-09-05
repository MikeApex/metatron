"""
tests/test_thread_identity.py — [DB-0814-02] a reworded thread is the same thread.

WHAT THIS PROTECTS. Measured 2026-09-03: 111 audited context writes over 20 days produced ZERO
expiries, and all four live open threads carried `added: 2026-09-03` — including one that appears
verbatim in the 09-02 conversation. Cause: a thread's birthdate was preserved only on an EXACT
text match, while the Synthesizer rewrites the whole open-thread list on every response. One
changed character read as a brand-new thread and reset the clock, so a rephrased thread could
never reach the 7-day cutoff. Expiry was structurally dead.

MIKE'S RULING (2026-09-05), which these tests encode:
  * Metatron rewording its own list        -> the thread KEEPS its original `added` date.
  * The USER engaging the thread this turn -> the date REFRESHES.

That is the grace rule's principle applied one level down: the system re-stating its own prior
output is not evidence of anything, including not evidence of newness.

Identity is a KEY comparison, never a similarity score — open-ended semantic matching is the
class `[DB-0827-07]` was closed to keep out. Anchor sets, `_IDENTITY_MIN_SHARED_ANCHORS` shared
tokens. The recorded false-positive trap ("call the dentist" vs "call mom later", 0.5 on the
grace bar's 0.34) is asserted below as staying two threads.

Every check here FAILS on the pre-2026-09-05 code except the false-positive one, which passes
both before and after and is there to prove the fix did not buy expiry by over-merging.

Run:  python3 tests/test_thread_identity.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "thread_identity_test"

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def _age_all(tracker_path: Path, days_ago: int) -> None:
    """Back-date every open thread on disk to a fixed age."""
    data = json.loads(tracker_path.read_text())
    old = (date.today() - timedelta(days=days_ago)).isoformat()
    for t in data["open_threads"]:
        t["added"] = old
    tracker_path.write_text(json.dumps(data))


def _tick(tracker_path: Path) -> None:
    """
    Advance the clock one day: shift each thread's stored `added` back by a day, whatever it
    currently says.

    RELATIVE, not absolute, and the distinction is the whole test. Back-dating to a fixed age
    would hand every thread the age the assertion needs and pass on the broken code too — which
    is the shape of mistake that let the first version of grace ship green. A relative tick
    reproduces the real failure honestly: on the old code each rewording reset `added` to today
    and the tick moved it to yesterday, so the thread sat permanently one day old and the
    7-day cutoff was unreachable no matter how long the loop ran.
    """
    data = json.loads(tracker_path.read_text())
    for t in data["open_threads"]:
        if t.get("added"):
            t["added"] = (date.fromisoformat(t["added"]) - timedelta(days=1)).isoformat()
    tracker_path.write_text(json.dumps(data))


def main() -> int:
    from core.persona import persona_data_dir, persona_scope
    from tools.context_tracker import (
        _OPEN_THREAD_EXPIRY_DAYS,
        _anchor_tokens,
        _same_thread,
        read_context_tracker,
        write_context_tracker,
    )

    today = date.today().isoformat()

    with persona_scope(PERSONA):
        data_dir = persona_data_dir()
        tracker_path = data_dir / "context.json"
        audit_path = data_dir / "context_audit.jsonl"

        # --- (a) A Synthesizer rewording preserves the birthdate -------------------------
        # The measured failure, in miniature: the same thread, rephrased once a day, with the
        # user never mentioning it. Before the fix each rewrite stamped today and the age never
        # exceeded zero.
        print("(a) Metatron rewording its own list does not reset the clock:")
        shutil.rmtree(data_dir, ignore_errors=True)
        write_context_tracker(["the mover's claim is still unresolved"], [], [])
        _age_all(tracker_path, 3)   # opened three days ago; the cutoff is not in play yet
        birthdate = read_context_tracker()["open_threads"][0]["added"]

        wordings = [
            "still waiting on the mover's claim",
            "the mover's claim has not been resolved yet",
            "unresolved: the movers claim",
            "the mover's claim, still open",
        ]
        for wording in wordings:
            write_context_tracker([wording], [], [], user_text="what's the weather like")
        state = read_context_tracker()
        check(
            "four rewordings later, the thread still has ONE entry",
            len(state["open_threads"]) == 1,
            str(state["open_threads"]),
        )
        check(
            "the reworded thread keeps its original added date",
            state["open_threads"][0]["added"] == birthdate,
            str(state["open_threads"]),
        )
        last = json.loads(audit_path.read_text().splitlines()[-1])
        check(
            "the audit line names it as reworded, not merely added",
            last["reworded"] == ["the mover's claim, still open"],
            str(last),
        )

        # --- (b) A user-driven rewording refreshes the date -------------------------------
        print("\n(b) the user engaging a thread refreshes it:")
        shutil.rmtree(data_dir, ignore_errors=True)
        write_context_tracker(["the mover's claim is still unresolved"], [], [])
        _age_all(tracker_path, 4)
        write_context_tracker(
            ["chasing the mover's claim response this week"], [], [],
            user_text="I finally got somewhere with the movers claim today",
        )
        state = read_context_tracker()
        check(
            "user-engaged rewording is stamped today",
            state["open_threads"][0]["added"] == today,
            str(state["open_threads"]),
        )
        check(
            "and it is still one thread, not two",
            len(state["open_threads"]) == 1,
            str(state["open_threads"]),
        )

        # --- (c) The recorded false-positive trap stays two threads -----------------------
        # "call the dentist" vs "call mom later" scores 0.5 word-overlap against the grace bar's
        # 0.34 — the exact pair [DB-0814-02] flagged. Under anchor sets they are {dentist} and
        # {mom}: "call" and "later" are generic, and one shared token would not be enough anyway.
        print("\n(c) short generic threads are NOT merged:")
        check(
            "_same_thread: 'call the dentist' is not 'call mom later'",
            not _same_thread(_anchor_tokens("call the dentist"),
                             _anchor_tokens("call mom later")),
            f"{sorted(_anchor_tokens('call the dentist'))} vs "
            f"{sorted(_anchor_tokens('call mom later'))}",
        )
        shutil.rmtree(data_dir, ignore_errors=True)
        write_context_tracker(["call the dentist"], [], [])
        _age_all(tracker_path, 3)
        write_context_tracker(["call the dentist", "call mom later"], [], [])
        state = read_context_tracker()
        dates = {t["text"]: t["added"] for t in state["open_threads"]}
        check(
            "both threads are carried separately",
            len(dates) == 2,
            str(dates),
        )
        check(
            "the new one is stamped today, not given the dentist thread's birthdate",
            dates["call mom later"] == today
            and dates["call the dentist"] != today,
            str(dates),
        )
        # Numbered siblings must also stay apart — digits are anchors for this reason.
        check(
            "_same_thread: 'topic 3' is not 'topic 4'",
            not _same_thread(_anchor_tokens("topic 3"), _anchor_tokens("topic 4")),
        )
        # ...and a genuine rewording of one subject IS matched.
        check(
            "_same_thread: a genuine rewording matches",
            _same_thread(
                _anchor_tokens("bookstore P&L review scheduled for Thursday"),
                _anchor_tokens("the bookstore P&L review, now on Tuesday"),
            ),
        )

        # --- (d) A thread reworded but never engaged actually expires ---------------------
        # The end-to-end claim: with the fix, a thread the Synthesizer keeps rephrasing and the
        # user never mentions reaches the cutoff and lands in `expired_open_threads`. On the old
        # code this loop ran forever with the thread permanently one day old.
        print("\n(d) rewording alone no longer confers immortality:")
        shutil.rmtree(data_dir, ignore_errors=True)
        write_context_tracker(["post-travel recovery still dragging"], [], [])
        rewrites = [
            "post-travel recovery is still dragging on",
            "recovery from the travel is dragging",
            "still recovering from the travel",
            "post-travel recovery continues",
        ]
        expired_texts: list[str] = []
        for day in range(1, _OPEN_THREAD_EXPIRY_DAYS + 4):
            _tick(tracker_path)
            write_context_tracker(
                [rewrites[day % len(rewrites)]], [], [],
                user_text="can you check my calendar for tomorrow",
            )
            raw = json.loads(tracker_path.read_text())
            expired_texts = [t["text"] for t in raw.get("expired_open_threads", [])]
            if expired_texts:
                break
        check(
            "a reworded-but-unengaged thread reaches the cutoff and is archived",
            bool(expired_texts),
            f"nothing expired in {_OPEN_THREAD_EXPIRY_DAYS + 3} days of rewrites",
        )
        state = read_context_tracker()
        check(
            "and it does not walk straight back in under its newest wording",
            state["open_threads"] == [],
            str(state["open_threads"]),
        )
        check(
            "the expiry is visible in the audit line",
            any(json.loads(ln)["expired"]
                for ln in audit_path.read_text().splitlines() if ln.strip()),
        )

        # --- Over-merging is the tolerated failure, not under-merging ----------------------
        # An identity match that is wrong means the older birthdate wins and something may
        # expire early — into an archive, recoverable, and re-openable the moment the user
        # mentions it. Asserted here so a future session tuning the key knows which way to lean.
        print("\nthe archive is recoverable — the user can always bring a thread back:")
        check(
            "an archived thread returns when the user engages it",
            True if write_context_tracker(
                ["post-travel recovery still dragging"], [], [],
                user_text="my post-travel recovery is finally over",
            ) else False,
        )
        state = read_context_tracker()
        check(
            "the returned thread is live again with a fresh date",
            len(state["open_threads"]) == 1
            and state["open_threads"][0]["added"] == today,
            str(state["open_threads"]),
        )

        shutil.rmtree(data_dir, ignore_errors=True)

    print()
    if _failures:
        print(f"{len(_failures)} failure(s): {', '.join(_failures)}")
        return 1
    print("All thread-identity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
