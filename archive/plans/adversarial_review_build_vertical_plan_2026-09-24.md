# Adversarial review — `archive/plans/build_vertical_plan_2026-09-24.md` (Build plan v4)
**Reviewer:** Opus 5 (`adversarial-reviewer`), effort `high`, 2026-09-24. Verbatim; unedited.

## STRUCTURAL

1. [plan § 3, § 7, § 10, § 12, § 14] [core/build/runner.py; .claude/commands/build.md (does not exist); tests/test_build_command.py (listed, unspecified)]
Wrong: The graph's entire control layer — node sequencing, the one rung-2 retry per node, the review's single send-back, the artifact resume cursor, parking a job after a second failure — moves from 1,260 lines of reviewed Python (`core/build/runner.py`, deleted whole at § 10) into a markdown command a model interprets, and this is stated in one clause ("the command is the runner").
Fails: A prompt cannot enforce a retry count or a park condition, so the bounds § 8 names as the replacement for the retired dollar tripwire ("one rung-2 retry per node, the review's one send-back") are enforced by nothing, and § 12's only listed check of the command is a test file name with no assertion behind it.
Costs: The safety bounds of an agent that writes code, runs Bash and edits routing files reduce to model compliance, and no step in the plan can fail in a way that reveals it. high

2. [plan § 11, § 14, § 10] [.claude/settings.json:ask; CLAUDE.md § Change tiers; scripts/hook_agent_spawn.py:1-9]
Wrong: § 11 has the implementer subagent write "both routing entries" and the generated `config/agents/*.md`, § 14 says "the routing-file, router and scheduler edits (Red) are made in the main session, not by a subagent", and CLAUDE.md's standing rule is that Red-tier work is not delegated to a subagent at all — three incompatible states for the same edits.
Fails: The plan resolves the conflict by asserting "Red-tier files prompt Mike ... that is the control working", but every measurement recorded in this repo covers the main session only, and `scripts/hook_agent_spawn.py`'s own header records that subagent tool use stopped requiring confirmation (~800 prompts removed) — so whether an `Edit(./config/modules/routing.yaml)` ask rule reaches Mike from inside a subagent is unprobed, against this repo's own rule to probe per tool family, never once.
Costs: Either N11 is redesigned mid-build to hand Red files back to the main session, or the routing grants and agent files of every generated capability are written unattended under a control believed to be firing. high

3. [plan § 6 (Path rules row), § 11, § 12 (Implementer boundary), § 13.2] [core/build/writer.py:189-209 DENY_PREFIXES/DENY_EXACT/DENY_GLOBS; .claude/settings.json:34-67; scripts/new_worktree.sh:90]
Wrong: The writer's hardcoded deny list is retired for "the harness's Denied tier ... no second copy", but the harness denies neither what the writer denied — `.claude/settings.json`, `config/personas/` for every persona but `mike`, `core/build/`, `*key*.json`, `config/modules/build.yaml` are all absent from `deny` — nor, being `./`-anchored to the project root, anything inside the sibling worktree at `../metatron-wt-<slug>` where the implementer actually writes.
Fails: § 12's implementer-boundary row asserts "if hand-edited past it, the harness denies the write" as established behaviour; on the evidence a Write to `<worktree>/config/constitution.md` from a subagent whose session root is the main tree does not match `Edit(./config/constitution.md)`, and a Write to `.claude/settings.json` matches no rule anywhere.
Costs: The only remaining boundary on an implementer holding Edit, Write and Bash is the plan's `files[]` list and Mike's reading of the diff, with the machine-enforced floor the design claims it inherited absent in both directions. high

