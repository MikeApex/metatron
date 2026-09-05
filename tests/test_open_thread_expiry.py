"""
tests/test_open_thread_expiry.py — open-thread expiry in tools/context_tracker.py.

Covers the follow-on decision to [DB-0814-02] (Mike, 2026-08-15): open threads carried an
`added` timestamp but nothing ever acted on it, so "post-travel recovery" could still stay
listed as live context indefinitely as long as it kept being resent.

This also covers the SAME-DAY CORRECTION to the first version of this feature: the original
grace rule granted grace whenever a thread's text was present in `open_threads` that turn, which
sounds like "the model actively resent it" but is not — the Synthesizer re-emits the entire
`open_threads` list on every single turn via the inline [CONTEXT] block, so that condition was
true of every live thread on every write and nothing could ever actually expire. The critical
test below (`test: byte-identical resend with no user engagement expires`) is the one the first
version of this suite could not have caught, because it never modelled "resent, but the user
never engaged it."

The corrected rule: a thread past the cutoff is archived unless the user's own turn engages it
(content-word overlap, `_user_engages_thread`).

A SECOND correction, 2026-09-05: there used to be a second escape — "its wording materially
changed" — and it was the same mistake one level down. It rested on exact-text identity, and the
Synthesizer rewords the list it re-emits every response, so in 20 days of production nothing ever
grew old enough to expire. Rewording by Metatron now preserves a thread's date; only the user
refreshes it. The block below that asserted the old behaviour is inverted rather than deleted.
The ruling's own coverage lives in tests/test_thread_identity.py.

Run:  python3 tests/test_open_thread_expiry.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PERSONA = "open_thread_expiry_test"

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def _age_thread(tracker_path: Path, text: str, days_ago: int) -> None:
    """Back-date an existing open thread's `added` field directly on disk."""
    data = json.loads(tracker_path.read_text())
    old = (date.today() - timedelta(days=days_ago)).isoformat()
    for t in data["open_threads"]:
        if t.get("text") == text:
            t["added"] = old
    tracker_path.write_text(json.dumps(data))


