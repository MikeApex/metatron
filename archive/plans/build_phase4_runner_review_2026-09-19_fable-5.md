# Build phase 4 — review of the runner, by running it

**Reviewer:** Fable 5.1, 2026-09-19. **Scope:** the uncommitted phase-4 diff (`git diff` on
`core/{actions,orchestrator,scheduler,server,trace,build/jobs,build/schemas}.py` and
`scripts/sync_dev_backlog.py`, plus untracked `core/build/{runner,brief,registry,coherence}.py`,
`tools/build.py`, `scripts/build_{board,brief}.py`, `tests/test_build_*.py`) against
`archive/plans/build_vertical_plan_2026-09-18.md` § 3, 5, 7, 8, 12, 14, with the three v3.5
corrections read as adopted. **Method:** every claim below was produced by running the code, not
by reading it. Probes reuse the writer suite's real git fixture repo and the fixture persona
`mike` under it, with the model stubbed exactly as `tests/test_build_runner.py` stubs it and both
live meters stubbed; **the real writer and the real `verify.run_all()` sweep ran in the loop**
(18 checks, ~10 s per landing). Probe scripts live in the session scratchpad and are described
beside each result so they can be rebuilt. No file outside this one was edited. Baseline before
probing: runner 38/38, registry 15/15, coherence 19/19, brief 14/14.

*Note for whoever commits: the working tree now also carries `.gitignore`, `android/**`,
`scripts/check_apk_sync.sh` and `tests/test_turn_source_marker.py` changes that were not there at
session start and are not phase 4's — another chat is in this tree. `git diff` each file first.*

---

## Part 1 — What the ten probes established

| # | Brief | Result |
|---|---|---|
| 1 | One job, every node, to `landed` | **Landed**, real writer + real verify 18/18. Node outputs in Part 3 |
| 2 | Second and third capability | All three land; registry 3 rows, tier 3 of 4; valid-name line carries each display exactly once; name map, confidential list and domain map correct; same-gap re-file refused as `landed 0d ago`; a fourth record reusing `Home Care` refused at N7 by the writer's peer rule. **Coherence input is empty** (D5) |
| 3 | `kill -9` mid-N4, restart, tick | Resumes at **attempt 2**, re-runs only N4, durable spend rows `[N2, N4]`, no duplicate artifact, no `.tmp`; a further tick does not bump the attempt |
| 4 | Failing check | Revert leaves the overlay exactly as before (`0 restored, 4 removed`), journal renamed, `BUILD_CHECK_FAILED` written, failing output carried in `verification.json`; a forged journal line naming the constitution → `SKIPPED`, **blocked flag raised, constitution untouched**; a crash between apply and verification re-applies and still reverts clean. Two defects beside it (D6, D11) |
| 5 | Budget | Limit 0.01 parks at N4's pre-node gate, no `brief.md`; `resume()` refuses while over; a tripped daily guard flags `blocked`, state untouched, zero calls, clears on the next node. `_run_single_agent` never calls `_spend_gate()`, and a pause-text reply fails validation rather than landing. **One defect** (D2) |
| 6 | `request_build` | Seven null-ish gaps refused; duplicate refused at `proposed`, at `landed` 13 d (allowed at 15 d), at `failed` 71 h (allowed at 73 h); `max_proposed` refuses the 13th; `max_open_jobs` the 4th open; `max_jobs_per_day` the 5th of the day |
| 7 | REPAIR hook | Three real `write_quality_event` corrections against a registered capability file one `repair` ticket at `proposed`; the same events file nothing again; a tracked specialist files nothing; N1r's dossier carries the origin job's Question Set (q1–q3) and Answer Ledger (3 rows). **Two defects** (D3, D7) |
| 8 | Coherence validation | One-id overlap, missing artifact, empty detail, invented kind, empty id, non-object → each rejected with its reason; `orphan` with one id accepted. **The model's reply never reaches it** (D4) |
| 9 | Trace | Each tick is one `RequestTrace`, `is_proactive`, `pipeline` of exactly one `build` record with the agents in `subagents` — the shape `metatron_monitor.py:745-749` walks. The Book itself was not opened; rendering is phase 7's criterion and stays unverified here |
| 10 | Empty queue, paths | `nothing runnable (0 job(s))`: zero calls, zero traces, zero spend-guard calls. Nothing new under the real repo, `git status` unchanged. Every fixture write is under `data/personas/mike/build/{jobs,overlay}` or the four homes § 5 names (`ledger.jsonl`, `registry.jsonl`, `logs/quality_events.json`, `traces/`); none in `git ls-files` |

