### 2026-08-28 (the decisions session — all eight ruled, one closed outright, six became builds) — `ROADMAP.md` § Section 0, `DEV_BACKLOG.md`, `archive/security/zdr_terms_evidence_2026-08-20.md`, capstone tracker — **not deployed (dev-context only)**

**The capstone plan's session ① ran with Mike: the full decisions batch, 8/8 ruled.** Each
disposition is recorded in its `DEV_BACKLOG.md` entry (the authority); this fragment carries
the reasoning and what was rejected.

- **ZDR `[DB-0827-08]` — closed.** The item's @waiting had already resolved early (opt-out
  refused 08-26), making the 08-21 draft amendment stale on arrival — it assumed the exception
  was obtainable. Rewritten as **Amendment 2026-08-28** in § Section 0: testing continues on
  the `mike` persona with Mike's own use as the control; **`tone_profiler` may use anything
  Mike shares with the tool** — Mike went broader than the proposed Google-held-channels-only
  condition, deliberately: the gate is his decision to share, not the channel.
- **`write_persona` `[DB-0815-11]` — approval-gated, as a toggle.** Mike's framing: the gate
  is for "the time being," removable once the inference engine earns trust — so a switch, not
  a hard rule. Plus a pre-write redundancy check (is there an existing setting/rule that is the
  better home?). Design note filed: persona preferences may become binaries/tags at multi-user.
- **Ritual `[DB-0809-02]` — decided.** Focus-rule reading confirmed (nothing-new → short; the
  rejected ≤2-sentence cap stays rejected). Asked-state memory + ritual ownership approved.
  New design frame recorded: **Metatron informs what to do NOW** — open items surfaced
  opportunistically against circumstance (home + free window), never nagged.
- **Knowledge seeding `[DB-0818-07]` — yes, if cheap;** bundled into the A4 run Step-6 owes.
  Explicitly not capstone-necessary.
- **Pro routing `[DB-0820-05]` — coordinator-only, evidence before flip.** Offline probe
  (no Synthesizer needed — `_run_single_agent` takes `model_override`, so no Red routing edit
  either): 15 turns both models on the **cached** path (Mike's question settled cached-both as
  the representative test) + replay of the four recovered `ROUTING_MISS` referent failures.
  Step-6 specialist caching approved. (M): BigQuery billing export — explained from
  definitions; meters forward only.
- **Grants `[DB-0810-03]` — all decided; the 39 had drifted to 24 live pairs** (the guard
  re-run superseded the 08-10 count). Six clusters: archive reads now, writes only with a
  dedup fix in-session; **journals: no grants — route through the Diarist** (Mike: multiple
  entries clog clarity); goals reads granted (+ finance `read_archive`); agent_config and
  search_memory grants complete their specialist sets (audited: only rel/rec and PM/rec were
  missing); `coordinator`→`write_quality_event` granted **with a dedup condition** (event in
  context package + `tools/logger.py` same-trace/same-type no-op backstop);
  **`learning_growth`→`write_config` NOT granted** — spec line redirects to
  `write_agent_config` (global config is confirm-gated on every call; a skill-streak tick
  would prompt every time). Logistics archive refusals dropped (spec no longer names them).
  Enforce mode stays off; the flip is its own later decision.
- **Accountability Index `[DB-0827-09]` — designed.** Code joins for structured outcomes;
  nightly Flash-Lite judgment gate for free text (indeterminate stays indeterminate);
  `stated_for`+2d / 7d default / trailing-30d report; surfaces **both** internally (A9
  content-free count) and in the weekly retrospective. **Audit filed as `[DB-0828-01]`**
  (Mike's instruction), due deploy+10 — date set at the build's close, not now.
- **Location `[DB-0815-12]` — extra-sensitive tier, above ordinary sensitive.** Raw
  coordinates never enter any model prompt; code-derived zones only; transitions stored, not
  the trail. Reasoning accepted: the 08-26 ruling's control is per-item judgment, which an
  ambient stream removes. App (Capacitor) ships modes 1+2 only — on-message ping **default
  OFF** (opt-in, confirmed by test) + manual button; background scheduled/stochastic modes
  are later improvements.

**Wrong earlier, corrected:** the item count ("39 decisions") and the logistics
`read_archive`/`write_archive` refusals were stale — the agent-file audits had changed the
spec underneath them. Verified against a fresh guard run before ruling (single-bin rule).

**Session-order change (Mike):** the grants are quick — batched into session ② (scheduler Red
pair) rather than their own run, together with Step-6 + the A4 run. A Green/Amber spinoff
chat takes the probe, write_persona gate, ritual code halves, index build and location draft.

No commits before the close-out's own; no deploy owed (ROADMAP/backlog/archive edits only).
Earlier same session: confirmed the 08-27 attack chat closed clean (`4b6779e`), answered a
peer session's status ping.
