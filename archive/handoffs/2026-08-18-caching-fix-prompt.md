# Handoff — the app's own turns never hit the prompt cache

**Read `SESSION.md` and `ROADMAP.md` first (`/metatron-code`). This file is the brief, not the plan —
verify every number below against the live VM before you change anything. Two of the three
hypotheses raised while finding this were wrong, both times because a cause was inferred from
timing, so nothing here is to be taken on trust.**

---

## The measurement

28 Synthesizer turns off the VM (`/monitor/traces?persona=mike`, 2026-08-16 → 08-18):

| | Median input tokens per turn |
|---|---|
| **`is_proactive: false`** — Mike in the app | **22,967** |
| `is_proactive: true` — scheduled | 495 |

Same agent, same model (`gemini-3.1-pro-preview`), same ~19,000-token system prompt. **46×.**
Eight interactive turns in 45 minutes of testing on 2026-08-18: **248,457 input tokens**, against
~2,400 had they been billed at the scheduled rate. Turns showing ~45,000 are the two-turn cases —
the whole prompt again on turn 2.

Prompt composition on the 16:48 turn (77,084 chars total):

| Share | Size | Section |
|---|---|---|
| **65%** | 50,703 | `config/agents/synthesizer.md` |
| 17% | 13,366 | persona config |
| 13% | 10,653 | recent context |
| 3% | 2,362 | conversation history |

`synthesizer.md` was 43,655 bytes on 08-08 and 51,086 on 08-16 — **+17% in eight days**, a little at
a time, unmeasured. Uncached, all of it is billed on every message Mike sends.

## The cause, and it is structural rather than recent

Two code paths reach the Synthesizer and only one of them caches.

- **Non-streaming** (`_run_single_agent`, line ~3356): `synthesizer` is in `_HEAD_LAYER_AGENTS`, so it
  goes to `run_session_gemini_cached()` → `_get_or_create_vertex_cache()` →
  `_run_gemini_native_loop(..., cached_content=...)`. **Cached.** This is the scheduler's path.
- **Streaming** (`_run_pipeline_session_stream_inner`, line ~4093): `synth_provider == "gemini"` →
  `_openai_compat_stream(system_prompt, ...)`. **The full system prompt on every request, and it
  never touches `_get_or_create_vertex_cache` at all.** This is the app's path — every turn Mike
  takes.

It was wired this way to get token-by-token delivery, which the native loop could not do:
`_run_gemini_native_loop` is `-> str` and calls `client.models.generate_content`, not the streaming
variant. **So the interactive path opted out of caching to buy streaming.**

**And it did not get streaming either.** Mike, live: *"the entire bubble publishes at once, not word
by word."* Confirmed — the reply is one flush. `_openai_compat_stream` yields `delta.content` the
moment it arrives (line ~3125) and the client appends per chunk
(`static/index.html:972`); both halves are correct. A thinking model emits reasoning as a token class
carrying no `delta.content`, so the wire is silent for the whole think (1,000–3,000 tokens today) and
the 130–260 output tokens then arrive in a burst. **Do not go looking for a bug in the streaming path
or the client — both were read and both are right.**

So the current state is the worst of both: **46× the input cost, and no streaming to show for it.**

## Options

**A — Stream from the native SDK, keeping the cache. The real fix.**
`google-genai` is 2.8.0 and `Models.generate_content_stream` exists (verified). Add a streaming
sibling to `_run_gemini_native_loop` — a generator that keeps `cached_content` — and point the
streaming pipeline's `gemini` branch at it. Gets caching **and** genuine token-by-token delivery.
Cost: a second copy of an agentic loop that carries tool dispatch, parallel `_PARALLEL_TOOLS`,
token-budget logging and `AI_TRACE` markers. **`_openai_compat_loop`/`_openai_compat_stream` are
already this exact pair, so the duplication has a precedent — and a warning: they have drifted before.**
Watch: Vertex rejects a request carrying `cached_content` together with `tools`/`system_instruction`,
which is why the cache bakes tools in (see `_get_or_create_vertex_cache`'s docstring).

**B — Route the Synthesizer's interactive turns to the cached non-streaming path. The cheap
mitigation, and it costs nothing perceptible *today*.**
One branch: in the streaming pipeline, call `run_session_gemini_cached()` and yield the result as a
single chunk. **The user-visible change is nil, because the reply already arrives as a single chunk.**
Saves ~46× immediately. It is a deliberate step backwards that becomes visible the day A lands or
the model stops thinking so long — so it must be recorded as temporary with the reason, not left to
be discovered.

**C — Cut `synthesizer.md`.** 65% of the prompt, and 51 KB of instruction for an agent that writes
three sentences is worth an audit regardless. But it is orthogonal: it reduces the bill on both
paths and leaves the 46× gap exactly where it is. **Not a substitute for A or B.**

## Recommendation

**B now, A next, C on its own clock.** B is one branch and buys back roughly two orders of magnitude
on the cost of ordinary use, with no user-visible regression *because streaming is currently
illusory* — that conditional is the whole argument and it must be written into the code comment, or
someone will later read B as a decision that streaming does not matter. A is the correct end state
and restores the thing B trades away. C is a separate audit with its own argument.

**Do not do B and quietly stop.** A is what makes B safe to have done.

## Verify before you build

1. **Re-measure the split yourself** — `is_proactive` true vs false, `total_input_tokens` on the
   `synthesizer` step. If the gap is not there, everything above is wrong.
2. **Confirm the cache is actually hitting on the scheduled path** rather than the prompt merely being
   smaller there — read `cached_content_token_count` (`cache_read` in the token log), not just
   `prompt_token_count`.
3. **`CLAUDE.md` § Infrastructure traps, 6:** Vertex will not create a cache below 4,096 tokens and
   **fails silently**. Any prompt-shrinking under C must re-check that `coordinator` and
   `synthesizer` stay clear of that floor — a month of silently uncached calls has already been paid
   for once.
4. **Regression gate:** `python tests/run_a4_safety.py --suite pipeline` (clinical substance must
   survive) and `python tests/run_knowledge_routing.py --persona danny_park` — the latter exercises
   `run_pipeline_session_stream`, which is the function being changed and the one a move here is most
   likely to break.
5. `bash scripts/qa_sweep.sh`.

## Scope

`core/orchestrator.py` only, plus tests. **Green/Amber tier — no persona files, no `routing*.yaml`,
no agent files.** Deploy is Denied: hand the commit back to Mike, do not attempt `./deploy.sh`.

## Related, do not fold in

- The zero-source refusal for `research_agent` (authorised by Mike 2026-08-18) — different file.
- `[DB-0818-08]` verified/stated/inferred provenance — his decision pending.
- Sentence-chunked TTS, which Mike asked for and which A makes worthwhile: with real streaming,
  speech can start on the first complete sentence. **Do not build it in the same pass** — it depends
  on A landing first.
