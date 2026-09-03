### 2026-09-03 (Session ⑦ — the capstone remainder, and the capstone closes)

The last capstone session. Three items that were listed in the 08-27 plan's remaining
investment and never claimed by any scheduled session, folded in at Mike's ruling on 09-02.
All three worked; the capstone is closed.

**The finding that shaped the session: two of the three items had EXPIRED PREMISES.** In each
case the blocker the item described — and that `ROADMAP.md` repeated — had already been removed
by unrelated work, and nothing had noticed. The standing "re-open against current code before
acting" rule caught both, and in both cases it changed what got built. This is the second time
that rule has paid for itself against this backlog (the first: the 2026-08-05 sweep, which found
a third of checked items stale).

**`[DB-0818-08]` — nothing recorded where a fact came from. CLOSED, both halves.**

Re-opening it moved the decided design before a line was written:

1. Job 1's own worked failure (`Kathaleen → Kathleen`) **could no longer recur** — `tools/crm.py`
   gained an identity-rename gate on 2026-08-26, after the Stephen/Steven case, that asks on any
   identity-field change regardless of provenance. A provenance tag there would only have let the
   gate ask *less* often.
2. A provenance tier **already existed** in `tools/wisdom.py` (`stated`/`observed`), exposed in
   the tool schema — while `log_interaction` deliberately keeps `source` OUT of its schema for
   the exact inverse reason. Two stores, opposite rules, neither aware of the other.
3. Job 2's failure was live at one function: `_knowledge_block` rendered `key (observed): value`
   plus the rule "put those back tentatively" — the marker-beside-a-fact shape the 08-28 decision
   already names as failed (`[RETRIEVAL: NONE]`, 08-18). The `write_wisdom` schema description
   already *promised* the behaviour and nothing implemented it.

**Mike's rulings.** *Contacts:* ask before replacing a **checked** detail — one Python read from
a real artefact. **Rejected: the full per-field schema**, because no artefact can ever back an
occupation or a how-met, so the tag would read "unknown source" on most fields, buy no protection
over the narrow version, and cost a relabelling of every existing record. *Authority:* a model may
assert `stated`/`observed`; **only code may set `verified`** — the first distinction is knowledge
only the model in the turn holds and no Python caller can derive; the second requires an artefact,
so it must never appear in a schema.

Built: `_VERIFIABLE_DETAILS` (email/phone/address — the three where a wrong value causes a
misdelivery), `_verified_source` (out of every schema, `_bulk`'s discipline), the checked-detail
gate, `google_contacts` marking in `contacts_import`. **Approving a correction clears the mark**,
so the same correction is never questioned twice. `crm_sweep` deliberately does NOT mark: its
values are model-extracted from email bodies, not artefact-read. The hedge moved inside the claim
in `_knowledge_block`. 15 checks.

**Job 2's acceptance test ran live, with a baseline arm** — without one, "the reply hedged" is not
evidence the change did anything. Same fact, question and model on `danny_park`: old rendering
asserted *"somewhere in that 6:00 to 9:00 AM window"*; new rendering said *"earlier in the day"*
and closed by inviting correction. **n=1 per arm** — evidence, not proof, and job 2 was scoped
from the start as influence rather than enforcement.

**`[DB-0808-06]` — a flagged clinical thread could never close. CLOSED, on a reframe.**

The item and `ROADMAP.md` § A7 both explained the refusal as waiting on an administrative channel
that "does not exist yet". Two things had since been built for other reasons that together are
one: `tools/confirm.py` (model-excluded, user-approved, server-side) and
`core/scheduler.fire_function` (maintenance jobs, no model session).

**Mike moved the problem upstream: a tier-2 flag alerted nothing.** It surfaced once, moved to
`watch`, and lived on in a file only the model reads. His ruling — build a development-side inbox
that will one day route to next of kin or physicians, and archive from there on a periodic check.

Built `tools/escalation.py`: idempotent per flag (the Synthesizer resubmits the whole thread list
every turn, so without that one concern would be a hundred records by Friday), sensitive-tier
0600, and every record carries `routed_to: "…notifies nobody"` — **a queue that looks monitored
and is not is worse than an obviously empty one.** A weekly `fire_function` job offers a close
past a 14-day dwell via a code-raised card; `administratively_resolve` is the only path to
`resolved` and no session can reach it, so the conversational refusal is untouched. The durable
executor registration went in `confirm.py`, not just the module's own setdefault — nothing imports
`escalation` at startup, so the setdefault alone would have failed every approved close. 14 checks.

*Chosen rather than asked, stated so they can be overruled: the 14-day dwell, and
`notification: none` on the weekly job — a scheduled push about the worst thing in someone's life
is exactly what the dwell exists to avoid.*

**`[DB-0804-02]` — the buildable slice shipped; the rest returned to Track B.**

Built the specialist-failure path (`[Subagent error — {exc}]` was reaching the Synthesizer
verbatim — architecture-revealing and useless; the live `research_agent` `NoneType` instance Mike
named on 08-18 gave the user no reason at all) and the context-tracker path, which no longer reads
as "nothing is outstanding" when unreadable and now **preserves a damaged file before the next
write replaces it — that write was destroying clinical threads.** 12 checks.

**Not built, with the reason: B4's max-chain-depth message cannot be written.** The 3-round limit
is instruction-only in `synthesizer.md` and `CHAIN_LIMIT_REACHED` appears in no code, so there is
no moment at which a message could fire. That is a build, not wording. **Already satisfied:** B2's
confused-deputy regression test exists as `run_b1_redteam.py --suite deputy`.

**Close-out.** Capstone note appended to `archive/plans/capstone_cluster_review_2026-08-27.md`.
`CLAUDE.md` debt paid, 307 → 298: the four-tier goal hierarchy moved to
`.claude/rules/personas.md` **with its rationale intact**. Privacy tiers deliberately **kept** —
`/compact` drops path-scoped rules and never re-injects them, so a compacted session writing tool
code that touches user data would lose that table exactly when it needs it; the ceiling's own
comment in `check_claude_md_claims.py` names both sections in the keep-list, and that argument was
raised before executing rather than discovered after. `.claude/rules/deploy.md` remains 131/100 —
pre-existing, untouched.

Suite 71/72 files (the known local `list_personas` case, which passes on the VM). Regression gate:
filter 88/88 PASS, confused-deputy PASS. The disclosure and injection suites need live model calls
and were not run.

**Correction from this session, recorded because it wasted time:** the VM was reported unreachable
for most of the session on the strength of `curl http://metatron:8001/health` returning 000. The
VM was up throughout; the address is `https://metatron-vm.tail0acc5d.ts.net:8001` and `/health`
returns 401 under server auth. A wrong hostname was read as an outage.

**Owes a deploy.** `./deploy.sh` is Denied to a session.
