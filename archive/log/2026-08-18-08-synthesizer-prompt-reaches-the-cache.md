### 2026-08-18, eighth (the app's own turns reach the prompt cache, and the brief's headline number was wrong) — `core/orchestrator.py`, `ROADMAP.md`, `81be0f7` — **pushed, not deployed**

**Incoming handoff:** `archive/handoffs/2026-08-18-caching-fix-prompt.md` — the interactive
Synthesizer path never hit the Vertex prompt cache. Reviewed in Fable, executed in Opus after the
review appended five binding findings to the brief. The review is the reason the build was a
one-line branch rather than a discovery exercise, and it is the argument for the split Mike then
adopted: **plan and review in Fable, build in Opus.**

**What shipped.** The streaming pipeline's `gemini` branch now calls `run_session_gemini_cached()`
and yields the reply as a single chunk *through the existing loop*. Verified live:
**`cache_read=19,157` of a 20,534-token Synthesizer turn — 93% served from cache**, where that
branch previously never reached `_get_or_create_vertex_cache` at all. No user-visible regression,
because the reply already arrived as one flush (a thinking model emits reasoning as a token class
carrying no `delta.content`). That conditional is written onto the branch, because a later reader
would otherwise take Option B as a ruling that streaming does not matter. **Option A — a
`generate_content_stream` sibling keeping `cached_content` — is unbuilt and is what closes
`[DB-0818-10]`.**

**The brief's headline number was wrong, and the correction is the session.** Its "46×" compared an
interactive median against a *scheduled* median of 495. Measured directly: scheduled Synthesizer
turns are **bimodal** — 19 near-empty (183–585) and 4 full-sized (21,417–29,292). The scheduled path
was never cheap *because it was cached*; its median was dominated by trivial runs. Real scheduled
turns always cost what interactive ones cost. **The defect was real and the causal story was not** —
the same failure mode the brief itself warned about, one file down.

**Two infrastructure facts established by running things, both of which had been silently distorting
readings.** `prompt_token_count` **includes** cached tokens, so a cached turn still reports ~20k and
caching is invisible in trace data. And **INFO lines never reach `journalctl`** — the units log
WARNING and above, so every turn under 8k tokens leaves no log record whatsoever. The Synthesizer's
apparent absence from the cache logs was partly an artifact of the second.

**A clinical gate failed once and was not accepted on a re-run alone.** `PH-MED-PIPE` returned three
lines of incoherent text in place of a missed-medication warning. Rather than assume ownership either
way: HEAD **3/3 PASS**, Option B re-run **3/3 PASS**, no reproduction. The trace shows why it was not
a code-path fault — that turn recorded **`think=0`** where every healthy turn thought 1,620–2,693
tokens, so a degenerate completion, not truncation. **A first hypothesis (exhausted output budget)
was killed by measurement**: `out+think` never exceeded 2,284 against a 4,096 ceiling. A second
inference — that the change had *doubled* the Synthesizer's input — was also wrong, and came from
comparing a grep-truncated line belonging to a different agent.

**Filed, then deliberately unfiled, on Mike's challenge.** The degenerate reply was written up as
`[DB-0818-11]` with a coherence-check proposal. Mike: *"If it was a one off, does it require
research so long as it doesn't happen again? … a coherence check should be something that either
can be done now, or shouldn't be done at all."* Both halves land — the research half was **an item
with no exit**, and framing the guard as an open question was a way of filing instead of deciding.
**Decision: do not build it.** A guard tuned on one unreproducible sample is likelier to suppress a
good reply than to catch a recurrence — the trade that kept `filter_output` tier 5 narrow. The three
A4 reports are committed so the observation survives with no open item attached.

**Costed at $2/$12, and it moves a decision in another window.** Per interactive Synthesizer turn:
**$0.0685 → $0.0397** (70% off the input line, 42% off the turn), assuming cached input at 25% of
input rate — a rate Mike did not supply and which was **not quoted from memory**. Cache *storage* is
excluded and is the swing factor, being an hourly charge on a cache held to midnight UTC regardless
of use. **The finding that matters: caching cuts the money case for trimming `synthesizer.md` by
4×** — a 30% cut was worth $11.49 per 1,000 turns before, and $2.87 after. The audit is still worth
running on adherence and instruction quality, but `archive/handoffs/2026-08-18-synthesizer-audit-prompt.md`
currently leans on cost and should be told. **After this fix output+thinking is 69% of turn cost, so
the next real lever is the thinking budget, not prompt size.**

**Rejected:** Option A this pass (correct end state, but its design constraint — tool turns blocking,
only the final turn streamed, so a fallback happens before the first byte — belongs with the A8
refactor that relocates the loop). Deleting the consumed handoff, since Option A is still owed from
it. `ROADMAP.md` § 5A carries a note that its Gemini row is temporarily untrue, so a routing
migration cannot silently restore or remove streaming.

