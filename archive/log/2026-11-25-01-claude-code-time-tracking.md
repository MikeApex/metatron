### 2026-11-25 (Claude Code time tracking — a global tool that measures Mike's human time in front of Claude Code; planned, Opus-checked, built by an Opus subagent) — **no repo code changed; nothing committed but the plan; the tool lives under `~/.claude/`**

**Incoming handoff:** none — Mike asked whether the April–now message timestamps could be compiled, then to track time in Claude Code per project.

**What it does now.** A text-free ledger of every chat's events (`~/.claude/time_ledger/`) updates silently at every session start and at every `/archive`; `python3 ~/.claude/tools/cc_time_engine.py week | day YYYY-MM-DD | report --from --to` reports work sessions, **attended hours** (reading + writing + watching a run picked up promptly, all chats unioned, never summed), unattended agent hours and coverage. `archive_chats.py` now stamps each `**You:**` line in new readable transcripts with its London time. A section in the global `~/.claude/CLAUDE.md` tells every chat how to answer "how much time have I spent".

**First figures (a model, not a measurement):** 24 Oct–25 Nov **38.7 h** attended (35.3–43.9), 71 work sessions over 21 days; April–23 Oct **170.1 h** (155.8–213.9; 155.8–185.3 without the 1-hour pickup setting), 273 sessions over 91 days; 1–22 Oct is a real break (no commits, no logs). Busiest day 23 Nov, 6.97 h.

**A correction.** I first told Mike exact timestamps went back only to 10-24. **Wrong:** the live log folder keeps ~30 days (default), but `/archive` has copied verbatim logs to `archive/transcripts/raw/` since 04-03 — 459 files, every event timestamped. Only never-archived sessions older than 30 days are lost; 26 archived chats are partial (the tail after their last `/archive`).

**Decisions (Mike).** Per-chat metrics are not wanted — report work sessions (attended blocks with gaps ≤ 30 min), per-project hours secondary. Do not raise the 30-day retention (≈10× disk, full text kept longer); the ledger is the durable record. Time zone Europe/London via `zoneinfo`. Build in Opus throughout.

**Opus adversarial check — ten defects, all accepted** (plan § 7): a wake-up with no human behind it made a whole run look watched; pickup was tested on raw latency that already contains reading and writing; one short message in another chat credited a 3-hour unattended run; uuid-less rows and `.!NNNNN!` partial copies would corrupt the ledger; DST; hook concurrency; gap-fill bias; the archive lacks subagent logs. I verified two claims on disk (other three project folders hold no logs; 141 subagent logs exist).

**Where the Opus build departed from the plan:** reading after a late pickup sits just before the reply, not at the agent's last event (an overnight wake-up had credited reading at 3 am; −2 h and −2.6 h); typed slash commands count as presence; silences > 5 min are not agent time (a chat closed mid-turn resumed 59 h later as a "60 h run"), so unattended hours are a lower bound; `P` = 5 min from the histogram's shoulder (no clean valley; the only dip is ~1 h); April–October is probably slightly low (permission approvals logged only from 10-23; no subagent logs). Ledger grows ~5 MB/month, not 20 MB/yr.

**Verified.** 27 tests pass (re-run by me with `unittest`; no `pytest` installed). First full `archive_chats.py` run after the edit: worked, timestamps present, ledger updated, no hook errors. Not independently checked: the classifier hand-check counts and the report figures.

**Options rejected.** Raising `cleanupPeriodDays`; per-chat attribution; app-focus history (macOS knowledgeC) as ground truth — kept as an option only if the manual benchmark days disagree; filing a backlog item (the tool is outside Metatron's single bin).

**Owed — Mike (M).** Benchmark: on a coming day, note start/stop times, compare with `cc_time_engine.py day <date>`; the engine's five parameters are tuned from that. Quick check now: `day 2026-11-23` should show a gap near 12:28–12:58.

Plan: `archive/plans/cc_time_tracking_plan_2026-11-25.md`. Tool: `~/.claude/tools/cc_time_events.py`, `cc_time_engine.py`, tests in `~/.claude/tools/tests/`; backups of the edited `settings.json` and `archive_chats.py` in `~/.claude/time_ledger/backups/`.

