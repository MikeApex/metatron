### 2026-09-05, sixth (the horizon stops looking too far ahead — and two guards turn out to be citing things that were not there) — `tools/{horizon,diarist}.py`, `core/{orchestrator,rule_classes}.py`, `config/agents/logistics.md`, `config/modules/synthesizer_scheduled_sessions.md`, `scripts/check_agent_tools.py`, `tests/{test_horizon_ledger,test_persona_write_gate}.py`, `archive/handoffs/2026-09-05-weekly-and-school-sessions-setup.md` (new) — `73354e8`, `4abdb84`, `bb3df5a`, `471373a`, `4461107`, `282a50b` — **first four deployed by Mike mid-session; last two owe `./deploy.sh`**

Two troubleshoots of live exchanges (`004`, `006`) that each opened into a build. The through-line
is not the horizon work: **three separate mechanisms reported success or gave a citation, and in
every case the thing they named was not what had happened.**

#### The day's journal was filed to a date the Diarist invented (`73354e8`)

Exchange `004`. Mike's family day went to `journal/2026-03-30.json`, 159 days back; today's
journal had none of it and nothing errored. The Diarist is **the one specialist that ran without
a clock** — it shares the "no personal config or context" branch in `_run_single_agent` with
`bare` and `research_agent`, added to keep `goals.yaml` out of a write-only agent, and the clock
line went out with the goals. Its trace carried `context_sections ['agent_file']` alone while
every other specialist carried `[ctx:clock]`.

It guessed three times — `2026-03-30`, `2025-10-22`, then today — and only stopped because
`write_log` has the ±7-day guard from `[DB-0809-12]`. `write_journal` had none, so the first bad
date was accepted silently. **Two of the Diarist's six turns went on arguing with a guard that
only half its writes had.** Both halves fixed.

#### The horizon gate, and Mike's numbers rather than the proposed ones (`4abdb84`, `bb3df5a`, `471373a`)

There was no distance judgement anywhere: `context_block()` served every undelivered finding at
any distance and told the Synthesizer *"do not judge whether to mention them"* — the one agent
placed to make the call, explicitly forbidden from making it.

**Correction to this session's own first diagnosis**, recorded because it was reported to Mike
before it was checked: the troubleshoot named `config/modules/synthesizer_scheduled_sessions.md`
as the rule's home. That file had **no horizon content at all**. The chain was
`logistics.md` § Horizon scan → `record_horizon_item()` → `context_block()`.

`_due_now()` gates at the point of service, not at filing — *filing is not telling* is unchanged.
Four ways through, **all Mike's, given against a looser proposal**: today or tomorrow
(`_NEAR_DAYS = 1`, cut from the three offered him); a `deadline` at any distance; a precursor
falling today or tomorrow (new `precursor`/`precursor_by` fields — the mover's-claim shape, where
the posting earns the mention, not the deadline); undated. **A held finding is not charged an
offer** — the filter runs before `_charge_offers`, so it keeps its full `_MAX_OFFERS`. Quieter,
not lossier, and that has a test.

**Rejected:** a date-only gate keyed on `kind` alone, which would have handled both cases from
that exchange and re-failed on the first distant item with a real precursor filed as an `event`.

Mike then asked for the counterweight unprompted — *"Daily wrap up should run through all of
tomorrow's events whether previously stated or not. It's a review."* `review_block()` (tomorrow)
and `week_block()` (seven days) suspend raise-once, which is safe **only because both are
read-only**: no offer charged, nothing marked delivered, no write at all. Shipping the gate
without the weekly was half a decision — a Friday commitment was held on Monday with nowhere to
appear.

**And the weekly became a setting, not a session, on his question.** `weekly_review_on: <weekday>`
on any schedule entry, so it rides a brief already in the week. His reasoning is the product's
own: a separate session is attention spent, and the core metric is absorbed work measured
*against* attention. **Also rejected on his ruling:** a `topic` field for the school half — a
tool-level answer to a persona-level need.

#### Two guards that cited things which were not there (`4461107`, `282a50b`)

Exchange `006`. Mike was told the duplicate Friday swim class was removed. It was not. Logistics
called `delete_calendar_event` and got `{"success": true}` — on `e55deb2e`, a **one-off 10:00 copy
on Sept 4**. Two recurring weekly series existed; the 10:00 one (`214b6d4f`, from 08-07) was never
touched and kept generating a duplicate every Friday. Every link was locally truthful and the
outcome was wrong. **Deleted the series this session at Mike's instruction and verified against a
four-month read: one series left, the 09:30 one.** The underlying defect — nothing distinguishes
deleting an occurrence from deleting a series — is **not fixed and not filed** (Mike: skip, no
backlog item).

The same exchange's `write_persona` was refused with *"already in force… held at
`config/templates/scheduler.yaml:52`"*. Line 52 reads `prompt: "Check in."`. Two causes:

1. `shared_rules()` covered `config/agents/*.md` but not `config/modules/*.md`. **The corpus was
   not written wrong — it went stale**: it covered the agent files because that is where the
   scheduled-session conduct lived, until the 2026-08-27 synthesizer audit moved it out and
   nothing moved the corpus with it. `tools/rule_audit.py` shared the blind spot.
2. **Widening the corpus changed nothing, and that was this session's recommendation to Mike
   before it was tested.** `similarity()` is an overlap coefficient — `|a∩b| / min(|a|,|b|)` — so
   a rule reducing to `{check}` scores a **perfect 1.000** against anything mentioning a check-in
   and out-ranks every genuine candidate permanently. The real home scored 0.333. A three-word
   floor now falls back to Jaccard below it; **exactly one rule in the 187-rule corpus is
   affected** — `"Check in."` itself.

Consequence stated rather than discovered: that write now **warns instead of refusing**, which is
what `check_new_rule`'s docstring always said and what the 2026-08-03 entry records being
reverted once already.

#### The observability gap that made the third finding expensive (`4461107`)

The 2:44 complaint is real and is **adherence, not plumbing** — proved on the VM: `session_kind()`
resolved `companion_checkin` and **8,278 characters of conduct were injected**, containing *"when
there is genuinely nothing… ask what's on"*. The model did the first half.

The trace could not answer that question. `_synth_conditional_sections()` output is appended to
the system prompt and then dropped — `context_sections` recorded everything except the one
section whose presence is *conditional*. It had to be reproduced out of band. That distinction
separates "add another copy of the rule" (the `[DB-0822-10]` mistake) from "enforce it", so it is
now recorded as `conduct` on both Synthesizer paths. **Mike ruled: skip the structural gate for
now, and file nothing.**

#### Verification

`test_horizon_ledger.py` 52/52 (from 29 — 13 existing tests were asserting the old always-serve
behaviour and were **baselined at HEAD first**, without which they would have been reported as
pre-existing failures); `test_persona_write_gate.py` 19/19; `check_rule_overlap` 14 pairs before
and after; `qa_sweep` 9/9 throughout. Composed blocks were **run**, not just compiled, on every
path — which is what surfaced the both-blocks overlap on evening close.

#### Owed

`./deploy.sh` for `4461107` and `282a50b` (VM at `471373a`). The persona pastes in
`archive/handoffs/2026-09-05-weekly-and-school-sessions-setup.md` are **still undone** — verified
absent on the VM — so the weekly and school sessions cannot fire yet; both were tested against a
real copy of Mike's `scheduler.yaml`, including that `schedules:` is the last top-level block and
so the append lands at the right indent.