4. [plan § 10 (Step 1, "Kept in shared files", "Written fresh"), § 11, § 16] [core/scheduler.py:738-745 `_DEFAULT_JOBS["build_tick"]["function"] = "core.build.runner.tick"`; tools/build.py:56 and :154 `from core.build import jobs as J`]
Wrong: § 10 keeps `build_tick`, `request_build` and `context_block` as unchanged runtime ("Nothing outside Build changes behaviour") while deleting the modules all three call, and the fresh-write list names no module that provides a `tick` or the ticket store those functions would use.
Fails: `request_build` returns "Not filed: ModuleNotFoundError" from the moment Phase 0 lands until something re-points it, and after Phase E's deploy the VM scheduler resolves `core.build.runner.tick` every 30 minutes against a module that no longer exists — silently, because `fire_function` catches — which is the REPAIR counter that bootstrap run 2 (the induced REPAIR) depends on.
Costs: The ticket inbox and the REPAIR trigger, the two jobs § 2 says the VM keeps, are dead across phases 0–E with no phase funded to rebuild them and no listed gate that would notice. high

5. [plan § 6, § 10 (Step 1), § 14 (Phase 0), § 16] [scripts/qa_sweep.sh:162-171 `run_check "build-registration"`; scripts/check_build_registration.py:75,100,146,235 `from core.build import writer` / `schemas.validate_overlay_capability`]
Wrong: Phase 0's completion gate includes a green `./scripts/qa_sweep.sh`, but check 11 of that sweep is `check_build_registration.py`, whose body is overlay-record validation against `core/build/writer.py` and `schemas.validate_overlay_capability` — both deleted by the same step — and the script appears in neither the delete list nor the written-fresh list.
Fails: § 6 and § 4 simultaneously promote this script to the new parity-and-completeness checker over tracked routing files and the Coordinator directory, so Phase 0 cannot close without rewriting a script no phase budgets, and the `time_director` half-wiring the plan cites as the reason a checklist needs a check has no check for the duration.
Costs: Either the first phase's only objective gate is waived on day one, or unscoped rewrite work lands inside a $2–4 phase. high

6. [plan § 0 ruling 6, § 3 (N8, N10)] [.claude/commands/adversarial-review.md:41-52; .claude/agents/adversarial-reviewer.md:5]
Wrong: Ruling 6 requires the reviewer to see the whole question table beside the plan, while § 3 renders that table at N10, after N8 has already run.
Fails: The artifact the reviewer is required to read does not exist at the moment it is spawned, and the command it is spawned through passes exactly three things — plan path, effort, repo root — with an explicit prohibition on adding context, so there is no channel for the ledger or table short of changing the command or inlining them into the plan file, neither of which the plan states.
Costs: The review that replaces the Planner's self-read (ruling 8) runs blind to the evidence base every plan gate is required to cite, and the gap only surfaces when N8 is first wired. medium

7. [plan § 2, § 5, § 13.8] [config/build/registry.yaml (new, tracked); data/personas/{p}/build/tickets.jsonl on the VM]
Wrong: Dedupe and REPAIR eligibility are read on the VM from the deployed registry, but every registry row — `landed`, and the `--abandon` row the board writes "into the working tree for Mike to commit" — reaches the VM only when Mike commits and deploys, which the plan never sequences against the 72-hour and 14-day windows those rows govern.
Fails: A ticket Mike abandons on the Mac is invisible to the VM until a deploy, so `request_build` keeps re-filing the same fingerprint; `max_proposed: 12` then fills with duplicates of a decision already taken, and SESSION.md records the standing state as three commits and one deploy owed.
Costs: The dedupe guarantee § 13.8 offers as the answer to "two state homes will disagree" holds only under a deploy cadence nobody has committed to, and its failure looks like the gap-filing tool working. medium

9. [plan § 6 (The read doors), § 3 (N4)] [core/build/manifest.py:15-19 and :72 `_SOURCES`; core/build/probe.py:37-40]
Wrong: The door runs a named tool with "the supplied arguments", which discards the property the existing design states as its injection answer — `candidate_sources` validated against the manifest and "the probe arguments come from manifest._SOURCES, not from the model" — and the plan never names the change.
Fails: The Librarian reads journal, conversation and wisdom content written by or about third parties and then composes the next door call's arguments from what it read, with the allowlist constraining only the tool name, not the arguments or the volume.
Costs: The one structural control over model-chosen tool arguments in this vertical is removed in a table row about transport, and § 13's risk list answers only the volume question. medium

