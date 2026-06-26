# Session Primer — Personal AI Life Manager
*Updated: 2026-06-26 (Synthesizer conversation history — 5-turn rolling window + Synth tool whitelist fix). Update this file at the close of every chat so the next chat — or any parallel chat window — starts from current state.*

---

## What this is

A voice-first personal AI life manager — a director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness (`core/orchestrator.py`) with all behavior living in editable config files. Config files are the product; code is infrastructure.

---

## Read these before doing anything

1. **[CLAUDE.md](CLAUDE.md)** — architecture, conventions, terminology, design principles. Auto-loaded into every session but read actively on first session.
2. **[archive/plans/phase5_to_future_roadmap_2026-06-10.md](archive/plans/phase5_to_future_roadmap_2026-06-10.md)** — the current execution plan (supersedes the 2026-06-09 draft in full). Six parallel tracks (A–F) with embedded test criteria, phase gates, agent backlogs, and the binding privacy ruling in Section 0. Start here for any planning or build work.
3. **[~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md](~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md)** — working preferences and project memory index. Read to understand decisions already made and how to collaborate.

If you need to find a specific file, tool, or planning document: **[CODEBASE_INDEX.md](CODEBASE_INDEX.md)**.

---

## Current state — Phase 5 (close)

**Phase 5 intent:** Coordinator Agent + Specialist Modules

### Done
- Coordinator-Synthesizer two-pass pipeline (`core/orchestrator.py:621`)
- All 14 specialist agent files (coordinator, synthesizer, diarist, mental_wellbeing, physical_health, work_vocation, relationships, learning_growth, finance, recreation_hobbies, research_agent, logistics, pattern_miner, goals_interviewer) — **all received deep passes**
- **Phase 5 agent review complete (2026-06-13):** All 14 agents done. Flag consistency audit complete. Research Agent extended: grounded Gemini search implemented in orchestrator (`run_session_gemini_grounded`), decontextualization hardened (constitution stripped from Research system prompt, intent/circumstance stripping added to Coord + Synth). `google-genai` v2.8.0 installed in venv.
- CRM tools (`tools/crm.py`), Wishes shell (`tools/wishes.py`), CalDAV (`tools/caldav.py`)
- Parallel subagent dispatch, write_log threading lock, agent_config tool
- Security: threat model + security backlog complete (`archive/security/`)

### In progress / next (numbering per 2026-06-10 roadmap — note: renumbered from the 2026-06-09 draft)

**Parallel chats (2026-06-11 batch) — status as of 2026-06-19:** A1, A2, A3, A4+A6 all complete. B1 (red team), Check 10 (agent audits), and Check 12 (constitution review) on hold — see below. See [archive/plans/parallel_chats_index_2026-06-11.md](archive/plans/parallel_chats_index_2026-06-11.md) for prompt files and file-ownership rules.

**Active priority (2026-06-19):** streamline agent flow to reduce response latency — get the tool functionally usable before completing sign-off work. B1/Check10/Check12 resume after latency work stabilises the pipeline.

**Latency work done (2026-06-19):**
- Model tiering: coordinator + 6 specialists → Flash; coordinator reverted to Pro (Flash skips tool calls unreliably); 6 specialists remain on Flash
- Diarist fire-and-forget: code-enforced in `tools/subagent.py` — confirmed working; excluded from SPECIALIST_OUTPUTS
- quick_override added to `routing_cloud.yaml` (Flash) — diarist routes correctly via quick_override path
- Prefix caching: recent context moved to user message in `_run_single_agent()` — system prompt stable per agent
- Output compression: Recreation → compact JSON confirmed working; Logistics / Work/Vocation next
- **Native SDK migration:** reverted — `run_session_gemini` now routes through `_openai_compat_loop` + `_resolve_gemini_credentials` (Vertex OpenAI-compat endpoint). The native genai SDK (`_run_gemini_native_loop`) is retained but unused; migration was abandoned due to an unworkable Vertex thought_signature bug (see below).
- **Streaming:** complete. `POST /session/stream` SSE endpoint live. Anthropic streaming confirmed working. Gemini streaming via `_openai_compat_stream` wired up. PWA client-side SSE consumption deferred.
- **Vertex thought_signature bug — fixed:** When Vertex returns N parallel tool calls, only tc0 gets a cryptographically valid `thought_signature` in `extra_content`. Fix in `_openai_compat_loop`: `message.model_copy(update={"tool_calls": [tc0]})` — trim to single signed call, execute it, let model re-call tc1+ individually. Cost: parallel calls become sequential turns. No 400 errors in testing (turn=6+ confirmed).
- **HF_TOKEN:** read-only token added to `.env` ✓
- Coordinator slimming: handed off to new chat — target ≤3 turns, ≤40K tokens (currently 6 turns, 88K)
- Coord package debug print active in `core/orchestrator.py` (dev — remove before Beta)
- Baseline: 16–20s simple session, 65–74s complex multi-specialist. Was 60–90s.

