# 2026-06-26 — Synthesizer Conversation History

## What was built

Added rolling 5-turn (10-entry) conversation history to the Synthesizer so it no longer cold-starts each pipeline turn.

### Problem
The Coordinator → Synthesizer pipeline was fully stateless. Each user message arrived as a fresh cold-start for Synth — no memory of what had just been said in the same session. This caused Synth to miss references ("like you said", "change that") and lose conversational continuity.

### Design decision
History goes to Synthesizer only, not Coordinator. Coord is routing infrastructure and doesn't need conversational context. Synth is the user-facing voice and is where continuity matters. Also avoids leaking conversation content to a model that may be cloud-routed under less strict privacy rules.

Window: last 10 entries = 5 user/assistant turn pairs. Turn 6 drops turn 1.

### Changes

**`core/orchestrator.py`**
- `_anthropic_stream`: added `history` param, injects prior turns before user message (defensive — Synth uses Gemini in cloud mode, but kept for consistency)
- `run_pipeline_session`: added `history` param; passes `list(history[-10:])` copy to `_run_single_agent("synthesizer", ...)`; appends current turn to history after; trims to 10 entries
- `run_pipeline_session_stream`: added `history` param; applies Synth tool whitelist via `get_allowed_tools("synthesizer")` (bug fix — streaming pipeline was giving Synth all ~20 tools instead of its 8; also fixed the "context file not registering" observation); passes `recent_history` copy to all 4 provider streaming calls; appends turn to history after stream completes
- `run_session`: threads `history` through to `run_pipeline_session` (previously dropped it; removed the "stateless" comment)

**`core/server.py`**
- Added `_session_history: dict[str, list[dict]] = {}` — per-persona in-memory history, keyed by persona name
- Both `/session` and `/session/stream` endpoints look up `_session_history[persona]` and pass it on every request
- History updates in-place inside the pipeline functions; trimming happens there too

### Side fix
The streaming pipeline was calling `register_tools()` without applying the Synth tool whitelist. Synth was seeing all tools instead of its 8 allowed ones. This has been fixed — now matches `_run_single_agent` behavior.

## Deployment
Deployed to VM via `./deploy.sh`. Confirmed working.

## Deferred
Nothing deferred. History is in-memory only — resets on server restart. Persistent cross-session history (beyond what logs + Pattern Miner already provide) not planned.
