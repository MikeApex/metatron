### 2026-09-24 (Build phase A — `core/build/` rebuilt with salvage, the overlay retired)

Build session on Opus 5, executing phase A of plan v4.11 in a worktree
(`metatron-wt-v4a-package`, based on `505b254`). The new `core/build/` package is written, every
caller re-pointed, the old 19-module package and its four load seams deleted, and all six
regression gates are green. **Nothing user-visible ships and nothing deploys — § 16 sends
phases 0, A, B, B-Red and D to the VM as one deploy at E.** Left as a patch plus a handoff at
`archive/handoffs/2026-09-24-build-phase-A.{patch,md}` for Mike to land and commit.

**What the package is now.** 17 files: the nine salvaged pieces copied across (the validators
with the compass-rule ordering byte-identical, the transcript fixture, the id allocator, the
question index, the constitution check, the policy shape, `manifest._SOURCES` with all seven D4
argument repairs, the runner's control layer, the writer's deny list) and eleven written fresh —
`tickets jobs tick manifest table brief registry coherence gates verify driver`. `doors.py` is
phase B. 236 checks across eleven suites, all green, plus a rewritten
`check_build_registration.py`, a new sweep check 12 (`scheduler-functions-resolve`), a
`--sandbox` flag on `new_worktree.sh`, the `metatron-wt-build-` skip in `hook_subagent_gate.py`,
a fresh read-only `build_board.py`, and one `.gitignore` line for `data/build/`.

**Three defects the plan did not anticipate, each found by a test written for a § 12 row.**
(1) **The review's one send-back could never have fired** — the bound sat at N7, but N7's
artifact exists as soon as the first plan is written, so the cursor skipped N7 and the walk never
reached the check. Both job-level bounds now run before the node walk. (2) **Channel (a) refuses
the harness's own edit markers, and verify round 3 fixed only channel (b)** — a
`.claude/.session_state/` marker is not in `files[]`, so (a)'s own rule refuses it. It is
currently invisible because `.gitignore` carries `.claude/*`, i.e. an ignore rule was holding up
a security property; `gates.HARNESS_MARKERS` makes the exemption explicit. (3) **A "name contains
a dot" suffix heuristic silently disabled the send-back counter** — `build_plan.v1` was written
without `.json`, so the `build_plan.v*.json` glob that *is* the counter found nothing.

**One § 12 row describes a path that cannot exist, and the mechanism is still right.** It asserts
a write to `<wt>/.git/hooks/pre-commit`; in a git worktree `<wt>/.git` is a pointer *file*, so
that raises `NotADirectoryError`. The reachable attack resolves `--git-common-dir` and writes to
the main repository's hook path, which channel (c) refuses. The suite now tests the reachable
form plus a second check that overwriting the pointer itself is refused by (b). No mechanism
changed — only the test's route to it.

**A sixth content gate was added mid-phase, on Mike's approval: the tier gate.** A capability
whose plan reads a `kind: history` ledger row, or decides a `judgment` row, is refused on the
bulk tier. **Not a privacy control** — everything routes to Vertex Gemini under the 08-26 ruling.
What it guards is judgement *variance*, and ROADMAP § D2 has it measured: `relationships`, on the
bulk tier and commented "no clinical stakes", gave opposite answers to the same class of evidence
four minutes apart. **That is why it is a gate and not a test** — a ceiling shows on the first
clean run, variance shows on none, so acceptance passing proves nothing about it. Run 1's own
`home_care` is exactly this shape. Two constraints held: the bulk tier is read from the routing
file's `quick_override` (never a literal — ids here have a half-life of days), and it runs at N13
with the other Red-reading gates, because at N12 the sandbox holds no routing entry and the gate
would pass vacuously on everything.

**Rejected, with the reason: the local-mode half of that gate.** A generated `routing.yaml` entry
omitting `local: true` would read personal data and route to Vertex in the one mode whose point
is that it does not, and parity checking cannot catch it because the two files legitimately
differ on provider, model and the flag. Not built (Mike, 09-24): `DEPLOYMENT_MODE=cloud`, Ollama
unused, so it would be a control for a path nobody runs — and an unexercised control rots. The
rule, the reason and the revival trigger are recorded in `gates.py`, with a test asserting the
block survives so it cannot be tidied into reading like an oversight.

