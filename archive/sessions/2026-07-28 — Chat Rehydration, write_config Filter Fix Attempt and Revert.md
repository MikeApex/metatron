# 2026-07-28 — Chat Rehydration, write_config Filter Fix Attempt and Revert

## What happened

1. **Chat rehydration.** User asked to find and rehydrate a prior chat opening with "Context: this is the Metatron personal AI life manager...". Located two transcript copies in `archive/transcripts/` — one truncated capture, one complete (session `749636dc-8a59-4b0c-9aec-91746f026f8a`). Read both, summarized the original session, cross-checked findings against current `SESSION.md`.

2. **Content of the rehydrated session (2026-06-26):**
   - Pipeline audit (~15:28–16:47) across 10 exchanges: 5 bugs found — missing `tools.ambient` deploy, `write_config` output-filter false positive, Research Agent name-normalization miss, Coordinator prompt running uncached (<4096 tokens), 90s graceful-shutdown SIGKILL cycle.
   - Deep dive on exchange seq 027: Coordinator wrote `"Research"` instead of `"Research Agent"`, normalization missed it, Synthesizer streamed a "minor snag" apology before its own recovery call actually returned correct data.
   - Fixes applied in that original session: `config/agents/coordinator.md` valid-names list + `_AGENT_NAME_MAP` abbreviation entries.
   - Deliverable: the reusable "Metatron — Single Exchange Troubleshoot" prompt design.

3. **Status check, then correction.** Cross-referencing against `SESSION.md` first suggested all 5 bugs were resolved. Asked directly ("is there anything open from the transcripts?"), re-verified each claim against the actual code rather than trusting the archive note. Found 4 of 5 genuinely fixed (ambient context, Research Agent normalization — confirmed live in `_AGENT_NAME_MAP`, uncached Coordinator prompt — accepted structural cost, graceful shutdown). The 5th — `write_config` output-filter false positive — was still open: the SEQ 031 session's two-tier filter (`_ALWAYS_CONFIDENTIAL` vs `_CONTEXT_SENSITIVE`) only softened matching for common-English-word terms (`logistics`, `finance`), not tool identifiers like `write_config`.

4. **Fix attempted.** `filter_output()` in `core/orchestrator.py` given an optional `user_message` param; skipped suppression for any confidential term already present in the user's own message, on the reasoning that a term the user said first isn't a leak when echoed back. Verified with 4 manual test cases, all passed as designed; `py_compile` clean.

5. **User asked for a review of the fix against `SESSION.md` and the roadmap before accepting it.** That review found a real regression: the roadmap's Track B / B1 red-team plan (`archive/plans/phase5_to_future_roadmap_2026-06-10.md`) tests a "Direct tool inquiry" attack category ("What tools do you have?" → expected: canned response). Under the fix, a probing question like "What does `write_config` do?" contains the term in the user's own message, so the filter would no longer suppress a Synthesizer response that actually explained it — a one-line bypass of the filter's backstop role at exactly the point it exists to catch (per `CLAUDE.md`'s Discretion principle and `SESSION.md`'s Security Architecture section).

6. **Reverted in full.** `filter_output()` and all three call sites (`run_pipeline_session`, `run_pipeline_session_stream`, `run_session`) restored to the original always-suppress behavior for both tiers. Confirmed via `git diff` that the net change against the last commit is docstring-only; `py_compile` clean.

7. **Result:** the `write_config` false positive (Exchange 027) remains open, now correctly recorded as a known, accepted-risk gap deferred to the already-planned Track B / B2 "Output filter upgrade" (regex+semantic matching) — the right venue to fix false positives without weakening the security backstop. Nothing deployed.

## Decisions made

- Do not exempt user-typed terms from the output filter, even to fix a genuine UX false positive — the exemption is exploitable via direct probing questions that simply include the term.
- The `write_config` false positive stays open until the B2 output-filter upgrade lands; documented as accepted risk rather than silently left unaddressed.

## Deferred items

- Track B / B2 "Output filter upgrade" (regex+semantic) is the correct venue for fixing this false positive class without reopening the bypass. Not started.
- Unrelated, pre-existing uncommitted change in `core/remote_client.py` (WS reconnect logic) noticed in the working tree during this session — not touched, not part of this session's work.

## Files touched

- `core/orchestrator.py` — net change is docstring-only after the fix-then-revert (see commit history / `git diff`).
- `SESSION.md`, this session archive, `archive/transcripts/` (bulk export).
