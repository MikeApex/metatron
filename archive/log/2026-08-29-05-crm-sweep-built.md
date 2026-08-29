### 2026-08-29, fifth (session ④ — the CRM sweep is built, and the gate was re-run rather than asserted) — `tools/crm_sweep.py` (new), `config/agents/crm_sweep.md` (new), `config/templates/crm_sweep.yaml` (new), `tests/test_crm_sweep.py` (new), both routing files, `config/agents/relationships.md`, `core/{orchestrator,scheduler}.py`, `tools/{crm,confirm}.py` — `f75a338`, `89cfbcb` — **deployed by Mike in-session (rode the parallel window's close-out deploy); live and enabled for `mike`**

**Incoming handoff:** session ④ of the capstone, gated on Mike re-reviewing
`archive/plans/crm_sweep_plan_2026-08-27.md` — his explicit instruction when he accepted the
plan on 08-27, tracked as `[DB-0827-03]`.

**The gate resolved differently than either branch offered.** Asked whether the re-review had
happened, Mike answered *"run the review now, but nothing has changed. If the review passes,
continue with the build."* So the re-review was performed in-session against current code
rather than taken as done, and the build proceeded on its result. **The plan held; five things
had moved under it:**

1. **The measured problem got worse, not stale.** Step 0's re-take, read live off the VM:
   200 traces (08-22→08-29), 776 tool calls, `write_log` 232, `write_journal` 52,
   **`log_interaction` 0** — down from 1 per 200 traces on 08-19. `list_contacts` 3.
2. **05:45 was taken.** Session ③ put `daily_accountability_judgment_gate` there. The sweep
   went to **05:50**, preserving the plan's stated intent (after the 05:30–05:40 block, on a
   closed day).
3. **The plan named only `routing_cloud.yaml`; the entry went into both.** Every
   extractor-pattern agent (`intake_extractor`, `accountability_judge`, `tone_profiler`)
   carries a `local: true` parity entry, and cloud-only would have left the sweep unrouted
   whenever `DEPLOYMENT_MODE=local`. One Red edit beyond the plan's tier table — the deviation
   is additive and was reported before building.
4. **The build dependency was already met.** `[DB-0827-01]` (declining did nothing) shipped
   08-27 with the re-proposal guard, so the batch confirm tap has a working exit. The plan
   listed it as owed.
5. **Two premises had drifted cosmetically only.** `tools/crm.py:1113–1200` is now :1334
   (`log_interaction`), and `danny_park/conversations/` is empty rather than populated — the
   test plan already called for seeding, so neither changed the work. **Both `crm.py` hazards
   re-verified live and still present.**

**What was built.** A nightly bare Flash-Lite extractor over yesterday's conversation +
journal → Python validation → append-only `crm/proposals.jsonl` → a quiet one-line morning-brief
digest → conversational accept/decline → `apply_crm_proposals(accept_ids, decline_ids)` replaying
the ledger row by id behind one batch confirm tap. Off by default per persona.

**Decisions taken inside the build, none of which the plan settled:**

- **Identity fields (`name`, `first_name`, `last_name`, `nickname`, `referred_to_as`) are not
  fillable, even when empty.** Two reasons and the second is load-bearing: a swept-in given
  name is the `Kathaleen` shape (`[DB-0818-08]`); and `write_contact`'s update gate raises its
  own confirmation card on any identity change, which — reached from inside a tool already
  behind a batch confirm — would nest one card inside another and return a JSON payload where a
  result was expected. Excluding the fields keeps the two gates from meeting.
- **An ambiguous proposal cannot be accepted at all**, only declined. The plan said ambiguity is
  "carried into the proposal and shown as a question"; it did not say what `apply` does with
  one. Allowing acceptance would have required the sweep or the model to resolve it, which is
  the two-Stevens operation at volume. The user answers, then the ordinary conversational tools
  do the write behind their own near-match gates.
- **The digest's framing instructs the head layer to ROUTE, not to call.** First draft told the
  Coordinator/Synthesizer to call `apply_crm_proposals`, which is granted to `relationships`
  alone — the instructed-but-ungranted class `.claude/rules/agent-files.md` exists to prevent,
  authored by accident inside the same session that read the rule. Caught before commit.
- **`source` was added to `log_interaction`'s Python signature but NOT its tool schema.** A
  model that could set provenance could assert a check the system never performed — the
  `[DB-0818-08]` failure mode, one layer down. Asserted by a test.
- **A failed apply leaves the proposal `pending`, never `accepted`.** A ledger claiming a write
  that never landed would suppress that fact forever by fingerprint.

**Rejected:** bundling `[DB-0818-08]` (contact provenance) into this session. The capstone
offered "bundled or immediately after" and Mike's rule was *"if it was in the plan for this
session, proceed; if not, hold off."* The plan he re-reviewed excludes it and argues why the
sweep does not wait on it, so it was held. Applied sweep entries carry `"source": "sweep"` as
the backfill seed for when the tier field lands.

**Believed true and wrong:** the post-deploy CLI command handed to Mike was
`python3 tools/crm_sweep.py`, which puts `tools/` on `sys.path` instead of the repo root and
died on `import core` on the VM. The repo convention is `python3 -m tools.crm_sweep`, matching
`obligations`/`accountability`/`calendar_reconcile`; the module form always worked and nothing
in the file said so. Comment added (`89cfbcb`) — no behaviour change, no deploy of its own.

**Testing.** `tests/test_crm_sweep.py`, 37 checks, repo-native runner (not pytest — none is
installed). Three failed on first run: all three were wrong test premises, not defects (a first
run has no cursor and reads yesterday only; a corrupt day file short-circuits before the model
call). Existing CRM, confirm, scheduler, intake and decline suites all pass; `qa_sweep` 9/9;
`check_agent_tools` reports the new tool in no actionable class. **Also run end to end against
real Flash-Lite** on a seeded day: 4 correct proposals, nothing written to the store, and the
one non-person line ("book the car in for a service") correctly ignored.

**Privacy.** The sweep reads a whole day of conversation and journal — Sensitive tier, more of
it at once than anything else on the Vertex path, and the routing entry states so. Authorised by
`ROADMAP.md` § Section 0 Amendment 2026-08-28 and nothing further; lapses with that basis the
moment the deployment stops being single-user. It is the path `relationships` already reads this
material on, so nothing new was ruled on.

**Deploy.** Rode the parallel window's close-out deploy. Mike then created
`config/personas/mike/crm_sweep.yaml` with `enabled: true` on the VM — **the sweep is live and
switched on; first run 05:50 on 08-30, reading 08-29.**

**Outgoing handoff:** `[DB-0827-03]` is built, deployed and enabled, and owes **one live
confirmation**: a morning brief carrying the quiet line, then accept one suggestion and decline
one — pass is the accepted one appearing with the wording shown, the declined one never
returning, and one tap covering the batch. **Its backlog close-out was NOT performed by this
session** — `DEV_BACKLOG.md` was dirty with a parallel window's own close-out, so staging it
would have carried that window's uncommitted lines (CLAUDE.md § Deploy safety, rule 4). Next
session: retitle `[DB-0827-03]` to the live confirmation it now owes. `[DB-0818-08]` is
unstarted and is the recommended next build.
