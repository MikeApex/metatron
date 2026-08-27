### 2026-08-27 (the deep run reconciles the backlog, and the attack lands six builds in a day) — `DEV_BACKLOG.md`, `core/orchestrator.py`, `core/server.py`, `tools/{logger,context_tracker,confirm}.py`, `static/index.html`, `scripts/sync_dev_backlog.py` — `5b444be`…`196d344` + registry/backlog commits — **deployed by Mike same evening**

**The capstone planning chat ran `/backlog deep` end to end, then executed the Green/Amber
attack it identified.** Goal set by Mike: finish this rendition's core features (email, CRM,
research — plus National Rail and geolocation, promoted to first-draft by his ruling) and begin
full testing, with rebuild-adjacent work parked. The full cluster review with per-item status
is **`archive/plans/capstone_cluster_review_2026-08-27.md`** — the handoff artifact for the
next chat.

**Deep run:** all 9 `## Now` items verified real by two Sonnet workers (117k tokens); Inbox
emptied (2 closed, ZDR → `[DB-0827-08]`, Accountability Index → `[DB-0827-09]`);
`[DB-0822-01]` merged into `[DB-0820-05]`; machine log swept with pointers. The ⚠
`CLARIFICATION_NEEDED ×33` was diagnosed live off the VM: the Coordinator fills its
USER_CORRECTION template slot with a bare label — filed and fixed same day as `[DB-0827-07]`.
The 10:00 anticipation pass's first firing was observed and the mechanism works; its stale
"Teams link" blemish became `[DB-0822-06]`'s fourth instance.

**Attack (3 worktree workers — 2 Opus, 1 Sonnet, ~258k tokens):** decline path `0f8f528`
([DB-0827-01]); Diarist user-turn gate `e6bde3d` ([DB-0822-05]); empty-label filter `24dabae`
([DB-0827-07]); false-action-claim detector `e673330` ([DB-0815-11] detection half); context
age annotation `cbd5ca3` ([DB-0822-06] half); context-audit line `17142c0` ([DB-0814-02] data
half); ROUTING_MISS reclassification `5b444be` ([DB-0827-05], **closed** — scripts-only).

**Believed true, turned out wrong / notable corrections:**
- ROUTING_MISS was "confirmed dead" by the 08-13 registry pass and its own guard test blessed
  the drop — the emitter was the Synthesizer's instructions, not Python. On re-registration
  **18 discarded events flowed back in**, and three of them are prior instances of the
  `[DB-0826-01]` referent-resolution class — that item's @waiting condition is met with four
  data points.
- Three more types (`FALSE_COMPLETION_CLAIM`, `MERGE_AUTO_ACCEPTED`, `THINKING_CAP_HIT`) were
  emitted by code and registered nowhere; fixed on main after the reconciliation test's
  pre-existing failure was read instead of skipped.
- `[DB-0822-08]`'s premise aged: `synthesizer.md` shrank 52.4k → 41.9k in the audit execution
  with the Proactive Anticipation section untouched — adherence must be re-measured post-audit
  before any fix.
- Process correction from Mike, saved to memory: "spin off a prompt" meant *deliver a prompt*,
  not run the attack inside the planning chat. The chat was crowded out; the tracking doc is
  the remedy and the lesson is recorded.

**Rejected:** delegating the two `core/scheduler.py` items ([DB-0822-07], [DB-0808-11]) to
workers — Red tier is not delegated; they run supervised. Pruning the Heathrow/correction
machine clusters — kept deliberately as behavioural evidence, third sweep in a row.

**Deploy:** Mike ran `./deploy.sh` the same evening (core/, tools/, static/ — also discharging
`[DB-0803-05]`'s long-owed deploy). Six 🔶 items now await only their live confirmations.