**Believed true earlier and wrong: the constitution check's sensitivity assertion had no
successor.** v3 asserted an overlay record's `routing.cloud.model_ref` named a *sensitive* tracked
agent; § 8 retires `model_ref`, so it went out with the overlay and phase A's step-8 report
recorded the gap as "weaker than a code gate". The tier gate replaces the half with measured
evidence behind it. The other half — that routing inherits a sensitive tier — still rests on
routing parity plus Mike reading the diff, and that remains recorded rather than closed.

**The deletion caused one real break, caught by a gate and not by the sweep.**
`_AGENT_NAME_MAP` went out with seam 3: it had been moved to module level so the overlay
validator could read it, so it sat inside the seam's block and read like seam machinery. It is
not — `_dispatch_from_coordinator` has always needed it. **`py_compile` accepted the removal and
`qa_sweep` was green; `run_knowledge_routing.py` crashed with `NameError`.** That is the sweep
header's own warning verbatim, and the second time a stale name has passed it here. Restored with
the reason at the site, then every touched file's module-level symbol set was diffed against HEAD
and each removal checked for live references.

**One guard transferred rather than dropped.** `check_agent_tools.py --overlay` made an ungranted
tool *fatal* for a generated agent. That branch worked only while generated agent files lived
somewhere the script could distinguish by path; they are ordinary `config/agents/*.md` now, so it
cannot and must not pretend to. The blocker moved to N13 via `gates.check_told_not_granted()`.

**Ordering note: one seam removal moved from step 9 to step 5.** Re-pointing `tools/build.py`
drops `answer_interview_item`, which makes `core/orchestrator.py`'s import fail and takes
`register_tools()` with it. It is not one of the two Red edits, was granted to no agent, and
nothing tracked ever reached it, so pulling it forward cost nothing the ordering protected.

**The Red half, and a state worth recording.** Phase A stopped at step 8 as instructed and
reported; Mike then made both Red edits in the main tree (`core/scheduler.py` → `core.build.tick.build_tick`,
`_merge_overlay_routing` removed from `core/router.py`). Those two files were copied into the
worktree to run the gates and **excluded from the patch**. Between the Red half landing and the
patch landing, the main tree is half-landed — `core/scheduler.py` names a module that does not
exist there, so the REPAIR counter is dark locally. The VM is unaffected (still `b2b1dc7`, old
package, internally consistent). This is the exact condition Opus finding 4's ordering exists to
prevent, and it is live until Mike commits.

**HEAD moved mid-phase**, so the patch was re-verified against the tree it will land in rather
than the one it was written on: the headset chat committed `3066d66`, and applying phase A plus
the Red half to a scratch worktree at that commit gave 12/12 sweep, 236 build checks and the
three non-Vertex regression gates green. A clean `--3way` apply is not the same as a coherent
result — both sides touched `core/orchestrator.py` and `core/trace.py`.

**Gates, with one structural deviation.** `test_a4_complexity_threading` PASS ·
`test_turn_referent` 22/22 · `test_synth_module_injection` 16/16 ·
`run_knowledge_routing --persona danny_park` GATE PASS · `qa_sweep` 12/12 · server start clean
and one full pipeline turn HTTP 200 in 288s with real persona context in the reply — **run as
`danny_park`, not `mike`, because `config/personas/mike*` is gitignored and VM-only and
`new_worktree.sh` deliberately never copies it, so `--persona mike` raises in any worktree.**
The `mike` form is owed in the main tree after the commit; it is an (M) item.

**Cost:** inside § 14's $24–34 for phase A, upper half. No rate-limit stall. The metered part was
the two live gates, which make real Vertex calls — the server turn alone ran eight Coordinator
turns plus a specialist against a warm cache.

**A trap worth knowing for every future live gate run in a worktree:** exercising a fixture
persona dirties *tracked* files (`data/personas/danny_park/{context.json,memory/*}` — `.gitignore`
does not untrack a file committed before the rule landed). They showed as ordinary modifications
and would have ridden into the commit; reverted before the patch was regenerated. The sweep does
not notice.

