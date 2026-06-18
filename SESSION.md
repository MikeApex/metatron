# Session Primer — Personal AI Life Manager
*Updated: 2026-06-18. Update this file at the close of every chat so the next chat — or any parallel chat window — starts from current state.*

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

**Parallel execution is live (2026-06-11):** seven simultaneous chats, one prompt file each — see [archive/plans/parallel_chats_index_2026-06-11.md](archive/plans/parallel_chats_index_2026-06-11.md) for the launcher, file-ownership rules, and close-out order. Covers A1, A2, A3, A4+A6, B1, and the check 10 + check 12 sign-off prep. A5 stays user-run (gated on A4); A7 runs last.

- ~~**A1** Compliance curve design conversation~~ — **done 2026-06-18.** All four design questions resolved. Shared principle + Synthesizer integrator (Q1); user-reported cold-start, ratchet research-gated (Q2); Synthesizer level only (Q3); nothing activates at A5c, produces plan only (Q4). Decision doc: `archive/plans/compliance_curve_decision_2026-06-13.md`. Agent file edits queued (apply when A2 chat closes). MCP server updates: o3+o1+auto-discovery added to ask_gpt; auto-discovery added to ask_gemini; Opus timeout fixed (600s) in ask_claude.
- ~~**A2** Logging Layer~~ — **done 2026-06-13.** `write_quality_event` in `tools/logger.py`, ROUTING_MISS wired in synthesizer.md, USER_CORRECTION in coordinator.md, PWA tap (`·` dot → `/feedback`). Tests deferred to Alpha launch (`tests/phase5_testing_plan.md` → Known gaps).
- ~~**A3** Cold-start baselines~~ — **done 2026-06-18.** 4 new functions in `tools/baselines.py`: `create_semantic_anchor`, `write_aspirational_baseline`, `shuffled_null_score`, `score_against_anchors`. All 8 canonical anchors written to `data/baselines/semantic_anchors.json`. All 3 roadmap tests pass. Truncated Goals Interview run-guide in `archive/sessions/2026-06-18 — A3 Cold-Start Baselines.md`. A5b re-run pending (after full Goals Interview).
- ~~**A4** Local routing enforcement~~ — **done 2026-06-13.** `local_enabled: true`, fail-closed sensitive routing (no cloud fallbacks), head layer + Learning & Growth + Recreation + Logistics re-tiered local, quick_override guard. MW mania hard-fail: PASS (front-loaded critical instructions). Finance arithmetic: FAIL/deferred D1. Session archive: `2026-06-13 — A4 A6 Local Routing and Token Budget.md`.
- ~~**A5** Goals Interview with real user~~ — **done.** A5b: re-run `write_aspirational_baseline` with existing A5 interview data (replaces A3 placeholder; required for A7 gate — run before A7). A5c preference activation status unknown — confirm if needed. **D1 note:** once VM is provisioned and new features are live, run a fresh Goals Interview + A5b re-run as first-use onboarding on the VM (new D1 item, separate from this A5b).
- ~~**A6** Token budget logging~~ — **done** (all four session paths; 8K warning threshold)
- **A7** Phase 5 sign-off — **blocked on parallel chats completion** (A1 and B1/check10/check12 prep from the 2026-06-11 batch not yet done; A3 done 2026-06-18). Gate: A1–A6 all complete. See [archive/plans/parallel_chats_index_2026-06-11.md](archive/plans/parallel_chats_index_2026-06-11.md) for what's outstanding.
- **B1** Red team can start now, independent of Alpha Gate

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

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate

# Run the full pipeline (Coordinator → Synthesizer → specialists)
python core/orchestrator.py

# Run a specific agent directly
python core/orchestrator.py --agent goals_interviewer --provider ollama

# Start the PWA server
python core/server.py

# Run the scheduler daemon
python core/scheduler.py
```

Ollama (local sensitive-tier model) runs at `localhost:11434`. Model: `qwen3:14b`.
Start with: `ollama serve` (if not already running as a service).
All 4 providers: anthropic (Sonnet 4.6), openai (o3), gemini (Flash/Pro), ollama (qwen3:14b).

---

## Model IDs (current as of 2026-06-10)

| Provider | Model | ID |
|---|---|---|
| Anthropic | Fable 5 (most capable) | `claude-fable-5` |
| Anthropic | Sonnet 4.6 (default) | `claude-sonnet-4-6` |
| Anthropic | Haiku 4.5 | `claude-haiku-4-5-20251001` |
| OpenAI | o3 | `o3` |
| Gemini | Flash | `models/gemini-3.1-flash-lite-preview` ⚠ verify |
| Gemini | Pro | `models/gemini-3.1-pro-preview` ⚠ verify |
| Ollama | Local 14B | `qwen3:14b` |

⚠ Gemini model IDs in `routing.yaml` may be stale — verify at Phase 6 / D2 before model validation pass.

---

## Key design decisions (don't revisit without cause)

- Config files are the product. Code is infrastructure. Behavior changes = config edits.
- All personal context is sensitive-tier. Cloud LLMs receive only fully decontextualized requests.
- **Sensitive data never reaches shared cloud infrastructure — fail-closed, no fallbacks (binding ruling 2026-06-10).** Head layer and all personal-data specialists run local. Ollama down = hard error, never a cloud call. **Amendment 2026-06-18:** a dedicated VM with verified Zero Data Retention (e.g., Vertex AI ZDR) is acceptable during testing — contractual sequestration is a distinct threat model from shared cloud. North star is still architectural security on private hardware (local/A100/H100); VM path is explicitly temporary.
- Discretion: users never see which agent was called, which model ran, or how data was routed.
- The tool surfaces hypotheses, not verdicts. Output invites correction; doesn't foreclose it.
- Archive-on-merge: data is never deleted; moved to archive with a merged_into pointer.
- `age` encryption deferred to Phase 6. Until then, file permissions (600) are the protection.
