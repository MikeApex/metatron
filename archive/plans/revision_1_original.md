# Personal AI Life Manager — Spec & Project Plan
*Revision 2 — incorporating PM feedback*

---

## Context

This system is a personal operating system for a human life. It works from first principles — top-level life values and vision — down through mid-term priorities, weekly focus, and daily direction. It is not a scheduler. It is a director: it surfaces the best use of your time, clusters tasks by context and energy, exercises judgment about what can be deferred and what is essential, and deepens its usefulness as it learns your patterns, preferences, and rhythm. It is also a companion — initiating conversations, noticing things, and growing more anticipatory as data accumulates.

Built as a learning exercise and personal tool first, with clean architecture that could generalize later.

---

## Executive Summary

**Mission:** Build a voice-first personal AI life manager that acts as a daily director and long-term companion — grounding every decision in your actual values and goals, learning your patterns over time, and proactively directing your attention toward the best use of each moment. It starts lean and immediately useful, then grows in depth and capability as it earns trust through accuracy.

**Not:** a scheduler, a to-do app, a smart calendar, or a replacement for judgment. A force multiplier for your own judgment.

---

## Spec Sheet

### Core Design Philosophy

| Layer | What lives here | Change frequency |
|---|---|---|
| **Harness** | Voice pipeline, agent orchestrator, data router, MCP servers | Rarely — stable infrastructure |
| **Config files** | Goals, agent instructions, check-in templates, skills, prompts, module settings | Often — user editable, git-versioned |
| **Data** | Logs, journal entries, life wisdom, archives | Continuously — append-only |

Config files *are* the product. Code is infrastructure. If changing behavior requires a code change, that's a design failure.

### Privacy & Data Architecture (Phased)

**MVP phase:** No meaningful sensitive data accumulation yet. Basic security (HTTPS, standard password hygiene) is sufficient. Don't over-engineer encryption before there's anything to encrypt.

**Phase 2+ (once real data exists):**

| Tier | Data types | Storage |
|---|---|---|
| **Open** | Research, scheduling, general queries | Cloud APIs allowed |
| **Semi-sensitive** | Goals, preferences, activity logs | Local primary; anonymized summaries may go cloud |
| **Sensitive** | Health, mood, finances, biometrics | Local-only, encrypted at rest |

**Encryption stack (cross-platform, not macOS-specific):**
- Files at rest: `age` encryption (simple, modern, works on macOS/Linux/Windows/Android)
- Data in transit between devices: TLS over Syncthing
- Key management: passphrase-derived, stored in user's memory only — no keychain dependency

### Hardware & Multi-Device Strategy

**MVP:** Main laptop is the "base." No dedicated hardware required.

**Post-proof-of-concept (Phase 3+):** Dedicate an always-on machine (Mac Mini, NUC, or similar). Syncthing handles encrypted peer-to-peer sync across devices. Partial functionality survives when base is offline (cached context + local STT on phone).

**Device surfaces:**
- Laptop: deep work sessions, development, long check-ins
- Phone (PWA): on-the-go logging, quick voice check-ins, proactive notifications
- Future: wearable integration

### Sandboxed Development Profile

Don't create fake data. Use **secondary accounts fed from primary ones:**
- Example: Primary Google Calendar has a "shared sub-calendar" → secondary Google account has read/write to that sub-calendar only
- Agents can read and write to secondary accounts freely
- Primary accounts remain untouched by agents at all times
- This provides real, realistic data without exposing full account history to an untested system
- Migration to fuller access is deliberate and staged, not automatic

### Directing vs. Scheduling

The system is a **director**, not a scheduler. Concretely:
- It clusters tasks by context, energy state, and availability (not clock slots)
- It exercises judgment: "the plants can wait until tomorrow if John texted about beers"
- It knows what is essential vs. deferrable and says so, with reasoning
- Output format example: *"Three critical tasks today: 1, 2, 3. I'd like to fit in an Italian lesson before your attention falls off this evening. Working around school pickup, I'd suggest: household tasks now, work session for 1 & 2 this afternoon, 3 after kids are in bed. What do you think?"*
- It can be overridden, argued with, and updated

### Proactivity — Priority Ladder

| Level | Trigger | Channel |
|---|---|---|
| **Urgent** | Time-sensitive, can't wait | Push notification to phone |
| **Routine** | Daily/weekly check-ins, scheduled reflections | Scheduled voice/text, system-initiated |
| **Passive** | Background logging, observations | Ambient — surfaced at next check-in |

The tool often initiates. It doesn't wait to be asked.

### Check-in System

