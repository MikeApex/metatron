# SessionStart Context Hook and Troubleshoot Slash Command
**Date:** 2026-07-28
**Session type:** Tooling/config — reduce chat overstepping due to missing context

---

## Problem

Chats on this project tend to overstep because context (SESSION.md, active roadmap, ownership rules) isn't loaded before basic queries or edits — CLAUDE.md's "Mandatory Pre-Edit Context Check" is an instruction the model has to remember to act on, not a forced load. Prior incident (2026-07-27): an edit was made without checking SESSION.md/roadmap first, had to be fully reverted.

## What was built

### 1. SessionStart hook — automatic context primer
- `.claude/session_context_primer.py` (Python; superseded an initial bash version, deleted).
- Wired into `.claude/settings.local.json` under `hooks.SessionStart`, alongside the existing `Stop` hook (`show_phase_progress.py`) — left untouched.
- On every session start/resume/clear/compact/fork, injects into context: full `SESSION.md`, the currently-active roadmap (resolved dynamically by parsing SESSION.md's "Read these before doing anything" link, falling back to most-recently-modified `archive/plans/*roadmap*.md` — avoids hardcoding a filename that goes stale when the roadmap is revised), and `CODEBASE_INDEX.md`. ~1,560 lines / ~15–18K tokens total.
- CLAUDE.md deliberately **not** duplicated — Claude Code already auto-loads it.
- Output format: JSON `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}` — confirmed via `claude-code-guide` agent research as the documented-reliable format (plain stdout also works per docs, but JSON is the recommended path; switched from an initial plain-stdout bash version to this Python/JSON version for reliability).
- First line of injected content is the literal string `Default Hook Fired` — a user-visible confirmation marker, plus each loaded file is echoed with its resolved path/header so the specific roadmap version in use can be visually confirmed.

**Verification:** script tested standalone (valid JSON, correct first line, correct roadmap path resolved). Live in-session firing **not yet confirmed** — `SessionStart` only fires on `startup`/`resume`/`clear`/`compact`/`fork`, not on ordinary turns within an already-running session, so an in-session test query returned nothing (expected, not a bug). `/clear` was identified as the way to test without leaving the session; not yet run as of this archive.

### 2. `/metatron-troubleshoot` — callable slash command
- `.claude/commands/metatron-troubleshoot.md`.
- Reconstructed from a prompt template referenced in `archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md` (original text was only "in the chat transcript," not saved to a file — user supplied it verbatim this session).
- Usage: `/metatron-troubleshoot <DATE> <SEQ> <ISSUE>` (positional `$1`/`$2`/`$3`). Pulls conversation record + server logs (±3 min window) + pipeline trace for a given exchange via one SSH round-trip to `metatron-vm`, with a structured "what to look for" checklist.
- Added a note (not in the original prompt) about the trace-timestamp exact-minute-match false-negative found in `archive/sessions/2026-06-26 — SEQ 041 Single Exchange Troubleshoot.md` — retry with a ±2-minute window before concluding a trace is missing.
- Confirmed by user: **"Slash command works."**

## Design decisions

- Hooks (automatic, event-triggered, configured in settings.json) vs. slash commands (manual, user-invoked, `.claude/commands/*.md`) are different mechanisms — the default context load is a hook; the troubleshoot prompt is a command, per user's own framing ("default + callable").
- `.claude/settings.local.json` chosen over `.claude/settings.json` for the hook — matches where the existing `Stop` hook already lives; `.claude/` is fully gitignored on this solo/single-machine project so the distinction carries no real tradeoff here.

## Open / deferred

- **Live hook firing not yet confirmed** — run `/clear` (or start a fresh session) and re-ask a context-dependent question (e.g. "what does the roadmap say about Track B1") to confirm no `Bash`/`grep` fallback is needed and `Default Hook Fired` is visible.
- User is about to update VSCode. Researched via `claude-code-guide`: session JSONL data is stored independently of the extension (`~/.claude/projects/.../*.jsonl`) and should survive; hook JSON format is stable across recent versions; `/clear` behavior is stable. Genuine documented gap: whether already-open session tabs/panels reconnect cleanly post-update is not guaranteed either way. Recommended archiving first as cheap insurance — this session's archive run is that step.
