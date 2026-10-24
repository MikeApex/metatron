# Replies that arrive — no hangs, no blanks, fewer rounds, a waking-day Today list

*Plan v2, 2026-10-24. Author: Opus 5.5 (Claude Code), in the task-ledger post-deploy session.
Review: Fable 5.1 (Mike: "Put together a plan, review with a Fable reviewer and proceed").
v1 → v2: nine review findings, all accepted — § 11.*

---

## 1. The need, measured

Mike: turns have been taking a very long time; one reply never came. Measured on live traces
(541 traces 09-25 → 10-24, plus today's), VM journal and `ss`, and a Mac-side A/B probe:

- **11:45 turn — the reply never arrived.** The Synthesizer's first Vertex call took **586 s** to
  return. No timeout exists on any model client (`core/orchestrator.py:3260`, `:3828`, `:4589`,
  `:4707`). The reply Mike saw came from the app re-sending after the restart.
- **12:06 turn — a blank reply after 9 min 14 s.** The Synthesizer spent all 8 rounds
  (`max_iterations=8`, `:4324`) on tool calls — `list_tasks` ×3, `update_task` ×3, `open_task`,
  `read_wisdom` — 16–89 output tokens per round, then fell out of the loop with `result=""`
  (`:4489`). 7 of 8 rounds were redundant: the Tasks block is already in its context, and the
  specialists had already filed the tasks in the same turn.
- **Tools are not the cost.** All eight tool calls together took 0.64 s.
- **Cost:** a normal reply ≈ $0.02; the 8-round turn ≈ $0.13 (each round re-sends the whole
  conversation — 246k input tokens). Rounds drive cost; stalls drive wait.
- **Vertex's median speed has not changed** (~8 s per 1k generated tokens on `gemini-3.8-flash`
  every day since 09-25). **The tail has:** calls ≥3× slower than their tokens predict ran ~0.4%
  of calls to 10-19 and ~2.5% since 10-20, and longer (133–586 s). All on the reasoning model.
- **Not our account or a setting (§ 7).** Forum reports of the same symptom on Vertex 3.8 Flash
  from 10-21; Google's DSQ doc says a 429 reflects shared load, not a project limit; the 10-23
  retention change post-dates the first stalls.

## 2. What changes for the user, and the bound that is actually promised

1. **No reply ever hangs or comes back blank.** Every model call has a timeout, a stalled
   round is retried once, and a turn that runs out of rounds or passes its 150 s soft deadline
   answers from what it has (§ 3.1). A single stall costs at most ~2.5 minutes, not ten. A strict
   ceiling over the whole turn is **not** promised — the design for one was withdrawn in review
   (§ 3.1). Typical turns are unchanged (~20–60 s).
2. Ordinary task turns take one or two Synthesizer rounds, not eight.
3. ✓ Today shows the waking day only; a longer view on request in conversation.
4. A dropped task carries a reason; "Done, but…" closes it and opens the loose end as a task.
5. The day boundary is local midnight, user-adjustable (§ 6.4 — its own step).

## 3. Reliability (Amber: `core/orchestrator.py`, `core/server.py`)

1. **Soft deadline, not a hard ceiling (v4 — round 3 withdrew the ceiling, R14–R17).**
   `run_pipeline_session_stream` stores `soft_deadline` on the bound turn, counted from when
   the message arrived: **150 s** for a user turn, 240 s for a scheduled one. Past it no new
   Synthesizer round starts and § 3.4 forces the reply — a real answer from what was done.
   **Withdrawn:** v3's server-side holding line that abandoned a still-running turn. With no
   per-persona lock, the abandoned turn keeps writing history, context and confirm cards into
   the user's next turn; the real reply had no delivery path to the device that asked
   (`message` excludes the sender; the client draws it as a foreign row); the scheduler's
   `send_one` would have recorded the holding line as the session's reply; and the deploy drain
   would kill the producer after the line had promised a follow-up. A true hard ceiling needs a
   per-persona turn lock first — not built here.
   **The bound that is actually delivered:** no call waits more than 75 s (Synthesizer) or 300 s
   (others) and no turn is blank. A single stalled Synthesizer call costs at most ~150 s
   (75 + 2 + retry); the theoretical worst case — every phase stalling at its ceiling — is several
   minutes, and is reported as that rather than promised away.
