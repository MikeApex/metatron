# Build v4.11 — phase A handoff

*Worktree: `/Users/md-homefolder/Desktop/metatron-wt-v4a-package` (branch `wt/v4a-package`,
based on `505b254`). Patch: `archive/handoffs/2026-09-24-build-phase-A.patch`.
Nothing is committed, nothing is deployed, nothing user-visible ships.*

> **STATUS: phase A complete.** All ten steps done. The Red half landed in the main
> tree, the deletion followed it, and all six regression gates are green. One gate was
> run against a tracked persona rather than `mike` for a structural reason — see
> § The six regression gates.
>
> **Plus a sixth content gate, approved by Mike mid-phase and built here:** the TIER
> GATE (§ The tier gate, below).

---

## What shipped

### The new `core/build/` package — 16 modules

**Salvaged by copy** (§ 10's table, all nine rows):

| Piece | Where it now lives | What changed |
|---|---|---|
| Question Set / ledger-row / plan validators | `schemas.py` | the removed fields; **the compass-rule ordering is byte-identical** |
| the transcript fixture and its test | `tests/fixtures/inquiry_rsvp_2026-09-17.md`, `tests/test_build_spine.py` | three retired fields stripped; **every spine position untouched** |
| the id allocator | `ids.py` | re-pointed at the ticket store; replay-under-lock unchanged |
| Build's question index | `index.py` | store relocated to `data/build/index/<persona>/` |
| the constitution check | `constitution.py` | composes the ceiling from `gates.py`; one check removed (below) |
| the policy record shape and resolver | `policy.py` | home → `config/build/policies/{persona}/{id}.yaml`, tracked, YAML |
| the presence-check call table | `manifest.py`'s `_SOURCES` | **verbatim**, all seven D4 argument repairs and all seven `live: True` rows |
| the control layer | `driver.py` | `_ask()` became "name the step"; node order, `MAX_NODE_RETRIES`, the product cap, the artifact-is-cursor rule and `NodeOutcome` carried across |
| the deny list | `gates.py` | `DENY_PREFIXES` / `DENY_EXACT` / `DENY_GLOBS` verbatim |

The `_SOURCES` repairs were verified individually rather than assumed:
`log` → `{start_date, end_date}` + `probe_dates: 14` · `memory` → `{query: "day", k: 8}` ·
`archive` → `{category: "books"}` · `intake_queue` → `{domain: "logistics"}` ·
`agent_config` → `{agent_name: "coordinator"}` · `email` → `{count: 20}` · 7 live rows.

**Written fresh:** `tickets.py` `jobs.py` `tick.py` `manifest.py` `table.py` `brief.py`
`registry.py` `coherence.py` `gates.py` `verify.py` `driver.py` (+ `__init__.py`).
`doors.py` is phase B and is not written.

### Outside the package

- **`scripts/check_build_registration.py` — rewritten** as the tracked-file checker:
  routing parity, the Coordinator directory entry and valid-name list, knowledge domains,
  the registry row and run line, the deny list, the gitignore line. Asserts wiring
  **only for `landed` rows**, with `--capability` for the driver's scoped N13 run.
- **`scripts/check_scheduler_functions.py` — new**, wired as sweep check 12
  (`scheduler-functions-resolve`).
- **`tools/build.py`** re-pointed at `core.build.tickets`; `context_block` reduced to the
  filed-gap count.
- **`scripts/new_worktree.sh --sandbox`**: links `.venv` only, registers as
  `metatron-wt-build-<slug>`, refuses `--with-personas`.
- **`scripts/hook_subagent_gate.py`**: `BUILD_SANDBOX_PREFIX` skip in `_dirty_worktrees`.
- **`scripts/build_board.py` — rewritten**: read-only join of the fetched ticket file, the
  local job directories and the tracked registry, plus `--abandon`. The v3 write half
  (`--queue/--approve/--accept/--refuse/--resume/--tick`) is gone with the VM state it moved.
- **`config/modules/build.yaml` — rewritten**: caps + `api_allowance_usd_per_step: 1.00` only.
- **`.gitignore`**: one new line, `data/build/`.

### Deleted (step 9, after the Red half landed)

`core/build/{settle,condense,probe,cost,overlay,writer,runner}.py` — the seven the new
package does not reuse · the eight old suites
(`test_build_{brief,coherence,manifest,overlay,probe,runner,verify,writer}.py`) ·
`scripts/build_brief.py` · the four load seams in `core/orchestrator.py` · the
`domain_agent_map` seam in `tools/wisdom.py` · the per-job cost seam in `core/trace.py` ·
the `--overlay` flag on `check_agent_tools.py`, `check_rule_overlap.py` and
`check_knowledge_domains.py` · the four Build agent names in `_ALWAYS_CONFIDENTIAL` ·
`answer_interview_item` in `register_tools()` and `core/actions.py`.

**`core/build/` is now exactly 17 files: the 16 modules and `__init__.py`.**

---

## § 12 rows, with their output

All eleven suites run standalone (`python3 tests/test_build_*.py`). **236 checks, 0 failures.**

```
schemas      36/36 passed        gates        52/52 passed
spine        12/12 passed        coherence    20/20 passed
tickets      14/14 passed        wiring       19/19 passed
tick         14/14 passed        jobs         18/18 passed
driver       19/19 passed        table        13/13 passed
registry     19/19 passed
```

| § 12 row | Suite | Result |
|---|---|---|
| Schemas | `test_build_schemas.py` | 36/36 |
| Compass rule | `test_build_spine.py` | 12/12 — **turn 2 fails, turn 4 passes, unchanged** |
| Driver | `test_build_driver.py` | 19/19 |
| Sandbox and patch | `test_build_gates.py` | 52/52 |
| Wiring gate | `test_build_wiring.py` | 19/19 |
| Gates | `test_build_gates.py` | 52/52, incl. the tier gate |
| Tick | `test_build_tick.py` | 14/14 |
| Question table | `test_build_table.py` | 13/13 |
| Registry | `test_build_registry.py` | 19/19 |
| Registration check | `test_build_wiring.py` | 19/19 — incl. the staged↔landed pair on one tree |
| Implementer boundary | `test_build_schemas.py` + `test_build_gates.py` | both |
| Landing pre-checks | `test_build_gates.py` | 3 checks |
| Sandbox stop gate | `test_build_gates.py` | 3 checks |

The compass-rule pair, verbatim:

```
PASS  turn 2 (the filter) FAILS validation
PASS  turn 4 (the compass) PASSES validation
PASS  turn 2 fails on feasibility-before-intent, named as the inversion it is
PASS  turn 4's class sequence is non-decreasing, and reaches feasibility sixth
12/12 passed
```

---

## Findings — things the plan did not anticipate

Three real defects, each found by a test written for a § 12 row.

1. **The review's one send-back could never have fired.** The bound was expressed at N7, but
   N7's artifact exists as soon as the first plan is written — so the cursor skips N7 and the
   walk never reaches the check. Both job-level bounds now run *before* the node walk.
   *(`driver.py`; `test_build_driver.py` "a SECOND send-back parks the job for Mike".)*

2. **Channel (a) refuses the harness's own markers, and round 3 only fixed channel (b).**
   A `.claude/.session_state/` marker is not in `files[]`, so channel (a)'s "every changed
   path is in the implementer's half" rule refuses it on its own account. In *this* repo
   `.gitignore` carries `.claude/*`, so the porcelain never reports one and the hole is
   invisible — an ignore rule holding up a security property. `gates.HARNESS_MARKERS` makes
   the exemption explicit so channel (a) is correct whether or not that ignore rule survives.

3. **`artifact_path`'s "name contains a dot" suffix heuristic silently broke the send-back
   counter.** `build_plan.v1` contains a dot, so it was written with no extension, and
   `plan_versions()` — which globs `build_plan.v*.json` and *is* the counter — found nothing.
   Replaced with an enumerated suffix list plus a `write_plan()` helper.

Two smaller ones: `schemas.SchemaError` was raised with one argument in `climb(inject=)`, so
the guard raised `TypeError` instead of its own message (latent in v3); and `tick.py`'s
`datetime.utcnow()` is now the non-deprecated spelling of the same naive-UTC value, which it
must stay because the comparison is a string compare against what `tools/logger.py` writes.

### Where I departed from the plan, and why

- **§ 12's `.git/hooks` row describes a path that cannot exist.** It asserts a write to
  `<wt>/.git/hooks/pre-commit`. In a git worktree `<wt>/.git` is a **pointer file**, not a
  directory, so that path raises `NotADirectoryError`. The *defence* is right and still
  needed — the reachable attack is resolving `--git-common-dir` and writing to the main
  repository's hook path, which channel (c) refuses. The suite now tests the reachable form,
  plus a second check that overwriting the pointer file itself is refused by channel (b).
  **No mechanism changed; only the test's route to it.**

- **One constitution check was removed with the overlay, deliberately.** v3 asserted that an
  overlay record's `routing.cloud.model_ref` named a *sensitive* tracked agent, so a
  capability could not inherit `research_agent`'s decontextualised tier. § 8 retires
  `model_ref` outright, so there is no ref left to check. What replaces it is
  `check_build_registration.py`'s parity assertion plus Mike reading the routing entry in the
  diff. **That is weaker than a code gate, and is recorded here as such** rather than left to
  be discovered.

- **`answer_interview_item`'s removal moved from step 9 to step 5.** Step 5 removes it from
  `tools/build.py`, which makes `core/orchestrator.py`'s import fail immediately and takes
  `register_tools()` down with it. It is not one of the two Red edits, it was granted to no
  agent in either routing file, and nothing tracked ever reached it — so pulling it forward
  costs nothing the ordering was protecting. Also removed from `core/actions.py`'s action list.

- **The salvaged fixture lost three fields.** `candidate_sources`, `manifest_fingerprint` and
  `policies_consulted` are exactly what ruling 5 retires, and their *presence* is now a
  validation defect, so turn 4 could not have passed carrying them. The spine — every
  question, class and position — is byte-identical, and the fixture records the edit and why.

### § 10's acceptance criterion

*"Outside Build, the only behaviour that changes is the removal of the four seams' fallbacks."*
**Held.** The only other changes outside Build are this phase's own deliverables (sweep check
12, the worktree flag, the gate skip) plus the `answer_interview_item` removal above. All four
live seams were exercised and degrade open exactly as designed:

