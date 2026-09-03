# Red-tier proposals — session ⑥, 2026-09-03

Two agent-file changes this session diagnosed but did not make. `config/agents/*.md` is
Red; the judgement is the work, so it is Mike's call and not a subagent's.

Both are staged with the evidence that produced them. Neither is urgent — the Green
halves shipped in this session already remove the user-visible damage in each case.

---

## 1. `coordinator.md` — ROUTING_MISS is never defined for the Coordinator

**Problem in plain language.** The quality log — the one signal that finds routing
faults — filled with entries recording that routing *worked*: *"Coordinator handled
morning session prompt successfully."*, *"Routed inbox check and logistics task
appropriately."* Fifteen since 09-01, thirteen of them noise. A miss log full of
non-misses stops being read. `[DB-0902-01]`.

**What the evidence says.** Measured across all 34 ROUTING_MISS events in the live log:

| Period | Events | Noise |
|---|---|---|
| 2026-06-22 → 2026-08-29 | 19 | **0** |
| 2026-09-01 → 2026-09-03 | 15 | **13** |

Three clean months, then a clean break at the 09-01 fleet migration, with **no code
change in between**. Several of the pre-09-01 events became real work — the referent
resolution built in session ⑤ started as one of them.

**The gap.** `config/agents/coordinator.md` defines `USER_CORRECTION` at length (line 42,
line 110's output slot, line 208's tool note) and **never defines `ROUTING_MISS` at
all.** Line 208 lists it as an available event type and nothing says what one is. The
only definition in the repo is in `synthesizer.md`. `gemini-3.1-pro-preview` inferred it
correctly for three months; `gemini-3.7-flash` fills the slot with a description of what
it just did — the same "a field that looks required gets filled with something
plausible" reflex already documented in `tools/logger.py`'s `is_null_ish` docstring.

**Proposed edit — add to `coordinator.md` beside the USER_CORRECTION rule at line 42:**

> **`ROUTING_MISS` — only for routing that went wrong.** Log one when a message was
> routed to the wrong specialist, when a specialist that should have been called was
> not, or when you resolved the user's intent incorrectly and a later turn revealed it.
> The detail must name what was missed and which specialist should have caught it.
>
> **Routing that worked is not an event.** Do not log a `ROUTING_MISS` to record that a
> session was handled, that a scheduled prompt was processed, or that a package was
> produced successfully. If nothing was missed, log nothing — an empty quality log is the
> correct output for a session that went well.

**What already shipped, so this is not load-bearing.** `tools/logger.py` now refuses a
`ROUTING_MISS` whose detail asserts the routing succeeded — measured at **0 of 21
genuine misses rejected, 8 of 13 noise events rejected**
(`tests/test_routing_miss_success.py`). The five it lets through assert nothing about
success and are merely descriptive (*"Coordinator test run check"*); separating those
from a real report needs judgement code should not attempt. **This proposal is what
closes that remaining five.**

---

## 2. `synthesizer.md` — the interest-level surfacing rule is not firing

**Problem in plain language.** An email Mike would want to hear about — a Death Cab for
Cutie ticket confirmation, Troxy, Sep 26 — was processed correctly one layer down and
never reached him. `[DB-0822-09]`'s surfacing half, whose first live test failed on
2026-09-02.

**What the evidence says, and what it rules OUT.** This was suspected of being the same
intake-queue split as `[DB-0902-02]`. **It is not.** Both 09-02 runs read the same
source:

| Run | Job | Tool call | Result |
|---|---|---|---|
| 11:36:16 | pipeline (*"summarize any relevant logistics details"*) | `read_email(count=15)` | `logistics` produced **536 output tokens** |
| 11:37:09 | direct (*"any actionable items or urgent messages"*) | `read_email(count=15)` | HORIZON_ITEMS with Death Cab + Jimmy Carr, COORDINATION_OPPORTUNITIES with real legs |

In the 11:36 run the Synthesizer received **21,630 input tokens** — including
`logistics`' 536-token package — and emitted **177**: *"Your focus window remains clear
for the Apex migration delivery, Mike."* The items were in front of it and were dropped.

So the remaining fix is Synthesizer wording, exactly as `[DB-0822-09]` last recorded, and
it is now confirmed rather than suspected. Note the rule was written against
`gemini-3.1-pro-preview` and has never been measured on `gemini-3.7-flash`, which is what
served this run.

**Proposed direction — Mike's call between two shapes:**

1. **Strengthen the instruction** in `synthesizer.md` § What you receive: make
   `HORIZON_ITEMS` a *must-surface* channel on inbox-summarize sessions specifically,
   rather than a general report-interest-level preference that a focus-window judgement
   can outrank. Cheapest, and the same class of fix that has twice been ignored before.
2. **Make it structural** — surface HORIZON_ITEMS from Python the way the ACTIONS block
   is generated, so the Synthesizer cannot silently drop it. More work, and the fork this
   item has been sitting on since the closed `[DB-0822-08]`.

**Recommendation: (2).** This is the second time an instruction-side fix for this exact
behaviour has been built and then not fired, and the project's own repeated finding is
that a rule in a 52KB agent file is not a control. `enforce_pending_receipt`'s docstring
already states the precedent for taking the report away from the model. (1) is worth
doing anyway as the cheap half, but it should not be the thing relied upon.

---

## ✅ BOTH APPLIED — 2026-09-03, commit `a4a9364` (Mike approved in session)

**Proposal 1** applied as written, beside the `USER_CORRECTION` rule it mirrors.

**Proposal 2** applied as the **structural** option, with one change the scoping forced and
the recommendation above did not anticipate: the Red edit is a **format** change, not an
instruction. `logistics.md` now emits `HORIZON_ITEMS` as JSON with `date` and `venue` as
separate fields, because the ledger's dedupe key cannot be extracted from prose — across three
real runs the same show was written two ways with no title string in common. Delivery itself
is Green (`tools/horizon.py`).

**What the scoping added that this document got wrong.** It recommended making delivery
structural without asking what would happen once it was guaranteed. Mike's question — *"how
would the code know whether something is of interest?"* — is what surfaced it. The answer is
that code never decides interest (`logistics` does, and does it well), but that guaranteed
delivery without a record of what was already said would have repeated the same Jimmy Carr
show daily until 13 September. **The ledger is not a refinement of the structural option; it
is the thing that makes it safe.** Recommending "make it structural" before establishing that
was the gap in this document.
