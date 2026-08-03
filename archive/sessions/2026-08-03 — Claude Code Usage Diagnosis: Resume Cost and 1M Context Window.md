# 2026-08-03 — Claude Code Usage Diagnosis: Resume Cost and 1M Context Window

Not a Metatron build session. Diagnostic session on Claude Code (the development interface) — why Pro-plan usage jumps from 0% to ~30% on the first message into an existing chat. **No project code, config, or agent files were touched.**

---

## The question

User reported new behavior: first message into an existing chat immediately consumes ~30% of the Pro plan allowance, per the claude.ai dashboard.

---

## What was measured

Read directly from the session JSONL files at `~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/*.jsonl`.

**Session sizes:** several multi-day sessions at 5.4–5.9 MB. Two most recent (`d0c992f5`, `2d051505`) at ~2.5 MB each, running 456–491 assistant turns across 2026-08-02 → 2026-08-03.

**Per-turn context, current sessions:** 385,000–417,000 cached input tokens per turn. One older session (`81e0b53d`) reached 850,244.

**Cache re-creation on resume after a gap:**

| Session | Gap | Tokens re-written to cache |
|---|---|---|
| d0c992f5 | 1.7 h | 150,123 |
| d0c992f5 | 9.6 h | 233,023 |
| d0c992f5 | 1.0 h | 329,416 |
| 2d051505 | 1.8 h | 59,555 |
| 2d051505 | 10.6 h | 171,264 |
| 2d051505 | 1.4 h | 340,651 |

Cache read at each of those resume points was only 12,738 tokens — the stable system-prompt prefix. Everything else was re-processed.

**Model:** `~/.claude/settings.json` sets `"model": "opus"`. Transcripts confirm the switch: `claude-sonnet-5` on 2026-07-27 → `claude-opus-5` by 2026-08-02.

**Context files:** `CLAUDE.md` 45,872 bytes (~12k tokens, re-sent every session); user global `CLAUDE.md` 6,659 bytes; `MEMORY.md` 7,721 bytes. Three global MCP servers registered (ask_gpt, ask_gemini, ask_claude).

---

## Findings

1. **First explanation given was wrong and was corrected in-session.** Initially attributed the 30% jump to a cold-cache re-read on resume. User clarified they had resumed within minutes (warm cache) but that the 5-hour usage window had rolled over. The cache-write data above is real but was not the operative cause for this particular event.

2. **Actual mechanism — the denominator reset, not the message cost.** The API is stateless: the full conversation history is re-sent on every turn. A ~385k-token conversation costs ~385k tokens per message regardless of cache state. Cache reads are discounted (~0.1× base input rate) but still count against the allowance. When the 5-hour window resets to 0%, the very next message in a conversation that size immediately consumes a large slice. **Intentional behavior, not a bug.** The second message costs roughly the same again.

   Caveat stated to user: token counts are visible in the transcripts, but the quota denominator Anthropic divides them by is not, so the exact arithmetic producing "30%" could not be verified — only the mechanism.

3. **Opus 5 context window is 1M tokens** — default *and* maximum, no beta header. Verified against the `claude-api` skill's model catalog. Sonnet 4.6 and Sonnet 5 are also 1M; Haiku 4.5 is 200K.

4. **The 1M window is the trap, not the benefit.** It explains the reduced compaction alerts: on a 200K model these conversations would have hit auto-compact long ago and been summarized down. At 1M they grow to 385k and later 850k with nothing interrupting, and every token is re-billed each turn.

5. **`~/.claude/show_usage.py` under-reports.** The Stop hook hardcodes `CONTEXT_WINDOW = 200_000`. At the observed 850,244 tokens it would print `Context: 425%`; at 385k, `193%`. The number has not been meaningful since the move to Opus 5.

6. **Two compounding causes for "this is new":** the model switch to Opus 5 (heavier draw on the Pro allowance per token than Sonnet), and sessions that have grown large enough for the per-message floor to dominate. The same working habit was cheap in July.

---

## Recommendations given

1. **Start new chats rather than resuming long ones** — the primary lever. ~13k tokens/turn fresh vs ~385k resumed; roughly a 30× difference on *every* message, not once per resume.
2. **Invoke `/compact` deliberately** before leaving a session — auto-compact will rarely fire at 1M.
3. **Switch to Sonnet for routine work** (`/model sonnet`, or the `model` key in `~/.claude/settings.json`) — same 1M window, materially lighter allowance draw.
4. **Resume within the hour** if resuming at all — inside the cache window the re-read is nearly free.
5. **Trim `CLAUDE.md`** — 45KB of fixed per-session overhead; the deployment-recreation detail could move to a read-on-demand doc. Smaller lever than 1–3.

---

## Deferred / open

- **`show_usage.py` context constant not fixed.** Offered to change `CONTEXT_WINDOW` from `200_000` to `1_000_000`; user did not respond before archiving. Local Mac file only — no VM deploy implication.
- **`CLAUDE.md` trim not attempted.** Would need agreement on what moves out; note the Vertex cache-padding memory (4096-token minimum) — though that constraint applies to the Metatron runtime's Vertex calls, not to Claude Code's own prompt.
- No Metatron project work done. Phase 5 state unchanged; SEQ 021 changes remain uncommitted/undeployed as recorded in `SESSION.md`.

---

## Verbatim transcript

Exported via `python3 ~/.claude/tools/archive_chats.py` → `archive/transcripts/` (3 new, 2 updated this run).