---

## Part 2 — Defects, ranked by cost of being wrong

**D1. `refuse()` reverts and abandons ANY job — including a landed one — and the registry keeps
saying `landed`.** `approve()` and `accept()` check the state; `refuse()` does not. Probe: land
`home_care` (probe 1's path), then `refuse(job)` → `abandoned — reverted — 0 restored, 4 removed`;
overlay `capabilities/` is empty, `R.capabilities(live_only=False)` still `{'home_care': 'landed'}`,
coherence's code pass now reports `orphan home_care`. Also `proposed`, `queued`, `executing` →
`abandoned`. Reach: `build_board.py --refuse BLD-…` with the wrong id deletes a live capability
and its brief; the generated bytes are gone (they were new files, so the journal holds no
`bytes_before`). Cost: the one irreversible board command has no guard on it.

**D2. A job that crosses its spend limit during the Planner call is FAILED, not parked — and a
re-file is then refused for 72 h.** The pre-node gate is `>=` before the call; the call itself
can cross the line; N7 then runs `writer.apply(dry_run=True)`, whose `_job_gate` refuses on
`spend > limit`, and `_n7_planner` treats that refusal as a plan defect → rung 3 → `failed`
(terminal). Probe: `budget.per_job_usd: 0.10`, stub calls at $0.0375 → N4 admitted at $0.075,
N7 lands spend at $0.1125 → `N7 planner rejected after retry: the writer refuses this plan's
files: REFUSED — spent $0.11 against a $0.10 limit`; state `failed`, `cost.approve_limit()` has
nothing to release. The module header says a job "overshoots by at most one node"; the writer
gate turns that tolerated overshoot into a terminal state. With the $2.50 placeholder this is the
likeliest way run 1's budget question gets answered: by the job dying at the moment the number
proves wrong, with no `awaiting_approval` to approve.

**D3. Correction attribution blames whatever wrote the newest trace, and that is usually not the
turn being corrected.** `_corrected_agents()` reads `last_trace()` and drops only
`coordinator|synthesizer|build`. Probe: after a `build_tick` the newest record is the tick's →
`['build_inquiry', 'build_librarian']`; after a Diarist-only trace → `['diarist']`. The Diarist
is fire-and-forget on its own thread with its own `RequestTrace` (`core/trace.py`'s push_agent
comment), written after the turn it followed — so on an ordinary user turn the record "on top"
when the next correction arrives is plausibly the Diarist's, not the exchange. *Inferred from
trace.py's own comment, not measured on a live pipeline.* The tick trace also becomes
`turn_referent`'s "exchange immediately before this one" block for the next user turn. Cost:
REPAIR counts `source_agent ∩ registry`, so a mis-attributed correction never reaches three for
anything Build built — the trigger this attribution exists to feed is inert — and the backlog's
machine log gains `diarist`/`build_inquiry` signatures.

**D4. The `log` source — the primary corpus — probes as `error` on every question, on the real
tree too.** `manifest._SOURCES` fixes the probe call as `get_log_window(days=14)`;
`tools/pattern_miner.get_log_window(start_date, end_date, …)` has no `days` → probe records
`state: error, "probe arguments do not fit get_log_window"`, `data_available: False`. Probe 1's
N3 row q1 and a direct `probe("log", "mike")` against the real persona tree. Phase 2's defect,
found by phase 4's first real walk — and it is the plan's "N3 is the highest-value node": every
question naming `log` reaches the Librarian as *"the code could not read the logs"*, and settle
can never settle a log-backed single-point question by data.

**D5. Coherence cannot see a surface map, so its overlap detector never fires.** `_surface_of`
reads `row.surface_map` or `record.surface_map`; `record_landing()` does not write one and the
overlay record schema has no such field. Probe 2: `home_care` and `garden_care` both claim
`read` on `watering` in their plans → corpus `surface: []` for all three → `code_findings: []`.
§ 13.7's falsifiable example (*"both claim `create` on `plant_watering`"*) is the one comparison
the pass cannot make.

**D6. The coherence model pass drops every well-formed reply.** The prompt asks for *"a JSON
list"*; `_ask_model` runs the reply through `repair_json`, which extracts the first `{…}` from a
bare list and returns the first finding as a dict; `.get("findings")` → `None` → `validate_findings`
→ `"findings is not a list"`. Probe: bare list → `None`; fenced list → `None`; only
`{"findings": [...]}` — which the prompt does not request — returns the list. `model_ran: True`
with the rejection recorded, so the board reads as a review that found nothing.

**D7. A job parked above the ceiling at N12 is stranded after `resume()`.** `resume()` sets
`planning`; every node's artifact already exists so all are skipped; N12 requires `executing`;
`approve()` requires `briefed`. Probe 4E: `may_create_agent_files: false` → N12 `PARKED` →
`awaiting_approval`; flag raised, `resume` → `planning`; two ticks: `N1r … N10 skipped`, state
`planning`; `approve` → `at planning — [N9] approves a job at briefed`; `context_block` empty.
The `PARKED` message's *"raise the flag on the VM to proceed"* leads nowhere without ledger
surgery.

**D8. REPAIR files a new ticket for every correction after the third.** The gap text embeds the
count (`… answered wrongly 3 times …`), the fingerprint hashes the gap, so ×4 is a new
fingerprint. Probe 7: ×3 → `BLD-0919-02`, same events → nothing, one more → `BLD-0919-03 (REPAIR
home_care x4)`, both at `proposed` with different fingerprints. Nine more corrections fill
`max_proposed`.

**D9. The run line's `dispatches_expected_per_day` is the Coordinator's turns per day, not the
trigger's frequency, and it writes `0.0` where its own contract says `None`.** `_expected_dispatches`
returns `counts["coordinator"] / days` for any gap; on a persona whose only trace file is the
tick's own, `days == 1` and the figure is `0.0` — the "it never fires" verdict the docstring says
it must not give. Probe 1: `dispatches_expected_per_day: 0.0` on the registry row; probe 2: the
same on all three, then `refresh_run_counts` writes `actual 0.0` over the tick's own traces.

**D10. Two events in one trace collapse to one.** `write_quality_event` dedupes by event type
per `RequestTrace`. Probe 7c: two jobs at `executing` fail their checks in one tick → both
`failed`, **one** `BUILD_CHECK_FAILED`. Two `request_build` calls in one user turn → two tickets,
**one** `BUILD_PROPOSED`. The "second record until one earns trust" drops the second ticket in
exactly the turn a Coordinator files two.

**D11. A writer crash at N12 is read as a successful apply.** `apply()`'s exception path
returns `"{job_id}: writer failed and reverted — …"`, which starts with neither `PARKED` nor
`REFUSED`; N12 proceeds to the full sweep, and the board's `detail` ends as `verify: 1 of 18
FAILED — capability-tests | revert: nothing to revert`, hiding `writer raised: disk full`.
Probe 4C. End state is `failed` by accident (the writer had already set it), so the cost is a
wasted sweep and a wrong reason on the board.

**D12. Every documented VM command fails with `PersonaError` unless `METATRON_PERSONA` is in the
shell.** `build_board.py` (no args), `--tick`, and the `context_block`/docstring
`cost.approve_limit('BLD-…', 5.00)` all resolve the persona from scope or env, and none of the
usage text says `--persona`. Probe: `env -u METATRON_PERSONA python3 scripts/build_board.py` →
traceback; `--tick` → `build_tick: failed — PersonaError`; `--persona mike` → `No Build jobs.`
The ssh one-liner in § 8's C2 has the same shape.

**D13. [N6] is not reachable in conversation.** The context block for a `needs_interview` job
names the job and the gap but not the question; no `brief.md` exists for a parked job (the
writer refuses the write from that state, by design); `answer_interview_item` is granted to no
agent in either routing file. Probe 6: block = *"needs answers before it can be planned —
nothing owns it"*, question on disk only. Phase 5 owns the grant; the missing question is
phase 4's.

**D14. Small, each confirmed.** (a) `brief.md` is never updated after N10 — the `_write_brief`
calls at N12 and N14 are refused (state not writable), so the landed brief still says `State:
briefed` with no Verification section, and a revert deletes it (`brief.md survives the revert:
False`). (b) `_index_questions` passes `ctx.persona` into `add_question`'s `question_class`
slot (`runner.py:378`): under the scheduler's scope it indexes with `class: "mike"`; from the
board it logs *"question indexing skipped: No persona resolved"*. (c) `_reject`'s detail says
*"rejected after retry"* on the N7 dry-run path, where no retry ran.

---

## Part 3 — What each node produced on the fixture (probe 1, the only phase 1–2 coverage)

`request_build` → `BLD-0919-01` at `proposed`, `BUILD_PROPOSED` written; tick 1 walks past it.
After `queue`: tick 2 runs N1 → N5 as one trace (`build` root, `build_inquiry`, `build_librarian`
nested) and parks at [N6]; one answer releases it; tick 3 runs N7 → N10 (`build_planner` twice)
and parks at [N9]; `approve`; tick 4 runs N12 alone and parks at [N13]; `accept` → N14 → `landed`.
Spend rows `[N2, N4, N7, N8b]` at $0.0375 each, $0.15 total, priced through `spend_guard`.

- **N1 manifest** — 26 sources, `journal_range` and `conversations` unavailable (the two phase-6
  briefs, as designed), 20 tracked capabilities, 0 policies, fingerprint `dd1d1b68…`.
- **N2 question_set** — q1 intent→`log`, q2 surface→`wisdom`, q3 authority→`user`; `job_id`,
  `manifest_fingerprint`, `upstream_fingerprint` injected by code and validated.
- **N3 evidence** — asked 3, to Librarian 2, to interview 1; q1 `get_log_window` **`error`** (D4),
  q2 `read_wisdom` `no_data` 0 rows, q3 `needs_interview`.
- **N4 librarian** — 2 judgment rows (q1, q2); skipped entirely when a spine names only `user`
  (shipped test; re-confirmed).
- **N5 answer_ledger** — 3 rows, every `question_id` survives the merge, q3 later carries
  `user_answer` + `settled_by: interview`; `upstream_fingerprint` is the question set's digest.
- **N7 build_plan** — `home_care` agent, 3 files (agent `.md`, record `.yaml`, test `.py` in the
  job dir), `_dry_run: OK (dry run) — 3 edit(s) [agent_file, artifact, capability_record]`.
  *Note for phase 5:* the record must arrive inside `files[]` with a correct `agent_sha256` and
  the real `job_id`; nothing in the runner computes either. The stub did.
- **N8 estimate** — `usd 0.0375, spent 0.1125, limit 2.50 (placeholder), calls 3,
  dispatches_expected_per_day 0.0` (D9).
- **N8b review** — advisory text stored (the stub returned the plan; a real reviewer file is
  phase 5's open question).
- **N10 brief** — 87 lines through the writer, `leaked: []`, no fixture profile value
  (`Prudential Apex`) in the body.
- **N12 apply+verify** — overlay gains `agents/home_care.md`, `capabilities/home_care.yaml`;
  4 journal entries (the brief plus three files); verify 18/18 including the four `:overlay`
  passes and the capability's own test.
- **N14 close** — registry row v1 with run line `blocking / 8000 ms / expected 0.0 / actual None`;
  tier 1 of 4; `docs/BUILD_REGISTRY.md` render carries no `one_line`.
- **Seams after landing** — `load_agent("home_care")` serves the overlay file; the assembled
  Coordinator prompt carries `"Home Care"` once; name map `home care → home_care`.

---

## Part 4 — Held, and worth keeping as a list

kill -9 resume · revert byte-exact and journal renamed only when nothing was skipped ·
`SKIPPED` keyed by clause · pre-node budget gate · daily guard → flag not state · null-ish gap
refusal · all three dedupe windows · all three caps · REPAIR ×3 bar, signature collapse, dossier
· coherence finding validation · one trace per tick, agents nested · empty tick at zero ·
no write anywhere in `git ls-files`, none under the real repo · scheduler runs function jobs
sequentially on its main loop (`schedule.run_pending()`), so a tick cannot re-enter a job
underneath itself — the heartbeat's only job is the attempt bump, which is what it does.

On the writer's hazard note: confirmed as stated. Today `resolve_model("build_inquiry")` raises
because no routing entry exists, so an un-stubbed `advance()` fails before any provider is
reached; the moment phase 5 adds the four routing entries that protection is gone, and the
suite header is the only guard.

---
---

# Part 2 — Re-check after round 1 (working tree, 2026-09-19, later the same day)

*Parts 1–4 above are the first review. This is the re-check after Mike's session fixed all
fourteen on the working tree. Same reviewer, same method: every round-1 probe script re-run
**unchanged** against the fixed tree, each on a fresh fixture copy, then one probe per fix.
Baseline before probing: runner **56/56** (+18), coherence 24/24 (+5), jobs 21/21 (+1), probe
41/41 (+3), writer 36/36 (+3), registry 15/15, brief 14/14, manifest 16/16, `qa_sweep` 11/11.*

## Nothing that held was reopened

All ten round-1 probes still hold on the fixed tree: one job to `landed` through the real
writer and the real 18-check sweep; three capabilities spliced once each into the valid-name
line; `kill -9` resumes at attempt 2 with no duplicate call or artifact (*note: the driver's
poll read a stale ledger from round 1, so this run's kill landed between N2 and N3 rather than
mid-N4 — round 1 covered mid-N4, and the resume held either way*); a failing check reverts
byte-exact with the `SKIPPED` clause raising the flag; the daily guard flags and clears; seven
null-ish gaps refused; all three dedupe windows and three caps; the REPAIR bar, dossier and
signature collapse; coherence finding validation; one nested trace per tick; empty tick at zero;
nothing new under the real repo and nothing under `git ls-files` (one new fixture write:
`build/index/`, which § 14 names and which is the index fix below working).

## The fourteen, each closed or open

| # | Defect | Status | Probe output |
|---|---|---|---|
| D1 | `refuse()` reverts any job | **Closed** | `refuse(landed)` → *"is landed — a terminal job cannot be refused … that is a retirement, not a refusal"*, overlay and registry intact, coherence reports nothing; `proposed`/`queued`/`executing` → *"refusing is for a job waiting on you at ['briefed', 'verifying']"*, state unchanged; `failed` → terminal refusal; `briefed` → `abandoned — 0 restored, 1 removed`; `verifying` → `abandoned — 1 restored, 4 removed`, overlay empty |
| D2 | Limit crossed during a call fails the job | **Closed** | Limit 0.10 → `N7 planner parked`, `awaiting_approval`, detail *"spent $0.1125 against a $0.10 limit"*, `resume_to: planning`; `approve_limit` + `resume` → *"resumed at planning"* → `briefed` with no repeated call. Same shape crossing during N2 (`resume_to: inquiry`) and at N8's estimate. Limit 0.01 now parks at **N2 post-node** — "overshoots by at most one node" is literally true; the dry run is no longer budget-gated |
| D3 | Attribution blames the newest trace | **Closed for `_corrected_agents`, one remainder** | Exchange (`coordinator`, `home_care`, `synthesizer`) then a Diarist-only trace then a tick then a scheduled run → `['home_care']` every time; a nested specialist under the Coordinator → `['garden_care']`; no user exchange on disk → `[]` (falls back to `coordinator`). **Remainder:** `tools/turn_referent.context_block()` still presents a `build_tick` trace as *"the exchange immediately before this one"* (its `is_proactive` line says *"a scheduled run"*) — not a phase-4 file, but the tick's trace is phase 4's. Observation, by design: a correction of a **scheduled** session's specialist is skipped as proactive and falls back to `coordinator` |
| D4 | `log` source probes as `error` | **Closed** | All 26 manifest sources probed on the fixture persona: no `error` state anywhere; `log` → `no_data` with `{'start_date': '2026-09-05', 'end_date': '2026-09-19'}`; on the real persona tree `log` → `no_data`, `calendar` → `data 1`, `memory` → `data 8`. The seven outbound feeds report a new `live` state with **empty probe args — no call is made**; `settle` routes a live-source question to the Librarian as residue rather than settling it on a zero row count |
| D5 | Coherence sees no surface map | **Closed** | Registry row now carries `surface_map` triples; probe 2's corpus lists them and the code pass returns `overlap garden_care ↔ home_care in surface_map — both claim read on watering as in_scope` |
| D6 | Model reply dropped by `repair_json` | **Closed** | `_ask_model` on a bare list, a fenced list and a `{"findings": …}` object → `list of 1` each; prose → `[]`; `review()` with a bare-list reply: `model_ran True, rejected []` |
| D7 | Ceiling park strands at `planning` | **Closed** | N12 `PARKED` → `awaiting_approval`, `resume_to: executing`; flag raised, `resume` → *"resumed at executing"*, next tick → `N12 apply+verify gate`, state `verifying`, context block says accept or refuse; `accept` → `landed`. A stale `resume_to` is cleared by the next plain transition (`executing` → `None`) |
| D8 | REPAIR re-files per correction | **Closed** | ×3 → `BLD-0919-02`; ×4 → `[]`; ×5 → `[]`; one ticket, gap without the count, count in `trigger` (*"seen x3 in 14d"*). After that ticket `fails`, the 72 h dedupe holds — as designed |
| D9 | Expected dispatches = turns/day, `0.0` for None | **Closed** | `dispatches_expected_per_day: None` on the estimate and the registry row; `--run-cost` prints `expected —`. *Minor, left:* `refresh_run_counts` on the landing day counts the tick's own trace file as one day and writes `actual 0.0 over 1d` — the landing-day figure is a tick, not a day |
| D10 | Same-trace events collapse | **Closed** | Two jobs failing checks in one tick → two `BUILD_CHECK_FAILED`; two `request_build` in one user turn → two `BUILD_PROPOSED` |
| D11 | Writer crash read as apply | **Closed** | `_apply` raising → `N12 apply+verify failed`, detail *"writer failed and reverted — RuntimeError: disk full"*, no `verification.json`, no sweep run |
| D12 | VM commands need an unstated persona | **Closed** | Board and brief with no persona → *"No persona is bound. Pass --persona mike, or export METATRON_PERSONA=mike"*, exit 2, no traceback; `--persona mike` → the board. The `resume()` refusal and the context block carry `METATRON_PERSONA=mike` on the `approve_limit` one-liner |
| D13 | [N6] unreachable in conversation | **Closed for the question; grant is phase 5's** | Context block: *"needs answers before it can be planned — nothing owns it / `q3` What is decided here versus surfaced?"*. `answer_interview_item` is still granted to no agent in either routing file, which the plan's C3 puts in phase 5 |
| D14 | Small three | **Closed, one nit** | (a) `brief.md` after landing carries the Verification section and survives a revert (`True`); *nit:* its State line reads `executing`, because the write now precedes the move to `verifying`/`landed`, so the landed brief never says landed. (b) Index written with the explicit persona, no scope: `build.faiss` + `metadata.json`, classes `intent/surface/authority`. (c) N7's dry-run refusal reads *"rejected"*, not *"rejected after retry"* |

## New, from this round

**N1. The landed brief says `executing`.** The fix writes the brief before the state moves so
the writer admits it, which means the final document records the state it was written from,
not the one the job reached. Cosmetic; `build_brief.py` re-renders fresh. Left as a nit rather
than a defect.

**N2. `turn_referent` still reads the tick's trace as the previous exchange** (D3's remainder,
above). The probe: write a tick trace, call `context_block()` → the block opens *"The exchange
immediately before this one … This was a scheduled run"*. Reach is one user turn after a tick
with work, and only the header lines; but the plan's "the tick is one request" now has a reader
that treats it as a conversation.

**N3. Landing-day run counts** (D9's minor, above).

Nothing else new. Every write is still under the persona tree; the real repo is untouched
(`git status` unchanged before and after); no probe bought a token.

---
---

# Part 3 — Re-check after round 2 (working tree, 2026-09-19, evening)

*Round 2 fixed the three items Part 2 left. Same reviewer, same method: every round-1 **and**
round-2 probe re-run unchanged on fresh fixture copies, then one probe per fix. Baseline:
runner **59/59** (+3), registry **18/18** (+3), jobs 21/21, coherence 24/24, probe 41/41, writer
36/36, brief 14/14, manifest 16/16, `tests/test_turn_referent.py` 22/22, `qa_sweep` 11/11.*

## Nothing that held was reopened

All fourteen round-1 closures hold under their own probes on this tree — `refuse()` guard,
post-node budget park with `resume_to`, attribution, all 26 sources without an `error` state,
surface triples and the overlap finding, coherence parse, ceiling resume, REPAIR once at ×3,
expected dispatches `None`, two events per two facts, writer crash reported as itself, board
and brief persona message, interview questions in the context block, index with explicit
persona — and every round-1 "held" claim still holds: one job to `landed` through the real
writer and the 18-check sweep, three capabilities spliced once each, `kill -9` resume at
attempt 2 with one call, revert byte-exact with the `SKIPPED` flag, all dedupe windows and
caps, dossier, one nested trace per tick, empty tick at zero, nothing written outside the
persona tree or into the real repo.

## The three, each closed

| # | Item | Status | Probe output |
|---|---|---|---|
| N1 | Landed brief said `executing` | **Closed** | `brief.md` State line: `briefed` at N10, `verifying` after N12, `failed` after a failed check (and `build_brief.py`'s fresh render agrees), **`landed`** after N14 — each the state the job is *entering*, written while the writer still admits it |
| N2 | `turn_referent` read the tick as the previous exchange | **Closed** | Exchange → Diarist → tick on disk: block = *"The user said (just now): "water the plants?" / The reply began: "They were watered on Tuesday.""*, `_corrected_agents` → `['home_care']`; only a tick on disk → block `''`, attribution `[]`; no traces → same. One rule, `turn_referent.is_exchange()`, read by both callers (`_corrected_agents` imports `last_exchange`). **Design change to note:** a scheduled session now *is* an exchange for both readers — the block opens *"This was a scheduled run — the user did not speak in it"* and a correction after it is attributed to the specialist it dispatched (`['logistics']`), where round 1 skipped it. Consistent, and the better reading: the user can correct what a scheduled run said |
| N3 | Landing-day run counts wrote `actual 0.0 over 1d` | **Closed** | Landing day with three tick traces → *"no full day of use since landing — 1 count(s) left uncounted rather than written as zero"*, run line stays `None`; still `None` after a user exchange that same day (the landing day never counts). Landed yesterday, two dispatches today among three ticks → `actual 2.0 over 1d`; `dispatch_counts(after=…)` excludes the tick records from both numerator and measured days |

## New, from this round

Nothing. Every write is under the persona tree, the real repo's `git status` is unchanged
before and after, and no probe bought a token. The two things left open by earlier rounds are
both owned elsewhere and unchanged: `answer_interview_item` is granted to no agent (phase 5's
routing files), and The Book's rendering of a tick has not been opened (phase 7's criterion).