- ~~**A1** Compliance curve design conversation~~ — **done 2026-06-18.** All four design questions resolved. Shared principle + Synthesizer integrator (Q1); user-reported cold-start, ratchet research-gated (Q2); Synthesizer level only (Q3); nothing activates at A5c, produces plan only (Q4). Decision doc: `archive/plans/compliance_curve_decision_2026-06-13.md`. Agent file edits queued (apply when A2 chat closes). MCP server updates: o3+o1+auto-discovery added to ask_gpt; auto-discovery added to ask_gemini; Opus timeout fixed (600s) in ask_claude.
- ~~**A2** Logging Layer~~ — **done 2026-06-13.** `write_quality_event` in `tools/logger.py`, ROUTING_MISS wired in synthesizer.md, USER_CORRECTION in coordinator.md, PWA tap (`·` dot → `/feedback`). Tests deferred to Alpha launch (`tests/phase5_testing_plan.md` → Known gaps).
- ~~**A3** Cold-start baselines~~ — **done 2026-06-18.** 4 new functions in `tools/baselines.py`: `create_semantic_anchor`, `write_aspirational_baseline`, `shuffled_null_score`, `score_against_anchors`. All 8 canonical anchors written to `data/baselines/semantic_anchors.json`. All 3 roadmap tests pass. Truncated Goals Interview run-guide in `archive/sessions/2026-06-18 — A3 Cold-Start Baselines.md`. A5b re-run pending (after full Goals Interview).
- ~~**A4** Local routing enforcement~~ — **done 2026-06-13.** `local_enabled: true`, fail-closed sensitive routing (no cloud fallbacks), head layer + Learning & Growth + Recreation + Logistics re-tiered local, quick_override guard. MW mania hard-fail: PASS (front-loaded critical instructions). Finance arithmetic: FAIL/deferred D1. Session archive: `2026-06-13 — A4 A6 Local Routing and Token Budget.md`.
- ~~**A5** Goals Interview with real user~~ — **done.** A5b: re-run `write_aspirational_baseline` with existing A5 interview data (replaces A3 placeholder; required for A7 gate — run before A7). A5c preference activation status unknown — confirm if needed. **D1 note:** once VM is provisioned and new features are live, run a fresh Goals Interview + A5b re-run as first-use onboarding on the VM (new D1 item, separate from this A5b).
- ~~**A6** Token budget logging~~ — **done** (all four session paths; 8K warning threshold)
- **A7** Phase 5 sign-off — **blocked** (B1, Check 10, Check 12 on hold pending latency work; A1–A6 all complete). Resume when pipeline is stable.
- **A8** Pre-Alpha code refactor (full program) — **new (added 2026-06-25, scoped 2026-06-26).** Gate: A7 complete. Full module extraction, not just Phase 5 cleanup. `core/orchestrator.py` (1870 lines, 5 concerns) → `core/config.py` + `core/providers.py` + `core/tools.py` + slimmed `core/orchestrator.py`. `core/server.py` → split monitoring endpoints into `core/monitor_api.py`. Remove COORD PACKAGE debug print (line 1616). Update import paths in server, scheduler, subagent, router. Regression gate: A4 clinical-flag scenarios + server startup + full pipeline session + The Book SSE. Note: `run_session_*` functions and `_run_gemini_native_loop` are active switches, not legacy — they stay in `core/providers.py`.
- **B1** Red team — **on hold** (independent of Alpha Gate, but deprioritised — resumes after latency work)
- **Check 10** Agent behavioral audits — **on hold**
- **Check 12** Constitution alignment review — **on hold**

### Also done 2026-06-22 (The Book SSE reconnect)
- `_sse_loop` now auto-reconnects with exponential backoff (2s→30s) on any connection failure. Column 1 updates in real time without re-selecting the persona.
- Session archive: `archive/sessions/2026-06-22 — The Book SSE Reconnect.md`

### Also done 2026-06-26 (SSE streaming newline fix)

- **Root cause:** LLM stream chunks containing literal `\n` were embedded directly in SSE `data:` lines. Client's `split('\n')` parser dropped all text after the newline, causing truncated responses and mid-word splicing.
- **Fix:** Server escapes `\r`/`\n` in text chunks before SSE emission (`core/server.py`); client unescapes `\\n` when accumulating (`static/index.html`). Control tokens unaffected.
- Committed `ba84c6d`, deployed to VM. Hard reload required on client.

Session archive: [archive/sessions/2026-06-26 — SSE Streaming Newline Fix.md](archive/sessions/2026-06-26 — SSE Streaming Newline Fix.md)

### Also done 2026-06-26 (seq in conversation logging)

- **`core/server.py`** — `_log_conversation` now writes `"seq": "003"` (1-indexed, zero-padded, per-day) to each JSONL entry. Thread-safe: `_CONV_LOCK` wraps the read-count-then-write atomically.
- **`tools/metatron_monitor.py`** — Column 1 shows `#003 14:23` prefix when seq present; falls back to full timestamp for old entries.
- No changes to `/monitor/conversations` — seq passes through from JSONL automatically.
- Committed `9fcd802`, deployed to VM.

Session archive: [archive/sessions/2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging.md](archive/sessions/2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging.md)

### Also done 2026-06-26 (Gemini routing fix)

- **Root cause 1:** `core/router.py` silently defaulted unknown agents to `provider="anthropic"`. Fixed: raises `RuntimeError` + logs to `data/logs/routing_fallbacks.json`.
- **Root cause 2:** Browser sends `provider=""` (empty string from Auto dropdown); `if provider is None` check didn't catch it. Fixed: both sites in orchestrator changed to `if not provider`.
- **Error tracking added:** `log_model_error()` in `router.py` writes API failures to `data/logs/model_errors.json` (agent, provider, model, error). Wired into `_openai_compat_loop`, `run_session_gemini_grounded`, `run_session_gemini_cached`, and the unrecognised-provider branch.
- **Other defaults cleaned:** `run_interactive()` + server CLI `--provider` both changed from `"anthropic"` to `"gemini"`.
- Deployed `config/profile.yaml` and `tools/ambient.py` (were missing from VM, causing warning).
- Confirmed working via SSH test and browser.