- **Daily (~5 min):** Free-form voice conversation. System extracts: mood, energy, focus intent, blockers, wins. Structured fields emerge over time and live in editable templates.
- **Weekly:** Reflection + priority re-ranking against current 90-day focus
- **Monthly:** Pattern review — what did data reveal? Adjust mid-tier priorities.
- **Quarterly (90-day):** Mid-tier goal planning — which projects, people, and learning areas get focus this quarter? (e.g., "Learn basic Italian, spend time with John before he heads to college, go deep on Spaghetti Westerns") — enough flexibility to fit everything in, with KPIs
- **Vision-level goals:** Rarely change. Not tied to quarterly cadence. Revisited only when the user initiates.

Check-in templates live in `/config/templates/` as Markdown files. Editable directly or through the tool.

### Life Wisdom Depot

A separate data store from goals and from daily logs. Stores:
- **Seasonal patterns:** "Better sunlight needed in winter months," "Raspberry picking season in late July"
- **Personal quirks:** "More creative in mornings," "Better at coding from the coffee shop on heavy-focus days"
- **Recurring annual events:** Birthdays, anniversaries, tax season, school schedules
- **Evolving preferences:** Things discovered over time through pattern mining

Stored as categorized YAML/JSON files in `/data/wisdom/`. Surfaced proactively when relevant to current context (season, upcoming date, task type).

### Module Roadmap (Dynamic Priority)

Module priority is **not pre-fixed**. The goals interview and early usage frequency will determine the order. The framework below is a starting hypothesis — it will be revised after the first interview session.

Hypothetical initial order:
1. **Time Director** — goal hierarchy, daily direction, task clustering (MVP)
2. **Diarist** — ongoing conversation logging, journal, life archive (movies, books, experiences, ideas)
3. **Life Wisdom Depot** — pattern accumulation and proactive surfacing
4. **Pattern Miner** — insight extraction from logs; grows with data volume
5. **Health Advisor** — diet, sleep, exercise, biometrics
6. **Finance Advisor** — expenses, budget, investments, tax prep
7. **Research Agent** — information diet, topic monitoring, synthesis
8. **Social Secretary** — correspondence, relationship CRM, social capital
9. **Logistics Coordinator** — travel, grocery, shopping

Modules are added as agent instruction files + MCP tools + data schemas. No code changes required.

### Open Standards for Integrations

All integrations are MCP tools built and owned in this repo. No third-party plugins. Open standards used as the data exchange layer:

| Standard | Purpose | Where it runs | OS/compatibility |
|---|---|---|---|
| **CalDAV** | Calendar read/write | Self-hosted (Nextcloud, Radicale) or any CalDAV server | All platforms; export to .ics anytime |
| **CardDAV** | Contacts/CRM | Same as CalDAV | All platforms; export to .vcf anytime |
| **IMAP/SMTP** | Email read/send | Any email provider; read-only connection recommended for sandbox | Universal |
| **OFX/QFX/CSV** | Financial data ingestion | File imports from institutions; no live API required initially | Universal |
| **Apple Health export / CSV** | Health data ingestion | Manual export from phone apps | No live sync required initially |

Data portability: all formats above are open and exportable. You can leave any of these services and take your data. The system never becomes dependent on a specific provider.

---

## Project Plan (Claude Code Build Sequence)

### Phase 0 — Foundation (Days 1-2)
**Goal:** Runnable skeleton. Structure is right even if content is thin.

1. Initialize git repo at `/Users/md-homefolder/Desktop/multi-model-mcp`
2. Create directory structure:
   ```
   /core/              # harness code (Python)
     voice_pipeline.py
     orchestrator.py
     data_router.py
     memory.py
   /config/
     mission.md        # top-level vision (populated in goals interview)
     goals.yaml        # goal hierarchy
     /agents/          # sub-agent instruction Markdown files
     /templates/       # check-in templates
     /modules/         # per-module YAML settings
   /data/
     /logs/            # daily check-in JSON records
     /journal/         # free-form entries
     /wisdom/          # life wisdom depot YAML/JSON
     /archive/         # movies, books, experiences, ideas
     /memory/          # FAISS vector embeddings index
   /tools/             # MCP server implementations
   CLAUDE.md           # orchestrator context — always loaded
   ```
3. Write `CLAUDE.md` to load mission + goals into every agent context
4. Verify: Claude CLI reads and acts on config files

**Critical files:** `CLAUDE.md`, `config/mission.md`, `config/goals.yaml`

---

### Phase 1 — Goals Interview + Time Director MVP (Days 2-5)
**Goal:** System has your goals. Daily use begins.

**Goals Interview (first real session):**
Three-part structure, ~20 minutes, conversational:
1. *Discovery* — "What's most important to you right now?" / "What are you proud of?"
2. *Visioning* — "A year from now, what would make it feel like a success?" / "What do you daydream about achieving?"
3. *Detailing* — "Immediate next steps?" / "Obstacles you foresee?"

Outputs reviewed and edited by user before saving. Populates `mission.md` and `goals.yaml`.

**Time Director agent** (`config/agents/time_director.md`):
- Goal hierarchy: vision → 90-day focus → weekly → daily
- Task clustering by context and energy (not clock slots)
- Judgment layer: essential vs. deferrable
- Output: a proposed day plan with reasoning, open to revision

