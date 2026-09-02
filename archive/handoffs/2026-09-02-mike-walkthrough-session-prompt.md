# (M)-walkthrough session — closing everything gated on Mike, with guidance (launch prompt)

Model: Fable 5. Instructional session, Mike executing live with guidance — judgement sits in
the wisdom-store review and in adapting steps when a console differs from the script, which is
why this is not a cheaper model's job.

**Budget:** ~60–90 Mike-minutes plus preparation; splittable — items 1–2 are the dated ones.
No build cost beyond small config writes; run-cost delta zero.

**Why this session exists:** first application of CLAUDE.md § *Mike-gated work gets a
walkthrough, not a wait* (Mike's rule, 2026-09-02) — six (M) items were standing on lists with
nothing scheduled to close them.

---

/metatron-code (M)-walkthrough session, Mike present. For each item: present the prepared
steps, then guide Mike through them live, verifying each result before moving on. Work the
dated ones first; any item can be deferred to a second sitting — but it leaves with a date,
not back onto a list.

1. **Label the intake corpus ([DB-0820-03], `due: 2026-09-09`).** ~50 real messages into
   `tests/intake_fixtures/` on the VM (gitignored, never committed). Walk through: where the
   swept mail sits (accumulating since 08-29 13:54), the labelling format, and how few are
   actually needed per category. Then the session runs steps (b)–(d) itself (free-mode eval,
   `--extractor` run, scoped `/code-review`) — the flip to `extractor.enabled: true` is Mike's,
   citing the eval output. Closes the item.

2. **Review the wisdom-store cleanup proposal ([DB-0818-06]).** Per-entry approve/amend pass
   over `archive/plans/wisdom_store_cleanup_proposal_2026-08-27.md` — 24 of 59 entries are
   proposed for action. Decision-shaped; the session applies what Mike approves on the VM
   (archive-on-merge, nothing deleted).

3. **Register the Darwin API key ([DB-0818-04]).** Walk through National Rail's OpenLDBWS
   registration; key lands in the VM `.env` (Mike pastes it — the session never reads `.env`).
   Unblocks the National Rail first-draft build.

4. **Location: zones file + APK + one ping ([DB-0815-12]).** Write mike's zones file on the VM
   together (zone names Mike chooses), sideload the rebuilt APK, then confirm one ping at a
   named zone arrives with the zone abstraction — the confirm the item has owed since deploy.

5. **BigQuery billing export toggle** (owed since the caps work). Console walkthrough: enable
   the export to the named dataset so `spend_guard` reconciliations stop depending on manual
   breakdowns.

6. **The off-machine backup decision (unfiled, standing since 08-29).** The daily backup is
   live but has no off-machine copy; the Restic external-drive job is designed and not
   installed. This one is a decision first: install it now (walk through the drive setup), or
   decline with a date. Either way it stops being an unfiled ⚠ in `SESSION.md`.

At close: each item either closed with its evidence or re-dated by Mike's word. Update
`DEV_BACKLOG.md`/`SESSION.md` accordingly. /archive at close.
