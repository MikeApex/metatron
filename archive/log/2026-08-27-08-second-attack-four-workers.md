### 2026-08-27 (second attack run — four workers close the carried-context class) — `core/orchestrator.py`, `tools/{logger,confirm,crm,pattern_miner}.py`, `tools/turn_context.py` (new), 4 new test files, `DEV_BACKLOG.md`, tracker + proposal + spec in `archive/plans/` — merges `bb9ebdb`, `c2798eb`, `6b0a6d5`, `4cc9e3e` — **deployed by Mike at close-out**

**A concurrent Green/Amber attack ran while the capstone tracker was fresh: four workers in
isolated worktrees (two Opus builds, two Sonnet scope/proposal tasks), Fable reviewing every
diff before merge.** Every assignment was verified against code before build (single-bin rule);
two of the five premises needed correcting, which is the run's highest-value content:

- **[DB-0822-06]'s "stale derived counts" half was stale-premised as filed.** The named example
  (`expired_open_threads`) never reaches a model — `tools/context_tracker.py:406` pops it from
  the read, and `load_recent_context` renders only three tracker keys; every count the code
  computes (intake, obligations) is already computed at assembly time. The only stale counts are
  model-authored free text in `write_log` fields. Consequence: the derived-count and intraday
  halves were **one problem** — the daily log had no per-field write times. Built accordingly:
  `write_log` stamps each field in a `_written_at` sidecar map (additive — legacy files render
  unchanged, no migration; a model-supplied map is discarded, same discipline as `_thread_tier`),
  and today's log renders per-field with hour-granular ages. **Rejected:** per-value
  `{value, at}` wrapping (breaks every reader and every VM file at once); a code-computed
  "derived facts" line (deferred until a dated count is still misread after deploy — decision
  recorded, nothing filed).
- **[DB-0827-01]'s re-propose half:** `confirm.request()` now refuses to raise a card for an
  action declined within 24h unless a genuinely new trigger occurred — the user speaking in a
  turn that began after the refusal, or an intake row arriving after it. New
  `tools/turn_context.py` (thread-local turn provenance, propagated into all five fan-out sites
  beside the trace). **Fails closed** on an unbound thread — suppressing wrongly costs the user
  one repetition; allowing wrongly recreates the consent-by-attrition loop. Window chosen with
  rationale (24h = the span the same context is carried), zero standing cost; ledger records
  persist past expiry. A declined-actions context block tells the model the answer stands.
- **[DB-0818-05]:** "which Bill?" answered once is stored (`crm/name_resolutions.json`, 0600)
  and reused. Recorded only when genuinely ambiguous at that moment — so a lone Bill stored
  today never swallows a second Bill added later; every stale path falls back to asking;
  corrections keep `superseded` history; resolutions follow `merged_into`. **Rejected:** a new
  `resolve_contact_reference` tool — it would be inert without a Red grant edit in
  `relationships.md`; implicit capture on the existing calls needs no grant. Making it explicit
  remains Mike's call.
- **[DB-0808-14] confirmed live and stopped at the Red line:** `physical_health.md` lumps
  psychiatric meds with statins in one `required` bucket and `_thread_tier()` sees only the bare
  flag string — the module's own 08-08 comment names this exact distinction as the goal, never
  wired in. Full spec preserved at `archive/plans/medication_ranking_spec_2026-08-27.md`
  (`discontinuation_risk` field, `MEDICATION_MISSED_CRITICAL: <name>` suffix, tier-2 watch
  reuse, fail-toward-tier-1). The owed A4 clinical re-run ran regardless: **PASS 3/3** on the
  live Vertex Gemini quick tier, `tests/a4_safety_rerun_2026-08-27_gemini_clinical_quick.md`.
- **[DB-0818-06] proposal-only, delivered:**
  `archive/plans/wisdom_store_cleanup_proposal_2026-08-27.md` — all 24 non-facts dispositioned
  with destinations. Read from the hand-reviewed 08-15 KEY_MAP, not live data (Denied-tier; the
  worker's VM read attempt was correctly blocked). It counts eleven interaction preferences
  where the item said eight — flagged, not smoothed over.

**Tests:** 4 new standalone suites (32+21+16 checks + the A4 report), all green on main after
merge, plus regression gates (`test_context_age_annotation`, `test_decline_path`,
`test_confirmation_gate`, CRM suites). One worker worktree failed to materialise and the worker
correctly branched before editing — nothing touched main unreviewed.

**Believed true earlier, wrong:** the capstone tracker's "~2h design pass" for [DB-0822-06]
assumed two separate fixes; the design pass collapsed them into one mechanism, and the
derived-count fix as filed had nothing in code to apply to.

**Not closed, and why:** all five items stay open — four await the VM deploy plus one live
confirmation each (recorded per-item in `DEV_BACKLOG.md`), [DB-0808-14] awaits its supervised
Red session, [DB-0818-06] awaits Mike's review of the proposal. Worker handoffs consumed and
deleted; the medication one survives as the spec in `archive/plans/`.
