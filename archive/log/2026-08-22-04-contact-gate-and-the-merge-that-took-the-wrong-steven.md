### 2026-08-22 (the contact dedup gate ships; its first live merge takes the wrong Steven) — `a192821`, `b980b93`, `6d6d46c`, `30b181c`, `4c05b8b` — **deployed mid-session**

**Incoming handoff:** `archive/handoffs/2026-08-18-decisions-and-diagnosis-prompt.md` — three
decisions for Mike, one undiagnosed defect, two items recorded as tested that were not.

**Decision (c) closed itself.** A parallel window shipped both caching options while this session
was putting the decisions; checking before asking is what the handoff instructed and it was right.
**Decision (b), the thinking budget, Mike took to another window.** **Decision (a), provenance
tiers, he decided here** — build both halves, and hold the second to a test.

**The (a) reasoning worth keeping, because it generalises past this item.** Two jobs hide inside
one field. *Job 1* — stop a checked value being silently replaced — is an `if` at the write path
and is certain. *Job 2* — stop a guess being spoken as fact — happens on the way out, where there
is nothing binary to test, so **every option is influence, not enforcement**. The first answer
overstated this ("smallest AND certain to work" was applied to an option that only does job 1) and
Mike caught it. The chosen shape for job 2 is to **rewrite the fact rather than tag it** — the
store renders an inferred value as *"you inferred, but have not confirmed, that…"* — because a
marker beside a fact is an instruction the model can negotiate with, and that pattern had already
failed: `[RETRIEVAL: NONE]` was attached to the Southeastern turn and the Synthesizer softened it.

**Then the session did the thing it was warned about, and Mike stopped it.** The handoff said to
add a frame log *"readable from the app"*. That was a prior session's wording, not Mike's approval,
and it shipped a long-press that printed frame types and exchange ids into the conversation
**rendered as the assistant speaking** — an architecture-disclosure surface built into the product,
in the one layer with no `filter_output`. He asked whether it was a security issue before it
deployed. **Reverted to byte-identical, and rebuilt server-side** (`a192821`): every outbound frame
logged with its socket and emit path, read at `/monitor/ws_frames`. **The server version is also the
better instrument** — it answers *did the server send it twice*, which decides client-vs-server on
its own. Content-free; auth via the existing middleware.

**Trying to test the monitoring flag found the flag was wrong, and that outranks the test.** `ok`
was set `False` in exactly one place, the `except` around dispatch. Measured on the VM: **786 tool
calls, one `ok:false`** — a missing required argument on a scheduled agent — while every graceful
failure a user hits rendered green. **No phrasing could ever have turned it red**: ten tools were
checked and all handle invalid input gracefully by design. Fixed in `b980b93`, keyed on a leading
`Error:` token, deliberately narrow — a false red sends someone debugging a call that worked.

**The gate (`6d6d46c`), and why neither cheaper answer survives.** The *score* cannot decide it:
Stephen/Steven 0.77 is one person, Dave/Dan Bennett 0.87 is two, Anna/Hannah 0.80 is two — pinned as
test assertions so nobody re-proposes a threshold. The *agent* cannot: identical evidence four
minutes apart produced an offer to merge, then *"Stephen with a 'ph' is added as a separate
contact"*. **Mike asked whether this was a model-strength issue** — a fair question, since
`relationships` runs Flash-Lite — and the answer is that turn 1 proves the model **can** ask, so it
is variance, not a ceiling. A stronger tier lowers the rate without reaching zero. **Recorded in
`ROADMAP.md` § D2 as a judgement-consistency test** measuring how often a model *asks*, not which
answer reads better, and scoped to every specialist whose tier is set.
**Mike's instruction: a production note that the gate is expected to become unnecessary.** It is in
four places — the code, the test, the item, § D2 — because the models of tomorrow are not the
models of today and the lighter design is evidence-not-verdict.

**A regression was introduced and caught before it shipped:** bulk import calls `write_contact`
per record, so 200 contacts would have raised 200 blocking confirmations. `_bulk` exempts it,
**deliberately absent from the tool schema** so no model can set it. Found by
`tests/test_contacts_import.py`, not by reasoning.

**The first live run of `merge_contacts` — 0 calls in 786 before this — corrupted a real record.**
*"Merge them, keeping Steven"* was ambiguous across **three** Stevens; the agent picked Mike's
actual friend (spouse Yana, dinner 21 June) and folded **both** gym records into him. His contact
now says he was met at the gym and carries a phone of `"ph"` — the model had turned *"Stephen with
a 'ph'"* into a phone value, which `_is_placeholder_phone` does not catch. **There is no unmerge.**
Filed `[DB-0822-03]`/`[DB-0822-04]`. **The test instruction was mine and it handed the agent that
ambiguity knowing there were three records** — the same ask-vs-assert failure, now destructive.

**Two claims corrected mid-session.** The VM was reported unreachable; it was never down — the
hostname, scheme and port were all wrong. And the sweep prompt was described as *"written and
waiting"* when no line of it existed.

**CRM design, answered with measurement rather than opinion.** 200 traces: `write_log` 172,
`write_journal` 53, **`log_interaction` 1**. `notes` is overwritten wholesale so it cannot
accumulate; `interaction_log` is the right structure and is unused. **22 of 23 `write_contact`
fields are already exposed** — Mike's "we don't have Employer" example was checked and the field
exists — so the gap is capture, not schema. Inline capture rejected (latency, plus a durable-fact
judgement on Flash-Lite mid-answer); **sweep chosen, and it proposes rather than writes.** Briefed
in `4c05b8b`.

**Backlog:** Mike asked whether entries were being grown instead of closed. They were.
`[DB-0815-07]` **closed and removed** on its `@waiting` condition actually occurring, evidence in
`archive/backlog_closed_2026-08.md`; `[DB-0810-07]`'s verbose addition cut to five lines.