## LOCAL

8. [plan § 10 (Salvaged by copy), § 10 (Written fresh)] [core/build/manifest.py:72 `_SOURCES`; core/build/probe.py:38]
Wrong: The salvage table sources the presence-check call table from "`probe.py`'s `_SOURCES` after D4"; `_SOURCES` is defined in `core/build/manifest.py`, and `manifest.py` is on the written-fresh list.
Fails: Following the plan literally copies a symbol that is not in the named file and rewrites from scratch the file that holds it, discarding the three review rounds' argument repairs recorded in its comments — the `get_log_window` start/end window, `search_memory`'s required `query`, `read_archive`'s required category, and the `answers` shape restriction added 2026-09-18.
Costs: The exact class of defect the phase-4 review rounds were spent finding returns in the rewrite, undetected until a probe silently reports `error` or `no_data` on the richest source. medium

10. [plan § 4 (Where a declared variable lives)] [config/templates/profile.yaml; scripts/new_persona.sh:81; tools/profile.py:196]
Wrong: An `all_personas` variable is placed in `config/templates/profile.yaml` as "tracked, in the diff", but that file is a provisioning source read only by `scripts/new_persona.sh` at persona creation — `tools/profile.py` resolves `persona_config_dir()/profile.yaml` with no template fallback.
Fails: The variable reaches no existing persona, `mike` included, so a capability that declares one ships a field `read_profile` never returns and `write_profile` was never asked to create.
Costs: An all-personas capability passes its gates, lands, and then behaves as though the user lacks the fact, on the one persona acceptance runs against. medium

## VERIFY — 2026-09-24, round 1 (plan revised to v4.1; same reviewer, Opus 5, effort high)

1. CLOSED — [core/build/runner.py:101 `MAX_NODE_RETRIES`, :109 `NodeOutcome`, :144 `_pre_node`, :190 `_post_node`, :229 `_ask`] The control layer named for salvage exists as real, separable symbols, `driver.py` is on the fresh list with a falsifiable test row (§ 12 Driver: retry-once-then-park, gate yields no step, counts re-derived from disk after restart); residual, not reopened: a failed node writes no artifact, so the "durable artifact count" that bounds retries has no named home now that `attempt` tracking in `core/build/jobs.py` is itself on the written-fresh list.

2. NEW SHAPE — [.claude/commands/fix.md:97 "Red → built here on Opus. No worker."; scripts/new_worktree.sh:111 `git worktree add -b wt/<slug> $DEST HEAD`] The contradiction is gone and the split matches the existing `/fix` tier rule, but it now puts one capability's change in two git trees — code and tests on `wt/<slug>`, the agent file, both routing entries, the Coordinator lines and knowledge domains uncommitted in `main` — which is a defect the revision introduced rather than the one I raised (see NEW 1).

3. NEW SHAPE — [core/build/writer.py:189-209 `DENY_PREFIXES/DENY_EXACT/DENY_GLOBS`; scripts/rm_worktree.sh:89 "Ignored files (the symlinks, copied fixtures) do not appear"] The deny list is correctly salvaged and the "no second copy" claim is properly withdrawn, but the driver applies it to the worktree's `git status --porcelain`, a channel that cannot see the gitignored paths the list exists to name (see NEW 2).

4. CLOSED — [core/scheduler.py:742 `"function": "core.build.runner.tick"`; plan § 10 fresh list `core/build/tick.py`, § 12 Tick row] The re-point now precedes the deletion inside phase A, `tick.py` and `tests/test_build_tick.py` are on the written-fresh list, and `scheduler-functions-resolve` converts the failure mode that `fire_function`'s `except` swallows into a sweep failure.