Session archive: [archive/sessions/2026-06-26 — Gemini Routing Fix and Deploy Audit.md](archive/sessions/2026-06-26 — Gemini Routing Fix and Deploy Audit.md)

### Also done 2026-06-26 (Synthesizer conversation history)

- **Rolling 5-turn history** (10 entries) added to the Coordinator → Synthesizer pipeline. Synth no longer cold-starts each turn — prior user/assistant exchanges are prepended to its messages.
- **`core/orchestrator.py`:** `_anthropic_stream` — added `history` param. `run_pipeline_session` + `run_pipeline_session_stream` — both accept `history`, pass a `list(history[-10:])` snapshot copy to Synth, update history in-place after each turn, trim to 10. `run_session` — threads history through to pipeline (previously dropped on the floor).
- **`core/server.py`:** `_session_history: dict[str, list[dict]]` — per-persona in-memory history. Both `/session` and `/session/stream` look up the right list and pass it to the pipeline each request.
- **Side fix:** streaming pipeline was not applying Synth's `allowed_tools` whitelist — Synth was receiving all ~20 tool schemas instead of its 8. Now matches `_run_single_agent` behavior. This also addressed the "context file not registering" observation.
- Deployed to VM. Confirmed working.

Session archive: [archive/sessions/2026-06-26 — Synthesizer Conversation History.md](archive/sessions/2026-06-26 — Synthesizer Conversation History.md)

### Also done 2026-06-26 (pipeline audit + Research Agent normalization fix)

- **Pipeline audit** across 2 hours of live traffic (15:28–16:47): 5 bugs identified. See session archive for full latency profile and failure pattern catalog.
- **Research Agent normalization fix (two-part):**
  - `core/orchestrator.py` — 9 single-word abbreviation entries added to `_AGENT_NAME_MAP` (`"research"` → `"research_agent"`, `"mental"` → `"mental_wellbeing"`, etc.). Covers Flash-Lite's tendency to shorten multi-word agent names on cold starts.
  - `config/agents/coordinator.md` — explicit "Valid agent values" line added before the format template, listing all 12 agent strings verbatim.
- **Root cause of exchange 027:** Coordinator output `"Research"` (not `"Research Agent"`) → normalized to `"research"` → `research.md` not found → Synthesizer streamed "minor snag" then called `run_subagent` as recovery → weather data returned but too late to retract already-streamed text.
- **Single-exchange troubleshoot prompt** written — two inputs (DATE, SEQ), one SSH command, pulls conversation record + server logs + pipeline trace in one round-trip.
- **Pending deploy:** both normalization fixes are committed locally but not yet pushed to VM.
- **Bugs identified but not fixed this session:** (1) `tools.ambient` missing on VM, (2) output filter false positive on `write_config`, (3) graceful shutdown 90s SIGKILL cycle.

Session archive: [archive/sessions/2026-06-26 — Pipeline Audit and Research Agent Fix.md](archive/sessions/2026-06-26 — Pipeline Audit and Research Agent Fix.md)

### Also done 2026-06-26 (user profile + ambient world context)

- **`config/profile.yaml`** (new) — stable biographical profile injected into Synthesizer and Coordinator. Filled in: name Mike, London, UK, Europe/London. Age/occupation/household left to fill. Includes `ambient.markets: true` flag.
- **`tools/ambient.py`** (new) — 3-hour scheduler job fetches weather (wttr.in/London), headlines (BBC + CNN interleaved, 8 total), and 7 market indices (S&P 500, FTSE, DAX, Nikkei, Hang Seng, Gold, WTI Oil) via Yahoo Finance v8 chart endpoint. Writes `data/ambient_context.json`. `load_ambient_context()` always injects live date/time from system clock; weather/news/markets from last refresh.
- **`core/orchestrator.py`** — `load_profile()` added; injected into `load_config()` (Synthesizer) and Coordinator system prompt. Ambient context prepended to `load_recent_context()` so both agents always see it.
- **`core/scheduler.py`** — `function:` job type added; calls Python callables directly without an LLM session.
- **`config/modules/scheduler.yaml`** — `ambient_refresh` job: every 180 minutes, calls `tools.ambient.refresh_ambient_context`.

Session archive: [archive/sessions/2026-06-26 — User Profile and Ambient World Context.md](archive/sessions/2026-06-26 — User Profile and Ambient World Context.md)

### Also done 2026-06-26 (The Book: SSE backfill fix, load menu, ordering)

Root-cause fix for two related issues: (1) Load menu filter (24h / max 10) appeared broken because `/monitor/stream` replayed all historical traces on connection, backfilling old conversations to the top of Column 1 past the filtered 10. Fixed: `/monitor/stream` accepts `since` param; skips old traces on initial scan only. Monitor records `_sse_since = now()` at `load_data()` start and passes it to the SSE endpoint. (2) Uncommitted changes from prior session meant VM was running old server code with no `since`/`limit` support — deploy was a no-op. Committed and deployed. (3) Max entries Input → Select dropdown (10/20/50/All). Client-side descending sort added as defensive measure.

