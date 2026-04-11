# Personal AI Life Manager — Planning Document
*Session date: 2026-04-02 | Status: Revision 2 pending PM review*

---

## How This Session Ran

Claude moderated. GPT-4o was consulted at four major junctures; its responses were surfaced directly in each round. Decisions were made iteratively via Q&A. The plan went through one full revision (Revision 1 → Revision 2) based on PM feedback, and Revision 2 is now pending PM review before implementation begins.

---

## GPT-4o Contributions (Key Highlights)

**Round 1 — Initial architecture review:**
- #1 risk: overcomplication — feature density kills adoption even for personal tools
- MVP recommendation: top-level organizational layer, calendar/task integration, basic pattern recognition, strong privacy assurances front and center
- Privacy breach destroys trust permanently — address architecture early even if not fully implemented

**Round 2 — Voice + multi-device + sandboxing + integrations:**
- Voice-first stack: Whisper (local STT, privacy + low latency) + wake-word via Porcupine + Coqui/Tacotron TTS
- Tiered data routing: classify at capture, enforce at the data layer (not in agent prompts)
- Sandbox is the right call; failure modes are credential mixing and access issues
- Open standards: CalDAV/CardDAV/IMAP/SMTP as integration foundation; owning all integrations increases development burden but ensures full control

**Round 3 — Multi-device architecture, cross-platform encryption, mobile voice, life wisdom:**
- Multi-device: Raspberry Pi or always-on machine + Syncthing (P2P encrypted sync); partial offline via cached context
- Cross-platform encryption: `age` for files at rest + TLS for Syncthing transit; passphrase-derived key, no keychain dependency
- Mobile voice: PWA calling Whisper endpoint on home server is fastest path; no app store, no native app maintenance burden
- Life wisdom depot: categorized YAML/JSON, separate from goals and logs

**Round 4 — Goal interview design, context management, encryption specifics:**
- Interview structure: Discovery → Visioning → Detailing; ~20 min; reflective summaries throughout prevent shallow answers
- Context management: FAISS vector embeddings from day one + rolling period summaries (weekly/monthly digests) — don't retrofit later
- Encryption: `age` + passphrase is practical cross-platform recommendation; complements FileVault but not dependent on it

---

## Q&A Summary — Decisions Made

| Question | Answer | Implication |
|---|---|---|
| Primary interface (MVP) | Voice-first; phone + laptop | Voice pipeline needed early |
| Privacy model | Tiered by sensitivity | Data classified at capture; encryption deferred until real data exists |
| Intended users | Personal MVP fast, potential product later | Clean architecture, not over-engineered for multi-user |
| Integrations | No third-party plugins; own everything; open standards | CalDAV/CardDAV/IMAP/SMTP/CSV as data layer |
| Voice hardware | Laptop for dev, phone for on-the-go, wearable future | PWA for phone moved to Phase 2 |
| Check-in style | Hybrid: free-form with editable structured elements | Templates in `/config/templates/`, evolve over time |
| Current task management | Ad hoc, nothing systematic | Blank slate; high freedom in data model |
| Dev role | Between collaborative and architect; understand deeply; modify files manually | Thin harness + config-file-driven behavior |
| Base hardware | Main laptop for MVP; dedicated machine post-POC | Security/encryption deferred until meaningful data |
| Sandbox population | Secondary accounts fed from primary via shares | Real data, zero agent access to live accounts |
| Proactivity | All of the above — context-dependent | Priority ladder: urgent → push, routine → scheduled, passive → ambient |
| Goals interview timing | Run live during Phase 1 build | mission.md and goals.yaml populated in first real session |

---

## Next Steps

1. **Phase 0:** Initialize git repo + create directory structure (Days 1-2)
2. **Phase 1:** Goals interview runs live as first session → Time Director agent built (Days 2-5)
3. **Phase 2:** Voice pipeline (Whisper on laptop) + PWA for phone (Days 5-10)
4. Module priority finalized after goals interview

