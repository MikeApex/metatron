### 2026-08-18, seventh (Phase 1 live testing with Mike at the app — four items closed, three defects found, and four confident explanations killed by measurement) — `core/orchestrator.py`, `DEV_BACKLOG.md`, two handoffs, **not deployed**

**Mike drove the app while this session read the VM's traces live.** That pairing is the finding
about method: **every claim this session ran held up, and every claim it inferred from timing or a
partial read was wrong.** Four causal explanations were proposed for one defect and all four died —
one to a reproduction, one to reading the client line by line, two to Mike's own observations. The
value came from him noticing things in passing, not from the test plan.

**Closed, with evidence.** `[DB-0815-04]` Bulgarian render (already closed earlier in the day, held
up live); `[DB-0815-05]` the profile guard — a contact-name correction left `profile.yaml` untouched;
`[DB-0809-16]` the dictation readout, 5/5 on its pass conditions, **spoken into for the first time**
eleven days after being code-verified.

**`[DB-0810-01]` REOPENED, and closing it this morning was a mistake.** Two deliberate reconnect
tests passed — including a Tailscale cut, which produces the half-open socket the 1500 ms fallback
exists for — and it was recorded as closed. **The item's own text said "do not close on 'it works
now'."** Doubling then appeared on the two ordinary messages after. Symptom, precisely: **one bubble,
identical repeated text, intermittent, gone after an app restart.**

**The four dead explanations, recorded so nobody re-runs them:** two devices / a ghost connection
(refuted — one bubble, not two); the app rendering a superseded socket's frames (refuted by reading
every handler — each carries `if (sock !== ws) return`); the server's `exclude=websocket` identity
check failing with a second socket registered (**refuted by measurement** — two sockets opened as one
persona, 1 chunk to the sender, 1 to the other); leftover accumulated text from an interrupted reply
(refuted — that yields two *different* texts, and Mike confirmed identical). **Next step is frame
logging in the client, not a fifth theory.**

**Three defects found, none by the test plan.**

1. **Nothing streams, and it is measured on the wire now.** Mike, unprompted: *"the entire bubble
   publishes at once."* Confirmed — the reproduction received a whole reply as **1 chunk**. The
   streaming code is correct and the client repaints per chunk; a thinking model emits reasoning as a
   token class carrying **no `delta.content`**, so the wire is silent for the whole think.
   **This inverts `[DB-0809-13]`** (sentence-chunked TTS, closed this morning as "don't build until
   we know whether 2.8s feels slow"): 2.8s was never the problem, 11–33s of upstream silence is.
   Mike asked for it — now `## Now` item 2.
2. **The app's own turns never hit the prompt cache — 46×.** Median input tokens: **22,967** for a
   turn Mike starts, **495** for a scheduled one. Same agent, same ~19,000-token prompt. Eight test
   turns cost **248,457** input tokens against ~2,400 cached. Cause: the streaming path calls
   `_openai_compat_stream` and never touches `_get_or_create_vertex_cache`; only the non-streaming
   head-layer path caches. **It opted out of caching to buy streaming and did not get streaming
   either.** `synthesizer.md` is **65% of that prompt** and grew 43.6 KB → 51.1 KB in eight days.
3. **A research answer with no sources was delivered as fact.** Asked for the Southeastern line, two
   searches returned **zero sources** and the reply was *"it's showing a good service overall"* plus
   an invented incident. **Fixed** in `core/orchestrator.py`: the body is now **withheld**, not
   labelled, and replaced with a directive carrying the refusal wording Mike asked for on 08-18.

**Believed true earlier, wrong — three times, all mine.** (1) *"It called no tool at all"* — it
called `run_subagent(research_agent)`; an artefact of how the trace was queried. (2) *"The knowledge
layer is causing the token bloat"* — taking the prompt apart showed **no knowledge section in it at
all**; the bloat is one instruction file at 65%. Both were causes inferred from timing. (3) Closing
`[DB-0810-01]` on two clean turns.

**Two test designs also failed to reach the code they tested, so two items are UNTESTED rather than
passing.** `[DB-0815-07]` — *"make a note that Stephen from the gym recommended Jimmy"* went to
`write_journal`; **no contact write was attempted**, so the near-match guard was never reached.
`[DB-0810-07]` — *"the 32nd of September"* was refused by the **model before any tool ran**, so
nothing failed and the red flag was never exercised. Both need tests that force the path.

**Filed at Mike's instigation, both from questions he asked about passing tests.** `[DB-0818-08]` —
provenance tiers (`verified`/`stated`/`inferred`), scoped by him to a universal, after a *verified*
contact spelling was silently overwritten by a dictated one; his hypothesis is that an `inferred`
tier suppresses hallucination, recorded as hypothesis not promise, and his constraint —
**"user instruction should generally be the winner"** — is binding: a confirmation, never a refusal.
`[DB-0818-09]` — an *implausible* instruction is written silently; only an *impossible* one is
caught, and that was luck. The calendar write path runs a conflict check and **nothing else**.

**Options rejected.** Filing `[DB-0818-08]` as a `.claude/backlog_inbox/` fragment — Mike challenged
it, correctly: the fragment path is real and the sync folds it in, but it lands in `## Inbox`, which
means *untriaged*, and an item awaiting his decision should not queue behind that. Written straight
into `## Later` § Decisions. Also rejected: building the offline shell and the psychiatric-medication
tier as quick wins — both need a deploy to confirm, and **deploy is Denied**, so confirmation could
not happen in the session making the fix.

**Two handoffs written rather than one, at Mike's request** — `2026-08-18-caching-fix-prompt.md`
(self-contained build, **run first**, depends on none of the decisions) and
`2026-08-18-decisions-and-diagnosis-prompt.md` (three decisions in the format he asked for, the
doubling with all four dead theories named, and the two untested items with tests that reach the
code). He caught that the first draft carried only the caching work and would have lost everything
else — *an item recorded only in a session narrative is lost.*

**Not deployed:** `f4cc812` and today's research guard. Mike deploys after this archive.

