# Context Archiving Protocol Session
*2026-06-19. Short session focused on improving session archiving reliability after A1 context loss.*

---

## What happened

The A1 continuation session (earlier today) exposed a gap: context compression in the prior window had already occurred before the continuation started, making verbatim recovery impossible from within the session. This session diagnosed the problem and updated the archiving protocol.

---

## Changes made

### [CLAUDE.md](~/.claude/CLAUDE.md) — two edits

**1. Proactive archiving triggers** — replaced vague "when compression is approaching" (unobservable) with a list of concrete event-based triggers:
- After any batch of multi-model research queries returns
- After any major document is written or finalized
- Before starting a new major work block
- After ~2 hours of dense work

**2. "Archive this chat" behavior** — updated to run `python3 tools/archive_chats.py` (lossless JSONL export) + write `.md` summary. Manual `.txt` file dropped; script output is strictly better (system-written, not reconstructed from memory). Manual `.txt` retained as fallback for projects without the script.

Both proactive triggers and the on-demand command now use the same mechanism: the script.

---

## Key findings from the discussion

- Context window is a flat token pool — tool results are the most expensive line item, not conversation
- Multi-model research sessions fill context fast: 6 queries × ~1,000–1,500 tokens each = 6–9K tokens before adjudication begins
- The compression algorithm is generic — good at preserving final states, poor at preserving verbatim model responses, reasoning paths, and correction loops
- `archive_chats.py` reads from the JSONL (system event log), which is written independently of context state — pre-compression content is recoverable from it even mid-session
- Context compression algorithm is not directly editable; CLAUDE.md influences behavior, not the algorithm
- Hooks system may offer a path to automatic archiving on a threshold event — not investigated this session

---

## Also done this session

- `tools/archive_chats.py` updated to overwrite when source JSONL has grown (mid-session or extended conversation). Now shows "new / updated / skipped" in output. Previously skip-on-exists only.

## Deferred

- Investigate Claude Code hook events for a context-threshold trigger (would make milestone archiving automatic rather than rule-dependent)
- Working pattern rules (file-first, scope-narrow sessions) — discussed, not yet codified in CLAUDE.md; user deferred