**Daily check-in template** (`config/templates/daily_checkin.md`):
- Free-form voice/text → structured extraction
- Saves to `/data/logs/YYYY-MM-DD.json`

**MCP tool:** read/write log files

**Verification:** Run a full daily check-in, receive a directed day plan, confirm log file written.

---

### Phase 2 — Voice Pipeline + Phone Interface (Days 5-10)
**Goal:** Hands-free on laptop and phone. Phone moved up because logging while away from desk is essential.

**Laptop voice:**
1. Install `whisper.cpp` or `openai-whisper` Python locally
2. `core/voice_pipeline.py`: push-to-talk → Whisper → orchestrator → TTS (`say` on macOS to start)
3. Wrap as MCP tool

**Phone voice (PWA):**
1. `core/server.py`: lightweight FastAPI server running on laptop
2. PWA at `http://[laptop-ip]:8000` — mic input → POST to Whisper endpoint → response → TTS via Web Speech API
3. Works on phone browser; no app store required
4. Offline fallback: cached last context + basic STT via Web Speech API (browser-native) when base is down

*Note: Why not 2 weeks for voice? Whisper install + a basic FastAPI server + Web Speech API in the browser is 2-3 days of focused work, not 2 weeks. 2 weeks was an overcautious original estimate.*

**Verification:** Complete a check-in entirely by voice on phone while away from desk. Latency under 5 seconds.

---

### Phase 3 — Diarist + Life Wisdom Depot (Days 10-14)
**Goal:** System starts accumulating the data that powers future intelligence.

**Diarist agent** (`config/agents/diarist.md`):
- Ongoing conversation, not just end-of-day
- System often initiates: "You mentioned earlier you wanted to note the film you watched — want to log it now?"
- Archive: movies, books, experiences, ideas, observations
- Saves to `/data/journal/` and `/data/archive/`

**Life Wisdom Depot:**
- Structured YAML files in `/data/wisdom/` (seasonal, quirks, recurring, preferences)
- MCP tool to add/query/update wisdom entries
- Surfaced proactively when relevant

**Log schema** (JSON): mood, energy, sleep, focus, tasks completed, location, context tags

**FAISS memory layer** (`core/memory.py`):
- Embed all logs and journal entries on write
- MCP tool: `search_memory(query, k=10)` — retrieves relevant past context for any query
- Prevents context window limits from degrading recall over time

**Verification:** After 7 days of use, a weekly check-in surfaces at least one data-backed observation.

---

### Phase 4 — Pattern Miner + Proactive Initiation (Weeks 3-4)
**Goal:** System starts generating insights and initiating conversations.

1. Pattern Miner reads logs at increasing time scales: 7-day, 30-day, 90-day, annual
2. Weekly insight report: top correlations surfaced to user ("You complete more deep work from the coffee shop — any idea why?")
3. Proactivity engine: scheduled morning brief, push notifications for urgent items, end-of-day prompt
4. Proactivity templates editable in `/config/templates/`

---

### Phase 5 — Specialist Modules (Month 2+)
Add modules in order determined by goals interview + usage frequency. Each follows the same pattern:
- Agent instruction file (Markdown)
- MCP tools for that domain
- Data schema
- Check-in template addition

Order TBD after Phase 1. Hypothetical: Health → Finance → Research → Social Secretary

---

### Phase 6 — Dedicated Hardware + Full Encryption (Month 3+)
1. Migrate base to always-on dedicated machine
2. Implement `age` encryption for all Tier 2+ data files
3. Syncthing for cross-device sync with TLS
4. Evaluate Vaultwarden (self-hosted Bitwarden) for credential management

---

## Non-Negotiable Design Constraints

1. **Config files are the product.** Code is infrastructure. Changing behavior = editing a file, not code.
2. **Sensitive data never leaves the system** (enforced at MCP tool layer, not in agent prompts)
3. **MVP must be usable on day one** — Phase 0 + Phase 1 completable in first sessions
4. **Git is the history** — all config evolution tracked in git
5. **No third-party plugins** — all integrations are MCP tools owned in this repo
6. **The tool often initiates** — it's a companion, not a search engine

---

## Open Decisions (Address During Build)

- **Module priority:** Finalize after goals interview reveals what matters most
- **Model selection per task:** Fast/cheap (Haiku) for quick lookups; best available (Opus/Sonnet) for reflection and pattern analysis. Route by task type in orchestrator.
- **Proactive notification channel:** Phone push notifications require either a PWA with Web Push or a messaging channel (Signal, Telegram self-hosted). Decision: test Web Push in Phase 2 PWA; fall back to a self-hosted messaging bot if unreliable.
- **iOS mic access:** iOS Safari has restrictions on background mic/audio in PWAs. Test early. If blocking, build a simple iOS shortcut that triggers the voice pipeline via URL scheme.
