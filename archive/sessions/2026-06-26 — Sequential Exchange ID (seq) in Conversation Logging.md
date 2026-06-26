# 2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging

## What was built

Added a per-day sequential exchange ID (`seq`) to Metatron's conversation logging, and surfaced it in The Book's Column 1.

## Changes

### `core/server.py`

- Added `import threading` and module-level `_CONV_LOCK = threading.Lock()`
- Rewrote `_log_conversation` to:
  - Acquire the lock before any file I/O
  - Count existing non-blank lines in today's JSONL to determine the next seq
  - Add `"seq": "003"` (1-indexed, zero-padded to 3 digits) to each log entry
  - File-not-existing case handled naturally: `existing = 0` → seq `"001"`
  - Read + write happen inside the same lock acquire, preventing races under concurrent requests

### `tools/metatron_monitor.py`

- Added `fmt_ts_short(ts: str) -> str` helper — returns `HH:MM` from an ISO timestamp
- Updated `MessageBlock.compose`:
  - When `seq` present: title prefix is `[dim]#003[/] [bold cyan]14:23[/]`
  - When `seq` absent (old log entries): falls back to existing `[bold cyan]%Y-%m-%d %H:%M:%S[/]`
  - No backfill, no breakage of old entries

## Decisions

- `/monitor/conversations` endpoint required no changes — seq is part of the entry dict and passes through automatically from JSONL
- Concurrency approach mirrors the `_WRITE_LOG_LOCK` pattern in `tools/logger.py`
- Old log entries display cleanly with the full timestamp fallback

## Deployment

Committed (`9fcd802`) and deployed via `./deploy.sh`. VM services restarted.
