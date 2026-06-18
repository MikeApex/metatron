# 2026-06-02 — Global CLAUDE.md Setup, Chat Archiving Mechanism

## What was built

- **[tools/archive_chats.py](../../tools/archive_chats.py)** — bulk JSONL export script. Copies raw JSONL to `archive/transcripts/raw/` and writes verbatim readable `.md` transcripts to `archive/transcripts/`. Idempotent. Trigger: "run the chat archive script" or "archive all sessions".
- **[archive/transcripts/](../../archive/transcripts/)** — 40 sessions exported (April 3 – June 2), raw + readable.
- **[~/.claude/CLAUDE.md](~/.claude/CLAUDE.md)** — global QOL rules file, applied across all projects.

## Global rules established

1. Session archiving / "archive this chat" — verbatim `.txt` + `.md` to `archive/sessions/`
2. No Co-Authored-By in commits
3. File links in chat — always markdown
4. Numbered lists for multiple items
5. Explain terminal commands before approval
6. Plan mode panel is read-only
7. Multi-model discussions — include own answer
8. Ask criteria before arbitrating
9. Generated file naming — date + qualifier required
10. No full file rewrites without explicit permission *(added by user directly)*

## Confirmed

- `ask_gpt`, `ask_gemini`, `ask_claude` already registered globally in `~/.claude/claude.json` — available in all projects, nothing to build.

## Correction made

I initially wired "archive this chat" to `tools/archive_chats.py`, overriding the existing session logging instruction. Corrected after user flagged it. The two triggers are now distinct.
