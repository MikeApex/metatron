# Phase 4 Plan — Pattern Miner + Proactive Initiation
*Drafted 2026-05-19. Incorporates all Phase 3 outcomes, model comparison results, and design discussions from the Phase 4 planning session.*

---

## What Phase 4 delivers

Three things the system cannot do today: (1) reach out on its own, (2) extract meaning from accumulated data at scale, (3) route sensitive data to a local model. It will do all three after Phase 4 — the third via a toggle that is a no-op until Ollama is ready, designed so the switchover is a single config change.

---

## Deliverable 1 — Sensitive routing layer
**~4 hours**

`config/modules/routing.yaml` — routing table mapping agent names and tool categories to model targets. Three values: `cloud_fast` (Gemini 2.5 Flash), `cloud_deep` (Sonnet 4.6 or o3), `local` (Ollama endpoint, currently disabled).

```yaml
routing:
  local_enabled: false
  local_endpoint: "http://localhost:11434"
  local_model: "qwen3:14b"
  agents:
    diarist: local
    pattern_miner: local
    time_director: cloud_deep
  tools:
    search_memory: local
    write_log: local
    write_journal: local
    write_wisdom: local
    run_analysis: local
```

`core/router.py` — `resolve_model(agent, tool) -> ModelConfig`. Reads routing table, checks `local_enabled`, falls back to `cloud_deep` if local is off. Called by the orchestrator before every API call. When a `local`-routed call falls back to cloud, a warning is written to `data/logs/routing_fallbacks.json` — so when Ollama comes online, every call that was leaking is visible.

Orchestrator updated to call `resolve_model()` instead of hardcoded provider strings.

---

## Deliverable 2 — Pattern Miner sub-agent
**~8 hours**

The analytical engine. Runs against FAISS + raw logs at five time scales. Assigned model: o3 (decontextualized synthesis via cloud, routing table marks it `local` for future switchover once Ollama is ready).

### Time scales
- **7-day** — recent state, blockers, short-term shifts
- **30-day** — monthly rhythm, streak patterns
- **90-day** — goal trajectory, seasonal effects
- **365-day** — year arc, identity-level shifts
- **All-time** — full longitudinal history; not an aggregation of shorter scales, runs its own queries

The all-time scale feeds into all formal check-in meetings (weekly, monthly, quarterly) as a context layer.

### Design principles baked into the agent instruction file

**Insights validate and challenge, not just discover.** The Pattern Miner surfaces patterns the user hasn't noticed *and* validates or challenges ones they believe to be true. "I'm always tired on rainy days" is a hypothesis; the data may show 60% on rainy days vs 20% otherwise — still meaningful, but the magnitude matters. The gap between stated belief and measured reality is high-value signal. Where the gap is small, self-knowledge is confirmed. Where it's large, there's an opening.

**Insights are not filed — they are fed back.** The Pattern Miner output is not a report that gets archived. It surfaces in the next check-in via the Diarist ("You've mentioned you feel slow on rainy days — I've been tracking this, want to look at it?"), potentially influences the Time Director's scheduling suggestions, and over time informs the wisdom layer. The Pattern Miner produces hypotheses; the companion loop translates them into something the user experiences. This is explicit in the agent instruction file.

**Output format:** `[OBSERVATION] + [EVIDENCE] + [HYPOTHESIS] + [SUGGESTED ACTION OR QUESTION]`. Never bare assertions. An insight is only worth writing if it could not be derived from a single log entry.

**Confidence annotation is not optional.** Every finding is annotated with the baseline used and the data volume behind it. "Based on 6 weeks of data, this is a weak signal" is honest. "Based on 4 years, this pattern appears every November" is strong. The distinction is surfaced to the user.

### Baseline strategy

Baseline selection is the core analytical design decision. Three classes, deployed in sequence as history accumulates:

**Class 1 — Trailing window (Phase 4, default)**
- 7-day vs. trailing 30-day; 30-day vs. trailing 90-day; 90-day vs. trailing year
- No calendar dependency; works from week one
- Statistically thin but immediately available

**Class 2 — State-anchored / FAISS semantic similarity (~6 months of data)**
- The FAISS-native approach: retrieve semantically similar prior periods rather than adjacent calendar windows
- "How does this week compare to other weeks when I was under deadline pressure?" — the baseline is a slice of history selected by similarity on a specific dimension, not by calendar proximity
- No fixed window needed; scales naturally with corpus depth
- Design for this in Phase 4; implement in Phase 5 once sufficient history exists

**Class 3 — Calendar-anchored + event-conditioned (2+ years of data)**
- Same calendar period in prior years (seasonal patterns, annual cycles)
- N days following a specific category of life event ("periods after receiving bad news")
- External event triggers (calendar invites, communications) as labeled timestamps — requires CalDAV/IMAP integration (Phase 5)
- Requires enough repetitions to average out noise; flag in `pm_future.md`

**Baseline selection logic:** The Pattern Miner checks available history depth and selects the most sophisticated baseline class the data supports. It annotates the selection in every output. The system records which baseline produced which insight and whether the user engaged with it — baselines that consistently produce actionable insights are promoted over time. No separate ML model needed; the Diarist context tracker captures engagement naturally.