```
router _load_routing: 18 agents      load_agent(coordinator): 23049 chars
_overlay_confidential(): []          domain_agent_map: 12 domains
filter_output clean: 'Your plants are fine.'
```

---

## The tier gate — the sixth gate, added mid-phase

**What it refuses.** A capability whose plan reads a `kind: history` ledger row through
`information_sources[]`, or decides any `judgment` row, routed to the **bulk tier** in
`routing_cloud.yaml`.

**Why it is not a privacy control.** Everything routes to Vertex Gemini under the
2026-08-26 ruling and the `mike` persona is kept thin. What it guards is **judgement
variance on a standing judgement over a history** — and ROADMAP § D2 has that measured, not
assumed: `relationships`, on the bulk tier and commented "no clinical stakes", was handed
near-match evidence twice on the same class of case four minutes apart and gave opposite
answers. Same model, same evidence.

**That is why it is a gate and not a test.** A ceiling shows up on the first clean run;
variance does not show up on any single run, so a passing acceptance proves nothing about
it. Only refusing the configuration can. And run 1's own capability is this exact shape —
`home_care` is a last-done date derived from a log, and § 3 names the Coordinator's
recorded failure on that request as doing the arithmetic itself from stale context. An
under-tiered `home_care` reproduces the defect it was built to remove, with routing parity,
the agent file, the registry row and the constitution check all green.