---
---
---

# Revision 1
*Original plan — preserved for context. See PM comments inline.*

---

## Context *(PM comment: "doesn't strike me as 100% aligned with what we're aiming for — perhaps some additional questions about vision, use case examples might help refine this")*

The project manager wants a personal AI life manager built as a learning exercise that produces an immediately useful tool. It should work from first principles — top-level life goals and vision — down through prioritized sub-goals, daily direction, and eventually anticipatory intelligence. The system is for personal use first, with an architecture clean enough to generalize later. It is built on Claude Code + MCP as the agent runtime. The guiding design philosophy: a **thin, stable code harness** where all agent behavior, goals, prompts, and skill definitions live in **editable configuration files** — not in application code.

---

## Executive Summary

**Mission:** Build a voice-first personal AI life manager that starts as a daily time and goal organizer, deepens into a pattern-learning companion, and grows into a full-spectrum personal operating system — directing health, finances, research, social capital, and logistics — while maintaining strict data sovereignty and remaining fully legible and customizable by its owner.

**Core principle:** The system must be immediately useful on day one and earn more trust and capability over time through demonstrated accuracy and helpfulness.

---

## Spec Sheet

### Architectural Philosophy

| Layer | What lives here | Change frequency |
|---|---|---|
| **Harness** | Voice pipeline, agent orchestrator, data router, MCP server | Rarely — stable infrastructure |
| **Config files** | Goals, agent instructions, check-in templates, skills, prompts, module settings | Often — user editable, git-versioned |
| **Data** | Logs, journal entries, insights, archives | Continuously — append-only, encrypted where sensitive |

### Privacy & Data Sensitivity Tiers

| Tier | Data types | Routing |
|---|---|---|
| **Open** | Research tasks, scheduling, general queries | Cloud APIs (Claude, GPT) |
| **Semi-sensitive** | Goals, preferences, activity logs | Local first; anonymized summaries may go cloud |
| **Sensitive** | Health, mood, finances, biometrics, location | Local-only; encrypted at rest; never leaves device *(PM comment: "This can't be local only, since the tool will be used over multiple devices. Data and commands, as generated, should go through an encryption layer for communication with the main device. Since this is for personal use I won't be setting up a server immediately and I want it to work remotely in case the 'base' goes down. But all the data should be housed in one secure device, backed up frequently.")* |

Data is tagged at the point of capture with its sensitivity tier. The router enforces the boundary.

### Sandboxed Development Profile *(PM comment: "we need to figure out how to populate this. Rather than create a false profile, I'd rather just selectively load in elements in coordination with my existing email accounts, CRM, etc. We'll need to brainstorm the most effective and hassle free way to do this so that the agents don't have any write/agency access to my personal account, but perhaps a read-only to transfer things over to the sandbox accounts.")*

All accounts, email addresses, and service logins used during development are purpose-created and isolated from the user's personal life. Agents act only within this sandbox. Real personal migration happens deliberately, as a controlled step, not by default.

### Voice Interface *(PM comment on Phase 2: "Why will this take 2 weeks? It looks as if it should be a straightforward install and configuration?")*

- **MVP (laptop):** Push-to-talk or wake word → Whisper (local STT) → agent → TTS output
- **Phase 2 (phone):** Lightweight mobile web app or native app with same Whisper+TTS pipeline *(PM comment: "Is this something we'll develop ourselves, or are there plug and play solutions for this?")*
- **Future:** Wearable integration (watch, earpiece)
- Low-latency is a hard requirement — local STT/TTS preferred over cloud for primary voice path

### Agent Architecture

```
[User Voice/Text Input]
        ↓
[Orchestrator Agent] ← reads mission.md, goals.yaml, context/
        ↓
  ┌─────┼──────────────────────────────────┐
  ↓     ↓     ↓       ↓        ↓           ↓
Time  Health Finance Research Social    Logistics
Mgr   Agent  Agent   Agent   Secretary  Agent
  ↓     ↓     ↓       ↓        ↓           ↓
[Local data store] + [Tiered cloud routing where allowed]
```

