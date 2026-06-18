# 2026-05-26 — Phase 5 Planning, Goals Interview, Voice Recording

## What happened

### Plan review (Phases 3-4 → Phase 5)
Full Phase 3-4 review integrated into the plan. Key findings:
- Model routing now concrete: Sonnet 4.6 = Pattern Miner primary (tested best); Gemini Pro = viable secondary after prompt fix; GPT-4o = conversational only, written off for structured analytical agents; o3 = untested, still production target (~$4-8/run)
- State-anchored baseline needs ~6 months real data — Pattern Miner Phase 5 enhancements scoped accordingly
- Goals Interview is the most blocking gap: prime_directive.md, mission.md, goals.yaml all blank for real user; Time Director and all specialists are running ungrounded

### CLAUDE.md — Phase Review Convention added
New section added above Phase Testing Convention. Requires each finding to carry an actionable implication (not just a summary). Provides a checklist of categories: model routing, data requirements, blocking prerequisites in order, stale plan elements, flagged deferrals.

### Gemini 3.1 Pro baseline poll completed
Previous attempt (Phase 4) got 503. Completed this session. Seven new baseline strategies surfaced — full detail in previous session. The most immediately actionable:
- **Absolute Semantic (Zero-Shot) Baseline** — embed canonical state anchors (burnout, flow, exhaustion, etc.) using all-MiniLM-L6-v2; measure user entry distances from Day 1, no history needed
- **Aspirational/Onboarded Baseline** — user writes "great week" / "difficult week" profiles at onboarding (or these are surfaced through the interview); embed as personal reference
- **Shuffled Null / Permutation Baseline** — compare current window to N random samples from all past data; better statistical use of sparse data than adjacent trailing window
- **Predictive/Counterfactual** — trajectory divergence (what happened vs. expected); better framed as trajectory divergence than anomaly detection; needs confidence annotation
- **Variance/Stability** — cluster tightness as the signal, not just centroid; catches mental health signals before they appear in the mean
- **Boundary/Extremity** — compare against personal best/worst (top/bottom 5%), seeded from "1 in 100" interview question
- **Contrastive Pair** — find divergent historical trajectories for same event type (quick recovery vs. prolonged); use both as simultaneous baselines

Gemini's sequencing timeline: Days 1-30 = Absolute Semantic + Aspirational; Months 1-6 = + Shuffled Null + Variance/Stability; Months 6-24 = + State-Anchored + Predictive/Counterfactual; Years 2+ = + Calendar/Seasonal + Contrastive Pair; End state = Learned-Optimal routing.

### "Good old days" reframing note added to pm_future.md
The "1 in 100" extremity anchors are not fixed — they drift as newer highs/lows emerge and as current events reframe memories of prior ones. Added as a design note to the exit interviews / retrospective layering section of pm_future.md.

### Post-MVP design review note saved to memory
Once the tool is in real use (Phase 6+), revisit: baseline strategy effectiveness, embedding model resolution, statistical approach appropriateness, coordinator routing accuracy. Full topics in memory file `project_design_review_deferred.md`.

### Holiday persona config files created
`config/personas/ryan_holiday/prime_directive.md` and `config/personas/ryan_holiday/mission.md` created from the persona profile. `goals.yaml` was pre-existing. The orchestrator's `--persona` flag doesn't yet pick up these subdirectory files — that's Deliverable 1.

### Goals Interviewer updated
Two changes to `config/agents/goals_interviewer.md`:
1. **Dynamic Flow section** added at the top of Approach — explicit permission for redirects, non-linear phase movement, command acceptance ("skip this," "go deeper on X," "come back to that"), no phase announcements, no time limit
2. **All phase time estimates removed** from headers — "(3-4 min)" etc. removed entirely; replaced framing with "this conversation has no time limit"

### Voice recording added to PWA
`static/index.html` — `MediaRecorder` runs parallel to Web Speech API STT. Starts when mic button activates, stops when recognition session ends. POSTs `.webm` blob to `/upload-audio`.

`core/server.py` — `POST /upload-audio` endpoint added. Writes to `data/audio/YYYY-MM-DD/HH-MM-SS.webm`. Personal archive feature, not a design feature.

### Communication apps strategy
Start with whatever has a clean API (Telegram, email via IMAP, SMS via Twilio). Build a data capture / bot layer for services without accessible APIs (iMessage, Signal, WhatsApp). Revisit specific services during Deliverable 6.

## Phase 5 block plan (final order)

| # | Deliverable | Estimate |
|---|---|---|
| 1 | Persona config support + voice recording (done) | ~3h — partially complete |
| 2+3 | Coordinator Agent deep conversation → agent file → specialist first-pass sweep (in unison) | ~2-3 days |
| 4 | Pattern Miner cold-start baselines (Absolute Semantic, Aspirational, Shuffled Null, Variance/Stability) | ~4-6h |
| 5 | Goals Interview — real user (dedicated session) | dedicated session |
| 6 | Integrations: CalDAV + IMAP/email + CardDAV/contacts + maps + dynamic info (weather/markets/news/transit) + messaging (API-first, bot/capture for rest) | ~12-16h |
| 7 | Diary ingestion + simulation framework (Pepys full run, Dooce, Reddit personas) | ~1.5 days |
| 8 | o3 Pattern Miner test | ~2h |

**Voice recording (index.html + server.py) already done this session.** Deliverable 1 remaining work: extend `--persona` flag to load subdirectory config files.

## Key decisions

- **Specialist sweep done in unison with Coordinator** — deep conversation about what each agent does kicks off Coordinator routing design; specialist first-pass files written alongside
- **Specialists begin with general instructions** — MVA schema (agent file + tool list + routing rule + data schema + scenario seeds + enhancement backlog); modules added continually as use reveals what's needed
- **All specialists built in first pass** — no serialized deep builds; enhancement rounds driven by usage signals and test failures
- **Contemporary diary preferred** for ingestion over Pepys historical; Dooce (Heather Armstrong, 2001-2023) as primary candidate; Reddit redditors for real-world texture; Pepys full run retained for historical baseline
- **Simulation from midpoint** — ingest up to split date, run Pattern Miner, compare predictions against what actually happened in remaining entries

## Files changed this session

- `CLAUDE.md` — Phase Review Convention added
- `config/agents/goals_interviewer.md` — Dynamic Flow section, time estimates removed
- `config/personas/ryan_holiday/prime_directive.md` — created
- `config/personas/ryan_holiday/mission.md` — created
- `static/index.html` — MediaRecorder audio capture added
- `core/server.py` — /upload-audio endpoint, datetime import, UploadFile/File imports
- `research/pm_future.md` — "Good old days" reframing note added
- Memory: `project_design_review_deferred.md` created, MEMORY.md updated