**Both implementation constraints held:**

1. **The bulk tier is read from `quick_override` in the routing file**, never a literal.
   That is the same anchor `core/router.py` resolves `complexity: quick` through, so the
   gate and the router cannot disagree about which tier a model is on. A test asserts the
   fixture's model id appears nowhere in `gates.py`.
2. **It runs at N13, with the other Red-reading gates** — `verify.content_gate()`, not
   `verify.code_checks()`. At N12 the sandbox holds no routing entry, so the gate would
   match nothing and pass on every capability. A test asserts `check_tier` is in the first
   and not the second.

**The local-mode half is deliberately not built**, and `gates.py` carries a block stating
the rule that is missing (a generated `routing.yaml` entry reading persona data must carry
`local: true`), why parity checking cannot catch it (the two files legitimately differ on
provider, model and the flag), why it is not built (`DEPLOYMENT_MODE=cloud`, Ollama unused
— a control for a path nobody runs rots unexercised), and **what would make it live again**
(any return to local mode, or a second deployment using it). A test asserts that block is
still there, so it cannot be tidied away into reading like an oversight.

Eleven assertions in `test_build_gates.py`, including the one Mike named: the same plan
fails on the bulk tier and passes on the reasoning tier, with nothing else changed.

---

## The Red stop, and what followed

