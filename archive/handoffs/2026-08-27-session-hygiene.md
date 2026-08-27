# 2026-08-27 — session hygiene worker (worktree `wt/session-hygiene`)

All five manifest items shipped, five commits, `core/orchestrator.py`, `tools/logger.py`,
`tools/context_tracker.py` and five new test files. **Not deployed.** Every test is a
standalone script (`python3 tests/<file>.py`), matching the house style in `tests/`.

| Commit | What a user would notice |
|---|---|
| `e6bde3d` | The journal no longer records days nobody spoke — `has_real_user_turn()` gates the Diarist dispatch; a proactive session the user replies to still journals, because the reply is a separate non-proactive turn. Suppression logs a debug line. Test: `tests/test_diarist_user_turn_gate.py` |
| `24dabae` | A bare template label (`CLARIFICATION_NEEDED:`) no longer becomes a correction event; the same label with content after the colon is kept intact. Test: `tests/test_empty_template_label_events.py` |
| `e673330` | A reply claiming it wrote something down, with no write-family tool call in the turn's trace, now logs a `FALSE_ACTION_CLAIM` quality event. **Detect and log only** — the response is never suppressed or edited. Test: `tests/test_false_action_claim.py` |
| `cbd5ca3` | Carried-forward state now shows its age in the assembled context ("logged 9 days ago"; log lines dated *and* aged). Annotation, not filtering. Test: `tests/test_context_age_annotation.py` |
| `17142c0` | Context-tracker writes now leave a history: one line per write in `context_audit.jsonl` beside `context.json`, 600, with added / removed / expired split apart. Test: `tests/test_context_audit_line.py` |

## Backlog items to close, and the evidence

1. **[DB-0822-05]** — closeable. `e6bde3d` plus the gate test; the code refusal replaces the
   agent-file rule (`82d394b`) that failed. Live confirmation: a scheduled run should now show
   `diarist suppressed (no user turn)` in the trace and no journal entry for a silent day.
2. **[DB-0827-07]** (new, filed by the assigning session) — closeable on `24dabae`; the count of
   new `CLARIFICATION_NEEDED:`-only events after deploy should be zero.
3. **[DB-0815-11]** — **detection half only.** The policy half (may `write_persona` self-apply?)
   is untouched and still open; the item cannot be closed outright.
4. **[DB-0822-06]** — age-out half done. **The derived-count half has no clean code-side
   interception** and I did not force one: "Day 3 of a 5-day hiatus" is a string a specialist
   writes into free-text `notes`, and code cannot tell it from a legitimate quotation. The age
   annotation makes it *visible* as three days old, which is the most code can do here.
5. **[DB-0814-02]** — data-source half done. The measurement itself needs ~a week of audit lines
   on the VM before "does expiry fire?" can be answered; deploy is the gate, not more code.

## Must be carried by SESSION.md / another owner

- **`FALSE_ACTION_CLAIM` needs adding to the sync script's event registry.**
  `scripts/sync_dev_backlog.py` is another worker's file, so I did not touch it — the type must
  go in `WANTED` (or `KNOWN_DEAD_TYPES` with a note) or the events are collected by nobody.
- `tests/test_quality_event_reconciliation.py` **already failed on HEAD** (`ce94dd1`) for three
  unregistered types — `FALSE_COMPLETION_CLAIM`, `MERGE_AUTO_ACCEPTED`, `THINKING_CAP_HIT`.
  Mine makes it four. Same one-line fix in the same file, same owner.
- **Deploy owed:** `core/orchestrator.py`, `tools/logger.py`, `tools/context_tracker.py` → VM.
- Two related mechanisms now sit near each other and should not be merged by a later session:
  `enforce_pending_receipt()` catches a *gated* action reported as finished (confirm tokens);
  `check_false_action_claims()` catches a *persistence* claim with no write at all. Different
  evidence, different response (one amends the reply, one only logs).
- Known residual, recorded deliberately: the Diarist runs fire-and-forget with no trace of its
  own, so a claim satisfied only by the journal can still be flagged. A wrong line in a quality
  log, never a wrong word to the user.
- Intraday staleness (the 07:14/10:00 Teams-link case) is **not** fixed by day-granular ages —
  the log is one merged file per day with no per-field timestamps. That is the deeper cause and
  needs its own item if Mike wants it.