Sub-agents are defined by Markdown instruction files. The orchestrator loads relevant agents based on context. New agents can be added by creating new instruction files.

### Check-in System

- **Daily (2-5 min):** Free-form voice conversation. System extracts: mood, energy, focus intent, blockers, wins. Structured fields emerge over time and are stored as editable templates.
- **Weekly:** Reflection + priority re-ranking against goals
- **Monthly:** Pattern review — what did data reveal? Goal refinement.
- **Quarterly:** Vision-level review — are top-level goals still right? *(PM comment [×4]: "Top level goals won't change at the quarterly level. This is more mid tier focus — what will be learned, which projects/people/activities will be prioritized, etc. A 90 day window provides enough flexibility to fit everything in, but also have succinct KPIs to reach. eg Learn basic Italian, spend time with John before he heads to college, get deep into Spaghetti Westerns.")*
- Check-in templates live in `/config/templates/` as Markdown files. Editable through the tool or directly.

### Module Roadmap (Priority Order) *(PM comment: "We must revisit this priority list and define further. Early on I expect to query the tool for all sorts of varied help that can be done with AI — researching purchases, finding directions, etc. Out of this should come the parameters for the various agents. Perhaps these agents should be prioritized after the goals interview, or perhaps as a function of the frequency within which they're evoked for actual use.")*

1. **Time Manager** — goal hierarchy, daily direction, scheduling *(PM comment on "scheduling": "The goal here isn't so much scheduling as directing. I don't want to schedule watering the plants; I want to be reminded to do so, and eventually for the tool to cluster household tasks around the times of the day/week I'm home, available, and good at getting things done.")* (MVP)
2. **Diarist** — activity logging, journal, archive (movies, books, experiences) *(PM comment: "More generalized prompts, not just end of day. It should be an ongoing conversation, ideally one that the tool is often initiating.")*
3. **Pattern Miner** — insight extraction from accumulated logs *(PM comment: "This should do larger passes as more data accumulates.")*
4. **Health Advisor** — diet, sleep, exercise, biometrics
5. **Finance Advisor** — expenses, budget, investments, tax prep
6. **Research Agent** — information diet, topic monitoring, synthesis
7. **Social Secretary** — correspondence, relationship maintenance, social capital
8. **Logistics Coordinator** — travel, grocery, shopping, scheduling *(PM comment on "scheduling": "I once again want to emphasize the dynamic nature intended for this tool. More planning than scheduling, with a fair dose of judgement as to what can be pushed and what is essential.")*
9. **Tutor** — learning plans, educational guidance

### Open Standards for Integrations (No Third-Party Plugins) *(PM comment: "I'm unclear about some of these tools. I'd like to understand where they're run, and what the OS/server requirements look like, as well as compatibility for exporting data should we decide to use different tools in the future.")*

- Calendar: **CalDAV** (self-hosted, e.g., Nextcloud)
- Contacts/CRM: **CardDAV**
- Email: **IMAP/SMTP**
- Finance: Direct institution APIs or OFX/QFX file ingestion
- Health: Local file ingestion (Apple Health export, CSV) — no live third-party sync

### Config File Formats

- **Markdown:** Agent instructions, goals narrative, journal templates, prompts
- **YAML:** Structured settings, module configs, sensitivity routing rules
- **JSON:** Schemas, logs, structured data records
- **Git:** All config and data files version-controlled locally

---

## Project Plan — Revision 1

### Phase 0 — Foundation (Week 1)
**Goal:** Runnable skeleton.

1. Initialize git repo
2. Create directory structure
3. Write initial `mission.md` and `goals.yaml` via interview with user
4. Set up `CLAUDE.md`
5. Verify: `claude` CLI can read and act on config files

---

