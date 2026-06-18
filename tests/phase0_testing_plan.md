# Phase 0 Testing Plan — Foundation

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

Establish the runtime skeleton: a working orchestrator that can load config, call a model API, dispatch tools, and persist a log entry. Everything downstream depends on this being correct.

---

## Prerequisites Check

None — this is the foundation. All prerequisites are external (API keys, Python environment).

| Prerequisite | Check |
|---|---|
| Python 3.11+ | `python --version` |
| `ANTHROPIC_API_KEY` set | `echo $ANTHROPIC_API_KEY` |
| All dependencies installable | `pip install -r requirements.txt` without errors |

---

## Intent Checks

These verify the *purpose* was achieved, not just that files exist.

### 1. Config loading is ordered and complete
- Load the orchestrator and confirm system prompt contains: Constitution → Prime Directive → Mission → Goals → Agent — in that order
- **Pass:** All four tiers appear in the prompt, Constitution first
- **Fail:** Any tier missing, or order wrong

### 2. Tool dispatch round-trips correctly
- Trigger a `write_log` tool call and confirm the file appears at `data/logs/YYYY-MM-DD.json` with valid JSON
- **Pass:** File exists, is valid JSON, contains the content passed
- **Fail:** File missing, malformed, or tool call silently dropped

### 3. The orchestrator loop handles tool calls without hanging
- Send a message that will trigger a tool call; confirm the model receives the tool result and produces a final text response
- **Pass:** Conversation completes: user → model → tool call → tool result → model → text response
- **Fail:** Loop exits early, hangs, or returns tool result as final response

### 4. Adding a tool requires no core code changes
- Add a trivial new tool function + schema to `tools/logger.py`, register it in `orchestrator.register_tools()`
- **Pass:** Tool is callable without touching any other file
- **Fail:** Requires changes outside of `tools/` and `register_tools()`

---

## Known Gaps (from Phase audit)

- Sub-agent dispatch was never designed into the foundation. The orchestrator runs one flat agent per session with no mechanism for one agent to call another. This is the origin of the MAIN coordinator gap that surfaces in Phase 5.

---

## Sign-off

Phase 0 is complete when all four intent checks pass and the known gap is documented.
