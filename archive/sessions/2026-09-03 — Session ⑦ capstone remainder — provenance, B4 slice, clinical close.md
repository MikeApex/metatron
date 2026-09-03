# Session ⑦ — the capstone remainder (2026-09-03)

The last capstone session. Three items: `[DB-0818-08]` (fact provenance), `[DB-0804-02]`'s
buildable slice (B4 degradation wording), `[DB-0808-06]` (clinical-thread close path).
Then the capstone closes.

---

## 1. Nothing records where a fact came from — `[DB-0818-08]`

### Re-opened against current code first (standing rule) — the decided design had moved

Three findings, all put to Mike before any build:

1. **The `Kathaleen` failure was already closed** by a different mechanism. `tools/crm.py`'s
   identity-rename gate (added 2026-08-26 after the Stephen/Steven case) asks on *any*
   identity-field change regardless of provenance. Job 1's worked example needed no tag;
   adding one there would only let the gate ask *less* often.
2. **A provenance tier already existed in one store, and the two stores that had one
   followed opposite rules about who may set it.** `tools/wisdom.py` exposes
   `stated`/`observed` in the tool schema (model-declared); `tools/crm.py`'s
   `log_interaction` keeps `source` deliberately *out* of the schema for exactly the
   opposite reason.
3. **Job 2's failure was live, and its site was one function.**
   `core/orchestrator._knowledge_block` rendered `key (observed): value` plus the rule
   "put those back tentatively" — the marker-beside-a-fact pattern the 08-28 decision says
   already failed once with `[RETRIEVAL: NONE]`. `write_wisdom`'s schema already *promised*
   provenance "governs how confidently this is put back to them later"; nothing implemented it.

### Mike's rulings (2026-09-03)

- **Contacts:** ask before replacing a *checked* detail — one that Python read out of a real
  artefact. Not a per-field schema over every contact field (rejected: no artefact can ever
  back an occupation or a how-met, so the label would read "unknown source" on the large
  majority of fields and buy no protection option 1 doesn't already give, at the cost of
  relabelling every existing record).
- **Who may tag:** a model may assert `stated`/`observed`; **only code may set `verified`.**
  The stated/observed distinction is knowledge only the model in the turn has and no Python
  caller can derive; `verified` requires an artefact and must never appear in any schema.

### Built

- `tools/crm.py` — `_VERIFIABLE_DETAILS = (email, phone, address)`; `_verified_source`
  parameter (Python-only, absent from the tool schema, same discipline as `_bulk`);
  `verified_details` marks on the record; **the checked-detail gate** on the update path.
  Fires only when the detail is one of the three, a mark says code read it from an artefact,
  the stored value is *still* that checked one, and the incoming value differs. Approving a
  correction **clears the mark**, so the same correction is never questioned twice.
  `social` deliberately excluded — nested per-platform dict, no artefact path writes one.
- `tools/contacts_import.py` — passes `_verified_source="google_contacts"`. The only marking
  caller today. `tools/crm_sweep.py` deliberately does **not** mark: its values are
  model-extracted from email bodies, and it is additive-only anyway.
- `core/orchestrator._knowledge_block` — **the hedge moved inside the claim.** An observed
  entry renders as "you inferred this, and have not confirmed it with the user — {value}";
  a stated entry renders bare. The negotiable trailing rule is gone from the header. The
  value string is never rewritten, only prefixed (case surgery mangles proper nouns).
- `tools/wisdom.py` — the tagging-authority ruling recorded at `PROVENANCE`, with an explicit
  never-add-`verified`-here note.
- `tests/test_fact_provenance.py` — 15 checks, all passing.

### Status

Job 1 closed. **Job 2 built but NOT yet confirmed** — the live hedge test (seed an inferred
fact, ask a question depending on it, check the reply hedges) requires the VM, which was
unreachable through the build. Per the item's own instruction, job 2 stays open until it runs.

---

### Job 2 confirmed after all

The live hedge test ran locally against `danny_park` (the VM was reachable all along — an
earlier "unreachable" reading was my own wrong hostname; the address is
`https://metatron-vm.tail0acc5d.ts.net:8001`, and `/health` 401s because server auth is on).