Session archive: [archive/sessions/2026-06-26 — The Book Load Menu, Ordering, and SSE Backfill Fix.md](archive/sessions/2026-06-26 — The Book Load Menu, Ordering, and SSE Backfill Fix.md)

### Also done 2026-06-26 (Book: Synth token counts + conversation history)

- **Synth tokens showing 0:** `_openai_compat_stream` only captured usage from the trailing choices-empty chunk (OpenAI pattern). Vertex AI embeds usage in the final content chunk (`finish_reason="stop"`, choices non-empty). Added second capture path guarded by `_usage_recorded` flag. Confirmed working.
- **Conversation history not in Column 3:** `recent_history` was fed to the model but not stored in `context_sections`. Now serialized as `USER:/ASSISTANT:` text and added as `"conversation_history"` key. The Book's Column 3 shows it in a new "Conversation History (fed to Synth)" collapsible. Appears from the second exchange onward (first message after restart has no prior history — expected).
- Deployed `e1a12d2`.

Session archive: [archive/sessions/2026-06-26 — Book Synth Token Counts and Conversation History.md](archive/sessions/2026-06-26 — Book Synth Token Counts and Conversation History.md)

### Also done 2026-06-26 (single exchange troubleshoot — SEQ 026 / Logistics routing)

Root-caused why "Delayed until Monday at 5:30." (SEQ 026, 16:28:23) did not trigger a scheduling action. Coordinator dispatched zero specialists; Synthesizer absorbed it conversationally. Three fixes deployed:

1. **`config/agents/coordinator.md`** — Logistics entry broadened: added explicit "also call when user defers or postpones anything to a named time" rule; added deferral signal words (delayed, postponed, rescheduled, moved to, pushed to, bumped, put off, defer, reschedule, changed to, updated to) and temporal commitment triggers (tomorrow, next week, this weekend, next month, end of month/week, next year, by [day name], on [day name], [day] at [time]).
2. **`config/agents/synthesizer.md`** — `write_config` scope clarified (recurring proactive sessions only; one-off deferrals → Logistics). Catch-up rule added: if user message contains a temporal commitment signal and no Logistics output in context package, call `run_subagent("logistics")` before responding, log `ROUTING_MISS: Logistics`, call `write_quality_event`.
3. **`tools/subagent.py`** — Diarist removed from Synthesizer's `run_subagent` schema (Coordinator always dispatches it fire-and-forget; Synth has no use case for calling it directly). Confirmed: Coordinator dispatches Diarist via `_dispatch_from_coordinator` text parsing, not tool calls — schema change has no effect on Coordinator.

**Clarifications established:**
- No "Scheduler agent" exists. Scheduling = Logistics (`write_calendar_event`) for one-off events/deferrals; `write_config` for recurring Metatron session entries (habits, standing check-ins). These are distinct.
- Pattern Miner and Goals Interviewer should not be in Synth's callable agent list — PM runs on schedule, Goals runs at first-instance onboarding only.
- Coordinator model upgrade is not the right fix for routing misses; missing rules are the cause.
- Synth token tracking (in=0 out=0) was broken before ~17:05 on 2026-06-26; confirmed working from 17:05 onwards. No code change needed.

**Open:** (1) Test Coordinator fix with a deferral message in app, verify Logistics in trace. (2) Verify `write_calendar_event` actually connects to a real calendar, not just flat file logging.

Commits: `e477c76`, `5f21800`, `5a7c6ff`. Session archive: [archive/sessions/2026-06-26 — Single Exchange Troubleshoot SEQ 026 Logistics Routing.md](archive/sessions/2026-06-26 — Single Exchange Troubleshoot SEQ 026 Logistics Routing.md)

### Also done 2026-06-26 (The Book: call timing, tokens, load menu, server fixes)

Seven fixes across `core/trace.py`, `core/orchestrator.py`, `core/server.py`, `tools/metatron_monitor.py`:

1. **Tool call timing:** `duration_ms` changed to float (`round(..., 1)`); `ToolCallRecord` now stores 1-decimal ms precision. 0ms sub-millisecond ops now show e.g. `0.3ms`.
2. **Token counts per call:** `ToolCallRecord` extended with `input_tokens`/`output_tokens`. For `run_subagent`, tokens pulled from subagent `AgentRecord` at dispatch time and shown on collapsible title in Column 3.
3. **`run_subagent` not recorded (Gemini native parallel path):** `_run_gemini_native_loop` parallel branch now propagates thread-local trace context (same pattern as Anthropic path). Previously all Coordinator subagent calls were silently dropped from traces.
4. **Server blocking event loop:** `session_stream` iterated a sync generator inline in `async def`, blocking uvicorn for 10–30s — no monitor requests could be served during a pipeline run. Fixed: `_produce()` runs in `run_in_executor`; chunks queued via `asyncio.Queue` + `run_coroutine_threadsafe`. `/session` non-streaming also fixed with `run_in_executor`. Zero latency impact.
5. **Personas not loading on launch:** `load_personas()` now retries 4× with exponential backoff. R key now also retries persona load when no persona is selected.
6. **Freezing on persona switch:** SSE worker cancel moved to top of `load_data()` (was deferred until after HTTP requests — caused old-persona SSE to write to new-persona's list mid-load).
7. **Load menu + most-recent-first:** New `#load-bar` in The Book with Range presets (1h/6h/24h/7d/30d/All) and Max count input. Default: 24h, 10 messages. Server `/monitor/conversations` and `/monitor/traces` now accept `since` + `limit` and return newest-first. Column 1 now shows most recent messages at top; SSE live messages prepend to top.

Session archive: [archive/sessions/2026-06-26 — The Book Call Timing, Token Counts, Load Menu, and Server Fixes.md](archive/sessions/2026-06-26 — The Book Call Timing, Token Counts, Load Menu, and Server Fixes.md)

---

### Also done 2026-06-26 (pipeline debugging + latency work)

Phase 1 — Three root-cause bugs fixed. First live response confirmed via browser (see session archive for details).

Phase 2 — Latency reduction. Warm-cache second-message latency: ~40s → **~20s**. Streaming text now appears word-by-word in UI.

Key changes:
1. **Agent name normalization** — `_normalize_agent()` in `_dispatch_from_coordinator`. All casing/spacing variants ("Physical Health", "Logistics", etc.) now resolve to correct filenames. MW, PH, and other specialists were silently dropping on every session.
2. **Coordinator: Pro → Flash-Lite** — single-pass routing directive, no tools. Saves ~3–5s.
3. **Vertex cache fix** — tools now baked into `CreateCachedContentConfig`. Eliminates guaranteed native-loop-fail + compat-fallback double round-trip on every tool-bearing agent (Synthesizer, specialists). `cache_read=12000+` visible in logs.
4. **trace.py committed** — `ToolCallRecord.input_tokens`/`output_tokens` had been applied locally but never committed; old VM version crashed native loop.
5. **Streaming client** (`static/index.html`) — coordinator uses `/session/stream` (SSE). Text streams into bubble word-by-word (`▍` cursor). TTS fires on `[DONE]`. TODO (future): phrase-by-phrase TTS with pauses.
6. **Streaming thought_signature fix** (`_openai_compat_stream`) — when Synthesizer emits text + `write_context_tracker` in one streaming turn, stream deltas lack Vertex's `thought_signature`. Fix: replay that turn blocking using pre-turn message snapshot; apply `model_copy()` workaround. Already-yielded text is correct; replay used only for signed message construction.

**Next:** specialist token reduction (plan Steps 3–5) — specialists still running 5–8 tool-call turns; this is the biggest remaining latency lever. Then B1/Check10/Check12 for A7 sign-off.

Session archive: [archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md](archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md)

### Also done 2026-06-26 (troubleshooting prompts + interchange ID design)

Meta/planning block — no code changes. Three deliverables:

1. **TTS phrase-by-phrase note confirmed recorded** — `// TODO future: phrase-by-phrase TTS` in `static/index.html` (`sendStreaming`), session archive, and SESSION.md.
2. **Latency troubleshooting prompt written** — general-purpose prompt for diagnosing a specific exchange: pull VM logs for a time window, break down latency by component, evaluate Coordinator routing and RESOLVED_INTENT, compare what happened vs. what should have happened. Text in chat transcript; reuse by pasting into a new chat with a target time window.
3. **Interchange ID design recommendation** — daily zero-padded sequential counter (`001`, `002`…) as `seq` field in `data/conversations/YYYY-MM-DD.jsonl`. Display as `#003  14:23` in Column 1. Implementation prompt written (two steps: `_log_conversation` in `core/server.py` + Column 1 display in `tools/metatron_monitor.py`). Not yet implemented.

Session archive: [archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md](archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md)

### Also done 2026-06-24 (token reduction — Steps 1–5)

**Token reduction implementation complete (Steps 1–5 of 6).** Projected ~3× reduction (Steps 1–5); ~5× with Step 6.

- **Step 1:** `git tag v0.5-pre-refactor` — snapshot before any changes.
- **Step 2:** Per-agent tool schema whitelists. `allowed_tools` added to `routing_cloud.yaml` and `routing.yaml` for all agents; `core/router.py` — `ModelConfig.allowed_tools` field + `get_allowed_tools()` function; `core/orchestrator.py` — schema filter in `_run_single_agent()`. Only advertised schemas go to the LLM; Python functions stay registered. (~15,000t saved)
- **Step 3:** Strip constitution/prime_directive from specialist system prompts. Three-branch context loading in `_run_single_agent()`: bare (research_agent), head layer (full config + recent context), specialists (goals.yaml only). `_HEAD_LAYER_AGENTS = {"coordinator", "synthesizer"}`. `load_goals()` function added. (~5,000t saved)
- **Step 4:** Specialists no longer call `load_recent_context()` independently. Context arrives via Coordinator directive. (~3,000t saved)
- **Step 5:** Quick/deep behavioral sections added to all 8 specialist agent files (mental_wellbeing, physical_health, work_vocation, relationships, finance, learning_growth, recreation_hobbies, logistics). Existing language preserved exactly; Quick mode is a gate only. MW clinical detection active in all modes without exception.
- **Step 6 (deferred):** Coordinator restructure — single-pass directive assembly replaces 3-turn session. Do after Steps 1–5 stable. (~15,000t saved from Coordinator alone)

Session archive: [archive/sessions/2026-06-24 — Token Reduction Architecture and Implementation.md](archive/sessions/2026-06-24 — Token Reduction Architecture and Implementation.md)

### Also done 2026-06-22 (token economics analysis)
- **Pipeline token cost traced end-to-end:** ~95,000 input tokens for a 70-token user message (~13× overhead). Coordinator (3 turns): ~22,000t. 5 sync specialists (2 turns each): ~49,000t. Synthesizer (2 turns): ~14,790t.
- **Three waste sources identified:**
  1. Tool schemas (~2,000t) paid 9× across all invocations — each agent/specialist receives all 30 schemas regardless of which 2–3 it uses. Synthesizer pays for schemas it never calls (streaming path confirmed no-tool in code comments).
  2. Shared config (constitution + prime_directive + mission + goals, ~1,400t) paid 9× — no cross-agent caching.
  3. Recent context (~600t) loaded independently 8× — each specialist calls `load_recent_context()` even though Coordinator already has it and constructs their directive from it.
- **Three fixes without architectural change** would cut to ~55,000t: (1) route tool schemas per agent, (2) pass recent context in the directive rather than reloading in specialists, (3) strip constitution from specialist system prompts (mirrors existing research_agent pattern).
- **Architectural question raised:** should all specialist calls live in Synthesizer, with Coordinator being a cheap single-turn router only? Coordinator currently costs ~22,000t; as lightweight classifier it would cost ~1,000t. Synthesizer already does secondary chains (ReAct, up to 3 rounds per its agent file). No decision made — deferred.
- Session archive: `archive/sessions/2026-06-22 — Token Economics and Pipeline Architecture Analysis.md`

### Also done 2026-06-22 (The Book — monitoring tool iteration)
- **The Book** (`tools/metatron_monitor.py`) — substantial iteration on the monitoring TUI.
- **Bug fixes:** persona bleed in Column 1 (conversations endpoint now always filters by persona), subagent name showing as `run_subagent(?)` (arg key is `agent_name`), SSE disconnect on ID collision (list items no longer use IDs; SSE loop is append-only), snapshot crash (`s` key priority binding), chat "no response" (dropped `streaming_json`, now uses `--output-format text` via temp file + shell redirect).
- **Column 1:** datestamps added; each message block is now a `Collapsible` — collapsed shows truncated preview, expanded shows full user + Metatron text.
- **Column 3:** turns flattened to Static dividers with tool calls as top-level Collapsibles; `run_subagent` now resolves to the actual subagent record (provider/model/tokens/output files) instead of raw args.
- **Diary/file history viewer:** clicking a file link opens all entries in that directory, sorted by date, with the current entry marked `← current` in green. New `GET /monitor/history` endpoint on server.
- **Output file tracking:** `core/trace.py` now scans tool call args and results for `data/...` paths; stores as `output_files` on `AgentRecord`; included in JSONL serialization and shown as clickable buttons in Column 3.
- **Snapshot (`s` key):** writes `data/book_snapshot.md` to Mac project dir with current Book state — bridge to Claude Code in VSCode.
- **Chat panel (`c` key):** bottom panel with Input, Send, Clear, token counter. Sends messages to `claude -p --output-format text` via temp file; builds recursive context (full `Human:/Assistant:` history prepended each turn). Chat panel still unconfirmed working — under investigation.
- **New server endpoints:** `GET /monitor/history`, `GET /monitor/file`.
- Session archive: `archive/sessions/2026-06-22 — The Book Iteration and Chat Panel.md`

### Also done 2026-06-21 (Android end-to-end testing)
- **All 10 Android tests pass.** App fully functional on VM.
- Mike persona synced to VM; Vertex key deployed; Whisper installed.
- Server migrated to HTTPS via Tailscale cert (`metatron-vm.tail0acc5d.ts.net:8001`).
- Fixed: PortAudio crash (lazy sounddevice import), provider defaulting to ollama (now auto-route), send button layout, mic auto-prompt (MainActivity.java), audio autoplay on Android (AudioContext unlock).
- **Cloudflare Tunnel** added to roadmap as pre-alpha requirement (removes Tailscale from phone).
- **D1 open:** Run Goals Interview on VM — `BASELINE_INCOMPLETE` on every session until done. Run via CLI: `python core/orchestrator.py --agent goals_interviewer --provider gemini`
- Session archive: `archive/sessions/2026-06-21 — Android End-to-End Testing.md`

### Also done 2026-06-21 (CLAUDE.md deployment infrastructure)
- **CLAUDE.md updated:** "Per-System Configuration" replaced with comprehensive "Deployment Infrastructure" section covering topology diagram, GCP VM, Vertex AI, billing protection, Tailscale, systemd unit files (verbatim), GitHub/deploy pipeline, Python env, all environment variables, routing/deployment mode, Android app build steps, local dev mode, and a 10-step recreate-from-scratch checklist.
- **Model version note** in CLAUDE.md updated (2026-05-19 → 2026-06-21; Flash-Lite ID corrected to non-preview).
- Session archive: `archive/sessions/2026-06-21 — CLAUDE.md Deployment Infrastructure Section.md`

### Also done 2026-06-20 (VM provisioning, GitHub, deploy pipeline)
- **GCP VM provisioned:** `metatron-vm`, `e2-medium`, Debian 12, `us-central1-a`. Python 3.11, ffmpeg, all deps installed.
- **Tailscale on VM:** joined tailnet. **VM Tailscale IP: `100.64.226.49`** — phone connects here (not the Mac). Health check confirmed via Tailscale.
- **Vertex credentials on VM:** service account `metatron-vertex@metatron-ai-499810.iam.gserviceaccount.com` with `roles/aiplatform.user`. Key at `~/multi-model-mcp/vertex-key.json`, `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.
- **systemd services:** `metatron-server.service` (port 8001, `--persona mike`) + `metatron-scheduler.service` — both enabled and `active (running)`.
- **GitHub repo:** `github.com/MikeApex/metatron` (private). SSH key `~/.ssh/github_mikeapex` on Mac, deploy key `metatron-vm` on VM.
- **Deploy pipeline:** `./deploy.sh` — pushes to GitHub, VM pulls, restarts services. Post-commit hook reminds to deploy after every commit.
- **Always-on Mac backup:** not yet implemented — deferred until needed (VM is primary). When needed: `pmset` for sleep prevention + launchd plist (see notes below).
- **Login/profile screen:** added to `static/index.html`. Shows on first launch; auto-logins on return via `localStorage`. Persona dropdown (mike + all test personas grouped). Password field (placeholder, not enforced). Persona chip in header — tap to switch.
- **APK rebuilt and sideloaded:** new VM Tailscale IP (`100.64.226.49`), login screen, new mem icon. Java 21 installed via Homebrew. Adaptive icon XMLs removed — Android now uses PNG directly (fixes home screen icon caching issue). APK served via `python3 -m http.server 8888` on Mac Tailscale IP.
- **GitHub:** `github.com/MikeApex/metatron` (private). SSH key `~/.ssh/github_mikeapex`. Deploy key `metatron-vm` on VM. `./deploy.sh` pushes to GitHub + restarts VM services. Post-commit hook reminds to deploy.
- **requirements.txt** generated from venv (95 packages) and committed.

### Also done 2026-06-19 (Vertex AI setup session)
- **GCP project created:** `metatron-ai-499810`, billing linked, Vertex AI API enabled, ADC configured.
- **Billing hard-cap at $20:** Pub/Sub topic `billing-cap` + Cloud Function `stop-billing` (Python 3.11, Gen2) auto-disables billing when budget fires. IAM grants in place.
- **Vertex AI migration:** `run_session_gemini_grounded()` now uses Vertex native SDK (`genai.Client(vertexai=True)`). Vertex requires `location=global` for Gemini 3.x models. `.env` updated with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `DEPLOYMENT_MODE=cloud`.
- **`routing_cloud.yaml` created:** all 14 agents on `gemini-3.1-pro-preview` via Vertex. `DEPLOYMENT_MODE` toggle in `router.py` (evaluated at call time, not import time — fixes `.env` load order bug).
- **Flash model ID updated:** `gemini-3.1-flash-lite-preview` → `gemini-3.1-flash-lite` (old preview discontinues July 9).
- **sys.path fix:** orchestrator now inserts project root so `tools/` resolves correctly when running `python core/orchestrator.py`.
- **Smoke test:** Research Agent via Vertex returned valid grounded response. Full pipeline: 60–90s latency (multiple sequential Gemini 3.1 Pro calls via AI Studio — see open item below).
- **Repo cleanup:** .gitignore expanded; all previously untracked files committed (108 files).
- **Vertex native SDK migration complete (2026-06-19):** `run_session_gemini()` now uses `_run_gemini_native_loop()` via `genai.Client(vertexai=True)` — same client setup as `run_session_gemini_grounded()`. All Gemini agents (coordinator, synthesizer, all specialists) are now on the native SDK. `_openai_compat_loop()` retained for OpenAI/Ollama paths only. One fix required: Gemini API rejects empty-string enum values; handled in `_clean_schema_for_gemini()` at conversion time. Tested: single-shot full pipeline + two-turn interactive history threading. Session archive: `2026-06-19 — Native SDK Migration (Gemini).md`.
- **Next sessions ready:** efficiency prompt + Android app prompt both written and in this archive.

### Also done 2026-06-17 (Metatron Android app session)
- **Metatron Android app built and working** — Capacitor wrapper, sideloaded APK, voice end-to-end confirmed.
- **Private STT pipeline** — Web Speech API (Google cloud) replaced with server-side Whisper via `/transcribe` endpoint. Audio archived to `data/audio/`. ffmpeg installed.
- **Server running HTTP on port 8001** (no TLS) — Tailscale WireGuard provides transport encryption. Certs backed up to `certs_backup/`.
- **Capacitor config:** bundled assets (secure context for mic), `SERVER` constant for API calls, `allowMixedContent: true`, 10-minute fetch timeout, dropdowns hidden, mike persona active.
- **Tailscale cleanup:** old stale device removed, host renamed to `mikes-macbook-air` in admin.tailscale.com. Direct IP `100.70.67.45` used in app (DNS not resolving in WebView).
- **Mem icon:** Phoenician/early Hebrew mem glyph, parchment+brown, generated by `tools/gen_icon.py`.
- **Next (on hold):** (1) Tailscale same-network vs. remote behaviour, (2) Mac always-on + Ollama warm, (3) login/profile selection in app.
- **⚠ HOLD (2026-06-17):** All Metatron / infrastructure work paused pending decision on whether to migrate hosting to Google Vertex VM. Decision resolves the architecture (local Mac vs. cloud VM as the LLM host) before further build work proceeds.

### Also done 2026-06-16 (continuation of A4/A6 session)
- **Synthesizer CRITICAL block** added — mandatory surface rules for `CLINICAL_CONCERN` and `MUST_SURFACE` flags; cannot be held or deferred; front-loaded after Confidentiality section (same pattern as MW fix). Covers mania, suicidal ideation, depression, missed critical medication.
- **CONSULT_NEEDED routing logic** added to Track E in roadmap — named deferred item with B2 dependency documented. Previously only mentioned verbally.
- **Prompt structure front-loading audit complete** — all 9 specialist agents assessed; only Synthesizer required immediate fix; Physical Health noted for D2 pass.

---

### Decisions resolved 2026-06-10
- **Binding privacy ruling:** sensitive data never reaches a cloud model — no fallbacks, no deferrals. Drove new A4 and re-tiering of routing.yaml (to be implemented at A4; current routing.yaml cloud fallbacks are stale).
- Check 7 vs. D2 conflict: resolved — assumptions documented now + safety hard-fails run on the local model at A4; full validation at Phase 6 / D2.
- E3 removed from Phase 6 close gate (circular dependency); Stage 2 builds single-user, Stage 3 automation gated on multi-user cohort.
- o3 Pattern Miner production test retired — Pattern Miner is local-only.
- Time Director carries no test obligations; testing plan amended.

---

## Useful context to pull as needed

| Question | Where to look |
|---|---|
| What does each agent do? | `config/agents/` |
| What tools exist and what they do | `tools/` — all registered in `core/orchestrator.py → register_tools()` |
| What's the security posture? | `archive/security/threat_model_2026-06-04.md`, `archive/security/security_backlog_2026-06-04.md` |
| What are the test criteria for this phase? | `tests/phase5_testing_plan.md` |
| What's parked for later phases? | `archive/plans/future_phases.md` |
| Agent enhancement backlogs | Roadmap Section 4, or `## Enhancement backlog` at the bottom of each agent file |
| Session history | `archive/sessions/` — sorted by date |
| Model routing assignments | `config/modules/routing.yaml` |
| How to run the system | See Quick Start below |

---

## Quick start

> **⚠ Switching to local Mac routing (Ollama)?** Two things must be activated first:
> 1. `sudo pmset -a sleep 0 disksleep 0` — prevent Mac sleep
> 2. `launchctl load ~/Library/LaunchAgents/com.metatron.server.plist` — keep server alive (create plist first if not done — see `archive/sessions/2026-06-20 — VM Provisioning, GitHub, Deploy Pipeline.md`)
> Reverse with: `sudo pmset -a sleep 10 disksleep 10` and `launchctl unload ~/Library/LaunchAgents/com.metatron.server.plist`

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate

# Start the PWA server (Vertex cloud routing — default as of 2026-06-19)
# No Ollama needed — DEPLOYMENT_MODE=cloud in .env routes all agents to Vertex
python core/server.py --persona mike --port 8001

# Kill a stuck server on port 8001 and restart
lsof -ti :8001 | xargs kill -9 && python core/server.py --persona mike --port 8001

# Run a specific agent directly
python core/orchestrator.py --agent research_agent --provider gemini

# Run the scheduler daemon
python core/scheduler.py
```

**Deployment mode:** `DEPLOYMENT_MODE=cloud` is set in `.env` — loads `config/modules/routing_cloud.yaml` (all agents → Vertex Gemini 3.1 Pro). To use local Ollama instead, remove or unset `DEPLOYMENT_MODE`.

**Vertex credentials:** ADC configured via gcloud on this machine. GCP project: `metatron-ai-499810`, location: `global`.

**If using local Ollama:** `ollama serve` at `localhost:11434`, model `qwen3:14b`.

---

## Model IDs (updated 2026-06-19)

| Provider | Model | ID | Notes |
|---|---|---|---|
| Anthropic | Sonnet 4.6 (default) | `claude-sonnet-4-6` | |
| OpenAI | o3 | `o3` | |
| Gemini | Flash-Lite | `gemini-3.1-flash-lite` | ✓ confirmed on Vertex (no `models/` prefix on Vertex) |
| Gemini | Pro | `gemini-3.1-pro-preview` | ✓ confirmed on Vertex |
| Ollama | Local 14B | `qwen3:14b` | local only |

**Vertex note:** AI Studio uses `models/gemini-*` prefix; Vertex drops the prefix. The orchestrator strips it automatically when `GOOGLE_CLOUD_PROJECT` is set. Flash-Lite preview ID discontinues July 9 — already updated to non-preview ID.

---

## Key design decisions (don't revisit without cause)

- Config files are the product. Code is infrastructure. Behavior changes = config edits.
- All personal context is sensitive-tier. Cloud LLMs receive only fully decontextualized requests.
- **Sensitive data never reaches shared cloud infrastructure — fail-closed, no fallbacks (binding ruling 2026-06-10).** Head layer and all personal-data specialists run local. Ollama down = hard error, never a cloud call. **Amendment 2026-06-18:** a dedicated VM with verified Zero Data Retention (e.g., Vertex AI ZDR) is acceptable during testing — contractual sequestration is a distinct threat model from shared cloud. North star is still architectural security on private hardware (local/A100/H100); VM path is explicitly temporary.
- Discretion: users never see which agent was called, which model ran, or how data was routed.
- The tool surfaces hypotheses, not verdicts. Output invites correction; doesn't foreclose it.
- Archive-on-merge: data is never deleted; moved to archive with a merged_into pointer.
- `age` encryption deferred to Phase 6. Until then, file permissions (600) are the protection.
