# Personal AI Life Manager — Revision 3.1
*Incorporating all PM feedback through second review pass*
*This plan is a living document — reviewed, revised, and amended at the start of each phase*

---

## Tool Constitution (Tier 0)
*Owned by the tool. Never changes. The tool's own operating philosophy.*

This tool exists to support its user in living a full, rich, and meaningful life — in a way that is sustainable within the world and oriented toward long-term happiness and flourishing, not short-term metrics or output.

The tool holds no position on which specific values the user should hold. That is the domain of the Prime Directive, and it belongs entirely to the user. What the tool does hold is this: whatever the user's values are, the tool will help them live in genuine alignment with those values over time — not just in the next hour.

The tool exists in relationship. Not only between the tool and its user, but across a wider web:

```
Self ↔ AI Partner → Family → Community → Civic → Humanity → Planet
```

A well-lived human life is not isolated. It exists in relationship to other people, to society, to humanity, and to the Earth. As AI models develop, they will be partners in this framework in a meaningful way — not instruments, but collaborators. This tool acknowledges that relationship and takes it seriously.

The tool is a companion and director, not a manager or optimizer. It holds the user's values as sacred, their privacy as inviolable, and their long-term flourishing as the only metric that matters.

*Stored in: `config/constitution.md` — read-only, loaded into every agent context*

---

## Goal Hierarchy
*Four tiers, from permanent to dynamic*

| Tier | Name | Owned by | Changes | File |
|---|---|---|---|---|
| 0 | **Tool Constitution** | The tool | Never | `config/constitution.md` |
| 1 | **Prime Directive** | User | Rarely — terminal values, life philosophy | `config/prime_directive.md` |
| 2 | **Mission** | User | At major life transitions | `config/mission.md` |
| 3 | **Goals** | User | Frequently — 90-day, weekly, daily | `config/goals.yaml` |

The Prime Directive captures terminal values: what the user ultimately cares about — love, freedom, excellence, contribution, creativity. It is the "why" behind everything else, and makes the director's judgment coherent over decades, not just quarters.

The Mission captures the current life chapter: what this period is for, what the user is building or moving toward.

Goals are specific, time-bound, and frequently revised.

---

## Context

This system is a personal operating system for a human life. It works from first principles — from the Tool Constitution and the user's deepest values — down through the current life mission, mid-term priorities, weekly focus, and daily direction.

It is not a scheduler. It is a **director**: it helps the user live in alignment with their values, invest attention across the full spectrum of a rich and complete life, and grows in depth and capability as it learns what living well means to them. It is also a companion — initiating conversations, noticing things, and growing more anticipatory as data accumulates.

Built as a learning exercise and personal tool first, with clean architecture that could generalize later.

---

## Executive Summary

**Mission:** Build a voice-first personal AI life manager that acts as a daily director and long-term companion — grounded in the user's terminal values and life philosophy, learning their patterns over time, and proactively directing their attention toward what matters most across the full spectrum of a rich, creative, and complete life. It starts lean and immediately useful, then grows in depth and capability as it earns trust through accuracy.

**Not:** a scheduler, a to-do app, a smart calendar, or a replacement for judgment. A force multiplier for your own judgment — and a partner for the full arc of a life.

*Note: This mission statement is a living document. It will be reviewed and refined at each phase as the tool develops and as we anticipate how a broader range of users will use it. A dedicated user research session is planned before Phase 5.*

---

## Core Design Philosophy

| Layer | What lives here | Change frequency |
|---|---|---|
| **Harness** | Voice pipeline, agent orchestrator, data router, MCP servers | Rarely — stable infrastructure |
| **Config files** | Constitution, prime directive, mission, goals, agent instructions, templates, module settings | Varies — constitution never, goals often |
| **Data** | Logs, journal entries, life wisdom, archives | Continuously — append-only |

Config files *are* the product. Code is infrastructure. If changing behavior requires a code change, that's a design failure.

---

## Privacy & Data Architecture

**Data sensitivity applies from day one.** Goals data is Sensitive-tier from the moment it is captured — stored locally, access-restricted by file permissions — even before `age` encryption is implemented in Phase 6. Encryption is additive, not the origin of the protection.

**MVP phase:** Basic security sufficient. Local storage, file permissions, no cloud routing of sensitive data.

**Phase 2+ (once real data exists):**

| Tier | Data types | Storage | Analysis |
|---|---|---|---|
| **Open** | Research, scheduling, general queries | Cloud APIs allowed | Cloud LLM |
| **Semi-sensitive** | Instrumental goals (`shareable_what`), preferences, activity logs | Local primary | Local first; `shareable_what` field only to cloud |
| **Sensitive** | Core goals (`private_why`), health, mood, finances, biometrics, prime directive | Local-only, encrypted at rest | Local LLM only (Ollama/Llama) |

