# Phase 4 Plan + Baseline Strategy Poll
*2026-05-19*

## What happened

Full Phase 4 planning session. Plan drafted, discussed, revised, and archived to `archive/plans/phase4_snapshot.md`.

## Key decisions made

**Sensitive routing:** Toggle architecture now — `config/modules/routing.yaml` with `local_enabled: false`. Routing logic live in Phase 4; Ollama switchover is one config line when ready. Fallback calls logged to `data/logs/routing_fallbacks.json` for auditability.

**Pattern Miner:**
- Five scales: 7-day, 30-day, 90-day, 365-day, all-time. All-time runs its own queries (not aggregated from shorter scales) and feeds into all formal check-in meetings.
- Insights validate *and* challenge stated beliefs — gap between user self-perception and data reality is high-value signal.
- Insights feed back into companion layer (Diarist, Time Director), not just filed as reports.
- Wisdom merge = archive, never delete. Source entries move to `archive/wisdom/` with `merged_into` pointer. Same principle for all data layers.
- `pm_future.md` created during Phase 4 build, not called until post-Phase 6 roadmap complete.

**Baseline strategy — three-class taxonomy:**
1. Trailing window — Phase 4 default, works from week one
2. State-anchored (FAISS semantic similarity of prior periods) — Phase 5, needs ~6 months of history
3. Calendar-anchored + event-conditioned — Phase 5/6, needs 2+ years and event logging infrastructure

**Scheduler:**
- 90-minute companion check-in as default ("What's going on?") — real-time companion, not just daily anchor
- Morning brief (07:30, Time Director), EOD Diarist prompt (20:00), weekly Pattern Miner (Sunday 09:00)
- Research on engagement/habitual use best practices is a Phase 4 sub-task before finalizing check-in design

**Synthetic data test:**
- 8 weeks (2 monthly cycles + weeklies) — hard deliverable, Phase 4 exit criterion
- Generated without planted correlations — randomness is principled; Pattern Miner finding structure in random data is the point
- Testing framework note added: generator is not the oracle, Pattern Miner is
- Full-year extension deferred to Phase 5 once more modules are live

**Android app:** Deferred to Phase 6, alongside dedicated hardware migration. Google Play Console internal testing track for alpha distribution.

**Backup:** Restic to multiple external drives (rsync mirrors), 3-2-1 rule, deferred to post-Phase 4 completion.

**Communications/external triggers:** Future design note — external events (calendar invites, emails) should be written to logs as timestamped entries with `source` field when CalDAV/IMAP land in Phase 5. Behavioral probe concept flagged for Social Graph Agent (module #15).

## Model poll — baseline strategy

Question: best baseline structures for pattern mining at each time scale, no limits on suggestions, address sparse-to-rich transition.

**GPT-4o:** Trailing windows as early default. Behavior-pattern clustering (find prior periods that resemble the current via clustering, use those as reference — adaptive not fixed). Seasonal comparison (same month prior years) for monthly analysis. ML model to learn optimal baseline per user/pattern type over time.

**Sonnet 4.6:** State-anchored baselines (FAISS semantic retrieval) are the most meaningful long-term class — not time-anchored but state-anchored. Composite/learned-optimal baseline is the end state, discovered not designed. Confidence annotation mandatory in every output.

**Gemini 3.1 Pro:** Unavailable (503, high demand). Re-run when stable — its research coverage may surface baseline types missed above. Flagged for early Phase 5 revisit.

## Files created this session

- `archive/plans/phase4_snapshot.md` — full Phase 4 plan
- `archive/sessions/2026-05-19 — Phase 4 Plan, Baseline Strategy Poll.md` — this file
