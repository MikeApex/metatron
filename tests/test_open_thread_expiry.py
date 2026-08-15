"""
tests/test_open_thread_expiry.py — open-thread expiry in tools/context_tracker.py.

Covers the follow-on decision to [DB-0814-02] (Mike, 2026-08-15): open threads carried an
`added` timestamp but nothing ever acted on it, so "post-travel recovery" could still stay
listed as live context indefinitely as long as it kept being resent. This adds auto-drop at
the 7-day cutoff (`_OPEN_THREAD_EXPIRY_DAYS`), archived (never deleted) to
`expired_open_threads`, with a grace rule so a thread actively resent past the cutoff gets one
fresh stamp instead of vanishing mid-conversation.

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
        check(
            "fresh thread is not archived",
            "expired_open_threads" not in state,
        )

        # --- Regression guard on d40e73c: normal carry-forward of `added` -----------------
        write_context_tracker(["new topic"], [], [])
        state = read_context_tracker()
        check(
            "unchanged resend keeps its original added date (carry-forward, not reset)",
            state["open_threads"][0]["added"] == today,
        )

        # --- A thread older than the cutoff, NOT resent -> dropped and archived -----------
        write_context_tracker(["stale topic"], [], [])
        _age_thread(tracker_path, "stale topic", _OPEN_THREAD_EXPIRY_DAYS + 1)
        # Next write omits "stale topic" entirely — model has moved on.
        write_context_tracker(["new topic"], [], [])
        state = read_context_tracker()
        open_texts = [t["text"] for t in state["open_threads"]]
        check("expired thread is dropped from open_threads", "stale topic" not in open_texts)

        raw = json.loads(tracker_path.read_text())
        archived = {t["text"]: t for t in raw["expired_open_threads"]}
        check("expired thread appears in expired_open_threads", "stale topic" in archived)
        check(
            "archived entry preserves its original added date",
            archived.get("stale topic", {}).get("added")
            == (date.today() - timedelta(days=_OPEN_THREAD_EXPIRY_DAYS + 1)).isoformat(),
            str(archived.get("stale topic")),
        )
        check(
            "archived entry carries an expired_on stamp",
            archived.get("stale topic", {}).get("expired_on") == today,
        )
        check(
            "expired_open_threads is never returned by read_context_tracker",
            "expired_open_threads" not in state,
        )

        # --- Grace rule: resent past the cutoff survives, is NOT archived -----------------
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["still going"], [], [])
        _age_thread(tracker_path, "still going", _OPEN_THREAD_EXPIRY_DAYS + 3)
        write_context_tracker(["still going"], [], [])  # model actively resends it
        state = read_context_tracker()
        open_texts = [t["text"] for t in state["open_threads"]]
        check("actively resent past-cutoff thread survives (grace)", "still going" in open_texts)
        graced = next(t for t in state["open_threads"] if t["text"] == "still going")
        check("grace gives it a fresh stamp (today)", graced["added"] == today, str(graced))
        raw = json.loads(tracker_path.read_text())
        archived_texts = [t["text"] for t in raw.get("expired_open_threads", [])]
        check("grace does not archive the thread", "still going" not in archived_texts)

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
        check("no expired_open_threads key doesn't crash the read", "expired_open_threads" not in state)
        # A write against this data must not auto-expire the undated legacy thread.
        write_context_tracker(["legacy bare string"], [], [])
        state = read_context_tracker()
        check(
            "undated legacy thread is never auto-expired",
            state["open_threads"][0]["text"] == "legacy bare string",
        )

        # --- The archived list respects its cap ---------------------------------------------
        shutil.rmtree(persona_data_dir(), ignore_errors=True)
        write_context_tracker(["seed"], [], [])
        for i in range(_EXPIRED_OPEN_THREADS_CAP + 5):
            text = f"topic {i}"
            write_context_tracker([text], [], [])
            _age_thread(tracker_path, text, _OPEN_THREAD_EXPIRY_DAYS + 1)
            write_context_tracker(["seed"], [], [])  # omit `text` -> it expires this write
        raw = json.loads(tracker_path.read_text())
        check(
            "expired_open_threads is capped",
            len(raw["expired_open_threads"]) == _EXPIRED_OPEN_THREADS_CAP,
            f"got {len(raw['expired_open_threads'])}",
        )
        archived_texts = [t["text"] for t in raw["expired_open_threads"]]
        check(
            "the cap keeps the most recently expired entries",
            "topic 4" not in archived_texts and f"topic {_EXPIRED_OPEN_THREADS_CAP + 4}" in archived_texts,
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