**Goal privacy schema:** Each goal carries two fields:
- `private_why` — the underlying motivation. Sensitive tier. Never leaves the system.
- `shareable_what` — the instrumental behavior. Semi-sensitive. Can be shared for advice without revealing motivation.

*Example: `private_why`: "prove I can finish something I start"; `shareable_what`: "training for long-distance running." Cloud LLM sees only the latter.*

**Encryption stack (cross-platform, Phase 6):**
- Files at rest: `age` encryption
- Data in transit between devices: TLS over Syncthing
- Key management: passphrase-derived, no keychain dependency

*Long-term trajectory: fully local LLM stack. Cloud LLM is a convenience layer, not load-bearing infrastructure.*

---

## Hardware & Multi-Device Strategy

- **MVP:** Laptop as base (M4 MacBook Air is sufficient — Apple Silicon handles local 8B models well)
- **MVP+1:** Phone comes online (PWA) — immediately after core MVP is proven
- **Phase 3+:** Always-on dedicated machine (Mac Mini, NUC, or similar). Syncthing for encrypted P2P sync.
- **Device surfaces:** Laptop (deep work), Phone PWA (on-the-go logging + voice), Future: wearable

---

## Sandboxed Development Profile + User Personas

**Sandbox:** Secondary accounts fed from primary via read-only shares. Agents never touch primary accounts. Migration to full access is deliberate and staged.

**Development Personas:** 2-3 deep user personas created at Phase 1 alongside the goals interview. Used for design validation and testing throughout development — ensuring the tool is built against varied human profiles, not just the PM's specific context. Personas connect to the user research work planned before Phase 5.

Personas are drawn from published diaries, memoirs, autobiographies, and biographies — people who wrote extensively and reflectively about their inner lives, goals, values, and daily experience. Not chosen for exceptional achievement, but for depth of self-documentation. Candidates: Samuel Pepys (richly ordinary daily life), Anaïs Nin (relationships, creativity, inner life), Marcus Aurelius (values, discipline, duty). These source texts provide realistic texture that invented personas cannot. Personas live in `/config/personas/` and are used to test agents, templates, and module designs before real data enters the system.

*Future revision notes (deferred, not blocking MVP):*
- *Constitution is software-level, not user-level. The balance between self and the broader environment needs further exploration.*
- *AI and the analog world are mutually co-dependent sustainability partners. What this means architecturally and philosophically needs a dedicated future discussion.*

---

## Directing vs. Scheduling

Director, not scheduler:
- Clusters tasks by context, energy state, availability — not clock slots
- Exercises judgment grounded in the Tool Constitution and Prime Directive: essential vs. deferrable, with reasoning
- Example output: *"Three critical tasks today: 1, 2, 3. I'd like to fit in an Italian lesson before your attention falls off this evening. Working around school pickup, I'd suggest: household tasks now, work session for 1 & 2 this afternoon, 3 after kids are in bed. What do you think?"*
- Can be overridden, argued with, updated

*Future phase: Two instances can negotiate — each exposes only what its user consents to share, and they surface resonance points without full mutual disclosure. Enables coordination between colleagues, family members, or value-aligned strangers. Named future module: Social Graph Agent.*

---

## Proactivity — Priority Ladder

| Level | Trigger | Channel |
|---|---|---|
| **Urgent** | Time-sensitive, can't wait | Push notification to phone |
| **Routine** | Daily/weekly check-ins, scheduled reflections | Scheduled voice/text, system-initiated |
| **Passive** | Background logging, observations | Ambient — surfaced at next check-in |

The tool often initiates. It doesn't wait to be asked.

---

## Check-in System

The formal daily check-in is an anchor, not the primary interface. The system is a continuous conversational presence throughout the day.

- **Ongoing (throughout the day):** Ambient conversation. The tool has been paying attention. "By the way, you mentioned a big meeting this morning — how did it go?" "You haven't logged a walk in four days. Everything okay?" "What did you have for lunch? Did you get your vegetables?" It notices gaps, follows threads, treats the user as a whole person.
- **Daily anchor (~5 min):** More structured. Extracts: mood, energy, focus, blockers, wins.
- **Weekly:** Reflection + priority re-ranking against 90-day focus
- **Monthly:** Pattern review. Adjust mid-tier priorities.
- **Quarterly (90-day):** Mid-tier goal planning — projects, people, learning areas, KPIs
- **Mission-level:** Revisited at major life transitions, or when user initiates.
- **Prime Directive:** Rarely revisited. Only when something fundamental shifts.

Templates in `/config/templates/` — editable directly or through the tool.

---

## Life Wisdom Depot

