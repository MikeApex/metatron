# Session Primer — Personal AI Life Manager
*Updated: 2026-06-26 (The Book fixes — call timing, token counts, load menu, server unblocking). Update this file at the close of every chat so the next chat — or any parallel chat window — starts from current state.*

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

### Also done 2026-06-26 (pipeline debugging — first live response)

Three root-cause bugs fixed. First live response confirmed via browser.

1. **`tools=[]` → invalid Gemini API call** — `_to_gemini_tools([])` returned `[Tool(function_declarations=[])]` (invalid). Native loop threw, fell back to compat, which also passed `tools=[]` → `content=None`. Coordinator always returned `""`. Fixed: empty tools list → omit tools param in both loops.
2. **Synthesizer text discarded alongside tool call** — both loops only captured text when `finish_reason != "tool_calls"`. Fixed: capture text before entering tool-call branch in both `_run_gemini_native_loop` and `_openai_compat_loop`.
3. **Agent instruction gaps** — Coordinator produced prose instead of SPECIALISTS_TO_CALL format; Synthesizer called `write_context_tracker` alone with no text then returned nothing. Fixed: hard format mandate in coordinator.md; text+tool same-turn ordering rule in synthesizer.md.

**Open: agent name mismatch** — Coordinator writes "Physical Health" / "Mental Wellbeing" (spaced); dispatch looks for `physical_health.md` / `mental_wellbeing.md`. MW/PH specialists silently fail. Fix: normalization in `_dispatch_from_coordinator` or update coordinator.md agent names.

Session archive: [archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md](archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md)

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