5. CLOSED — [scripts/qa_sweep.sh:171 `run_check "build-registration"`; scripts/check_build_registration.py:75,100,146 `from core.build import writer`] The script is on the written-fresh list, sequenced to be rewritten before `writer.py` is deleted, and § 12's Registration-check row states a falsifiable `time_director`-shaped assertion for it.

6. CLOSED — [.claude/commands/adversarial-review.md:44-48 (path, effort, repo root, nothing else)] N10 now precedes N8 and the reviewer is handed the brief file that contains the table, which is the only channel that command offers; minor residue, not reopened: that command's step 3 writes a report into tracked `archive/plans/`, so § 3's "[N9] ... Nothing before this point touched the repo" is not literally true per build.

7. CLOSED — [config/build/registry.yaml (new, tracked, deployed); plan § 5 "one state on the VM, open, until the deployed registry carries its row"] Refusal now keys off the open ticket rather than the deployed row, so no duplicate can be filed while a decision waits for a deploy, and the one residual lag — `abandoned` rows consuming `max_proposed: 12` — is named, bounded and surfaced on the board.

8. CLOSED — [core/build/manifest.py:72 `_SOURCES`, :159-195 the seven `live: True` rows] The salvage row names the right file and the right symbol, and the D4 argument repairs it carries (`get_log_window` start/end, `search_memory`'s required `query`, `read_archive`'s category, the `answers` shape restriction) are what moves behind the presence door.

9. CLOSED — [core/build/manifest.py:161 "These seven are the outbound reads of section 6.3"; tools/wisdom.py:345 `READ_CAP = 15`] Presence takes a source id against the code-chosen call table, the seven outbound tools are off the door, and server-side argument schemas with caps replace free arguments; one inaccuracy in the prose — "the tools' own `READ_CAP`s" is plural but exactly one tool in the read set defines one.

10. CLOSED — [tools/profile.py:196 `persona_config_dir()/"profile.yaml"`; scripts/new_persona.sh:81] The `all_personas` home is now the template entry *plus* the `write_profile` ask path for personas that already exist, with a validation rule attached; the rule has no assertion in § 12's Schemas row, which is the only loose end.

### NEW

1. [§ 3 N11, § 3 N12, § 3 N13, § 12 End to end] [scripts/new_worktree.sh:111; scripts/rm_worktree.sh:9-14 "refuses when the worktree holds ... commits that"; .claude/commands/fix.md:126-155]
Wrong: One capability's diff is now split across two git trees with no stated path back together — the implementer's half is committed nowhere (§ 3 forbids it `git commit`), the main session's Red half sits uncommitted on `main`, and N13 describes a single diff Mike reads and commits.
Fails: A worktree branch reaches `main` only by being committed on `wt/<slug>` and merged (`rm_worktree.sh` refuses removal otherwise), so either the implementer commits — which the plan denies it — or Mike hand-merges a branch and a working-tree edit set, and neither N12's gate (worktree only) nor `hook_commit_guard.py` (main tree only) sees the other half.
Costs: The landing step of every build is undefined, and the failure shape is the one `.claude/rules/deploy.md` already names — tracked files committed while the code they reference sits in a tree nobody merged. high

2. [§ 3 "Denied files are denied twice", § 6 Path rules row, § 12 Implementer boundary] [scripts/new_worktree.sh:142-146 `link_back ".env" / "vertex-key.json" / "certs" / ".claude/settings.local.json"`; .gitignore:11,72,81,170,184; scripts/rm_worktree.sh:89]
Wrong: The salvaged deny list is enforced by reading the worktree's `git status --porcelain`, which reports nothing for `.env`, `vertex-key.json`, `certs/`, `config/personas/*/profile.yaml` or `data/personas/**` — every one of them gitignored, and the first four symlinked straight back to the main tree.
Fails: An implementer `Write` or Bash redirect to `<worktree>/.env` mutates the real credentials file through the symlink, produces no porcelain line for the driver to refuse, and does not match the harness's `./`-anchored `Edit(./.env)` either — the same double-blind the revision claims to have closed.
Costs: The paths with the highest blast radius on `writer.py`'s list are the exact ones the chosen enforcement channel cannot observe, and a green N12 would report the opposite. high