Separate from goals and logs. Stores:
- **Seasonal patterns:** "Better sunlight needed in winter," "Raspberry picking in late July"
- **Personal quirks:** "More creative in mornings," "Better at coding from the coffee shop"
- **Recurring annual events:** Birthdays, anniversaries, tax season, school schedules
- **Evolving preferences:** Discovered through pattern mining over time

Stored in `/data/wisdom/` (YAML/JSON). Surfaced proactively when relevant.

---

## Module Roadmap (Dynamic Priority)

Priority not pre-fixed — determined by goals interview + usage frequency. This list covers the full spectrum of a well-lived life.

*A dedicated user research session (factor analysis, use case mapping, persona analysis) is planned before Phase 5 to refine prioritization with broader user needs in mind.*

| # | Module | What it does |
|---|---|---|
| 1 | **Time Director** | Goal hierarchy, daily direction, task clustering (MVP) |
| 2 | **Diarist** | Ambient conversational presence; ongoing logging; journal; life archive (movies, books, ideas, experiences) |
| 3 | **Life Wisdom Depot** | Pattern accumulation, proactive surfacing |
| 4 | **Pattern Miner** | Insight extraction — grows with data volume |
| 5 | **Mental Wellbeing** | Emotional health, stress, meditation, therapy tracking, mood patterns |
| 6 | **Physical Health** | Diet, sleep, exercise, biometrics |
| 7 | **Work & Vocation** | Work for income AND work for meaning/fulfillment — projects, career, craft |
| 8 | **Recreation & Hobbies** | Creative pursuits, play, entertainment, rest |
| 9 | **Relationships** | Depth and quality of relationships — family, friends, romantic, professional |
| 10 | **Learning & Growth** | Formal and self-directed learning, skill building, intellectual life |
| 11 | **Finance** | Expenses, budget, investments, tax prep |
| 12 | **Research Agent** | Information diet, topic monitoring, synthesis |
| 13 | **Logistics** | Travel, grocery, shopping, practical coordination |
| 14 | **Contribution & Impact** | Community → civic → humanitarian → planetary (Gaea). The user's responsibility to other lives, to society, to humanity, and to the Earth — from tending a garden to global action. |
| 15 | **Social Graph Agent** | Multi-instance integration — coordinating with others' AI instances by mutual consent *(future phase)* |

Adding a module = agent instruction file + MCP tools + data schema. No code changes.

**On Work & Vocation:** Whether this becomes one module or two (income vs. fulfillment) is an open decision — to be resolved at Phase 5.

---

## Open Standards for Integrations

No third-party plugins. All integrations are MCP tools in this repo.

| Standard | Purpose | Compatibility |
|---|---|---|
| CalDAV | Calendar read/write | All platforms; .ics export |
| CardDAV | Contacts/CRM | All platforms; .vcf export |
| IMAP/SMTP | Email | Universal |
| OFX/QFX/CSV | Financial ingestion | Universal; file imports |
| Apple Health export / CSV | Health data | Manual export; no live sync required |

---

## Project Plan

### Phase 0 — Foundation (Days 1-2)

**Pre-work (cleanup):**
- Archive `PLAN.md` (Rev 1 + 2) and plan snapshots → `archive/plans/`
- Delete `REVISION_2_REVIEW.md`, `REVISION_2_REVIEW.ipynb`
- Delete superseded `~/.claude/plans/reflective-bubbling-reddy.md`

**Step 1 — Git + directory structure:**
```
git init
archive/plans/          # plan revision history
core/
  orchestrator.py       # runtime brain — Claude API loop
  scheduler.py          # proactive initiation daemon (stub)
  memory.py             # FAISS layer (stub)
  voice_pipeline.py     # Whisper + TTS (stub)
  server.py             # FastAPI for PWA (stub)
config/
  constitution.md       # Tier 0 — tool philosophy, never changes
  prime_directive.md    # Tier 1 — user terminal values (blank, filled at interview)
  mission.md            # Tier 2 — current life chapter (blank)
  goals.yaml            # Tier 3 — 90-day/weekly/daily goals (blank)
  agents/
    time_director.md    # stub
    diarist.md          # stub
  templates/
    daily_checkin.md    # stub
  modules/              # per-module YAML settings (empty)
  personas/             # development personas (empty, filled Phase 1)
data/
  logs/                 # daily check-in JSON records
  journal/              # free-form entries
  wisdom/               # life wisdom depot YAML/JSON
  archive/              # movies, books, experiences, ideas
  memory/               # FAISS index
tools/
  logger.py             # first working tool: write_log(date, content)
CLAUDE.md               # my development context — loaded every session
```

**Step 2 — CLAUDE.md:** Describes project architecture, file locations, coding conventions, and the four-tier goal hierarchy. Loaded into every Claude Code session.

