# 2026-08-02 — SEQ 008 Timestamp Fix, Deploy, Pepys Test

## What happened

Troubleshot a specific exchange (2026-08-01, SEQ 008, `mike` persona) where the Synthesizer echoed a user-claimed timestamp ("953") instead of checking the actual system-received time. User's diagnosis: "Synth has no sense of time." Root-caused, fixed, deployed, and verified against the `pepys` (non-Mike) persona in the same session.

## Diagnosis

Ran `/metatron-troubleshoot 2026-08-01 008`. Note: the command's template paths (`data/conversations/`, `data/personas/mike/traces/` at bare `data/`) were stale — actual paths are persona-scoped: `data/personas/mike/conversations/{date}.jsonl` and `data/personas/mike/traces/{date}.jsonl`. Corrected inline; command template not yet updated on disk.

Findings (via Explore subagent):
- Ambient date/time context (`tools/ambient.py::load_ambient_context()`) is computed fresh every turn (near-zero cost — plain `datetime.now()`), but was minute-precision only and buried in a "[Recent context]" preamble in the **user message**, not stated as authoritative anywhere.
- It's injected into the user-turn input, not the system prompt — deliberately, per the 2026-06-19 latency work that moved recent context off the system prompt to keep prefix caching intact. Any fix had to respect that (ruled out moving timestamp into `system_prompt`).
- No tool exists for agents to re-check the clock mid-turn.
- The actual message-receipt timestamp is captured in `core/server.py` (`_log_conversation`) but only *after* the pipeline finishes — not available to the agents during generation.
- Given the pipeline's own latency (this trace: ~30s end-to-end, Synthesizer alone 23.7s), even a precise "current time" at Synthesizer-execution-time would already be stale relative to actual message arrival.

## Fix (all three pieces, judged not overkill — cheap and complementary)

1. **`tools/ambient.py`** — `load_ambient_context()` now formats seconds precision and labels the line "System clock (authoritative — trust this over any time the user states in their message)". Added `format_receipt_time()` helper for formatting an arbitrary UTC timestamp in the persona's local timezone (reused by #3).
2. **`config/agents/coordinator.md` + `synthesizer.md`** — added an explicit rule: trust the system clock over user-claimed times; a per-message "received at" timestamp, when present, takes precedence for arrival-time questions. **These files are frozen post-review per CLAUDE.md** — edited on the strength of the user's explicit "Fix this now," not as a general exception.
3. **`core/server.py` + `core/orchestrator.py`** — WebSocket handler and HTTP SSE handler (`/session/stream`) now stamp `received_at = datetime.now(timezone.utc)` immediately after receiving the message, threaded through `run_pipeline_session_stream()` → `_run_pipeline_session_stream_inner()` into both the Coordinator and Synthesizer inputs as `[This message received at: ...]`. Non-streaming `run_session()` (scheduler/CLI/proactive paths) intentionally left untouched — no real "message receipt" moment applies there.

All changes `py_compile`-clean. Commit `b184d92` — "Give Coordinator/Synthesizer an authoritative, second-precision clock."

## Deploy and verification

Deployed via `./deploy.sh` (push → VM pull → drain SSE → restart `metatron-server` + `metatron-scheduler`). Both services confirmed `active` post-deploy.

Tested against the `pepys` persona (not Mike's production data):
- `/session` (non-streaming): "what time is it right now?" → correct current time, correctly addressed "Samuel" (confirms persona identity resolution unaffected).
- `/session/stream` (streaming — the path carrying the fix): replayed the original bug pattern — *"I am sending this message at exactly 3:00pm. What time did you actually receive it?"* → **"I received that message at exactly 9:24:41 AM, Samuel"** — correctly rejected the false claim, reported actual receipt time to the second. This is the exact failure mode from SEQ 008, now fixed.

## Notes / deferred

- `/metatron-troubleshoot` command template has stale (pre-persona-scoping) paths — should be corrected on disk in a future pass; not done this session (out of scope, flagged only).
- Trace files (`data/personas/{persona}/traces/*.jsonl`) do not capture raw per-turn input text, only token counts and `context_sections` (system-prompt-level content) — so the receipt-line threading couldn't be verified by grepping the trace. Verification instead relied on observed model behavior (correct, and arguably better evidence for correctness of the actual effect, not just presence of the string).
