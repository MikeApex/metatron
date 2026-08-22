# Handoff — plan the CRM sweep. Design session, no build.

**Run `/metatron-code` first.** This is a **planning** session: the deliverable is a plan document
and Mike's approval of it, not code. Mike asked for the sweep to be built and enacted
(2026-08-19); he also agreed it deserves its own session rather than being designed in the margins
of a test run.

> **The standing warning from the sessions that produced this brief.** Across 2026-08-18/19,
> *everything that was RUN held up and everything that was INFERRED was wrong* — four confident
> causal explanations for one defect, all four killed by measurement. **Treat every number below
> as re-checkable and every mechanism as a lead.** The measurements here were taken on
> 2026-08-19 against 200 live traces; re-take them before building on them.

---

## 1. The problem, measured

`/monitor/traces?persona=mike`, 200 traces, 786 tool calls, 2026-08-19:

| Tool | Calls |
|---|---|
| `write_log` | 172 |
| `write_journal` | 53 |
| `search_contacts` | 4 |
| `write_contact` | 5 |
| **`log_interaction`** | **1** |
| `list_contacts` | 0 |
| `merge_contacts` | 0 |

**Information about people is being captured constantly — into the journal and the daily log,
where it is prose nobody can query. The CRM is starving beside it.**

### Two structural facts that shape the answer

1. **`notes` is not an accumulator, despite reading like one.** It is a single free-text field and
   `write_contact` **overwrites it wholesale** (`_str_fields` loop, `tools/crm.py`). Anything that
   appends to it either clobbers prior content or grows unbounded.
   **`interaction_log` is the append-only structure** — typed entries with summary, follow-up and
   date, and it moves `last_contact`. **It is the right target, and it ran once in 200 traces.**
2. **The schema is not poor — it is empty.** 22 of 23 `write_contact` fields are exposed to the
   model (`employer`, `occupation`, `education`, `spouse_name`, `kids_names`, `how_met`,
   `important_dates`, `tags`, …); only `tone_shape` is deliberately withheld. **Mike's example of a
   missing "Employer" field was checked and the field already exists.** The gap is capture, not
   schema.

### The diagnosis

`write_contact` and `log_interaction` are granted to **`relationships` alone**
(`routing_cloud.yaml`). That specialist is dispatched when a turn is *about* a person — but people
are *mentioned* in turns about work, travel, health and calendars. **The capture opportunity and
the only agent able to act on it are routed apart.**

---

## 2. What was already decided, and must not be re-litigated

**Inline capture was considered and rejected (Mike, 2026-08-19).** Catching mentions inline means
dispatching `relationships` on turns that are not about relationships: a Coordinator change adding
a specialist to most turns, when turn latency is already 20–50s, and it puts a *"is this a durable
new fact about a person?"* judgement on a Flash-Lite agent mid-answer. **That is the exact
judgement class that failed twice that week** (§ 3). The sweep runs off the critical path, sees a
whole day at once — so it can tell a passing mention from a recurring one, which no single turn
can — and can batch its output into one review.

**BINDING: the sweep proposes, it does not write.** An unattended vacuum into the CRM is a write
path with no user present. Evidence for why that is not paranoia:

- **`[DB-0818-06]`** — 24 stored "facts" were found, several of them *inferred preferences recorded
  as observations*. A daily sweep multiplies that quietly.
- **The 2026-08-19 merge incident** (§ 3) — a destructive CRM operation performed on a silent,
  wrong assumption about a real person.

**The safety this needs is already decided and mostly unbuilt — `[DB-0818-08]` provenance tiers.**
A sweep-derived fact is `inferred` **by definition**, so the tier marks it and stops it being
phrased as fact. **Sequence the sweep after that**, or state explicitly in the plan why not.

---

## 3. Read this before designing the review step — it is the failure mode you are designing against

Two live incidents, days apart, same shape: **the agent resolved an ambiguity silently instead of
asking.**

1. **2026-08-19, contact creation.** Handed near-match evidence twice four minutes apart: turn 1 it
   surfaced the existing `Steven` and offered to merge; turn 2 it announced *"Stephen with a 'ph'
   is added as a separate contact"* and created the duplicate. Same model, same evidence, opposite
   answers. **Fixed by a confirmation gate** (`6d6d46c`) — and that gate carries a standing note
   that it is expected to become unnecessary when models ask reliably.