2. **Per-call timeouts, scoped per agent, set per request (not on the shared client — R8).**
   - **Synthesizer: 75 s** — the P99 of the month's single-round calls (692 calls: P50 6 s, P95
     37 s, P99 73 s; Mike: "set the timeout to the P99 of calls"). Passed as
     `http_options` on the Synthesizer's `generate_content_stream` config only.
   - **Every other agent: 300 s safety ceiling** — above every call observed in the month (max
     175 s), so no long scheduled job (Pattern Miner, evening close, Diarist) loses its tail; it
     exists only so nothing can wait forever. Applied as the client default on the native client
     (`:3260`, `:3828`) and both compat clients (`:4589`, `:4707`).
   - One constant each, beside `_SYNTH_THINKING_BUDGET`, with the measurement that set it.
3. **Retry is per ROUND, inside the loop, once (R3, amended in build — R13).** A retry in the
   wrapper re-runs `_run_gemini_native_stream` from round 1, re-dispatching every tool earlier
   rounds already executed — a duplicate write. *(Today's compat fallback has the same latent
   defect: "nothing emitted" is not "nothing done", because tool rounds emit no text.)* So:
   - A round whose `generate_content_stream` fails with a **capacity error** (timeout, 429, 503,
     dropped connection) **before that round produced any part** is retried once after 2 s
     (Google's DSQ guidance). Safe: none of that round's tools has run and nothing was shown.
   - Retry fails, or a capacity error mid-round → the loop ends through § 3.4/3.5 (no further
     model call, so straight to the fixed line or the cut line).
   - The wrapper's compat fallback stays for **non-capacity** errors only, and only while the loop
     reports **no tool dispatched and nothing emitted** (a `state` dict the loop fills). After a
     dispatch it never re-runs the turn: fixed line instead. Capacity errors never reach compat —
     it is the same Vertex pool, uncached, without attachments.
4. **Never a blank reply — in both the native stream and the compat stream (R3).** When rounds
   run out, the deadline's 150 s mark passes, or the loop ends with `result == ""`: one final
   call with a user-text part (*"Your tool budget for this turn is spent. Reply to the user now
   from what has been done. Do not call tools."*), and any function calls it returns are not
   executed. If that is empty or fails: the fixed line *"I did what I could on that, but couldn't
   finish the reply — ask me again if you need the details."* Mirrored in the non-streaming twin
   `_run_gemini_native_loop` and in `_openai_compat_stream`.
5. **Cut mid-reply (R8).** If a round times out after text has streamed, the text stays and one
   line is appended: *"(I lost the connection partway through — ask me to finish if you need the
   rest.)"* — never silence, never a duplicate.
6. **Synthesizer round cap: 4** (from 8; code only). § 3.4 means the cap yields a reply.
   `synthesizer.md`'s "3-round" text is **not** touched: it is the `run_subagent` follow-up chain
   limit (`CHAIN_LIMIT_REACHED`, line 145), a different rule that `[DB-0804-02]` keys on (R9).
7. **Tests** (new `tests/test_native_stream_limits.py`, fakes only, live meters stubbed):
   tools-only fake → ends with text in ≤ 4 dispatches; past the soft deadline → no new round,
   forced reply; a non-capacity error after a dispatch is not re-raised (no turn re-run);
   429 then success → exactly one
   retry, no compat call; timeout after text → text kept + the cut line; compat stream that ends
   on a tool call → forced reply.

## 4. Fewer rounds (Red: `config/agents/synthesizer.md`, prompts Mike)

1. **Stop redundant work.** The Tasks block and SPECIALIST OUTPUTS are authoritative for this
   turn: do not call `list_tasks` to re-read what the block shows (only for ids not shown, or a
   longer horizon), and do not repeat a task write a specialist reports as done. This alone makes
   the 12:06 turn one or two rounds.
2. **Batch independent calls.** When several tool calls do not depend on each other's results,
   issue them in the same response — the loop already runs them concurrently (`:4474`).
3. **Withdrawn from v1: delivering the reply before its writes run (R1, R2).** The model must see
   each write's result before it speaks: confirm-gated tools (`send_email`, `write_contact`,
   `write_agent_config`, …) return `PENDING_CONFIRMATION`, ledger writes can return `error:`, and
   neither the post-turn truth check (it keys on a write tool's *name*, not its result) nor the
   transport (the client closes the bubble on `done`) could correct a reply that had already said
   "done". Done-means-done outranks one round.
4. **Not proposed here:** lowering `_SYNTH_THINKING_BUDGET` — the largest latency lever on a
   normal turn, traded against quality; a separate measured session (§ 9).

## 5. "Run what isn't reply-dependent after the reply" — what that honestly covers

1. **Inside the Synthesizer:** nothing safely, per § 4.3 — every tool result can change the reply.
2. **Specialists:** not detached — the reply has to say what was done.
3. **Post-reply bookkeeping** (`persist_context_block`, `_close_turn_bookkeeping`; after the text
   has streamed, before `[DONE]`). On the WebSocket path the app uses, `done` is sent only after
   the producer finishes (`core/server.py:1036`), so moving code after the final yield changes
   nothing visible (R6). To make it real: the server sends `done` when it reads `[DONE]` and
   awaits the producer afterwards; and because **no per-persona turn lock exists**, the next
   turn's context load waits on a per-persona `threading.Event` the bookkeeping clears when done
   (bounded wait, 5 s, then proceeds and logs). **Gated on measurement:** one trace field per
   post-stream phase; built only if they exceed 0.5 s, otherwise recorded as measured-and-left.
4. Measure the ~7 s spent outside agent calls (mostly pre-Coordinator context load) with the same
   per-phase fields; act in a later session if one phase dominates.

## 6. Today list, completion options, stretching, day boundary

1. **Waking-day default (`tools/obligations.py` `today_items`).** Shown: overdue; due today; daily
   habits; interval tasks due today; a weekly/monthly quota **only** on a preferred day
   (`on_days`) or when today is the last day the target can still be met; waiting tasks at
   check-back. Not shown: upcoming (the already-written filter), undated one-offs, quotas on
   ordinary days, any quota in its `partial` first period. The head layer's Tasks block is
   unchanged. Mike's 9-row list becomes 3–4.
2. **Longer view on request:** `list_tasks` gains `horizon: "today" | "week" | "month"` (absent =
   today's behaviour). Schema change → `tests/test_task_ledger.py` schema checks updated.
3. **"Done, but…" and reasons.** `update_task` gains `done_with_followup` (`followup` required;
   closes as done, opens a deadline task with that text, `source_id` = the closed id). `dismissed`
   already requires `evidence` — the change is in the wording asked for (a *reason*) and in the app.
   **Ordering (R7):** `/tasks/act` accepts an optional `reason`; with none (today's APK) the
   evidence stays "marked in the app", so the shipped Drop button keeps working until the new APK
   sends one. App: Done / Done, but… / Drop, the latter two opening a one-line field. APK rebuild.
4. **Day boundary, user-adjustable — its own step, after 1–3 (R5).** Not a shift of `_today()`.
   A single `_ledger_day(dt)` = local date of `dt − day_starts`, used by **every** date consumer
   in the module — `_today`, `update_task`'s `on_date` check (`:1057–1061`), `sweep` and its
   callers' `as_of`, `today_items`, `context_block`, raise stamps, history keys,
   `daily_task_counts`, `accountability_items` — enumerated by grep in the build and each pinned
   by a test at 01:30 with `day_starts: "04:00"`. The Tasks block states the boundary when it is
   not midnight ("the day runs 04:00–04:00"), so it cannot read as contradicting the clock line.
   Set via `update_task(task_id="settings", action="day_starts", note="04:00")`; the action enum
   and description in the existing schema change, no new tool, no new grant. Default `"00:00"` —
   behaviour identical to today until someone sets it.
5. **Stretching merged** — one task `Stretching`, habit `every: day, times: 2`; the two current
   tasks dropped with reason "merged". Done by Mike in conversation during the live checks.

## 7. Is the Vertex tail ours? (research)

- **Others have noticed (WebSearch, deny lifted for one search by Mike and restored; search-result
  summaries only — WebFetch stayed denied).** Google developer forum, Vertex `gemini-3.8-flash`:
  a 2026-10-21 thread reports "five 200s, five 429s, and one connection that was dropped after
  about 60 seconds" (discuss.google.dev/t/…/406896); an adjacent, likely same-week thread reports
  429/504 on `global` with requests running "50–53 seconds before failing" despite Priority PayGo
  (…/407766). The Developer API forum carries its own 3.8 Flash 429/503 and "extremely slow"
  threads, undated — so "Developer API unaffected" is our probe's finding, not a public one.
  **No Google Service Health incident found** for Vertex Gemini in October (the last found:
  2026-02-27, global endpoint, 429s). Google's DSQ doc: a 429 is "a reflection of the entire
  system's current load … not a fixed limit imposed on your project"; recommended handling is
  truncated exponential backoff, the global endpoint, smoothing spikes, or Provisioned Throughput.
- **A/B probe, Mac, 2026-10-24 ~13:40 BST** — identical generic prompt (no personal content),
  `gemini-3.8-flash`, thinking 2048, 180 s timeout, alternating, two rounds (6 + 8 each):
  **Vertex `global`, our project: 11 of 14 completed, 2 hung to the timeout, 1 × `429
  RESOURCE_EXHAUSTED`, and 3 completions took > 50 s (worst 104.8 s, 102.4 s of it before the
  first chunk). Developer API: 14/14, 4.0–6.5 s.** The excess is queueing before the first chunk,
  not generation. Both probes used our project, so "all of Vertex" vs "this project on Vertex"
  is not separable from here — the forum reports and the DSQ doc are what point to the former.
- **Options, for Mike (§ 9):** (a) retry once with backoff, as § 3 — no routing change; (b) on a
  second stall, fall back to a different **Vertex** model for that round (`gemini-3.5-flash-lite`,
  which never stalled in the month) — keeps the § 0 Vertex terms, lower reply quality; (c) fall
  back to the Developer API — **different data terms from the 08-26/08-28 Vertex ruling; a privacy
  decision**, and the forum shows it has its own 3.8 Flash trouble; (d) Provisioned Throughput —
  removes DSQ contention, priced per reserved unit per month, far above this project's run cost.

## 8. Files, tier, order — each step leaves the live system consistent

| Step | Files | Tier |
|---|---|---|
| 0 | commit the uncommitted `today_items` upcoming filter + its test (never deployed — `deploy.sh` ships git) | Amber |
| 1 | `core/orchestrator.py` (§ 3), `tests/test_native_stream_limits.py` — round cap 4 lands *with* § 3.4, so a cap hit always yields a reply | Amber |
| 2 | `config/agents/synthesizer.md` (§ 4.1–4.2 only) | **Red — prompts Mike** |
| 3 | `tools/obligations.py` (§ 6.1–6.3), `core/server.py` (`/tasks/act` optional `reason`/`followup`), tests | Amber |
| 4 | `static/index.html` (Done, but… / Drop with reason) + APK rebuild | Amber + (M) |
| 5 | § 5.3 measurement fields; the `done`-before-bookkeeping change only if > 0.5 s | Amber |
| 6 | § 6.4 day boundary | Amber |
| 7 | regression: `test_task_ledger`, `test_false_action_claim`, `test_action_provenance`, `test_tool_error_flag`, `test_client_outbox.js`, `scripts/check_agent_tools.py`, `bash scripts/qa_sweep.sh` | — |

Steps 0–3 are one deploy; 4 is the APK; 5–6 may follow in a later sitting. **Not touched:** the
uncommitted `tools/caldav.py` change (another session's — never staged here; every file diffed
before staging), constitution, persona data, routing files, `deploy.sh`.

## 9. Decisions for Mike

1. § 7 fallback — **recommended: (a) now**; revisit (b) if the tail persists past 10-31.
   **Ruled (Mike, 2026-10-24): (a).** Built as retry-only; no model or endpoint fallback exists.
2. Thinking-budget A/B (§ 4.4) — recommended as a separate measured session.
   **Ruled (Mike, 2026-10-24): yes, its own session.** `_SYNTH_THINKING_BUDGET` untouched (4096).

## 10. Cost

- **Build:** this session, Opus 5.5 on the subscription — ~1.5–2.5M tokens, mostly cache reads;
  Fable 5.1 review ~0.3–0.5M per round.
- **Run:** *lower*. Fewer rounds cut a task turn from ~$0.13 to ~$0.02–0.04. One retry on ~1–3%
  of Synthesizer calls (~$0.02 each); the compat leg it replaces re-sent ~246k uncached tokens, so
  stalled turns get cheaper too. The forced-reply call fires only where a turn would have been
  blank. Probe: < $0.05, once.
- **Ancillary:** none persistent. **Unseen:** an abandoned worker's in-flight Vertex call is still
  billed — bounded to one call per abandoned turn, and visible in the trace as discarded.
  `settings.day_starts` is one key in an existing file.

## 11. Review round 1 — Fable 5.1: nine findings, all accepted

| # | Finding | Resolution |
|---|---|---|
| R1 | Reply-before-writes: confirm-gated tools return `PENDING_CONFIRMATION`, so an already-streamed "done" gets retracted or contradicted | § 4.3 withdrawn |
| R2 | The truth check keys on tool names, not results, and the transport can't send a correction after `done` — a refused `update_task` would be announced as done | § 4.3 withdrawn |
| R3 | The wrapper's existing compat fallback re-runs the turn uncached; v1's retry + compat = ~227 s and the blank-reply fix lived only in the abandoned native loop | Retry in the wrapper only, no compat leg for capacity errors; forced reply in compat too (§ 3.3–3.4) |
| R4 | "About two minutes" was unachievable: budget checked only between rounds; httpx's timeout is per-read on a stream | Turn-level wall-clock deadline via a queue-consumed worker; promised bound 180 s (§ 2.1, § 3.1) |
| R5 | Shifting `_today()` breaks the clock invariant and misses `as_of` callers, `on_date`, history | `_ledger_day()` across every consumer, its own step, tested at 01:30 (§ 6.4) |
| R6 | Code after the final yield still delays `done` on the WS path; no per-persona lock exists | Server sends `done` on `[DONE]`; a per-persona Event; gated on measurement (§ 5.3) |
| R7 | Making Drop require a reason breaks the shipped app until the APK is rebuilt | Optional `reason` on `/tasks/act`; old app keeps working (§ 6.3) |
| R8 | A client-wide 75 s cuts 1% of every agent's calls; a mid-text cut left a truncated reply | Synthesizer-only 75 s per request; 300 s ceiling elsewhere; cut line (§ 3.2, § 3.5) |
| R9 | The "3-round limit" is the `run_subagent` chain limit, not `max_iterations` | Not edited (§ 3.6) |

**Round 2 (Fable 5.1):** R1–R3 and R5–R9 CLOSED; § 3.2, § 3.3, § 5.3, § 6.3 and § 8 AGREE. Three new:

| # | Finding | Resolution (v3) |
|---|---|---|
| R10 | A worker thread for the Synthesizer stream holds no persona scope, trace or turn — every tool call would fail or hit the wrong identity | No new thread: the deadline moves to the server's existing queue consumer; the pipeline stays on its producer thread (§ 3.1) |
| R11 | The 180 s ceiling only began at the Synthesizer; Coordinator/specialists ran unbounded before it (R4 moved, not closed) | The server's deadline covers the whole turn from receipt (§ 2.1, § 3.1) |
| R12 | A `run_subagent`/write already in flight at the ceiling still lands after the user is told the turn ended | The producer is not discarded: its real reply and any card arrive as a follow-up; the holding line promises that instead of claiming nothing happened (§ 3.1) |

**Round 3 (Fable 5.1):** R10, R11 and R13 CLOSED; R12 reshaped into four new findings, all from
abandoning a running turn — R14 the follow-up had no path to the asking device and collided with
the exchange's save; R15 an abandoned turn races the next one (no per-persona lock); R16 the
scheduler would record the holding line as the session's reply; R17 the deploy drain kills the
producer after a follow-up was promised. **Resolution: the hard ceiling is withdrawn (§ 3.1); a
soft deadline inside the pipeline replaces it.** § 3.2–3.6, § 6, § 8 AGREE.