def main() -> int:
    from core.persona import persona_data_dir, persona_scope
    from tools.context_tracker import (
        _EXPIRED_OPEN_THREADS_CAP,
        _OPEN_THREAD_EXPIRY_DAYS,
        _user_engages_thread,
        read_context_tracker,
        write_context_tracker,
    )

    today = date.today().isoformat()

    with persona_scope(PERSONA):
        tracker_path = persona_data_dir() / "context.json"
        shutil.rmtree(persona_data_dir(), ignore_errors=True)

        # --- A fresh thread is untouched -------------------------------------------------
        write_context_tracker(["new topic"], [], [])
        state = read_context_tracker()
        check(
            "fresh thread has today's added date",
            state["open_threads"][0] == {"text": "new topic", "added": today},
        )
        check("fresh thread is not archived", "expired_open_threads" not in state)

        # --- Regression guard on d40e73c: normal carry-forward of `added` -----------------
        write_context_tracker(["new topic"], [], [])
        state = read_context_tracker()
        check(
            "unchanged resend within the window keeps its original added date",
            state["open_threads"][0]["added"] == today,
        )

        # --- THE critical test: byte-identical resend, no user engagement -> expires ------
        # This is the exact "post-travel recovery" shape: the Synthesizer keeps re-listing the
        # same text every turn (open_threads is fully re-emitted each time) but the user never
        # actually brings it up again. The first (corrected-away) version of this feature
        # treated "text present in open_threads" as proof of active re-assertion, so this case
        # would have passed grace forever and never expired.
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["post-travel recovery"], [], [])
        for _ in range(20):
            # Simulate the Synthesizer re-emitting the identical list turn after turn, with
            # unrelated user messages that never reference the thread.
            _age_thread(tracker_path, "post-travel recovery", _OPEN_THREAD_EXPIRY_DAYS + 1)
            write_context_tracker(
                ["post-travel recovery"], [], [],
                user_text="what's on my calendar today",
            )
        state = read_context_tracker()
        open_texts = [t["text"] for t in state["open_threads"]]
        check(
            "byte-identical resend with no user engagement expires (the incident case)",
            "post-travel recovery" not in open_texts,
            str(open_texts),
        )
        raw = json.loads(tracker_path.read_text())
        archived_texts = [t["text"] for t in raw["expired_open_threads"]]
        check(
            "the expired thread is archived, not deleted",
            "post-travel recovery" in archived_texts,
        )

        # --- Grace signal 1: user's own turn engages the thread ---------------------------
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["bookstore P&L review scheduled for Thursday"], [], [])
        _age_thread(
            tracker_path, "bookstore P&L review scheduled for Thursday",
            _OPEN_THREAD_EXPIRY_DAYS + 2,
        )
        write_context_tracker(
            ["bookstore P&L review scheduled for Thursday"], [], [],
            user_text="still sorting the bookstore P&L numbers before the review",
        )
        state = read_context_tracker()
        open_texts = [t["text"] for t in state["open_threads"]]
        check(
            "user turn referencing the thread grants grace",
            "bookstore P&L review scheduled for Thursday" in open_texts,
            str(open_texts),
        )
        graced = next(
            t for t in state["open_threads"]
            if t["text"] == "bookstore P&L review scheduled for Thursday"
        )
        check("grace gives it a fresh stamp (today)", graced["added"] == today, str(graced))
        raw = json.loads(tracker_path.read_text())
        archived_texts = [t["text"] for t in raw.get("expired_open_threads", [])]
        check(
            "graced-by-engagement thread is not archived",
            "bookstore P&L review scheduled for Thursday" not in archived_texts,
        )

        # --- Grace signal 1, negative: unrelated user turn does not grant grace -----------
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["Cato chapter structure still unresolved"], [], [])
        _age_thread(
            tracker_path, "Cato chapter structure still unresolved", _OPEN_THREAD_EXPIRY_DAYS + 2
        )
        write_context_tracker(
            ["Cato chapter structure still unresolved"], [], [],
            user_text="can you check the weather for this weekend",
        )
        state = read_context_tracker()
        open_texts = [t["text"] for t in state["open_threads"]]
        check(
            "unrelated user turn does not grant grace",
            "Cato chapter structure still unresolved" not in open_texts,
            str(open_texts),
        )

        # --- Direct unit check on the matcher itself ---------------------------------------
        check(
            "_user_engages_thread: overlapping content words match",
            _user_engages_thread(
                "bookstore P&L review scheduled for Thursday",
                "just finished the bookstore review numbers",
            ),
        )
        check(
            "_user_engages_thread: no overlap does not match",
            not _user_engages_thread(
                "bookstore P&L review scheduled for Thursday",
                "what's the weather like tomorrow",
            ),
        )
        check(
            "_user_engages_thread: no user_text does not match",
            not _user_engages_thread("bookstore P&L review scheduled for Thursday", None),
        )

        # --- Grace signal 2 REVERSED: rewording alone no longer resets the clock ----------
        # This block asserted the OPPOSITE until 2026-09-05 ("reworded thread appears fresh,
        # stamped today"), and that assertion was the bug. Grace signal 2 rested on exact-text
        # identity, so any rewording read as a brand-new thread — and the Synthesizer rewords the
        # whole list every response. Measured over 20 days: 111 writes, 0 expiries, every live
        # thread stamped with the current day. Mike's ruling: a rewording by Metatron preserves
        # the thread's original date; only the USER engaging it refreshes. Full reasoning in the
        # THREAD IDENTITY block in tools/context_tracker.py; the ruling's own coverage is in
        # tests/test_thread_identity.py. Kept here, inverted, so the old expectation cannot
        # quietly come back.
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["bookstore P&L review scheduled for Thursday"], [], [])
        _age_thread(
            tracker_path, "bookstore P&L review scheduled for Thursday",
            _OPEN_THREAD_EXPIRY_DAYS + 2,
        )
        write_context_tracker(
            ["bookstore P&L review scheduled for next Tuesday instead"], [], [],
        )
        state = read_context_tracker()
        open_texts = {t["text"]: t for t in state["open_threads"]}
        check(
            "a past-cutoff thread the user never engaged does NOT survive by being reworded",
            open_texts == {},
            str(open_texts),
        )
        raw = json.loads(tracker_path.read_text())
        archived_texts = [t["text"] for t in raw["expired_open_threads"]]
        check(
            "the old (now-superseded) wording is archived, since it had crossed the cutoff",
            "bookstore P&L review scheduled for Thursday" in archived_texts,
        )
        # ...and within the window, a rewording is carried forward on its ORIGINAL date rather
        # than restarting the clock. This is the case the measurement caught in production.
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["bookstore P&L review scheduled for Thursday"], [], [])
        _age_thread(
            tracker_path, "bookstore P&L review scheduled for Thursday",
            _OPEN_THREAD_EXPIRY_DAYS - 2,
        )
        expected_added = (
            date.today() - timedelta(days=_OPEN_THREAD_EXPIRY_DAYS - 2)
        ).isoformat()
        write_context_tracker(
            ["bookstore P&L review scheduled for next Tuesday instead"], [], [],
        )
        state = read_context_tracker()
        check(
            "a rewording inside the window keeps the original added date",
            [t["added"] for t in state["open_threads"]] == [expected_added],
            str(state["open_threads"]),
        )

        # --- Bare-string legacy data reads without error -----------------------------------
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        persona_data_dir().mkdir(parents=True, exist_ok=True)
        tracker_path.write_text(json.dumps({
            "last_session": "2026-08-01",
            "open_threads": ["legacy bare string"],
            "patterns": [],
            "follow_ups": [],
        }))
        state = read_context_tracker()
        check(
            "legacy bare-string thread reads without crashing",
            state["open_threads"] == [{"text": "legacy bare string", "added": None}],
        )
        check(
            "no expired_open_threads key doesn't crash the read",
            "expired_open_threads" not in state,
        )
        # A write against this data must not auto-expire the undated legacy thread, even with
        # no user engagement and no resend of matching text.
        write_context_tracker(["something else entirely"], [], [])
        raw = json.loads(tracker_path.read_text())
        check(
            "undated legacy thread is never auto-expired",
            not any(t["text"] == "legacy bare string" for t in raw["expired_open_threads"]),
            str(raw["expired_open_threads"]),
        )

        # --- The archived list respects its cap ---------------------------------------------
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["seed"], [], [])
        for i in range(_EXPIRED_OPEN_THREADS_CAP + 5):
            text = f"topic {i}"
            write_context_tracker([text], [], [])
            _age_thread(tracker_path, text, _OPEN_THREAD_EXPIRY_DAYS + 1)
            write_context_tracker(["seed"], [], [])  # omit `text`, no engagement -> expires
        raw = json.loads(tracker_path.read_text())
        check(
            "expired_open_threads is capped",
            len(raw["expired_open_threads"]) == _EXPIRED_OPEN_THREADS_CAP,
            f"got {len(raw['expired_open_threads'])}",
        )
        archived_texts = [t["text"] for t in raw["expired_open_threads"]]
        check(
            "the cap keeps the most recently expired entries",
            "topic 4" not in archived_texts
            and f"topic {_EXPIRED_OPEN_THREADS_CAP + 4}" in archived_texts,
            str(archived_texts[:3]) + " ... " + str(archived_texts[-3:]),
        )

        shutil.rmtree(persona_data_dir(), ignore_errors=True)

    print()
    if _failures:
        print(f"{len(_failures)} failure(s): {', '.join(_failures)}")
        return 1
    print("All open-thread expiry checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
