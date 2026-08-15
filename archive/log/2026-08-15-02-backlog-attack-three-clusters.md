### 2026-08-15 (`/backlog attack` — three clusters, one hook bug found and filed)

Ran `/backlog attack`. Scored `## Now` for ease (1–10, position taken as given): items 1
([DB-0810-13]) and 3 ([DB-0810-12]) scored ≤3 — broad behavioral change and a core provider
hot path respectively — and were skipped for parallel work per the standing rule that
routing/persona/scheduler-adjacent work is never delegated, even top-ranked. Items 4–7 were
time-gated or needed VM access no worker gets. Three clusters went forward, all verified
against current code before dispatch.

**Cluster 2 — instruction-only fixes, built here (Red tier, never delegated):**
[DB-0810-17](a) and [DB-0814-01]. Coordinator was declining CRM contact-count questions as
needing an external connection it doesn't have, when Relationships already holds
`list_contacts`/`search_contacts`. Logistics was correctly re-checking pending confirmations
(an awaited email) every proactive session but surfacing "still nothing" to the user on every
check instead of only on a real change. Fixed by adding routing/reporting guidance to
`coordinator.md` and `logistics.md`. Commit `b11e775`.

**Two workers dispatched into worktrees** (`new_worktree.sh`, no `isolation` flag, per
`/fix` § 3):

- **[DB-0810-09]** — quality-event registry. `write_quality_event()` accepted any
  `event_type`; `sync_dev_backlog.py`'s `WANTED` set silently dropped `USER_CORRECTION`
  (139/day, the largest signal in the file) and `CALENDAR_DUPLICATE`. Fixed the prerequisite
  first (blank `detail` now raises — was ~70% empty on `USER_CORRECTION`), added both types to
  `WANTED`, gave `CALENDAR_DUPLICATE` a stable uid-pair signature, and added
  `tests/test_quality_event_reconciliation.py` — a reconciliation test rather than a shared
  import, because `sync_dev_backlog.py` is deliberately stdlib-only (SessionStart hook, no
  venv). The test itself caught a third silently-dropped type, `CONTEXT_BLOCK_UNPARSED`, not
  named in the original item — fixed in the same pass. Commit `048e937`.
- **[DB-0814-02]** — `open_threads` timestamp. Was a bare `list[str]`, so nothing could tell
  how stale a thread was — the cause of "post-travel recovery" staying live for two weeks.
  Added a server-stamped `added` date per entry (never model-supplied, matching the existing
  `clinical_threads` convention), a merge function that carries the date forward when the same
  text is resent so a thread doesn't look freshly opened every session, and a read-time
  migration for old bare-string data. Scoped deliberately to the timestamp only — the expiry
  policy is a separate, still-open decision. Commit `d40e73c`.

**Both workers hit the same infrastructure bug at commit time, independently.**
`scripts/hook_commit_guard.py` resolves its project root from `$CLAUDE_PROJECT_DIR`, which
inside a worktree session still points at the main tree, not the worktree — so it runs
`git status` against the wrong tree, can't find the worktree's own edits there, and fails
closed as an unresolvable path expression. This is the same class of gap
`hook_context_gate.py` had, fixed 2026-08-14; `hook_commit_guard.py` didn't get the
equivalent fix. Both workers correctly stopped rather than force the
`METATRON_COMMIT_GUARD=off` override themselves — it was refused by the auto-mode
classifier in their non-interactive sessions, and forcing a permission denial is exactly
the failure mode `/backlog`'s worker protocol exists to prevent.

**What was believed, and corrected:** initially treated this as a one-off classifier hiccup
on a single retry. It was not — the coordinating session hit the identical denial on its own
first attempt to commit cluster 3, confirming the block is structural (the hook, not the
classifier, and not session-specific) before Mike explicitly approved the override.

Coordinating session independently re-verified both diffs before committing on the workers'
behalf — re-ran `py_compile`, re-ran both workers' test suites, read every changed line, and
confirmed via grep that no existing `write_quality_event` call site passes blank `detail` (so
the new `ValueError` guard can't break anything live; every call site is wrapped in
`try/except Exception` regardless). Both worktree branches merged into `main` cleanly, no
conflicts (`2fcf0bc`, `66fd00b`), `qa_sweep.sh` 9/9 on the integrated tree, worktrees torn
down (`rm_worktree.sh`, branches deleted as fully merged after copying each worker's handoff
into the main tree's `archive/handoffs/` first).

**Filed [DB-0815-01]** — the commit-guard bug itself — into `## Now` at Mike's explicit
instruction ("file the bug as now"), #11 against the ~10 cap. Recommended fix: mirror
whatever `hook_context_gate.py`'s 08-14 fix did — resolve root from the target path being
committed, not `$CLAUDE_PROJECT_DIR`.

**Deploy owed, accumulated across this session and the one before it:** `tools/logger.py`,
`tools/context_tracker.py`, `core/orchestrator.py`, `config/agents/coordinator.md`,
`config/agents/logistics.md`, plus the still-outstanding evening-ritual move
(`6913ad7`, session 2026-08-15-01) predating this one. None of it has reached the VM yet.

Commits: `b11e775`, `048e937`, `d40e73c`, `2fcf0bc`, `66fd00b`, `ac25f04`. Not deployed.