**Model poll results on baseline strategy (2026-05-19):**
- *GPT-4o:* Confirmed trailing window as early default; added behavior-pattern clustering (find prior periods that resemble the current one via clustering, use those as the reference — adaptive rather than fixed calendar). Proposed ML model to learn optimal baseline per user and pattern type over time. Seasonal comparison (same month prior years) specifically called out for monthly analysis.
- *Sonnet 4.6:* State-anchored baselines (FAISS semantic retrieval of similar periods) are the most meaningful long-term class — not time-anchored but state-anchored. Composite / learned-optimal baseline is the end state, discovered not designed. Confidence annotation as part of output format, not metadata.
- *Gemini 3.1 Pro:* Unavailable (503, high demand at time of polling). Re-run this question against Gemini when stable — its research thoroughness may surface baseline types not covered above. Flag for early Phase 5 revisit.

### Tools

`tools/pattern_miner.py`:
- `run_analysis(persona, scale, date) -> str` — multi-query FAISS search, aggregates raw log spans, returns synthesis
- `write_insight_report(persona, date, content) -> str` — writes to `data/personas/{persona}/insights/YYYY-MM-DD.json`
- `read_recent_insights(persona, n=5) -> list` — feeds into Diarist context at session open so recent patterns are surfaced in ambient conversation

`tools/wisdom.py` — extended with:
- `find_duplicate_wisdom(persona, category) -> list` — semantic similarity search within category (cosine on FAISS index); returns entries above threshold
- `merge_wisdom_entries(persona, keep_key, source_keys) -> str` — copies source entries to `data/personas/{persona}/archive/wisdom/` with `merged_into` pointer, then consolidates into the primary entry. **Source entries are never deleted.** Data storage is inexpensive; fidelity loss from deletion is not recoverable, especially for wisdom that uses internal vocabulary with greater salience to the user than to the model.

This archive-on-merge principle applies to all data layers. Journal entries are never deleted either — they move to archive with lineage pointers if restructured.

### Future work (deferred, not Phase 4)

`research/pm_future.md` is created during Phase 4 build as a placeholder. It is not called into any phase until the current roadmap (Phases 4-6) is complete. Contents:
- **384-dimension ceiling:** all-MiniLM-L6-v2 was chosen for speed. Its embeddings are optimized for semantic similarity but may not fully capture numerical/behavioral correlations as structured data (health, sleep, biometrics) comes online. Hybrid representation (text embeddings + structured feature vectors, joint analysis) is the likely evolution. Flag for dedicated discussion when Phase 5 structured data modules are live.
- **Non-linear correlations:** PCA/sparse PCA are linear. UMAP, kernel PCA, and other non-linear methods will extract structure linear analysis misses. Requires larger corpora to be meaningful. Deferred to post-Phase 6.
- **Composite learned baseline:** End-state baseline selection — the system discovers per-user, per-pattern optimal baseline structures from engagement signals. Not designed in advance.
- **Gemini baseline poll:** Re-run the baseline strategy question against Gemini 3.1 Pro when available.

---

## Deliverable 3 — Scheduler daemon
**~6 hours**

`core/scheduler.py` — runs continuously, fires orchestrator sessions on a schedule. The orchestrator remains stateless; the scheduler holds all timing state.

`config/modules/scheduler.yaml`:
```yaml
schedules:
  morning_brief:
    time: "07:30"
    agent: time_director
    days: weekdays
    notification: both         # terminal + push
  companion_checkin:
    interval_minutes: 90
    agent: diarist
    prompt: "What's going on?"
    days: daily
    notification: push
  evening_diarist:
    time: "20:00"
    agent: diarist
    days: daily
    notification: push
  weekly_pattern_miner:
    day: sunday
    time: "09:00"
    agent: pattern_miner
    notification: terminal
```

The 90-minute companion check-in is the default interval — a short invite, not a structured form. The Diarist generates a journal entry from the response and appends to the day's log. Frequency is user-configurable in `scheduler.yaml` (up or down). The check-in is the foundation of real-time companionship; research on engagement techniques and habitual use best practices is a Phase 4 sub-task before finalizing the check-in instruction design.

`core/scheduler.py`:
- `schedule` library loop; no cron dependency; runs as a background process
- `fire_session(agent, notification_channels)` — invokes orchestrator, captures output, dispatches to channels
- Terminal channel: stdout + macOS `osascript` notification banner
- Push channel: calls Web Push delivery (Deliverable 4)
- Crash-resilient: logs failures to `data/logs/scheduler_errors.json`, keeps running

Startup: `python core/scheduler.py &` or launchd plist (documented, not auto-installed).

---

## Deliverable 4 — Web Push to phone
**~5 hours**

Extends the Phase 2 FastAPI server to send push notifications to the registered PWA on the phone. Web Push works on Android Chrome without any app store involvement. On iOS, requires iOS 16.4+ and PWA added to home screen — serviceable.

