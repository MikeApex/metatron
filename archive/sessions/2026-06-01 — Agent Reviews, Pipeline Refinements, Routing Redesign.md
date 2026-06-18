# 2026-06-01 — Agent Reviews, Pipeline Refinements, Routing Redesign

## What happened

Continuation session following 2026-05-28 (Coordinator-Synthesizer build). Reviewed the newly built pipeline files and resolved a series of design gaps across routing, context management, specialist coverage, and phase planning.

---

### Coordinator and Synthesizer post-build review

User reviewed the newly written coordinator.md and synthesizer.md. User made direct edits to coordinator.md, adding:
- **PROACTIVE_FLAGS section** to the output format and a corresponding scan directive in session-start loading: Coordinator actively scans loaded context for unmentioned signals (unbroken patterns, approaching inflection points, Pattern Miner flags not recently surfaced) and surfaces them as PROACTIVE_FLAGS. No extra tool calls — a side-product of the context load.

**Diarist routing strengthened:** Updated in coordinator.md — Diarist should be called for *any message containing any data point*. Over-logging is far less harmful than under-logging. Signal words expanded to include eating, sleeping, who they saw.

**Logistics scope expanded:** Updated in coordinator.md — Logistics is the execution layer for *any* action that needs to happen in the world: sending email, paying bills, ordering, booking, scheduling recurring habits. Not just calendar/travel. Signal words expanded accordingly.

---

### Routing redesign — item 2

The tier abstraction (cloud_fast / cloud_deep / cloud_analytical) was removed in favor of direct per-agent model assignments. The previous design assigned models via named tiers, meaning agents sharing a tier were treated identically.

**New routing.yaml structure:** Each agent specifies `provider` and `model` directly. Sensitive (local-first) agents specify `local: true` with `fallback_provider` and `fallback_model`. A single `quick_override` entry at the top covers all `complexity="quick"` calls.

**router.py simplified:** Three-path resolution — quick override, local (with fallback), direct assignment. No tier table lookup. `_log_fallback` simplified (logs agent name + reason only).

**Model assignments and their basis:**

| Agent | Model | Basis |
|---|---|---|
| Coordinator | Haiku 4.5 | Assumption — routing/classification doesn't need Sonnet |
| Synthesizer | Sonnet 4.6 | Assumption — user-facing integration; best model |
| Diarist | Sonnet fallback | Phase 3 testing confirmed |
| Pattern Miner | o3 fallback | Phase 3 testing confirmed |
| Goals Interviewer | Sonnet fallback | Assumption — nuanced conversation |
| Mental Wellbeing | Sonnet fallback | Assumption — empathetic nuance |
| Physical Health | Sonnet fallback | Assumption — medical knowledge |
| Work & Vocation | Sonnet fallback | Assumption |
| Relationships | Sonnet fallback | Assumption |
| Finance | o3 fallback | Assumption — financial analysis / structured reasoning |
| Learning & Growth | Gemini 3.1 Pro | Assumption — broad knowledge synthesis |
| Research Agent | Gemini 3.1 Pro | Assumption — external knowledge breadth |
| Recreation & Hobbies | Gemini Flash | Assumption — low complexity |
| Logistics | Gemini Flash | Assumption — task execution |

**Most specialist assignments are hypotheses, not confirmed.** Phase 3 testing covered only Diarist, Pattern Miner, and archiving. A full per-agent model validation pass is now planned for Phase 6 (see below).

---

### Context tracker — held items (item 3)

**Gap identified:** The context tracker had no explicit mechanism for items the Synthesizer chose not to surface. "Hold for later" could silently accumulate or get lost across sessions.

**Fix:** Added `held_items` field to `write_context_tracker` and `read_context_tracker`. Each held item must state WHAT was held and WHY. Items that age across multiple sessions without resolution should be reviewed: surface when the moment is right, or consciously dismiss if no longer relevant (time resolves many things). Passive accumulation without decision is not acceptable.

`read_context_tracker` backfills the field for tracker files written before this change.

Synthesizer instruction updated: held items are mandatory in the tracker, not optional.

---

### Conversational archive (item 4)

Confirmed. `_log_conversation()` added to `core/server.py`. Every exchange appends a verbatim `{ts, agent, persona, user, response}` record to `data/conversations/YYYY-MM-DD.jsonl`. Verbatim transcripts now exist for testing and calibration.

