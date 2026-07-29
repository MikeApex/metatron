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

Cross-referenced the 2026-06-26 findings against `SESSION.md`:
- Research Agent normalization fix — landed and deployed (confirmed in SESSION.md "pipeline audit + Research Agent normalization fix" entry).
- Graceful shutdown 90s SIGKILL cycle — fixed same day (`timeout_graceful_shutdown=150` + drain gate in `deploy.sh`).
- `tools.ambient` missing / ambient context — resolved same day (`config/profile.yaml` + `tools/ambient.py` deployed).
- `write_config` output-filter false positive — resolved in the SEQ 031 troubleshoot session (two-tier `_ALWAYS_CONFIDENTIAL` vs `_CONTEXT_SENSITIVE` filter).
- The routing-miss bug family this audit started continued to recur and was most recently addressed in the SEQ 041 session (2026-07-27, commit `814e6c3`) — advice/suggestion requests not routing to domain specialists.

No open action items from this rehydration — it was a lookback, not new work.
