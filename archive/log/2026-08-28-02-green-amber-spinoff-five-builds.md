### 2026-08-28 (Green/Amber spinoff — five decided builds land in parallel)

The concurrent build run the 2026-08-28 decisions session commissioned: five workers in
isolated worktrees (four Opus, one Sonnet), each building to its item's decided disposition in
`DEV_BACKLOG.md`; Fable reviewed every diff and merged. All five merged; cross-worker
regression green on merged main. **Nothing deployed — the whole batch owes Mike's VM deploy,
and location additionally owes an APK rebuild + sideload.** Handoffs (kept, not consumed —
they carry verbatim Red proposals for sessions ②/③): `archive/handoffs/2026-08-28-*.md`.

- **Coordinator probe `[DB-0820-05]`** (`ec774da`): Pro fixes the referent class — 12/12 on
  the hard suite vs Flash-Lite's 6/12 — at ~+11s per reply, all thinking tokens. Report
  recommends a capped-thinking-budget probe before any flip; flipping as measured was
  effectively rejected by the latency evidence, and "don't flip, fix `coordinator.md`" is
  live because Pro's winning move was following a rule the file already states. **Wrong
  earlier belief corrected:** the cache helper was suspected of ignoring `model_override` —
  it never did. The real gap was `core/trace.py` dropping `cached_tokens`, making cache hits
  invisible (the 2026-06-24 failure shape); now stored and serialised. A clean-history
  replay of the four referent failures did not discriminate (both models near-swept it);
  only the competing-referent variant measures the class.
- **write_persona gate `[DB-0815-11]`** (`75a91d6`): inferred writes propose-and-confirm via
  `consume()`; toggle `proactive.persona.inferred_write_auto_accept` default false, in a file
  no tool writes; redundancy refusal at the `NEAR_DUPLICATE` bar names the existing home
  (the 08-18 duplicate scores 0.857 vs `config/templates/scheduler.yaml:21` and is refused).
  Deliberate reversal, flagged not decided: refusal applies to user-stated preferences too —
  old "warn, never block" held only for the weaker class-collision signal.
- **Ritual halves `[DB-0809-02]`** (`6451b51`): asked-state in `context.json` (verbatim
  question text withheld from the model — it cannot recite what it never receives);
  re-ask caps incl. max 1/day across all jobs, the constant that closes the measured
  four-jobs-one-day hole; nothing-new fingerprint stamped at run close (stamping at open
  would count the run's own writes as news — gate would be inert in production while green
  in tests); ritual ownership generalised to `*_ritual.md`-by-filename. No length cap, and a
  test asserts none can creep back. The Red `synthesizer.md` paragraph is written verbatim
  in the handoff for session ③.
- **Accountability Index `[DB-0827-09]`** (`c082fb6`): deterministic joins (calendar
  occurred / obligation closed), stated_for+2d / 7d windows, trailing-30d rate excluding
  indeterminate from the denominator; content-free counts into the A9 rollup; CLI. Judgment
  gate + scheduler wiring are Red → proposal handoff, including the worker's catch that
  "Flash-Lite nightly" needs a privacy-tier check (journal text is sensitive). Discovered,
  filed in handoff only: `_deep_merge` lets a second same-day intention silently overwrite
  the first — Diarist write-shape decision, Mike's. `[DB-0828-01]` gets `due:` = deploy+10
  at the index's deploy.
- **Location `[DB-0815-12]`** (`029905e`): coordinate stops inside `POST /location`; zone
  transitions only, 0600, no raw trail even behind a flag (rejected: a flag can be left on);
  on-message ping strict-off-default with a JS test; `config/templates/zones.yaml` template,
  live copy is VM's. No model-callable location tool registered — tightest reading;
  a grant decision if wanted.

Outgoing handoff context: sessions ② (scheduler Red pair + grants + Step-6/A4) and ③ (email
surfacing + `[DB-0822-08]` re-measure + ritual Red line) are unchanged and next; the probe's
option-2 run slots wherever Mike takes the Pro decision.
