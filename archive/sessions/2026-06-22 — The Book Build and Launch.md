# 2026-06-22 — The Book: Build and Launch

## What was built

### The Book (Metatron traffic monitor)

Three-part system to visually monitor Metatron's internal flow in real time from the Mac.

**core/trace.py** (new)
- Thread-safe per-request `RequestTrace` / `AgentRecord` / `TurnRecord` data structures
- Captures: agent name, provider, model, context sections loaded (agent file, config, recent context), per-turn token counts (in + out), tool calls (name, args, result preview, duration_ms)
- Writes to `data/personas/{persona}/traces/YYYY-MM-DD.jsonl` at end of each pipeline run
- Thread-local storage; parallel subagent dispatches propagate parent trace into worker threads via closure

**core/orchestrator.py** (instrumented)
- Added `import core.trace as _tr` and `import time`
- Token recording at every API call site: Anthropic, `_openai_compat_loop`, `_openai_compat_stream`, Ollama, Gemini grounded, Gemini native
- `push_agent` / `pop_agent` around `_run_single_agent` — captures context sections
- `start_request_trace` / `finish_request_trace` in both `run_pipeline_session` (blocking) and `run_pipeline_session_stream` (streaming)
- Synthesizer in streaming path manually push/popped (it's inlined there, not via `_run_single_agent`)
- Parallel ThreadPoolExecutor blocks in all three session runners now propagate trace context into worker threads

**core/server.py** (monitor API added)
- `GET /monitor/personas` — lists all persona directories + root user
- `GET /monitor/conversations?persona=X` — full history across all dates
- `GET /monitor/traces?persona=X&trace_id=Y` — full trace history or single trace lookup
- `GET /monitor/stream?persona=X` — SSE that pushes new trace entries as they're written (1s poll)
- Security: Tailscale-only access for now; shared-secret header deferred to Alpha

**tools/metatron_monitor.py** (new — The Book)
- Textual TUI, runs on Mac
- Persona dropdown → loads full conversation history + subscribes to SSE
- Column 1: conversation history (MessageBlock widgets: timestamp, user text, synth text)
- Column 2: agent call sequence per selected message (AgentLogItem: agent, provider/model, tokens, tool call list, subagents)
- Column 3: collapsible detail view (Agent Instructions, Config, Recent Context, per-turn breakdown with tool args + results)
- Live SSE mode: new traces auto-appear in Column 1 as conversations happen

**tools/requirements-monitor.txt** (new)
- Mac-only: `textual>=0.47.0`, `httpx>=0.24.0`

## Decisions made

- **Textual** chosen over PyQt/Electron — already in project ecosystem, no separate window manager needed
- **HTTPS with `verify=False`** — VM runs HTTPS (auto-detects certs in `certs/`); connecting via Tailscale IP causes hostname mismatch; WireGuard already encrypts the tunnel so cert validation is redundant
- **Trace files are per-persona** — written to `data/personas/{persona}/traces/` to match existing layout
- **No historic trace data on first launch** — traces only accumulate after the new instrumented code is deployed; existing conversations show in Column 1 but Columns 2/3 will be empty until new conversations run

## Bugs fixed during session

- `await self.load_data()` → `self.load_data()` — `@work` methods return a `Worker`, not a coroutine

## Setup (Mac)

```bash
cd ~/Desktop/multi-model-mcp
python3 -m venv .venv-monitor
source .venv-monitor/bin/activate
pip install textual httpx
python3 tools/metatron_monitor.py
```

## Deploy

```bash
cd ~/Desktop/multi-model-mcp && ./deploy.sh
```

## Deferred

- Drag-to-resize column handles (stubbed in code, not wired to CSS width)
- Auth header on monitor endpoints (Alpha)
- Subagent token counts in parallel dispatch (v1 captures tool call record but not per-turn tokens inside parallel worker threads for subagents)