**Reached and reported at step 8.** No Red file was edited by me at any point.

Mike landed both edits in the main tree: `core/scheduler.py`'s `build_tick` now names
`core.build.tick.build_tick`, and `_merge_overlay_routing` is gone from `core/router.py`.
I copied those two files into the worktree — reproducing an approved change, not authoring
one — and **excluded both paths from the patch**, which carries only my half. Confirmed:
the patch has no `diff --git` header for either file.

`scheduler-functions-resolve` went green the moment the scheduler edit was in.

### One real break the deletion caused, and how it was caught

**`_AGENT_NAME_MAP` went out with seam 3.** It was moved to module level on 2026-09-19 so
the overlay validator and the seam could both read it, so it sat inside the seam's block
and read like seam machinery. It is not: `_dispatch_from_coordinator` has always needed it
to turn the display name the Coordinator answers with back into an agent name, and that is
true of the tracked roster with no Build in the picture.

**`py_compile` accepted the removal. `qa_sweep` was green. The knowledge-routing gate
crashed with `NameError`.** That is the sweep header's own warning happening verbatim — "a
green sweep means nothing statically detectable is broken, never that this works" — and it
is the second time in this repo's history that a stale name passed the sweep and broke a
live path. Restored with a comment recording it, so the next person reading that block
knows why a name map sits in the middle of a section about a retired seam.

I then diffed the module-level symbol set of every touched file against `HEAD` and checked
each removed name for live references. Everything else removed is genuinely unreferenced;
the only two hits were a same-named local constant in my own new script and a mention
inside a comment.

### One guard transferred rather than dropped

`check_agent_tools.py --overlay` made class 2 (an agent file naming a tool it was not
granted) **fatal** for a generated agent, on the reasoning that no human will come along
and add the grant. That branch worked only while generated agent files lived somewhere the
script could tell apart by path; they are ordinary `config/agents/*.md` now, so the script
cannot distinguish them and must not pretend to. **The blocker moved to Build's N13**, via
`gates.check_told_not_granted()` through `verify.content_gate()`, where the capability
being checked is known by name. Recorded in a comment at the site.

---

## The six regression gates

| Gate | Result |
|---|---|
| `tests/test_a4_complexity_threading.py` | **PASS** — the flag reaches the router, the invalid combination is refused |
| `tests/test_turn_referent.py` | **22/22** |
| `tests/test_synth_module_injection.py` | **16/16** |
| `tests/run_knowledge_routing.py --persona danny_park` | **GATE PASS** — both passes; "a stored fact reached the reply `['egg', 'toast']`", and the counter-test still dispatched `physical_health` |
| `./scripts/qa_sweep.sh` | **12/12** — `agent-tools, confirm-executors, personas, rule-overlap, project-log, py-compile, backlog-ids, dev-markers, claude-md-claims, deploy-lock, build-registration, scheduler-functions-resolve` |
| Clean server start + one full pipeline turn | **PASS** — see below |

