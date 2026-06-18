# Phase 5 Opening Prompt
*Use this to open a new Claude Code session for Phase 5 work.*

---

You are Claude Code continuing development of a personal AI life manager.
Working directory: ~/Desktop/multi-model-mcp

Read these files before doing anything else:
- CLAUDE.md (architecture, conventions, terminology — read carefully)
- archive/plans/revision_3_1_snapshot.md (the overall plan)
- archive/sessions/2026-05-26 — Phase 5 Planning, Goals Interview, Voice Recording.md (this session's decisions)
- archive/sessions/2026-05-19 — Phase 4 Testing, Prompt Engineering, Web Push.md (Phase 4 completion)

Also check memory at ~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/memory/MEMORY.md
and read any memory files that seem relevant.

---

## WHAT'S BEEN BUILT (Phases 0-4 complete + Phase 5 partial)

**Core runtime:** core/orchestrator.py (23 tools, 4 providers: Anthropic/OpenAI/Gemini/Ollama, agentic loop)

**Agents:** Diarist, Time Director, Goals Interviewer, Pattern Miner (all in config/agents/)

**Memory:** FAISS (all-MiniLM-L6-v2, 384-dim), Life Wisdom Depot, context tracker

**Voice:** Whisper STT + Kokoro/edge-tts/Piper TTS

**PWA:** static/index.html served over HTTPS via Tailscale, Web Push working on Android
- Voice recording just added: MediaRecorder captures raw audio parallel to STT, POSTs .webm to /upload-audio, files land at data/audio/YYYY-MM-DD/HH-MM-SS.webm

**Scheduler:** core/scheduler.py — 90-min companion check-ins, morning brief (07:30), EOD Diarist (20:00), weekly Pattern Miner (Sunday 09:00)

**Routing:** config/modules/routing.yaml — sensitive agent toggle (local_enabled: false — flip to true when Ollama available)

**Tools:** logger, goals, config_writer, diarist, wisdom, memory, pattern_miner, baselines, context_tracker

**Test personas:** 7 development personas in config/personas/. Ryan Holiday has full Tier 1-3 config at config/personas/ryan_holiday/ (prime_directive.md, mission.md, goals.yaml). The --persona flag does NOT yet load these subdirectory files — that's Deliverable 1.

---

## PHASE 5 DELIVERABLE PLAN

### Deliverable 1 — Persona Config Support (~1-2h remaining)
*Partially done: voice recording changes made. Remaining: config path routing.*

Extend `--persona` flag in `core/orchestrator.py` → `load_config()` to load persona-specific Tier 1-3 files.

Currently loads: `config/prime_directive.md`, `config/mission.md`, `config/goals.yaml`
When `--persona ryan_holiday` is set, should load:
- `config/personas/ryan_holiday/prime_directive.md`
- `config/personas/ryan_holiday/mission.md`
- `config/personas/ryan_holiday/goals.yaml`

The persona character file (`config/personas/ryan_holiday.md`) is already loaded by the existing --persona logic; only the Tier 1-3 subdirectory loading is missing.

*Verification:* Run with `--persona ryan_holiday`. Time Director responds with Bastrop/bookstore/Stoic framing. Confirm it's loading Holiday's goals, not the blank real-user files.

---

### Deliverable 2+3 — Coordinator Agent + First-Pass Specialist Sweep (~2-3 days, in unison)

**This must start with a deep conversation about what each specialist agent is intended to do.** The Coordinator's routing rules can only be designed once each specialist's scope and boundaries are defined. The specialist instruction files are written alongside the routing rules — they're the same conversation.

**Coordinator to build:**

`tools/subagent.py`:
```python
def run_subagent(agent_name: str, message: str) -> str:
    """Spawn a sub-orchestrator session with the named agent, return result."""
```

`config/agents/coordinator.md` — routing instruction file:
- Intent recognition patterns for each specialist
- Handoff rules (when to route vs. handle directly)
- Never surface which agent was called (discretion principle)
- Default: Time Director for anything unclassified

Initial routing table (to be refined in the deep conversation):
| Intent signals | Route to |
|---|---|
| Diary / journal / reflection / "how did it go" | Diarist |
| Pattern / trend / insight / "what have you noticed" | Pattern Miner |
| Goals / priorities / direction / what to do | Time Director |
| [specialist domains] | [each specialist] |
| Anything else | Time Director |

Register `run_subagent` in `orchestrator.register_tools()`.
Update `core/server.py` default agent from `time_director` → `coordinator`.

**First-pass specialist sweep (MVA schema for each):**

Every first-pass specialist agent must have:
1. Agent instruction file (`config/agents/{name}.md`)
2. Tool list — which existing tools it uses; new tools flagged (only build if strictly required)
3. Routing rule — intent signals added to coordinator.md
4. Data schema — JSON fields it writes; new data files if any
5. Scenario seeds — 3-5 test scenarios drawn from persona files
6. Enhancement backlog — brief list of what it can't do at first pass

Specialists (order to confirm in the deep conversation, proposed order below):
1. Mental Wellbeing — emotional state is the multiplier on everything; tracks mood patterns, stress, resilience
2. Physical Health / Sleep — highest Pattern Miner signal; sleep correlations with output/mood
3. Work & Vocation — where most goal-oriented activity lives; directly serves Time Director
4. Relationships — qualitative first pass (who matters, recent contact, follow-ups); not Social Graph Agent yet
5. Learning & Growth — books, courses, skills; companion to Work & Vocation
6. Recreation & Hobbies — whole-life coverage; the tool should see the user when they're not working
7. Finance — sensitive-tier; first pass = income/expense logging, budget awareness (no financial advice)
8. Research Agent — outward-facing; cloud-routable since decontextualized; topic monitoring, synthesis
9. Logistics — practical coordination: travel, shopping, calendar-adjacent tasks

**Important design note:** Specialists begin with general instructions. Modules are added continually as use reveals what's needed (customized Diarist questions, admin directions for grocery orders, etc.). The first pass is intentionally incomplete — that's by design.

*Verification:* User says "I want to log something" from PWA → Coordinator routes to Diarist, entry written, user gets natural confirmation. "What patterns have you noticed lately?" → routes to Pattern Miner. User never selected an agent.

---

### Deliverable 4 — Pattern Miner Cold-Start Baselines (~4-6h)
*Can run in parallel with or after Deliverable 2. Does not require data accumulation.*

Build baselines that work from Day 1:

`tools/baselines.py` extensions:
- `create_semantic_anchor(label, description)` — embed canonical state description, store in data/baselines/semantic_anchors.json
- `score_against_anchors(persona, date_range)` — cosine distance from current period centroid to all anchors
- `write_aspirational_baseline(persona, good_week, hard_week, peak_days, floor_days)` — called by Goals Interviewer at session end
- `shuffled_null_score(persona, window_days, n_permutations=100)` — permutation baseline for sparse data

Initial canonical anchors: burnout, deep_focus, physical_exhaustion, creative_momentum, social_connection, emotional_depletion, groundedness, anxiety

Update `config/agents/goals_interviewer.md` to surface the "1 in 100" best/worst days question and call `write_aspirational_baseline` with results.

Note: "1 in 100" anchors are dated snapshots, not permanent coordinates — they drift as new highs/lows emerge and as current events reframe prior memories. See research/pm_future.md for full note.

---

### Deliverable 5 — Goals Interview (real user) — dedicated session
*Not a build task. A conversation. Schedule separately.*

Run `config/agents/goals_interviewer.md` against the real user.
Command: `python core/orchestrator.py --agent goals_interviewer`

Produces: `config/prime_directive.md`, `config/mission.md`, `config/goals.yaml` with real content.

The interview has no time limit. Dynamic flow enabled — the interviewer follows redirects, accepts commands, returns to template phases opportunistically. Full design in goals_interviewer.md.

---

### Deliverable 6 — Integrations (~12-16h)

Build as MCP tools in tools/:

**Already in open standards list — build these:**
- CalDAV: `read_calendar(days_ahead)`, `write_calendar_event(title, start, end, notes)`
- IMAP/SMTP email: `read_email(n=10, unread_only=True)`, `send_email(to, subject, body)`
- CardDAV contacts: `search_contacts(query)`, `get_contact(id)`

**New additions:**
- Weather: wttr.in (no API key), `get_weather(location=None)`
- Markets: Alpha Vantage free tier or Yahoo Finance (unofficial), `get_market_snapshot(symbols)`
- News: RSS feeds (user-configurable), `get_news(topics=None, n=5)`
- Transit: GTFS-RT for local agency, `get_transit_status(route=None)`
- Maps/geolocation: Nominatim (OpenStreetMap, no key), `geocode(address)`, `nearby(lat, lon, query)`

**Messaging — API-first, bot/capture layer for the rest:**
- Telegram: full bot API, easiest integration
- SMS: Twilio (requires account)
- iMessage / Signal / WhatsApp: no clean API → build data capture + bot-type system to effect desired behavior. Strategy to be confirmed with user when specific services are identified.

*Note: CalDAV integration makes Time Director grounded in actual schedule rather than described priorities. Build this first within Deliverable 6.*

---

### Deliverable 7 — Diary Ingestion + Simulation Framework (~1.5 days)

**Goal:** Real and contemporary longitudinal data for Pattern Miner testing, independent of accumulating real user data.

**Ingestion format:** Map to existing log JSON schema — `date`, `mood` (inferred), `energy` (inferred), `notes` (verbatim or lightly cleaned), plus `source` field.

**Sources (priority order):**
1. **Dooce** (Heather Armstrong, 2001-2023) — contemporary, domestic/emotional, daily/near-daily. Full archive publicly accessible. Scrape and convert.
2. **Reddit** — 3-5 redditors from r/decidingtobebetter or similar daily loggers. Real-world contemporary, variable quality, unambiguously public.
3. **Pepys full run** — 1660-1669, ~3,500 entries, public domain. Historical baseline. pepysdiary.com has dated, tagged, cross-referenced entries.

**Simulation framework:**
Each ingested diary can be split at a midpoint. System ingests up to split date, runs Pattern Miner analyses, then compares observations against what actually happened in remaining entries. Measures how well Pattern Miner hypotheses tracked reality.

*Example: Pepys split at 1665 (pre-Plague). Pattern Miner on 1660-1665 produces hypotheses. Compare against 1665-1669 — do flagged patterns manifest?*

---

### Deliverable 8 — o3 Pattern Miner Test (~2h, mostly cost/wait)

Run the same Pattern Miner test battery against o3 that was run on Sonnet 4.6 and Gemini Pro. Compare structured analysis quality, evidence citation, format compliance, cost (~$4-8/run). Commit to production Pattern Miner model before Phase 6.

---

## KEY DECISIONS NOT TO LOSE

- **Privacy:** All personal context is sensitive-tier. Cloud LLMs receive only fully decontextualized requests. routing.yaml local_enabled=false — flip to true only when Ollama is running with a capable model. One-line change.

- **Config files are the product.** Behavior changes = config edits. If changing behavior requires a code change, that's a design failure.

- **Archive-on-merge:** Wisdom entries never deleted. Moved to archive/ with merged_into pointer. Same principle for all data layers.

- **Discretion:** Users never see which agent was called, which model ran, or how data was routed. Methodology is infrastructure. Output belongs to the user.

- **pm_future.md** — deferred Pattern Miner work (384-dim ceiling, non-linear correlations, statistical modeling, gamification for Alpha, large-window retrieval, statistical pre-aggregation privacy layer, Gemini Pro cold-start baselines, "good old days" reframing). None of this is Phase 5 work — it activates post-Phase 6. Don't build it; don't overwrite it.

- **Model cost analysis** (archive/plans/model_cost_analysis_2026-05-19.md) — intentionally incomplete. Full pass after all agents built, before Phase 6. Topics: per-agent token estimates, prompt caching (not yet implemented), Time Director rightsizing, Gemini Flash pricing.

- **Restic backup** — being set up in a separate session. Not Phase 5 work.

- **GPT-4o one-shot prompt fix** — optional, worth one attempt before fully writing it off for structured analytical agents.

---

## WHERE TO START

Deliverable 1: Extend `core/orchestrator.py` → `load_config()` to load persona-specific Tier 1-3 files when `--persona` is set. Read `core/orchestrator.py` first to find the exact load_config implementation, then make the change. Verify with `--persona ryan_holiday`.

After Deliverable 1 is confirmed working: the deep conversation about each specialist agent's scope and boundaries, which produces the Coordinator routing table and kicks off the first-pass specialist sweep.
