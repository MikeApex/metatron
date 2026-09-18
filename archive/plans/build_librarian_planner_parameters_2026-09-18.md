# Librarian and Planner parameters — Mike's rulings, 2026-09-18

*The § 15 interview, held at the close of phase 2 so it is grounded in what the manifest and
probe can actually see rather than in speculation. Four questions asked, four answered. These
bind phases 3–5; nothing here is implemented yet, deliberately — phases 1 and 2 were the agreed
scope.*

---

## 1. The Librarian is a LOCATOR. It reads as much as it needs.

**Mike:** *"The Librarian aims to understand which questions have answers and where those answers
are currently located within user data. The Librarian should be able to read as much as needed."*

**This corrects the framing the interview was written in, and the plan supports Mike rather than
the question.** The Answer Ledger's fields are overwhelmingly about *whether* and *where* —
`answerable_by`, `data_available`, `data_home`, `evidence[{source, tool, probe, rows}]`,
`condensed_from`. Only the judgment rows carry a `decision`. So the primary job is mapping each
question to the place its answer lives; adjudication is what it does with the residue that has no
location.

**Consequences, in order of weight:**

1. **No per-question reading ration.** The flat ~1,200-character cap in `core/build/condense.py`
   stays a *default for one condensation call* and never becomes a budget on the Librarian's
   total reading. Phase 4 must not add one.
2. **The condenser's purpose changes.** It is not there to keep the judgment cheap by starving
   it — it is there to make a range READABLE. Same code, different reason, and the reason is what
   a later session will act on. `condense.py`'s docstring has been corrected accordingly.
3. **The only cost control left is the per-job budget tripwire** in `core/build/cost.py`. Stated
   plainly because a limit with no figure beside it is how this goes wrong: an unbounded Librarian
   pass can now consume a whole job's allowance and park the job at the Planner with the reading
   done and nothing built.

> **Pushback, raised rather than swallowed.** *"As much as needed"* is a correct instruction and
> not yet a number. **Recommendation: meter the Librarian's reading per run from run 1 and report
> it on the board** — characters read, sources touched, dollars — so `DEFAULT_JOB_LIMIT_USD`
> ($2.50 today, a placeholder) is set from three runs of evidence rather than guessed. The
> plumbing exists: `cost.record_job_tokens()` already attributes per node. This adds one field,
> not a mechanism.

**Open, for phase 4:** `settle.py` currently passes only the unresolved residue to the Librarian.
If the Librarian's job is locating, it may want the settled rows' locations too. Not decided here.

---

## 2. A broken lookup is triaged, not stopped — after a real troubleshoot.

**Mike:** *"The failure should be raised or passed on. If the information is a poison pill for the
plan construction Mike should be alerted. Otherwise a placeholder within the plan should aim to
retrieve that data at a later time. That is, of course, assuming the Librarian did a reasonable
troubleshoot on the failure error."*

**Better than all three options offered**, which were stop / ask Mike / treat as empty. The ruling
is none of those: it is **triage by whether the plan can be built without the data**, with three
ordered steps.

| Step | Behaviour |
|---|---|
| 1. Troubleshoot | The Librarian makes a reasonable attempt on the error before doing anything else. A 401 that clears on retry never becomes a decision. **New work — nothing in phases 1–2 retries a probe.** |
| 2. Load-bearing? | If the missing data is a **poison pill** — the plan cannot be honestly constructed without it — Mike is alerted. This is the fail-closed case, and it is narrow. |
| 3. Otherwise | The plan carries a **placeholder that retrieves the data later**. The build proceeds; the binding resolves on a later attempt or at runtime. |

**What this adds to the design, and it is genuinely new:** a BuildPlan can carry a *deferred data
binding*. Nothing in the plan document describes one. Phase 3's schema work owns it, and it needs
three things stated when it is built — what resolves it, when it is retried, and what the
capability does in the meantime. A placeholder with no retry owner is a silent hole.

**What is unchanged:** the three-state probe (`needs_tool` / `no_data` / `error`) built in phase 2
is exactly what this ruling needs to distinguish the cases. `error` still never collapses into
`no_data` — that distinction is what makes step 1 possible at all.

---

## 3. The Planner sees questions AND answers, and must cite both.

**Mike:** *"Questions and Answers. Planner can be forced to cite specific questions and answers in
the plan for tracing."*

**This answers the objection rather than accepting it.** The case for answers-only was
traceability: one recorded answer per runtime decision, so a misbehaving capability points at the
answer that caused it. Mike keeps the richer input and gets traceability by **making citation
mandatory** instead of by starving the input.

**Phase 3/4 consequence:** `validate_build_plan()` gains a rule — every decision gate in a plan
cites the question id and the ledger row it came from, and a plan carrying an uncited gate fails
validation. Not implemented here; it is a BuildPlan rule and phases 1–2 were the scope.

**Why this is strictly better than what was proposed:** citation is checkable by code, whereas
"the ledger is the only input" was a traceability property maintained by *withholding*
information — which would have degraded the plans to protect a property that a validator can
enforce directly.

---

## 4. The Planner plans. It does not create.

**Mike:** *"Planner's role is to plan. No reason that it should also need to create, that's what
Inquiry and Librarian are for."*

The Planner may not introduce a decision option that was not recorded during questioning. It
chooses among the options on the ledger, or it halts and says what it wanted to add.

**A cleaner reason than the one offered.** The interview argued this from traceability. Mike
argues it from **role boundaries**, which is the stronger form: Inquiry creates questions, the
Librarian creates decisions and their options, the Planner arranges what exists. Traceability is
then a consequence of the roles rather than a rule bolted onto them — and a rule that follows from
a role is one a later session can re-derive instead of having to find written down.

---

## What this changes, by phase

| Phase | Change |
|---|---|
| 3 | Deferred data bindings in the BuildPlan schema (ruling 2). Citation rule in `validate_build_plan()` (ruling 3). |
| 4 | Librarian gets a probe-error troubleshoot step, then poison-pill triage (ruling 2). Reading metered and reported per run (ruling 1, the pushback). No reading budget is added (ruling 1). Open: whether the Librarian sees settled rows. |
| 5 | `build_librarian.md` written as a LOCATOR first, adjudicator second (ruling 1). `build_planner.md` states the role boundary and the citation requirement (rulings 3, 4). |