**The server gate, and the one deviation.** `core/server.py --persona mike --port 8042`
starts clean and `/health` returns `{"status":"ok"}`. **The pipeline turn was run as
`danny_park`, not `mike`, and that is structural rather than a shortcut:**
`config/personas/mike.md` and `config/personas/mike/` are gitignored and VM-only, and
`new_worktree.sh` documents at length why a worktree must never carry them — so
`--persona mike` raises `Persona not found` in *any* worktree, before this phase and after
it. Copying them in would breach the rule the script exists to enforce.

The turn itself, HTTP 200 in 288s, full Coordinator → specialist → Synthesizer:

```
Tomorrow is completely clear, Danny. You don't have any meetings, calls, or
deadlines on your calendar, so outside of your usual work rhythm and walking
Basho, your day is wide open.
```

Real persona context reached the Synthesizer (the dog's name is from `danny_park`'s
store), so the knowledge layer, dispatch and the output filter all survived the seam
removal on a live path.

**One thing is still owed, and only Mike can do it:** the same turn as `--persona mike`,
in the main tree, after the patch and the Red half are committed. It is a five-minute
check and it is the only part of this phase a worktree structurally cannot run.

## Cost

Against § 14's **$24–34** for phase A. On the subscription there is no per-token bill, so
the figure that matters is window: this ran as one continuous session with no rate-limit
stall. My read is **inside the budget, toward the upper half** — the deletion, the
`_AGENT_NAME_MAP` recovery, the tier gate and the live pipeline turn all landed after the
step-8 report. **I did not pass $34.**

The one genuinely metered cost was the live gates: `run_knowledge_routing.py` and the
server turn both make real Vertex calls. The server turn alone ran 8 Coordinator turns plus
a specialist, ~133K cumulative input tokens against a warm cache.

---

## Left open

1. **The `--persona mike` server turn, in the main tree, after the commit.** (M) — only
   Mike can run it, because only the main tree has that persona config. Five minutes.
2. **The constitution sensitivity check has no successor in code.** The tier gate replaces
   the half with measured evidence behind it; the other half — that a capability's routing
   inherits a *sensitive* tier — now rests on routing parity plus Mike reading the diff.
3. **The local-mode `local: true` assertion**, deliberately unbuilt, with its revival
   trigger recorded in `gates.py`.
4. **`config/build/registry.yaml` does not exist yet.** Correct: nothing has landed. The
   checker passes on an empty system by design, and `build_board.py` prints "nothing
   landed".

---

## For the commit

The patch applies to the main tree and does **not** contain `core/router.py` or
`core/scheduler.py` — those are Mike's, already in his working tree. Two notes for staging:

- **`core/trace.py` and `core/orchestrator.py` are also touched by the headset-mode chat.**
  My hunks are the per-job cost seam (`trace.py`) and the four load seams plus the tool
  registration (`orchestrator.py`); the other chat's are elsewhere in both files. `git apply
  --3way` should carry both, but **`git diff` each file before staging** — that is the
  2026-08-09 rule and this is exactly the shape it was written for.
- `tests/test_build_{schemas,registry,jobs,spine,coherence}.py` show as **modified**, not
  added: the new suites reuse those five names. The other eight old suites are deletions.
- **The patch carries no `data/personas/**` hunks, and that took a deliberate revert.**
  Running the live pipeline turn wrote into `danny_park`'s tracked seed files
  (`context.json`, `memory/index.faiss`, `memory/metadata.json`) — `.gitignore` does not
  untrack a file committed before the rule landed, so they showed up as ordinary
  modifications and would have ridden into the commit. Reverted before the patch was
  regenerated. **Worth knowing for every future live gate run in a worktree:** exercising
  a fixture persona dirties tracked files, and the sweep does not notice.

**Next phase:** B — the read door on `core/server.py`, `probe.py` behind it,
`scripts/vm_read.py`, auth, tests. § 14 estimates $8–12.