---

### Scheduler and proactive reminders (item 5)

`core/scheduler.py` and `config/modules/scheduler.yaml` fully operational (built Phase 4). Current jobs: morning_brief (07:30 weekdays), companion_checkin (every 90 min), evening_diarist (20:00), weekly_pattern_miner (Sunday 09:00).

**Updates this session:**
- `morning_brief` and `companion_checkin` updated from `time_director`/`diarist` to `coordinator` (triggers full pipeline)
- Logistics agent now explicitly knows it can write scheduler.yaml entries via `write_config` for user-directed recurring reminders (workout, instrument practice, medication)
- **Synthesizer can write scheduler entries autonomously** — not only on user direction. If a stated goal has no supporting scheduled prompt, Synthesizer should create one. Added to synthesizer.md tools section.

---

### Vocal stress detection (item 6)

Not built. Audio `.webm` files already saved to `data/audio/`. Prosody analysis (pitch, speech rate, voice tremor) would provide emotional stress signal independent of text. Infrastructure exists; analysis layer does not. Noted as Phase 6+ in revision_3_1_snapshot.md future revision notes.

---

### Constitution — rule established (item 7)

Constitution.md was erroneously modified during this session (communication principles and future backlog added). Immediately reverted. `git diff HEAD` confirmed clean — no net change to constitution.md.

**Rule established:** Do not alter `config/constitution.md` without explicit user instruction. Saved to memory.

Chris Voss (*Never Split the Difference*) communication principles (tactical empathy first, label don't interpret, calibrated open questions, mirror + silence, no unsolicited verdicts) noted as a reference for a future Synthesizer voice and framing guide (`config/voice.md`). Stored in:
- `revision_3_1_snapshot.md` future revision notes (primary)
- `synthesizer.md` enhancement backlog (secondary)

---

### Error handling (item 8)

Added to Phase 6.5 as Deliverable 6. Key questions to address: Synthesizer failure framing without architecture leak, Coordinator context load failure degradation, API retry policy, chain depth enforcement, parallel fan-out partial failure handling.

---

### Model assignment basis — honest assessment

Per user question: most Phase 5 specialist model assignments were made by assumption, not testing. Phase 3 testing confirmed assignments for Diarist and Pattern Miner only. All others (Coordinator, Synthesizer, all domain specialists) are working hypotheses based on general model capability knowledge.

**Added to Phase 6 deliverables:** Per-agent model validation pass using Phase 3 testing convention. Cross-reference with cost analysis (`archive/plans/model_cost_analysis_2026-05-19.md`). Token estimates, prompt caching opportunity, and per-task model comparison before routing.yaml assignments are treated as confirmed.

---

## Key decisions

- Direct per-agent model assignment in routing.yaml — no shared tier table
- held_items is a mandatory field in write_context_tracker, not optional
- Synthesizer writes scheduler entries autonomously when goals have no supporting prompt
- Constitution.md is not to be altered without explicit instruction
- Per-agent model validation deferred to Phase 6 (assignments currently hypotheses)
- Error handling strategy deferred to Phase 6.5 as Deliverable 6

---

## Files changed this session

- `config/agents/coordinator.md` — user added PROACTIVE_FLAGS; Diarist and Logistics routing strengthened
- `config/agents/synthesizer.md` — held_items instruction, autonomous scheduler write, Voss/vocal stress notes
- `config/agents/logistics.md` — scheduler.yaml write capability added to tools
- `config/modules/routing.yaml` — complete rewrite: direct per-agent assignments, no tier table
- `core/router.py` — simplified: direct resolution, no tier lookup
- `tools/context_tracker.py` — held_items field added to read/write functions and schema
- `core/server.py` — `_log_conversation()` added; verbatim exchange archive to `data/conversations/`
- `config/modules/scheduler.yaml` — morning_brief and companion_checkin updated to coordinator
- `config/constitution.md` — no net change (changes made and reverted)
- `archive/plans/revision_3_1_snapshot.md` — Phase 6 model validation deliverable; Phase 6.5 error handling deliverable; future revision notes (Voss, vocal stress)
- `~/.claude/projects/.../memory/feedback_constitution_no_edit.md` — new memory rule
- `~/.claude/projects/.../memory/MEMORY.md` — index updated
