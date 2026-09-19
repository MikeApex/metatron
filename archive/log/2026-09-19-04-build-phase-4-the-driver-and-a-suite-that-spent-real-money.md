### 2026-09-19 (Build phase 4 — the driver walks the graph, and a test suite spent real money)

Phase 4 built: `core/build/{runner,brief,registry,coherence}.py`, `tools/build.py`, the two
read-only board scripts, and the wiring — `register_tools()` ×2, `_block_source` +1, four Build
agent names on `_ALWAYS_CONFIDENTIAL`, `core/actions.py` classification, `BUILD_PROPOSED` and
`BUILD_CHECK_FAILED` in the sync script, the `build_tick` `_DEFAULT_JOBS` entry (Red, prompted),
and the correction attribution. Four new suites, 86 checks; every prior build suite unchanged and
passing; `qa_sweep` 11/11. **Not committed, not deployed** — Mike's instruction was to stop at
the archive, and phases 1–6 reach the VM as one deploy.

**Three plan corrections recorded first, as v3.5, in the § 6 form.** Mike adopted all three with
one amendment. Their shape is not any of the three phase-3 rounds: **each is a claim the plan
made about a file nobody had opened.**

- **C1 — `tools/analytics.py` does not count dispatch per specialist.** § 14 said it did.
  `rollup_day()` walks the trace through `_walk_tools()`, which counts TOOL names; agent names
  are written on every `AgentRecord` and nothing counts them. `registry.py` counts from the trace
  files directly. **The A9 rollup is untouched** — its schema is gated on a review dated
  2026-10-01 whose first instruction is not to tune it against development traffic, and adding a
  field for one number would have started that review early on exactly that traffic.
- **C2 — the over-budget ask does not go through `tools/confirm.py`.** A card needs an
  `_EXECUTORS` entry or `POST /confirm` answers *"nothing here knows how to carry that out"* —
  `[DB-0815-03]` exactly. And an executor would make raising Build's own spend limit a **one-tap
  action**, in a design whose deny list exists so Build cannot raise its own ceiling. Mike's
  amendment: the approval is `cost.approve_limit()` **run on the VM over ssh, never from the Mac
  board**, because the ledger lives on the VM and the board reads it through a read-only fetch.
  Stated in the correction and in `build_board.py`'s usage text, so the command is found where
  the parked job is seen.
- **C3 — nothing granted `request_build` to the Coordinator.** § 2 says it is granted at Coord
  level; the routing bullet named the four Build agents and stopped. `allowed_tools` filters
  schemas, so the tool would have been registered and unaskable — the `c840415` lesson one layer
  along. Added to § 10 and to § 16's **phase 5** line, so the phase-5 prompt inherits it: the
  `coordinator.md` line and the grant must land together.

**Five defects found in this session's own code, four of them by its own tests.** Recorded
because the useful pattern is *where* they were:

1. **N10 had no artifact, so approving a job undid the approval.** `advance()` skips a node whose
   artifact is present; N10 wrote `brief.md` and no JSON, so after `approve()` set `executing`
   the next tick walked from the top, re-ran N10, and set the state back to `briefed`. N12 was
   unreachable and the approval was silently undone every thirty minutes, forever. **Every node
   that changes state needs something on disk saying it ran.**
2. **The brief's leak check could never fire.** `findings()` ran on the already-redacted body,
   which always reports clean. Split into `assemble() -> (raw, redacted)`; the check reads raw.
   A guard that cannot fail looks exactly like a guard that passes.
3. **A ledger row lost its `question_id` in the N5 merge.** `merge_code_block()` starts from the
   model's row and overlays only `CODE_WRITTEN_LEDGER_FIELDS`, which does not include the id — so
   a row the Librarian never saw merged anonymous, `answer_interview()` could not find it, and
   every REPAIR claiming to point at "the question that wasn't asked" rested on an id that was
   not there. N5 re-asserts it from the code row.
4. **A job at a gate accrued a stall attempt every tick.** A quiet heartbeat at `briefed` is a
   human, not a crash; the stale re-entry would have burned `MAX_ATTEMPTS` in under two hours and
   failed a job whose only offence was that nobody had read the brief. Stall re-entry is now
   runnable-only.
5. **`GATE_STATES` moved to `jobs.py`.** `tools/build.py`'s context block reads it on every user
   turn through `load_recent_context`; importing the runner for five strings would have put the
   writer, the registry, settle and the probe on the hot path of every ordinary session.

**The finding worth the most: the test suite spent real money and tripped the daily stop.** The
model stub calls `trace.record_turn_tokens()` and the runner writes a `RequestTrace` per tick —
both deliberate, because that is what makes the cost-seam and nesting assertions real rather than
simulated. Both end in **live** state. Fake tokens at 40k a call added ~13M tokens and **$12.53**
to this Mac's real daily total, crossed the **$15 daily stop**, and `check_before_session()` then
refused every subsequent node — so the suite failed 15 of its own tests by spending its own
budget, and would have blocked a real local session. 112 fake records also landed in
`data/personas/mike/traces/2026-09-19.jsonl`, which is what `turn_referent` reads as "the
previous turn". **The generalisable rule: a test that exercises a seam for real must stub every
live meter that seam ends in, and "the suite failed" is a weaker symptom than "the machine is
now blocked".** Both `spend_guard.record_tokens` and `check_before_session` are stubbed for the
module now, with one test driving the blocked path explicitly so it is still exercised. The
polluted spend file was moved to the session scratchpad (local sessions unblocked, confirmed);
**the trace file is in a Denied path — Mike deletes it**, his call this session, and the deny
refusing the move is the control working.

**Decisions and their reasons.**
- **`schemas.climb()` gained `inject=`**, a four-line additive change to phase-3 code. Every
  validator requires `job_id`, `manifest_fingerprint` and `upstream_fingerprint`, and no model can
  produce them; asking one to echo a digest is the `_AGENT_NAME_MAP` problem again. It refuses any
  field outside `CODE_WRITTEN_HEADER_FIELDS`, so the hatch cannot widen into supplying an answer.
- **`schemas.artifact_fingerprint()` is new and `manifest.fingerprint()` was the wrong tool** —
  it hashes source, capability and policy ids only, so every question set and every ledger would
  digest identically through it. An `upstream_fingerprint` that cannot tell two artifacts apart is
  worse than none, because it looks like provenance. Caught before it shipped, by reading it.
- **N8b re-reads its own plan through `build_planner`.** § 10 lists four agent files and none is a
  reviewer; the plan already calls N8b advisory and names § 6.5(a)–(c) as the enforcement. **Which
  agent file carries the N8b instruction is a phase-5 decision, not settled here.**
- **The two board scripts name what retires them**, per `.claude/rules/deploy.md`: nothing today —
  they are the bootstrap surface § 5 already calls "the primary interface during bootstrap" — and
  `tools.build.context_block()` growing into the conversational surface is what retires them.

**Believed true earlier and wrong:** the todo list said phase 4 owned five § 12 rows. It owns the
runner half of Restart, Budget, the nesting half of Trace contract, End to end, and the *mechanism*
behind Run ledger; the Book-rendering and post-landing halves are phase 7's and this session could
not have run them. Stated so they do not read as skipped.

**Commits: none.** Working tree carries phase 4 uncommitted, by instruction. **Deployed: NO.**
