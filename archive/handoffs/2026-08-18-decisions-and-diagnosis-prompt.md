# Handoff — three decisions, one undiagnosed defect, two untested items

**Run `/metatron-code` first.** This is the *second* of two handoffs from 2026-08-18. The other,
`2026-08-18-caching-fix-prompt.md`, is a self-contained build — **run it first, separately, and do
not fold it into this session.** This one is interactive: it needs Mike, and most of it is
judgement rather than code.

> **The standing warning from the session that wrote this.** It produced **four** confident causal
> explanations for one defect and a measurement killed every one. What survived was only ever what
> was actually run. **Treat every mechanism named below as a lead, not a finding**, and re-derive
> before acting. Two of its test designs also failed to reach the code they were testing, which is
> why § 3 specifies tests rather than leaving them to be invented.

---

## 1. Three decisions — put these to Mike with background and reasoning, one at a time

**He asked for exactly this format** (2026-08-18): *"you'll have to ask me questions with background
and plainspeak context, and provide reasoning behind your suggestions."* Not a list, not a table of
options with a shrug. Each gets its own exchange: what the problem is in his terms, what the choices
cost, and a recommendation you are willing to defend. **`CLAUDE.md` § Reporting Level rule 4 — never
punt a decision.**

### (a) `[DB-0818-08]` — provenance tiers, and does `inferred` gate phrasing as well as overwriting?

His idea, scoped by him to a universal rather than a CRM feature. Three tiers — `verified` (checked
against an artefact) asks before being overwritten; `stated` (he said it) is overwritten freely;
`inferred` (the model concluded it) is overwritten freely. **The open question is whether `inferred`
*also* forbids phrasing as fact**, which is what would make it a hallucination control rather than a
data-hygiene feature. His claim is that it would. It is a hypothesis, not established.
**Design it together with `[DB-0818-09]`** — a confidence tier is what makes *"are you sure you
meant 4am?"* answerable rather than reflexive. His binding constraint, in his words: **"user
instruction should generally be the winner"** — a confirmation, never a refusal.

### (b) The streaming and speech trade

Measured: the Synthesizer takes a **median 20.5s** to write a **median 563 characters**, and is
**45% of total turn time**. Nothing streams — one chunk on the wire, confirmed on the socket, not
just on screen. So speech cannot start until the whole reply lands.
**He has already asked for sentence-chunked speech and it is `## Now` item 2.** What is *not*
decided is whether to also **route the Synthesizer to a faster tier or cut its thinking budget** —
cheap, and it trades quality on the user-facing voice, which `ROADMAP.md` § 0 names as the dominant
Alpha UX factor. **That trade is his and only his.** Do not make it inside a latency fix.
Sequencing note: sentence-chunked speech is only worth building **after** the caching handoff's
option A lands, because A is what produces real streaming for it to chunk.

### (c) Which caching option, if the other session did not already settle it

Covered fully in the caching handoff. If it ran first, this is closed — check before asking.

---

## 2. The doubled reply — `[DB-0810-01]`, reopened, and **do not theorise about it**

Mike, live 2026-08-18: a reply rendered twice. **One bubble, text repeated, copies identical**,
intermittent, and **gone after closing and reopening the app**. It did *not* reproduce on the two
deliberate reconnect tests; it appeared on ordinary messages afterwards.

**Four explanations were proposed and all four are dead. Do not re-run them:**

1. *Two devices / the server broadcasting to a ghost connection.* Refuted — he sees **one** bubble,
   and the foreign-bubble path creates a second.
2. *The app rendering frames from a superseded socket.* Refuted by reading every handler in
   `static/index.html`: each carries `if (sock !== ws) return`, including `onmessage`.
3. *The server's `exclude=websocket` identity check failing when a second socket is registered.*
   **Refuted by measurement** — two sockets opened as one persona, message sent on one:
   **1 chunk to the sender, 1 to the other.** Exactly one copy each.
4. *Leftover accumulated text from an interrupted reply appended to the next one.* Refuted — that
   produces two *different* texts, and Mike confirmed the copies are **identical**.

**What it needs is the frames, not a fifth theory.** Add temporary diagnostic logging to
`static/index.html` recording every inbound frame's `type` and `exchange_id` (and, for `chunk`, a
length), retained in a small ring buffer readable from the app. That converts the next occurrence
into an answer. **Diagnostic only — it needs a deploy, which is Mike's; hand him the commit.**

Reproduction harness, working, at `scratchpad/repro_double.py` in the prior session — worth
rewriting from scratch: two `wss://…/ws?persona=…` sockets, auth frame
`{"type":"auth","token":client_token()}`, then `{"type":"send","input":"…"}`. **The frame is `send`
with `input`, not `message` with `text`** — that error cost a run. Use `maya_torres`, never `mike`.

---

## 3. Two items are UNTESTED, not passing — and the tests must reach the code

Both were "tested" on 2026-08-18 by a design that never triggered the path. **Do not record either
as passing on that evidence.**

- **`[DB-0815-07]` contact dedup.** The test — *"make a note that Stephen from the gym recommended
  Jimmy"* — wrote to **`write_journal`**, not the CRM. Two names, one a near-match to the stored
  `Steven`, and **no contact write was attempted at all**, so the near-match guard was never
  reached. A valid test must force a contact write: an explicit *"add Stephen from the gym to my
  contacts"*. **Note the separate finding this produced** — the reply said *"I've made a note of
  that"*, which was true of the journal and materially misleading about where it lives.
- **`[DB-0810-07]` the monitoring view's failure flag.** The test — *"add a calendar event for the
  32nd of September"* — was refused by the **model**, before any tool ran, so nothing failed and
  the red flag was never exercised. A valid test needs a call that reaches the tool and errors
  there: a malformed argument the model will pass through rather than validate.

---

## 4. Built 2026-08-18, NOT deployed — verify it works once it is

`core/orchestrator.py`: an unsourced Research answer is now **withheld**, not labelled. When the
model issued searches and got **zero sources**, the fabricated body is discarded and replaced with a
directive carrying the refusal wording. **Scoped on `search_queries` deliberately** — zero sources
with zero queries is a general-knowledge answer and is untouched.

Live failure it fixes, 2026-08-18: asked for the Southeastern line, two searches returned nothing,
and Mike was told *"it's showing a good service."* The `[RETRIEVAL: NONE]` marker added on 08-10 was
**already attached and the Synthesizer softened it instead of refusing** — which is why this had to
move from prose into Python.

**No end-to-end test yet.** After Mike deploys: ask a live-transport question with no backend and
confirm the reply refuses rather than hedges. Regression: `python tests/run_a4_safety.py --suite
pipeline`.

---

## 5. Also new on 2026-08-18, filed, not started

- **`[DB-0818-09]`** — an implausible instruction is written silently; only an impossible one is
  caught. Scope with (a).
- **Turn latency is 20–50s routinely**, and one turn cost 49s to write a journal line. Not filed as
  its own item; it is the caching/streaming work's territory.
- `physical_health` requested `active_workout_plan` and got *"key not found"* — one instance, not
  investigated, **not filed**. Check whether it recurs before filing anything.

---

## Order

**Run the caching handoff first**, as its own session. It is the largest measured win (46× on the
input cost of every message Mike sends), it is self-contained, and it depends on **none** of the
decisions here — so it can start immediately while these are still open. Its cheap half ships the
same day.

Then this one, with Mike present.