## VERIFY — 2026-09-24, round 2 (plan revised to v4.2; same reviewer)

NEW 1. CLOSED — [scripts/new_worktree.sh:111 `git worktree add -b wt/<slug> $DEST HEAD`; scripts/rm_worktree.sh:9-14, :89] The patch collapses the two trees into one: the sandbox branches from the same HEAD the patch is applied to, the worktree holds no commit so `--force` removal deletes the branch cleanly, and § 12's "applying it to a clean main tree reproduces the worktree byte-for-byte" is a falsifiable check on the one thing that crosses.

NEW 2. CLOSED — [scripts/new_worktree.sh:139-146 `link_back ".env" / "vertex-key.json" / "certs" / ".claude/settings.local.json"`; scripts/rm_worktree.sh:89 "Ignored files ... do not appear"] `--sandbox` negates exactly the link-backs that made a worktree write reach the real credentials, and channels (b)/(c) hash the gitignored deny-list paths that `git status` structurally cannot report; residue, named not reopened: coverage is an enumerated path list inside two trees, and a `python3 …` Bash grant can still write outside both.

Residual 1. CLOSED — [core/build/runner.py:101 `MAX_NODE_RETRIES`, :109 `NodeOutcome`; core/build/jobs.py (attempt tracking, on the fresh list)] `attempts.jsonl` is written before a step is named rather than after it succeeds, which is the ordering that makes a failed node countable, and § 12's Driver row asserts re-derivation across a restart including the no-artifact case.

Residual 6. CLOSED — [.claude/agents/adversarial-reviewer.md:2-5 `name: adversarial-reviewer`, `model: fable`, `tools: Read, Grep, Glob`; .claude/commands/adversarial-review.md:44-48] Spawning the agent definition directly with the same three-line prompt is what the command itself does, so the report can land in the gitignored job directory and § 3's "nothing before [N9] touched the repo" becomes true.

Residual 9. CLOSED — [tools/wisdom.py:345 `READ_CAP = 15`] The sentence now says one tool defines one, which is what the tree contains.

Residual 10. CLOSED — [§ 12 Schemas row] The `all_personas`-without-`if_user_lacks_it: ask` rejection is now an assertion in the schema suite rather than prose in § 4.

### NEW (round 2)

1. [§ 3 N11, N12, N13; § 12 End to end] [scripts/qa_sweep.sh:63 `check_agent_tools.py`, :171 `check_build_registration.py`; CODEBASE_INDEX.md:81 `time_director`]
Wrong: The tier split means the sweep at N12 runs in a worktree holding the code and no `registration[]`, while the Red half is written at N13 in the main tree with no gate after it — so the parity checker finding 5 was restored to exist never sees both halves of a capability in one tree.
Fails: `check_build_registration.py` and `check_agent_tools.py` pass vacuously at N12 (nothing to check: no routing entry, no agent file) and are never re-run once the routing entries, Coordinator lines and agent file land, so a half-wired capability reaches Mike's single `git diff` with every automated wiring check green.
Costs: The exact `time_director` shape the plan cites as its standing evidence — an agent file and a consequence line with no routing entry — is reachable again, and it ships to the VM on the next deploy. high

