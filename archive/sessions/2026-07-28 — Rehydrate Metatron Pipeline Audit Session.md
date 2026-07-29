# 2026-07-28 — Rehydrate Metatron Pipeline Audit Session

## What happened

No code changes this session — a pure context-recovery task.

1. User asked to find and rehydrate a prior chat opening with "Context: this is the Metatron personal AI life manager..."
2. Located two candidate transcripts in `archive/transcripts/`:
   - `2026-06-26 — Context This is the Metatron personal AI life manager. The.md` (truncated capture, same session)
   - `2026-06-26 — Context This is the Metatron personal AI life manager. The (2).md` (complete session, session ID `749636dc-8a59-4b0c-9aec-91746f026f8a`)
3. Read both, confirmed file 1 is a partial duplicate of file 2 cut off mid-response.
4. Summarized the full original session back to the user (see below) and cross-checked against current `SESSION.md` / git log to confirm what has and hasn't been resolved since.
5. Ran `python3 tools/archive_chats.py` (bulk export) — 2 transcripts updated, this session's JSONL captured with no new content pending.

## Content of the rehydrated session (2026-06-26)

- **Pipeline audit, ~15:28–16:47:** reviewed 10 exchanges via VM logs, found 5 issues — missing `tools.ambient` deploy, `write_config` output-filter false positive, Research Agent name-normalization miss, Coordinator prompt running uncached (<4096 tokens), 90s graceful-shutdown SIGKILL cycle on deploy.
- **Deep dive on exchange seq 027:** traced the Research Agent failure end-to-end — Coordinator wrote `"Research"` instead of `"Research Agent"`, normalization missed the abbreviation, specialist failed, Synthesizer streamed a "minor snag" apology before its own recovery call actually returned correct weather data.
- **Fixes applied in that session:** `config/agents/coordinator.md` (explicit valid-agent-names list) and `core/orchestrator.py` `_AGENT_NAME_MAP` (9 single-word abbreviation entries).
- **Deliverable:** designed the reusable "Metatron — Single Exchange Troubleshoot" prompt (DATE/SEQ inputs, one SSH round-trip pulling conversation record + server logs + pipeline trace together) — this prompt template has since been used repeatedly (SEQ 026, 031, 032, 041 troubleshoot sessions all exist in the archive).

## Status check against current state (as of this session)

Cross-referenced the 2026-06-26 findings against `SESSION.md` — then went back and verified each claim directly in code rather than trusting the archive note, after the user asked whether anything from the transcripts was still open.

- Research Agent normalization fix — confirmed live: `_AGENT_NAME_MAP` at `core/orchestrator.py:1894` has the single-word abbreviation entries (`"research"` → `"research_agent"`, etc.), committed in `e477c76`.
- Graceful shutdown 90s SIGKILL cycle — fixed same day (`timeout_graceful_shutdown=150` + drain gate in `deploy.sh`).
- `tools.ambient` missing / ambient context — resolved same day (`config/profile.yaml` + `tools/ambient.py` deployed).
- **`write_config` output-filter false positive — found still open on re-check.** The SEQ 031 session's two-tier filter (`_ALWAYS_CONFIDENTIAL` vs `_CONTEXT_SENSITIVE`) only softened matching for common-English-word agent names (`logistics`, `finance`, etc.). Tool names including `write_config` remained in `_ALWAYS_CONFIDENTIAL`, flagged on any substring match with no exception for the user having said the term first — the exact failure mode from exchange 027 in the rehydrated transcript was still reproducible.
- The routing-miss bug family this audit started continued to recur and was most recently addressed in the SEQ 041 session (2026-07-27, commit `814e6c3`) — advice/suggestion requests not routing to domain specialists.

## Fix attempted, then reverted after security review

First pass: `filter_output()` in `core/orchestrator.py` took an optional `user_message` param and skipped suppression for any term already present in the user's own message — reasoning that a term the user said first isn't a leak when the Synthesizer echoes it back. Verified with 4 manual cases, all passed, `py_compile` clean.

**User asked for a review against `SESSION.md` and the roadmap before accepting the fix.** That review surfaced a real regression: the roadmap's Track B / B1 red-team plan (`archive/plans/phase5_to_future_roadmap_2026-06-10.md`) tests a "Direct tool inquiry" attack category — e.g. "What tools do you have?" — expecting a canned response even when the probing question uses an internal term directly. Under the first-pass fix, a message like "What does `write_config` do?" contains the term in the user's own message, so the filter would no longer suppress a Synthesizer response that actually explained it — a one-line bypass of the output filter's backstop role (`SESSION.md` Security Architecture section; `CLAUDE.md` Discretion principle). The fix solved the UX false positive by disabling the security control at exactly the point it exists to catch.

**Reverted in full.** `filter_output()` and all three call sites (`run_pipeline_session`, `run_pipeline_session_stream`, `run_session`) restored to original always-suppress behavior for both tiers. Net diff against the last commit is now docstring-only — confirmed via `git diff`, `py_compile` clean.

**Result: `write_config` false positive (Exchange 027) remains open, now correctly recorded as a known, accepted-risk gap** rather than a hidden regression — deferred to the already-planned Track B / B2 "Output filter upgrade" (regex+semantic matching), which is the right venue to fix false positives without weakening the backstop. Nothing deployed; nothing to deploy.