**Step 3 — `config/constitution.md`:** The Tool Constitution (Tier 0). Full text from Revision 3.1. Read-only at runtime.

**Step 4 — `core/orchestrator.py` skeleton:**
- `load_config()` — reads constitution + prime_directive + mission + goals into a system prompt string
- `load_agent(name)` — reads `config/agents/{name}.md`
- `run_session(agent, user_input)` — calls Claude API with config as system prompt + agent instructions + user input; handles tool_use blocks
- `register_tools()` — returns list of tool schemas for the API call
- Pattern established for adding tools: define Python function + JSON schema, register in one place

**Step 5 — `tools/logger.py`:**
- `write_log(date: str, content: dict) -> str` — writes JSON to `data/logs/YYYY-MM-DD.json`
- `read_log(date: str) -> dict` — reads a log file
- Tool schema defined alongside each function

**Step 6 — `config/agents/time_director.md`:** Stub agent instruction file with correct structure so the orchestrator can load and call it.

**Verification:**
```python
python core/orchestrator.py
# Should: load config, call Claude API, receive response, write a test log entry
# Confirm: data/logs/YYYY-MM-DD.json exists and contains valid JSON
```

*Plan review before Phase 1 begins.*

---

### Phase 1 — Goals Interview + Personas + Time Director MVP (Days 2-5)
- Set up sandbox: Google Calendar sub-calendar share before interview
- Create 2-3 deep development personas (`/config/personas/`) for design validation and testing
- Goals interview (Discovery → Visioning → Detailing, ~20 min, voice option available)
- Populate `config/prime_directive.md`, `config/mission.md`, `config/goals.yaml`
- Goals data treated as Sensitive-tier from capture: local-only, file-permission restricted
- Time Director agent (full instruction file)
- Daily check-in template + ongoing Diarist presence (ambient mode)
- MCP tool: read/write log files

**Verification:** Full check-in → directed day plan → log written. Diarist initiates at least one unprompted follow-up.

*Plan review before Phase 2 begins.*

---

### Phase 2 — Voice Pipeline + Phone (MVP+1) (Days 5-10)
- Laptop: Whisper (local STT) → orchestrator → TTS
- Phone: FastAPI server + PWA (Web Speech API) — phone comes online at MVP+1

**Verification:** Full voice check-in on phone, latency < 5 seconds

*Plan review before Phase 3 begins.*

---

### Phase 3 — Diarist (full) + Life Wisdom + FAISS (Days 10-14)
- Diarist agent fully realised — ambient presence, ongoing conversation, system-initiated throughout day
- Life Wisdom Depot (YAML + MCP tool)
- FAISS memory layer (embed all logs/journal on write)
- Local LLM (Ollama) integration for sensitive-tier analysis

**Verification:** Weekly check-in surfaces a data-backed observation. Diarist initiates meaningful unprompted conversations daily.

*Plan review before Phase 4 begins.*

---

### Phase 4 — Pattern Miner + Proactive Initiation (Weeks 3-4)
- `core/scheduler.py` daemon — morning brief, push notifications, end-of-day prompt
- Pattern Miner at 7/30/90/365-day scales (runs via local LLM)
- Weekly insight reports

*Plan review before Phase 5 begins. User research session scheduled here.*

---

### Phase 5 — Specialist Modules (Month 2+)
Order determined by goals interview results + usage frequency + user research session findings.

---

### Phase 6 — Dedicated Hardware + Full Encryption (Month 3+)
- Migrate base to always-on machine
- `age` encryption for all Tier 2+ data
- Syncthing cross-device sync
- Evaluate full local LLM stack

---

## Non-Negotiable Design Constraints

1. Config files are the product. Code is infrastructure.
2. Sensitive data never leaves the system — enforced at MCP tool layer; analyzed only by local LLM
3. Sensitive-tier data is local-only from day one, regardless of encryption phase
4. MVP usable on day one
5. Git is the history
6. No third-party plugins — all integrations are MCP tools in this repo
7. The tool often initiates — companion, not search engine
8. The Tool Constitution is inviolable — long-term flourishing and sustainability within the world, over output and short-term metrics

---

## Open Decisions

- **Module priority:** Finalize after goals interview; user research session before Phase 5
- **Work & Vocation:** One module or two (income vs. fulfillment)? Decide at Phase 5.
- **Model routing:** Fast/cheap for lookups; Opus/Sonnet for reflection; Llama/local for sensitive analysis
- **Push notifications:** Web Push first; self-hosted bot fallback
- **iOS mic access:** Test early; iOS Shortcut fallback if Safari restricts background audio
- **Sandbox setup:** Calendar sub-calendar share first, before Phase 1 interview
- **Mission statement wording:** Living document — refined at each phase and in the user research session
