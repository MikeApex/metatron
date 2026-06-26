# 2026-06-22 — The Book: Iteration and Chat Panel

## What was built / changed

### Bug fixes
- **Persona bleed in Column 1** — `monitor_conversations` endpoint was reading all entries from a shared JSONL without filtering by persona. Fixed to always filter `entry.get("persona") == persona`.
- **Subagent name showing as `run_subagent(?)`** — the arg key is `agent_name`, not `agent` or `name`. Fixed lookup in `_populate_col3`.
- **Snapshot crash (`s` key)** — Textual `ListView` was capturing the keypress before it reached the app. Fixed with `priority=True` on the binding. Also wrapped file write in try/except.
- **SSE disconnect (ID collision)** — `_populate_col1` assigned `id=f"mb-{i}"` to each `MessageBlock`. Textual requires globally unique widget IDs; a second call after `lst.clear()` collided. Fixed by removing IDs from all list items, and making the SSE loop append-only (not full rebuild).
- **`TypeError: 'Worker' object can't be awaited`** — `persona_changed` was `async def` calling `await self.load_data()`. `@work` methods return a `Worker`, not a coroutine. Fixed by making `persona_changed` a plain `def` using `@on(Select.Changed)`.

### Column 1
- **Datestamps** — `fmt_ts` now returns `YYYY-MM-DD HH:MM:SS` instead of `HH:MM:SS`.
- **Expandable message blocks** — each row is now a `Collapsible`. Collapsed: timestamp + persona + truncated preview. Expanded: full user message + full Metatron response.

### Column 3 improvements
- **Flattened turn structure** — turns are now `── Turn N  Xin Yout ──` Static dividers; each tool call is its own top-level Collapsible, immediately visible without clicking through a parent.
- **`run_subagent` resolved** — instead of showing raw tool call args, Column 3 looks up the actual subagent record by `agent_name` and shows: provider/model, per-turn tokens, tool call names, output files. Falls back to raw args if no match.

### File viewer
- **Diary history** — clicking a file link in Column 3 now calls `/monitor/history` instead of `/monitor/file`. Returns all files in the same directory sorted by date, displayed with `─── YYYY-MM-DD ───` dividers. The current file is marked `← current` in green.
- **`GET /monitor/history`** added to server.py.
- **`GET /monitor/file`** added to server.py (single-file fallback, also used by history internally).

### Output file tracking
- **`core/trace.py`** — added `output_files: list[str]` to `AgentRecord`. `record_tool_call` scans args values and result string for `data/...` paths using regex and accumulates them. Included in serialization.
- File paths appear in Column 3 as clickable buttons that open the history viewer.

### Snapshot (`s` key)
- Writes `data/book_snapshot.md` to the Mac project directory with: persona, selected conversation, full pipeline summary (agents/models/tokens/duration/output files), focused agent detail.
- Intended as context bridge to Claude Code in VSCode — press `s`, switch to VSCode, say "read the book snapshot."

### Chat panel (`c` key)
- Bottom panel, toggled with `c`, auto-focuses input.
- Sends messages to `claude -p --output-format text` via a temp file (avoids TTY detection).
- Recursive context: each message prepends `[Book state snapshot] + full Human/Assistant history` for multi-turn continuity.
- Streams response line-by-line into the chat panel.
- **Clear** button wipes history and resets token counter.
- **Token counter** — running approximate total (chars / 4).
- Surfaces stderr from `claude` when stdout is empty, so failures are diagnosable.

## Decisions made

- **`claude -p` over direct Anthropic API** — same billing, no extra key management, consistent with the project's toolchain. Direct API remains a one-function swap if startup latency becomes annoying.
- **Recursive context accumulation** — standard stateless multi-turn pattern; token cost grows linearly per turn but sessions are short.
- **No IPC between The Book and VSCode** — there's no mechanism for Claude Code to actively receive messages from a separate process. The snapshot file + window switch is the closest practical bridge. The chat panel uses `claude -p` so Claude Code's model is in the loop, but it's a fresh call each time (no shared session state with the current VSCode conversation).
- **Tailscale-only security** — no auth on monitor endpoints yet; deferred to Alpha.

## Deferred
- Streaming `streaming_json` output from `claude -p` — dropped for reliability; plain `--output-format text` used instead.
- Drag-to-resize column handles — stubbed, not wired.
- Auth header on monitor endpoints — Alpha.
- Chat panel "no response" issue still under investigation — the temp file + shell redirect approach should fix it; not confirmed working yet as of archive time.
