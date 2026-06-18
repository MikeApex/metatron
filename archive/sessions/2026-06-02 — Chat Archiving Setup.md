# 2026-06-02 — Chat Archiving Setup

## What was built

- **[tools/archive_chats.py](../../tools/archive_chats.py)** — bulk JSONL export script. Reads all sessions from `~/.claude/projects/`, copies raw JSONL to `archive/transcripts/raw/`, and writes verbatim readable `.md` transcripts to `archive/transcripts/`. Idempotent.
- **[archive/transcripts/](../../archive/transcripts/)** — 40 sessions exported (April 3 – June 2), raw + readable.
- **CLAUDE.md** updated with "Chat Archiving" section clarifying the two conventions.
- Memory updated to fix incorrect wiring.

## Key decision

"Archive this chat" = verbatim `.txt` + `.md` summary to `archive/sessions/` (existing convention, unchanged).  
"Run the chat archive script" = `python3 tools/archive_chats.py` (bulk JSONL export — different trigger phrase).

## Correction made

I initially wired "archive this chat" to the Python script, overriding the existing session logging instruction. Corrected after user flagged it.