- `core/push.py` — `send_push(title, body, urgency)` via `pywebpush`. VAPID keys from `.env`.
- `data/push_subscriptions.json` — stores browser push subscription objects. Local-only; not committed to git.
- `POST /subscribe` — phone PWA calls on first load to register push subscription
- `POST /push/test` — dev tool to test delivery without waiting for a schedule trigger
- PWA service worker update: `push` event handler displays notification; `notificationclick` opens app

**Android app:** Revisit in Phase 6, alongside dedicated hardware migration. By then: real usage data, clear notification UX needs, known alpha tester group. Target: Google Play Console internal testing track for alpha distribution. iOS: evaluate TestFlight vs. PWA-on-home-screen at that point.

---

## Deliverable 5 — Synthetic data + deep test
**~6 hours — hard deliverable, Phase 4 exit criterion**

Eight weeks of simulated history for Ryan Holiday (richest persona: journal, logs, wisdom, archive entries). Eight weeks provides two monthly cycles and multiple weekly cycles — enough to test all active time scales.

### Generation methodology

`tests/generate_synthetic_data.py` — entries are generated without planted correlations. The model's own construction produces organic randomness, which means the Pattern Miner will surface real statistical structure the generator did not consciously design. **This is a principled methodology, not a limitation:** the generator is not the oracle; the Pattern Miner is. A finding counts as a valid insight if the Pattern Miner surfaces it, regardless of generator intent. Conversely, the generator's randomness provides a ground truth for false positive detection — if the Pattern Miner surfaces a "pattern" in purely random data, that is a calibration signal.

**This insight is recorded in `tests/testing_framework_notes.md`** for future development and testing methodology.

Realistic variation: some days sparse, some rich; recurring weekly structure (gym M/W/F, writing sessions on weekday mornings); seasonal drift; no deliberate planted correlations.

`tests/run_phase4.py` — test runner:
- Ingest synthetic data into FAISS index
- Run Pattern Miner at all five scales (7/30/90/365/all-time)
- Capture reports
- Manual evaluation: did it surface non-obvious patterns? Did it correctly annotate confidence levels? Did it distinguish weak-data signals from strong ones?

`tests/phase4_report.md` — output, same format as Phase 3 reports.

**Extension to full year:** Deferred. Even more signal when Phase 5 structured-data modules (health, sleep) are live. Flag for Phase 5 synthetic data run.

---

## Bug fixes (woven in, no separate budget)

- `write_log` sparse records: content validation in `logger.py` — if content is empty dict or None after coercion, log a warning and skip write. Stronger instruction patch in Diarist config.
- `read_log` / `read_journal` empty-arg defaults: verify during Deliverable 5 test runs.
- Wisdom deduplication: addressed in Deliverable 2 (`find_duplicate_wisdom`, `merge_wisdom_entries`).

---

## Off-machine backup (deferred to post-Phase 4)

**Tool:** Restic to one or more external drives. Restic encrypts locally (AES-256) before writing; the drive sees only ciphertext.

```bash
brew install restic
restic -r /Volumes/Drive1/life-manager init    # passphrase stored in password manager
restic -r /Volumes/Drive1/life-manager backup ~/Desktop/multi-model-mcp
rsync -av --delete /Volumes/Drive1/life-manager/ /Volumes/Drive2/life-manager/
```

Backup everything including `.env` (if drive is lost, rotate keys; backup was encrypted). Exclude: `certs/`, `__pycache__/`, `node_modules/`.

Multiple drives: primary Restic backup to Drive 1; `rsync` mirrors the Restic repository to additional drives after each backup. Restic repo is already encrypted — rsync copy is a fully valid, independently restorable backup. One drive offsite (3-2-1 rule). Script wrapped in launchd, runs when drive mounts.

Restic passphrase must live somewhere other than the machine being backed up.

---

## Future module notes

**Communications and external triggers:** External events (calendar invites, emails, messages) are not just logistical items — they are behavioral probes. A friend's invite, bad news by email, a cancelled meeting — all become labeled timestamps against which behavioral data can be indexed. "What happens in the 48 hours after you hear from this person?" is a Pattern Miner question. This belongs in the Social Graph Agent module (roadmap #15). Design note for Phase 5: when CalDAV/IMAP integrations are built, external events should be written to the log as timestamped entries with a `source` field, not just parsed for action items.

---

## Phase 4 exit criterion

> The scheduler fires at 07:30, runs a Time Director brief, and delivers it to the terminal and to the phone via Web Push. The 90-minute companion check-in fires, generates a Diarist journal entry, and appends to the day's log. The Pattern Miner runs on Sunday, produces a report against eight weeks of Ryan Holiday synthetic data, and surfaces at least two observations that are (a) backed by specific log evidence and (b) not derivable from any single log entry. All sensitive-routed tool calls log a routing fallback warning (since local is disabled), confirming the routing logic is live and auditable.

---

## Time budget

| Deliverable | Hours |
|---|---|
| Sensitive routing layer | 4h |
| Pattern Miner sub-agent | 8h |
| Scheduler daemon | 6h |
| Web Push to phone | 5h |
| Synthetic data + deep test | 6h |
| **Total** | **~29 hours** |

At 3-4 focused hours per day: **8-10 days.**
