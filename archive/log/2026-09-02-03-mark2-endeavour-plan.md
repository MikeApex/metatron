### 2026-09-02 (Mark 2 endeavour plan, and the development pipeline audited)

A planning-only session with Mike, scoping the Metatron Mark 2 rebuild as an *endeavour* —
sequencing, gates, buckets, cost — rather than as architecture, which the rebuild notebook
already holds. Produced `archive/plans/mark2_endeavour_plan_2026-09-02.md` (596 lines, nine
sections) and appended round five to `archive/plans/code_dominant_rebuild_notes.md`
(187 → 285 lines). No code, config or roadmap touched.

**Mike's rulings, in order made.** Alpha ships on **Mark 2**, which makes A8 a cancellation
rather than a deferral — refactoring `core/orchestrator.py` into modules Mark 2 replaces is the
clearest waste on the board. A7 **checks 10 and 12 are skipped** and fold into Mark 2; the
12-specialist behavioural audit (8–12 hrs) was the largest Mark-2-invalidated item on the list,
larger than A8 itself. **Development rules are instated at the outset**, not discovered by
failure. **Mike's persona data maintains into Mark 2 while Mark 1 still runs.** A **full review
of the complete Mark 2 file suite before any production begins** — gate G1, twelve checks.
Roadmap edits and the Mark 1 decommission condition are **Mike's to handle manually**, so
`ROADMAP.md` still reads as though A8 is live: known, not an oversight.

**Options rejected, with the reason.**
- **A correction-history corpus** (labelled `USER_CORRECTION` events + CRM merge/undo archive +
  traces) — proposed, then killed by Mike: most Mark 1 errors are functions of its construction
  and of poorly-followed directions, so a catalogue distracts. Replaced by **tests that fail on
  Mark 2 if the error classes recur** (eight seeded from named incidents), each to be observed
  failing before the code that satisfies it exists. Cheaper and it gives the inversion its first
  measurable claim.
- **Default-off / earn-back for *development* rules** — proposed by Claude, corrected by Mike.
  Those rules protect against process failures whose cost is real work lost; there is no upside
  to re-learning them. Earn-back survives only for the *project* layer.
- **Retrofitting event emission into Mark 1** so cutover could replay a log — breaks the
  bugfix-only freeze, touches exactly the modules holding live data, and buys history only
  forward from today. Chosen instead: point-in-time state export at cutover, Mark 2
  event-sourced from day one.
- **Rebuilding a plan-scoped deny-lift hook** — Mark 1 already proved it cannot work (below).

**Believed true earlier, found wrong.**
- **A shared append-only event log was assumed to exist as the Mark 1 → Mark 2 contract. It does
  not.** Measured: thirteen append-only streams with thirteen schemas and no common envelope; the
  trace stream is a *conversation* log (`trace_id / ts / user_input / synth_response / pipeline /
  grounded`), not a domain event log, so CRM state cannot be rebuilt from it; ~25 modules hold
  authoritative mutable state via whole-file `json.dump`, the substantive eight being `crm.py`
  (20 write sites), `intake`, `accountability`, `context_tracker`, `confirm`, `wishes`,
  `baselines`, `wisdom`. One counter-example already holds the target shape: the FAISS index is
  genuinely derived from `memory/metadata.json`.
- **The Mac's `data/personas/mike/` is a local-dev remnant** — four trace files (one empty, one
  from June), one journal day, a nine-entry index. The live data is on the VM. Also corrected
  mid-session: `data/personas/**` is `deny`-listed for **`Edit` only** — `Read` needs no lift.
- **The dev rule surface was undercounted.** Eight hook invocations across six events total
  **2,262 lines** — a second rule surface as large as `.claude/rules/` — missing from the first
  count of 2,344. Full surface ≈ 5,200 lines. G1 now reviews the hook set.
- **`scripts/hook_deny_lift.py` does not work and Mark 1 knows it** — probed 2026-08-29 with Mike
  present: the `settings.json` deny wins, hook `allow` does not override. Mark 2 must not rebuild
  it; the plan's approach is to make fewer things need lifting (Mark 1's blanket
  `Edit(./data/personas/**)` deny would block Mark 2's own importer), then a scripted lift whose
  restore is mechanical and loud, over a `NEVER_LIFT` floor.
- **`SessionStart` lives in `.claude/settings.local.json`** — untracked, absolute path, does not
  survive a clone.

**The framing that did the work: "the rules" are three buckets, not one** — development rules
(instated day one), project rules (keep-list + quarantine, discovered), and operational knowledge
(facts about the world, carried verbatim). Conflating them produced the session's one substantive
error. The sorting criterion, which also picks the delivery mechanism: **if the failure a rule
prevents is silent, it cannot be quarantined; if it announces itself, it can.** Only root
`CLAUDE.md` survives `/compact`, so silently-absent knowledge must live there.

**§ 4b — the development pipeline, twelve items**, added on Mike's challenge that item 3 of his
original brief was unaddressed. Archiving cuts the *duplication* rather than the step count (the
fragment's length goes to what git cannot hold); the verbatim transcript is **unconditional —
it runs even when the session changed nothing**; `SESSION.md` becomes generated state plus one
hand-written next-step paragraph; the backlog pipeline becomes a **cross-project standard living
in `~/.claude/`**, drafted before Mark 2's repo exists so Mark 2 is its first consumer rather
than its source; `verify` dissolves, because a bug closed by a test going red→green needs no
re-verification sweep. **The Book persists as REQUIREMENT R1** — a trace contract constraining
Mark 2's record format (per-request records, nested attribution, timing/token/cost, live stream),
settled before the format is designed rather than bolted on; `/metatron-troubleshoot` folds under
the same requirement. `/metatron-code` is preserved as **`/mark2-code`** for the post-construction
editing phase, and the backlog `SessionStart` hook ships day one reporting zeros on an empty log.
Parallel windows resolve to a `newwindow` script plus a **collision-triggered** warning — not a
worktree per window, since that costs a merge per session for a collision that usually is not
happening — with marker expiry so a crashed session cannot train Mike past a real warning.

**Three things are marked "probe at G1" rather than asserted**, because they were not tested:
whether slash-command frontmatter honours `model:`, whether a `SessionStart` hook can switch the
model, and whether `EnterWorktree` relocates a live session. Model selection at session start is
recorded as a **requirement**; the mechanism is external — Mike is building a universal one in a
separate chat.

Not committed at the time of writing; no deploy applies (planning documents only).