### Phase 1 — Core Time Manager MVP (Weeks 1-2)
**Goal:** Daily use begins. Voice or text check-in → prioritized plan for the day.

1. Build **Orchestrator agent** instruction file
2. Build **Time Manager agent** — output: "Your best use of time today is X because Y" *(PM comment: "More like 'There are three critical tasks today: 1,2,3. I'd like to fit in an Italian lesson before it gets too late and your attention falls off, and working around your pick up time at school I think it'll be best to knock out some household stuff now, do a work session for 1 and 2 and fit in 3 after the kids go to bed. What do you think?'")*
3. Build **daily check-in template**
4. Wire **MCP tool** for reading/writing log files
5. Test: full daily check-in → priority output loop

---

### Phase 2 — Voice Pipeline (Weeks 2-3)
*(PM comment: "Why will this take 2 weeks?")*
**Goal:** Hands-free operation on laptop.

1. Install and configure **Whisper**
2. Build `core/voice_pipeline.py`
3. Build MCP tool wrapping voice pipeline
4. Test: full voice check-in → spoken priority output

---

### Phase 3 — Diarist & Pattern Foundation (Weeks 3-4)
**Goal:** System starts accumulating data.

1. Build **Diarist agent** — prompt for end-of-day reflection
2. Build **log schema**
3. Build **Pattern Miner** (simple first pass)
4. Weekly check-in template

---

### Phase 4 — Specialist Modules (Weeks 4-8)
Add Health, Finance, Research, Social Secretary sequentially.

---

### Phase 5 — Phone Interface (Month 2) *(PM comment: "This might need to be moved up. It's impractical to log things only when in front of the computer.")*
1. Lightweight web app (Flask/FastAPI)
2. Accessible from phone browser
3. Same pipeline and data store

---

### Phase 6 — Anticipatory Intelligence (Month 3+)
1. Reactive → proactive
2. Pattern miner generates recommendations ahead of check-ins
3. Automation identification

---

## Design Constraints — Revision 1

1. **Config files are the product.** *(PM confirmed: "Confirming this is preferable and reasonable. It sounds great, but want to ensure we're not overlooking something.")*
2. **Sensitive data never leaves the device.** *(PM comment: "More like 'never leaves the system' and needs a way to encrypt/decrypt for transmission to core data storage.")*
3. **MVP usability on day one.**
4. **Git is the history.**
5. **No third-party plugins.**

---

## Resolved Design Decisions — Revision 1

### Goal Elicitation Interview
Three-part structure, ~20 minutes: Discovery → Visioning → Detailing. *(PM comment: "This is a good start. As the interview progresses I might inject some structure and focus into the conversation, but I like that there will be an interview prepared as well.")*
Outputs reviewed and edited by user before saving. *(PM comment: "Good, but I'll also want to review the outputs at the end. For first use it will certainly be iterative.")*

### Context Window Management
FAISS vector embeddings + retrieval from day one. Weekly/monthly period summaries as structured digests.

### Local Encryption
`age` encryption + **macOS Keychain** for private key storage. *(PM comment: "Are there other non-Mac options. On a Mac now, but not generally within that ecosystem. Further want to build something that's flexible for users not on MacOS, but using Android, windows, linux, etc.")*

---
---
---

# Revision 2
*Incorporating all PM feedback. Pending PM review.*

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

## Project Plan — Revision 2

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

*Note: Whisper install + FastAPI server + Web Speech API = 2-3 days of focused work, not 2 weeks.*

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
- **Proactive notification channel:** Test Web Push in Phase 2 PWA; fall back to self-hosted messaging bot if unreliable.
- **iOS mic access:** iOS Safari has restrictions on background mic/audio in PWAs. Test early. If blocking, build a simple iOS Shortcut that triggers the voice pipeline via URL scheme.
- **Sandbox account setup:** Decide which services to mirror first (calendar most likely). Set up read-only share from primary → secondary before Phase 1.
