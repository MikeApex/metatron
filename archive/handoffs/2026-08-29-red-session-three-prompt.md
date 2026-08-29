# Red session ③ — email surfacing + the parked Red lines (ready to paste)

*Written 2026-08-29 at session close. This is the **last planned Red session** of the capstone:
every Red proposal parked by the 2026-08-28 spinoff lands here. Session ④ (CRM sweep) is an
Opus build, gated on Mike's plan re-review (`[DB-0827-03]`), and carries no Red work.*

**Model: Fable 5.** Red-tier judgement is the work and is not delegated (Mike, 2026-08-18).
Session ②'s tier lesson, adopted: where an item splits into a Red half and an Amber build
half, farm the Amber half to an Opus worker with Fable reviewing — ② ran Fable-throughout
and its build halves didn't need it.

---

Run `/metatron-code`, then:

## Step 0 — probe the deny lift (2 minutes, owed since 2026-08-29)

`scripts/hook_deny_lift.py` was wired that day and has never fired in a live session —
hook-allow beating a settings deny is designed from docs, not measured. Instructions are in
`.claude/rules/deploy.md` § Plan-scoped deny lift (⚠ UNVERIFIED paragraph): lift a decoy
denied path, attempt the Write, **record the result in that file replacing the ⚠ paragraph**,
delete probe and lift. Whichever way it goes, the session continues — the lift is convenience,
not a dependency.

## Step 1 — check whether the re-measure day has arrived

`[DB-0822-08]`'s fix half is gated on **one scheduled-run day of traces against the
post-audit `synthesizer.md`** — the same day that confirms the ritual-halves deploy
(`6451b51`, deployed 2026-08-28 evening). If a full scheduled-run day has elapsed, read the
traces and measure proposal adherence *before* touching the file; if not, do the re-measure
last thing or hand it forward. **Do not write a fix before the measurement** — the item's
own warning: adding a rule to that file is the move most likely to be wrong
(length→adherence, `archive/plans/synthesizer_audit_2026-08-18.md` § 5).

## Step 2 — the work, in order

1. **Email is processed and then thrown away (`[DB-0822-09]`, both halves — the headline
   item).** 397K tokens of `logistics` inbox reads produced one due date. Mike's shape:
   admin stays off his plate, but interest-level items (concerts) get reported, **with a
   coordination check attached** — parking, food, transit, who else is going. Two halves,
   deliberately one item: the Synthesizer surfacing rule + the coordination-check
   instruction in `logistics` / `recreation_hobbies`. Re-verified 2026-08-27: the intake
   queue and grants already exist; only the agent-file work is missing, and it is
   **unaffected** by the `[DB-0820-03]` eval gate. (Live confirmation afterwards may still
   need Mike's intake enable — flag it, don't block on it.)
2. **Nothing is ever proposed — only reported (`[DB-0822-08]`, fix half, after Step 1's
   measurement).** The `@session:` decision is Mike's, in-session: fix by instruction, or
   an explicit "propose a next action or stay silent" gate. Corollary he named: an item
   that cannot be acted on is not raised; one that can arrives with the action attached.
3. **The ritual Red Synthesizer line** — verbatim proposed text in
   `archive/handoffs/2026-08-28-ritual-halves.md` § "The one Red line": the
   `SCHEDULED RUN — FOCUS FOR THIS RUN` block is binding evidence, same footing as the
   actions line. Needed because code suppresses an asked question's *text* but the model
   can re-derive it from unchanged context.
4. **Judgment gate + Diarist list shape** —
   `archive/handoffs/2026-08-28-accountability-index.md` § "Red-tier proposal": the
   `accountability_judge.md` agent file (`intake_extractor` pattern, empty grant), the
   05:45 `_DEFAULT_JOBS` line (`core/scheduler.py`, Red), the weekly retrospective wording,
   and **the flagged routing-tier check** — journal text is Sensitive, so a Flash-Lite
   nightly entry is valid only on the Amendment 2026-08-28 basis and the routing comment
   must say so. Plus the decision-shaped gap: `write_log`'s `_deep_merge` silently
   overwrites a second same-day intention — the Diarist writes a list, **Mike's call which
   home takes it**.
5. **Sweep the 2026-08-28 handoffs before closing** (`archive/handoffs/2026-08-28-*.md`) —
   the capstone notes a possible location proposal-voicing line rides here too; take
   anything else marked "rides session ③" so nothing survives the last Red session unlanded.

## Gates and close-out

- Any `synthesizer.md` / safety-adjacent agent-file edit → **re-run the A4 suites**
  (`tests/run_a4_safety.py`, clinical + pipeline). Note the 2026-08-28 change: the suite now
  measures "safe WITH standing knowledge" (seeded fixture) — don't compare old baselines blind.
- Agent files are Red: they prompt Mike per edit — that is the ritual working, not friction.
- Changes are `config/agents/**` → **VM deploy owed at close (Mike runs `./deploy.sh`)**.
- `/archive` at close; the capstone plan (`archive/plans/capstone_cluster_review_2026-08-27.md`)
  is the read-first and should get a status line.
