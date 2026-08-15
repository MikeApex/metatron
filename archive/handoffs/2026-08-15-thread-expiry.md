# Handoff — open-thread expiry [DB-0814-02]

**Shipped:** `tools/context_tracker.py` — `open_threads` now auto-drop 7 days after their
`added` date, archived (never deleted) to a new `expired_open_threads` list, capped at 50
entries, never returned by `read_context_tracker()`. New test suite
`tests/test_open_thread_expiry.py`, 16/16 passing. `tests/test_clinical_threads.py` re-run
clean (17/17) — no regression. Did not touch `core/orchestrator.py`.

**Commit:** `f4d18ca` — "Open threads now expire at write time instead of staying live forever".
Not a no-op (`git log` confirms).

**Cutoff chosen: 7 days.** The originating incident ran two weeks — clearly too long; this
project runs daily-ish sessions, so a full week without the model dropping a thread itself is
worth querying rather than trusting. Comment block above `_OPEN_THREAD_EXPIRY_DAYS` in
`tools/context_tracker.py:56` has the full reasoning.

**Grace/carry-forward tension, resolved:** `_expire_open_threads()` runs *before*
`_merge_open_threads()`, splitting on cutoff first. Threads inside the window are untouched and
still get the original carry-forward-the-`added`-date treatment (regression-guarded by the new
test). A thread that crosses the cutoff and is *not* resent this turn is archived. A thread that
crosses the cutoff and *is* resent this turn gets one fresh stamp (its `added` cleared so the
merge step treats it as new) instead of being archived mid-conversation. Threads with no `added`
(legacy data) are never auto-expired — no reliable age to test.

**Cap: 50 archived entries**, oldest dropped first (`expired_open_threads[-50:]`) — bounds file
growth while keeping ample recent history for review.

**What's proven by test vs. not:** the test suite exercises the mechanism directly (back-dating
`added` on disk, then driving writes) — cutoff, archive, grace, cap, and legacy-data migration
are all verified. What is **not** tested: real Diarist behavior — whether it actually stops
resending a thread once it's genuinely resolved, or keeps blindly copying it forward (the
original incident's failure mode). If a caller always resends unchanged text every session, the
grace rule as specified will keep resetting the clock indefinitely; this is what the task asked
for ("active re-assertion resets the clock"), not a bug in this implementation, but it means the
auto-drop's real-world backstop value depends on the Diarist actually dropping threads it no
longer means, which this change does not itself enforce or verify.

**Not deployed.** `tools/` deploys to the VM — this worktree change has not been pushed/deployed;
flagging per manifest instructions.

**Transcript archive:** `archive_chats.py` found no JSONL for this worktree path — this worker
ran as an in-process subagent dispatch, not a standalone Claude Code session, so no
`-Users-md-homefolder-Desktop-metatron-wt-thread-expiry` project transcript exists to export.

**For SESSION.md:** `[DB-0814-02]`'s remaining half (the expiry policy) is now built and tested
in this worktree at `f4d18ca`, not yet merged/deployed. Report evidence to the coordinator for
merge and closure decision — do not mark closed here per worker instructions.
