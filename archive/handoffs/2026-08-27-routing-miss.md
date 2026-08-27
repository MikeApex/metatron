# 2026-08-27 — routing-miss handoff

**Shipped:** `[DB-0827-05]` fixed. `ROUTING_MISS` moved from `KNOWN_DEAD_TYPES` to
`MACHINE_TYPES` in `scripts/sync_dev_backlog.py` — it was classed dead 2026-08-13 on a
code-only grep of `core/`/`tools/`, but the real emitter is the Synthesizer's agent
instructions (`config/agents/synthesizer.md`, 8 call sites at runtime), invisible to
that grep. 5 events were silently discarded on the live VM since 08-11.

**Also:** added `FALSE_ACTION_CLAIM` to `MACHINE_TYPES` pre-emptively, ahead of the
false-action-claim detector another worker is building today, so the same silent-drop
gap can't reopen for it. Reworded the `KNOWN_DEAD_TYPES` comment to require checking
`config/agents/*.md` (not just Python) before naming a type dead. `KNOWN_DEAD_TYPES`
is now empty.

**Commit:** `5b444be` — "Stop discarding ROUTING_MISS: the emitter was never Python"
(`scripts/sync_dev_backlog.py`, `tests/test_quality_event_reconciliation.py`).

**Test verification:** updated the ROUTING_MISS assertions in
`tests/test_quality_event_reconciliation.py`, confirmed the new assertions fail against
the pre-fix script (via `git stash` of just the script file), then pass with the fix.
Full-file run: 4/5 checks pass. The 1 failure
(`FALSE_COMPLETION_CLAIM`/`MERGE_AUTO_ACCEPTED`/`THINKING_CAP_HIT` unaccounted for) is
pre-existing and out of scope — confirmed present on `ce94dd1` before any of my edits.
Worth its own backlog item if not already filed.

**Close `[DB-0827-05]`** with evidence: commit `5b444be` + the stash-verified test flip
above.

**For `SESSION.md`:** none of my manifest files are tracked there; no primer change
needed from this item.