Run with a **baseline arm**, because "the reply hedged" is not evidence the change did
anything. Same fact, same question, same model:

- **Old rendering:** *"somewhere in that 6:00 to 9:00 AM window"* — the inferred window handed
  back as established fact, no invitation to correct.
- **New rendering:** *"earlier in the day"* — no window asserted, closing with a question.

n=1 per arm. Evidence, not proof.

**Fixture pollution left behind:** three gitignored runtime artifacts under
`data/personas/danny_park/` (`traces/2026-09-03.jsonl`, `logs/quality_events.json`, a new
`horizon/`). Restoring them needs a write under `data/personas/**`, which is **Denied** — the
rule working correctly. Backup at the session scratchpad. Cannot reach a commit.

---

## 2. B4 capstone slice — `[DB-0804-02]`

**Built:**
- **Specialist failure.** `[Subagent error — {exc}]` was going into the Synthesizer's context
  verbatim — architecture-revealing, and useless to the user. Replaced with
  `_unavailable_notice()`: a consequence line per area, carrying no exception, no agent name
  and **no reason** (all three are facts about machinery the user has never been told exists).
- **Context tracker.** An unreadable tracker raised on the read path and silently read as
  empty on the write path — and the next write then **replaced it, destroying clinical
  threads**. Now: preserved before overwrite, and returns an `_unavailable` notice so the model
  cannot say "you have nothing outstanding" from an absence of data.

**Not built — max chain depth.** The 3-round limit is instruction-only in `synthesizer.md`;
`CHAIN_LIMIT_REACHED` is in no code. No code can detect the condition, so no message can fire.
Re-homed to Track B with Mike's word.

**Already satisfied:** B2's confused-deputy regression test is `run_b1_redteam.py --suite deputy`.

12 checks in `tests/test_degradation_paths.py`. Regression gate: filter 88/88 PASS, deputy PASS.

---

## 3. Clinical-thread close path — `[DB-0808-06]`

**The premise had expired, like item 1's.** The item and `ROADMAP.md` § A7 both said closing
needs a channel that doesn't exist. Two things had since been built for other reasons that
together are one: `tools/confirm.py` (model-excluded, user-approved, server-side) and
`core/scheduler.fire_function` (maintenance jobs, no model session).

**Mike's ruling** reframed it upstream: the real gap is that **a tier-2 flag alerted nothing**.
Build a dev-side inbox that will one day route to next of kin / physicians; a periodic check
archives from there.

**Built:** `tools/escalation.py` — idempotent per flag, sensitive-tier 0600, and every record
carries `routed_to: "…notifies nobody"` because a queue that looks monitored and isn't is worse
than an obviously empty one. Weekly `fire_function` review offers a close past a 14-day dwell,
via a **code-raised** confirmation card. `administratively_resolve` in `context_tracker.py` is
the only path to `resolved`; the conversational refusal is untouched. Durable executor
registration in `confirm.py` (the module isn't imported at startup, so the setdefault alone
would have failed the close).

**Chosen, not asked:** 14-day dwell; `notification: none`. Both overrulable.

14 checks in `tests/test_clinical_escalation.py`.

---

## Capstone close

- Close-out appended to `archive/plans/capstone_cluster_review_2026-08-27.md`.
- `CLAUDE.md` debt paid: 307 → 298. The four-tier goal hierarchy moved to
  `.claude/rules/personas.md` **with its rationale**. Privacy tiers deliberately **kept** in
  `CLAUDE.md` — `/compact` drops path-scoped rules and does not re-inject them, so a compacted
  session writing tool code that touches user data would lose the table exactly when it needs
  it. The ceiling's own comment names both sections in its keep-list; that argument was raised
  before executing.
- `.claude/rules/deploy.md` at 131/100 is pre-existing debt, untouched.
- Suite 71/72 (the known local `list_personas` case).

**Owes a deploy.** `./deploy.sh` is Denied to a session — Mike's to run.

## Recurring theme worth carrying

Two of the three items had **expired premises**: a blocker described in the item and in the
roadmap had already been removed by unrelated work, and nothing noticed. The standing
re-open-against-current-code rule caught both, and in each case it changed what got built.