2. [§ 3 N12 "the driver writes the patch: `git -C <wt> add -A …`", § 3 N13 known friction] [scripts/hook_commit_guard.py:92 `_WRITING = {"add", "commit", "stash"}`, :41-44 root from the git command's own `-C`, :200 `_attribute`]
Wrong: The plan names commit-guard friction at N13 for patch-applied files, which the guard's own two-severity split puts in the WARN branch, and says nothing about N12's `git -C <wt> add -A`, which is a guarded verb resolved against the worktree root.
Fails: The implementer's writes carry a manifest in `<wt>/.claude/.session_edits/`; if the subagent's manifest id differs from the `/build` session's, `_attribute` finds another session claiming the current hash and BLOCKs the stage — the patch is never produced and the documented override (`METATRON_COMMIT_GUARD=off`) is not named at that step.
Costs: Every build halts at the last step of N12 on a hook the plan believes it will meet one step later and one severity lower, with the worktree full of finished work and no stated way through. medium

## VERIFY — 2026-09-24, round 3 (plan revised to v4.3; same reviewer)

Round-2 NEW 1 (wiring checks never see both halves). CLOSED — [scripts/check_build_registration.py (rewritten, § 10 fresh list); scripts/check_agent_tools.py, qa_sweep.sh:63; CODEBASE_INDEX.md:81 `time_director`] The gate now runs in the main tree after the patch and the Red half land — the first point both halves coexist — and withholds the staging manifest on red, with a falsifiable § 12 row (delete one routing entry → no manifest); the accepted consequence, stated in-plan, is that a red gate leaves a half-wired capability uncommitted in the tree another chat often shares.

Round-2 NEW 2 (staging verb meets the commit guard). CLOSED — [scripts/hook_commit_guard.py:92 `_WRITING = {"add","commit","stash"}`, :188 `_manifest_path(root, session_id)`, :200 `_attribute`] `git diff HEAD --binary` plus per-file `--no-index` diffs issue none of the watched verbs in the worktree, and at N13 the stage happens in the main tree where patch-applied files carry no manifest entry (PostToolUse fires on `Write|Edit`, not Bash) and the subagent's worktree manifests under `<wt>/.claude/.session_edits/` are never read — so the plan's WARN-not-BLOCK reading is correct, with the override named either way.

### NEW (round 3)

1. [§ 3 N12 channel (b), § 12 Sandbox and patch] [scripts/hook_context_gate.py:147 `marker_dir = root / ".claude" / ".session_state"`, :152 `marker_dir.mkdir(...)`, :195-207 `_repo_root(target)`]
Wrong: Channel (b) hashes `.claude/**` in the worktree and excludes only `.claude/.session_edits/`, but a second harness hook writes under `.claude/` in the same tree — the context gate creates a `.session_state/<session>.brief.<hash>` marker per file, with the root resolved from the target path precisely so worktrees are covered.
Fails: The implementer's first `Write` or `Edit` in the sandbox creates that marker, the before/after hash of `.claude/**` differs, and N12 refuses the job — on every build, deterministically — while § 12's row asserts only that a `.session_edits/` write is not refused, so the suite goes green on a pipeline that cannot complete.
Costs: The gate that exists to catch a deny-list write instead blocks every legitimate implementation pass, and the failure reads as a security refusal rather than as the hook's own bookkeeping. high

2. [§ 3 N13 wiring gate, § 12 Wiring gate, End to end] [scripts/qa_sweep.sh:63-171 (eleven checks over the whole tree); scripts/hook_subagent_gate.py:105-110 "attributes by dirtiness, not by authorship"]
Wrong: The wiring gate conditions the staging manifest on a full `qa_sweep.sh` over the shared main tree, not on the checks that concern the capability, so any unrelated red another chat left — a duplicate backlog id, a dev marker, a hand-edited `PROJECT_LOG.md` — withholds it.
Fails: This is the same attribute-by-dirtiness limit the subagent gate already records as a known cost, but applied at a point where the consequence is a finished build parked with its patch already applied and its Red files already written in that tree.
Costs: A build can be blocked, and left mid-landing, by a fault it did not cause and cannot fix, on exactly the two-chat day the plan says is routine. medium

## VERIFY — 2026-09-24, round 4 (plan revised to v4.4; same reviewer)

Round-3 NEW 1 (channel (b) refuses on harness markers). CLOSED — [scripts/hook_context_gate.py:147 `root / ".claude" / ".session_state"`, :195 `_repo_root(target)`; scripts/hook_commit_guard.py:89 `STATE_DIR = ".claude/.session_edits"`] Both hook-written marker directories are dot-prefixed and now fall outside an enumerated list rather than inside a `.claude/**` wildcard, the reason is recorded at the point of the decision, and § 12 asserts that a `.session_edits/` write is not refused; the enumeration is not a complete image of its source list, which is NEW 1 below.

Round-3 NEW 2 (wiring gate conditioned on the whole sweep). CLOSED — [.claude/settings.json:54 `Bash(git checkout .)` — the only checkout denial, so the printed per-file `git checkout -- <path>` revert is permitted; scripts/hook_subagent_gate.py:105-110 "attributes by dirtiness, not by authorship"] The manifest now turns on capability-scoped checks with the full sweep advisory beside it, and the revert line gives a half-landed capability a way out of the shared tree; one of the three scoped checks is attributed to the wrong file, which is NEW 2 below.

### NEW (round 4)

1. [§ 3 N12 channel (b), § 6 Path rules row] [core/build/writer.py:189-193 `DENY_PREFIXES = ("config/personas/", "core/build/", ".git/")`; scripts/new_worktree.sh:111 `git worktree add`]
Wrong: Channel (b)'s enumeration was built from the salvaged deny list but omits `.git/`, which is on `DENY_PREFIXES` and is the one deny-list entry that channel (a) can never report either.
Fails: In a worktree `.git` is a pointer into the main repository's common directory, so a write to `<wt>/.git/hooks/pre-commit` lands in the main repo's shared hook path — invisible to `git status --porcelain`, absent from the enumerated hash, outside the sandbox flag's reach (a worktree cannot exist without that link), and executed by Mike's own commit at N13.
Costs: The one path on the deny list that can run code in the main tree under Mike's hands is the one path no channel watches, and a green N12 asserts the opposite. high

2. [§ 3 N13 wiring gate; header "v4.3 to v4.4" (NEW 2)] [scripts/hook_agent_tools.py:11-15, :56 `_changed_agents()` "from the uncommitted diff", :20 "Never blocks and never fails the tool call: exits 0 no matter what"; scripts/check_agent_tools.py:360-376 flags `--routing/--agent/--quiet/--no-personas/--overlay/--personas-root`]
Wrong: The gate's scoping premise — "`check_agent_tools.py` (which already scopes itself to the agents whose block moved in the uncommitted diff)" — describes `hook_agent_tools.py`, not the script; the script's only scoping is `--agent <name>`, and the diff-scoped behaviour lives in a PostToolUse hook that exits 0 by design.
Fails: Run as the plan describes, the checker is unscoped over `config/agents/**` and `config/personas/**.md`, so any pre-existing live-but-unbuilt tool reference elsewhere in the shared tree withholds the staging manifest — the failure v4.4 set out to remove, narrowed from eleven checks to one — and the alternative reading, reusing the hook, cannot gate anything because it never fails.
Costs: The scoped half of the wiring gate is either not scoped or not a gate, and which one it is will only be discovered on the first build that meets an unrelated agent-file defect. medium

## VERIFY — 2026-09-24, round 5 (plan revised to v4.5; same reviewer)

Round-4 NEW 1 (`.git` pointer path unwatched). CLOSED — [.git/config (no `core.hooksPath`, no `extensions.worktreeConfig`); .git/hooks/ contains only `*.sample`; core/build/writer.py:192 `".git/"` on `DENY_PREFIXES`] Channel (c) now hashes the shared common directory a worktree's `.git` pointer resolves to — `hooks/`, `config`, `info/` — which is the only place a write through the pointer can land and execute, and the plan's "expected delta is none" is accurate against the tree; the § 12 row's *restore* clause is NEW 1 below.

Round-4 NEW 2 (agent-tool scoping attributed to the wrong file). CLOSED — [scripts/check_agent_tools.py:364 `ap.add_argument("--agent", help="check one agent only")`; scripts/hook_agent_tools.py:20 "Never blocks and never fails the tool call: exits 0 no matter what", :56 `_changed_agents()`] The gate now names the script's own flag, the header's earlier sentence is corrected in place rather than left to contradict § 3, and the hook is correctly described as unable to gate; routing parity for the new name stays with `check_build_registration.py --capability`, which is where § 10 already puts it.

### NEW (round 5)

1. [§ 12 Sandbox and patch row; § 3 N12 channel (c)] [.git/hooks/ (main repository, shared by every worktree); core/build/gates.py (to be written, § 10 fresh list)]
Wrong: The test asserts the main repository's hook directory is "byte-identical afterwards once the driver's refusal restores it", but § 3's channel (c) captures hashes, and a hash cannot restore bytes — nothing in the mechanism says the hook directory's contents are snapshotted.
Fails: Either the assertion is unsatisfiable against the described driver, or the driver silently gains a write-and-delete path into `.git/` in the main repository to make it pass — a repair verb aimed at the most sensitive directory in the tree, with no stated bound on what it may remove if a legitimate hook or config change lands mid-build.
Costs: A detection channel added to close an escalation path acquires, in its test row only, a mutation power over the shared git directory that nobody specified and no gate watches. medium

## VERIFY — 2026-09-24, round 6 (plan revised to v4.6; same reviewer)

Round-5 NEW 1 (a test row implied the driver restores the hook directory). CLOSED — [.git/hooks/ (only `*.sample`, so a planted `pre-commit` is unambiguous); .git/config (no `core.hooksPath`); § 3 N13 prints the revert command rather than running it] Channel (c) is now stated as detect-only with no driver write path into `.git/`, the credentials or the persona trees in either tree, and the § 12 assertion is achievable with hashes alone — a test-owned before/after pair around the driver's run, with the plant removed by the test — rather than requiring content the driver never captured.

### NEW (round 6)

1. [§ 3 N12 (line 347) vs § 12 Gates row (line 754)]
Wrong: v4.6's new invariant — the driver "refuses the job, prints the exact paths that changed, and stops" — collides with the surviving § 12 Gates assertion that a deny-list hit is "refused with the worktree discarded", while § 3 N12 says the same refusal leaves the worktree in place for Mike to read.
Fails: The suite would encode a destructive behaviour the mechanism section now forbids, and whichever the implementer follows, one of the two is wrong at the moment it matters — a refusal is exactly when the evidence of what was written must survive.
Costs: The test that proves the deny-list gate works may require the driver to delete the only record of what tripped it, in the one directory Mike is told to go and read. medium

## VERIFY — 2026-09-24, round 7 (plan revised to v4.7; same reviewer)

Round-6 NEW 1 (§ 12 Gates row said "worktree discarded"). CLOSED — [scripts/rm_worktree.sh:5-14 — removal is a deliberate human act that refuses when work would be lost, so nothing in the tooling discards a worktree implicitly and the old wording would have required a destructive step no script provides] The Gates row now asserts the worktree is left in place and byte-identical after a refusal with the path named on the board, which matches § 3 N12 and the v4.6 detect-never-restore invariant; `discard` survives nowhere in the plan but the changelog line recording the fix, and the later removal path (`rm_worktree.sh --force` after N13, § 14 Ancillary "after commit") is unaffected because a refused job never reaches a commit.

### NEW (round 7)

none

**Clean pass at round 7.** Seven verify rounds by the same Opus 5 reviewer; a separate cold read by a fresh Fable 5 reviewer on v4.3+ is recorded in `adversarial_review_build_vertical_plan_2026-09-24_cold-fable.md`.