2. **2026-08-19, the merge — worse, and it damaged real data.** Mike said *"Steven from the gym and
   Stephen from the gym are the same person. Merge them, keeping Steven."* **There were three
   Stevens.** The agent picked `keep_id = 5069065f` — Mike's actual friend, spouse Yana, dinner
   logged 21 June — and folded **both** gym records into him. Confirmed in the record afterwards:
   his contact now says he was met *at the gym* and carries a phone number of `"ph"` (the model had
   earlier turned *"Stephen with a 'ph'"* into a phone value; the placeholder guard does not catch
   it). **There is no unmerge tool.** The originals are archived with `merged_into` pointers, so
   recovery is a JSON edit on the VM.

**The lesson for this design, stated as a constraint: a sweep that proposes CRM changes is
proposing exactly this class of operation at volume, unattended, daily.** The review step is not a
nicety bolted on the end — it is the feature.

**Corollary: do NOT let v1 propose merges.** Additive proposals only.

---

## 4. Questions the plan must answer

1. **Input.** Conversation log, journal, both? What window — yesterday, or since last run? How does
   it avoid re-proposing what was already declined? (A declined proposal that returns tomorrow is
   how a review queue becomes noise and then becomes rubber-stamped.)
2. **Output shape.** What is a proposal? Precedent exists: `WISDOM_PROPOSAL` blocks parsed in
   Python by `_file_wisdom_proposals()` (`core/orchestrator.py`) — the agent emits, Python files.
   Reuse or diverge, and say which.
3. **Where proposals live** until reviewed, and **how they are reviewed.** A morning digest? A
   batch in the app? The Book? **Note the confirm-gate precedent and its limit** — one tap per item
   is right for 5 items and trains rubber-stamping at 50.
4. **Trigger.** `_DEFAULT_JOBS` in `core/scheduler.py` (maintenance, the `daily_analytics_rollup`
   precedent) or a persona `scheduler.yaml` entry? **`CLAUDE.md` § Infrastructure traps 5** —
   scheduler runs `--persona mike`; anything per-user needs the same decision A9a defers.
5. **Model tier.** Bounded extraction against a closed schema. Precedents both run Flash-Lite with
   an **empty tool grant**: `tone_profiler` and `intake_extractor`. An extractor with no tools
   cannot act on what it reads — relevant, because the log it reads contains user text.
6. **Privacy.** The sweep reads a whole day of personal log: **sensitive tier, ZDR path, no
   open-tier cloud call.** Nothing here needs a new ruling; confirm it in the plan rather than
   leaving it implied.
7. **`interaction_log` vs fields.** Does v1 propose interaction entries only, or field fills too?
   `notes` is the wrong target either way (§ 1).
8. **How success is measured.** `log_interaction` at 1 call per 200 traces is the baseline. State
   what the number should look like after a month, and how a *wrong* proposal rate gets counted —
   acceptance rate is the honest metric and it needs to be recorded from day one, per the A9
   lesson that you cannot retro-fit a question onto data you did not keep.

---

## 5. Explicitly out of scope for this plan

- **Field promotion from notes** (Mike's idea, 2026-08-19: review notes, promote recurring patterns
  into new CRM fields). **The mechanism is sound and its trigger has not fired** — it should run
  when notes are rich, and notes are empty. Revisit once the sweep has produced material. Do not
  design it now; do record the gate.
- **LinkedIn / social / researcher enrichment.** Mike wants it and has specified the shape
  (a toggle, per-contact opt-in, an identity confirmation showing a profile picture — *"is this the
  guy"*, context-dependent). **It needs a `ROADMAP.md` § Section 0 ruling before any build**:
  sending a named private individual to a research path is not decontextualized dispatch. Separate
  session, separate decision. Not folded in here.
- **Any build at all.** This session produces a plan.

---

## 6. Deliverable

`archive/plans/crm_sweep_plan_2026-08-XX.md`, approved by Mike. Per `~/.claude/CLAUDE.md`
§ Plan Mode, the plan carries a **token/cost budget** and a **named model recommendation** for
execution.

**Suggested split for the plan itself:** design in Fable, build in Opus — Mike's standing decision
from 2026-08-18, made after a Fable review turned a build into a one-line branch and caught five
constraints the brief had missed.

## 7. Scope and tier

Planning only. If it later builds: a new `tools/` module and a `core/scheduler.py` job are
Green/Amber; **`config/agents/**` and `routing*.yaml` are Red** and prompt every time.
**`./deploy.sh` is Denied — hand Mike the commit.**
