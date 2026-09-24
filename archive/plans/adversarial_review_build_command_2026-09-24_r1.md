*Reviewed: `.claude/commands/build.md` (Build v4.11 phase C). Model: Fable (the
`adversarial-reviewer` default). Effort: `high`. Date: 2026-09-24.*
*Round 1 of 3 — the opening pass. Verbatim; nothing edited, reordered or softened.*

---

## STRUCTURAL

1. [§ 1 table N7/N8, § 3 N8, preamble "the driver will not name the step"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step, _artifact_done, _gate_is_open; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/tests/test_build_driver.py:_plan_through_review]
Wrong: The command delegates the review's send-back to the driver, but `next_step` treats N7 as done once any `build_plan.v*.json` exists and returns the N9 gate whenever `brief.md` and `review.json` are present, so no code path ever names N7, N10 or N8 a second time.
Fails: After a structural finding the session must run N7 unnamed, delete `brief.md` and `review.json` by hand and re-run N10/N8 — the held-in-the-head sequencing the preamble forbids — or the job sits at N9 with a rejected plan; the driver test that asserts "v2 is written and N10 is named" never writes the brief or the review first.
Costs: The one bounded send-back the graph is built around does not exist in code, so the first real structural finding either stalls the job or produces an unbounded improvised loop; high.

2. [§ 3 N11 "Any refusal parks the job with the worktree left in place", "Snapshot the four channels before spawning", § 2 bookkeeping] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step (MAX_NODE_RETRIES); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:check_channels, hash_paths, hash_delta]
Wrong: A channel refusal recorded per § 2 is one `failed` row, which the driver answers with N11 attempt 2 rather than a park, and § 3 has the session retake the before-snapshots on every spawn.
Fails: The attempt-2 baseline is taken with attempt 1's deny-list write already on disk (a `.env` in the sandbox, a hook in the shared `.git/hooks/`), so `hash_delta` is empty and channels (b) and (c) pass the exact change they refused a minute earlier.
Costs: The only channel that can see a hook planted through the worktree's `.git` pointer is silenced on retry, and that hook runs under Mike's commit at N13; medium.

3. [§ 1 table N11/N12/N14, § 3 N11 last paragraph, § 2 "the artifact is the cursor"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:_artifact_done, _file_for, NODES; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:ARTIFACTS; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/schemas.py:climb]
Wrong: The driver marks N11 done only when `implementation.patch` exists and N12 only when `gates.json` exists, but the command assigns `D.write_patch` to N12 in the table and to N11 in § 3, and names no write of a `gates` or `acceptance` artifact anywhere.
Fails: Following the table, the driver re-names N11 after the implementer returns and the session re-spawns it; following § 3, N11 completes but N12 is re-named forever because nothing writes `gates.json` and the § 2 `S.climb` template raises `KeyError` for any kind outside its three validators, so `[N13]` is never reached and `done` never fires.
Costs: Every job stalls or double-spawns at the implementer, the most expensive node; high.

4. [§ 3 N13 step 5 `V.content_gate(...)`] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/verify.py:content_gate; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:check_record_fields, check_names, check_grants_declared; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/constitution.py:check; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/registry.py:new_row; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/.claude/agents/build-planner.md § The rest of the plan]
Wrong: `content_gate` needs a `record` carrying `display_name`, `directory_entry`, `unavailable_consequence` and `routing.allowed_tools`, plus `peers` as name→display_name, but no artifact the graph produces holds any of these — the plan's `capability{}` and `registration[]` lack them and `new_row` writes no `display_name`.
Fails: At N13 the session must invent the record from the Red prose it just hand-wrote and pass `peers={}`, so the confidential-identifier scan runs against unvalidated inputs and the peer display-name collision check runs vacuously.
Costs: The content gate that catches a second capability capturing the first's dispatch is decorative on every landing; high.

## LOCAL

5. [§ 3 [N6] "write his answers into the ledger rows"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/.claude/agents/build-librarian.md:"There is no `answer` field, and that is deliberate"; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/schemas.py:_check_inventory, _check_ledger_row; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/table.py:_location]
Wrong: The ledger row schema has no field for a user-supplied answer, and every field the table renders (`inventory.*`, `gap`, `decision`) is defined as what the Librarian found in data.
Fails: An `ask_user` row either keeps its verdict and carries Mike's answer nowhere the Planner or the table reads, or is flipped to `found` and must fabricate `inventory.source/form/coverage/completeness/freshness` to pass `_check_inventory` at the N7 re-validation.
Costs: Interview answers are invisible to the Planner or enter the ledger as fabricated inventory, on every job with an interview; high.

6. [§ 2 "Record before you run", preamble "every bound is re-derived from attempts.jsonl"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:MAX_ATTEMPTS_PER_JOB, next_step; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:attempts]
Wrong: `next_step` parks at `len(J.attempts()) >= 16` counting every row including `started`, and § 2 writes a `started` row at every node, so a construct job spends 9 rows (repair 10) before any failure occurs.
Fails: One send-back (+3 `started`) plus two single retries (+2 rows each) reaches 16 on a job inside every individual bound, and a session that records gate steps too ("identical at every node") reaches it by re-entering `[N9]` a few times.
Costs: Legitimate jobs park at the retry-product cap, some at N14 after Mike has already committed, recoverable only by hand-editing `attempts.jsonl`; high.

7. [§ 2 "Re-validate the ledger at N7 with `required_inputs=` the question ids the plan marks required"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/schemas.py:validate_answer_ledger, _check_lacks, validate_build_plan; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/.claude/agents/build-planner.md § The rest of the plan]
Wrong: No field in the BuildPlan schema or the planner's output spec marks a question id as a required input; `validate_build_plan` defines none and the planner is never told to emit one.
Fails: The session either passes `required_inputs=None`, so `_check_lacks` never fires and the "mandatory on exactly the rows that need it" rule is inert, or picks an unnamed proxy such as `information_sources[].row_id` that differs per session.
Costs: The ruling-7 second verdict is silently unenforced or enforced inconsistently; medium.

8. [§ 3 N11 "Then `V.code_checks(WT, files, tests)` and `D.write_patch(WT, JOB, PERSONA)`"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/verify.py:code_checks; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:write_patch; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/SESSION.md standing rule "a live gate run dirties TRACKED fixture-persona files"; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/scripts/new_worktree.sh:--sandbox]
Wrong: The channel snapshot and `check_channels` run before `code_checks` executes the plan's tests and the sweep, and `write_patch` diffs the whole tree afterwards with no `git checkout HEAD --` of fixture paths in between.
Fails: A test that touches `data/personas/<fixture>/…` (tracked and hollow in a sandbox) puts those paths into the patch, the `patch_paths == implementer half` assertion trips with no stated recovery, and channel (a), which would have refused `data/personas/`, was evaluated before the dirt existed.
Costs: The standing rule SESSION.md records as earned twice is absent from the one sequence that generates patches, stalling N12 with an unexplained assertion; speculative.

9. [§ 1 table N14 "or a REPAIR ticket"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/tickets.py header "NO WRITE PATH FROM THE MAC EXISTS OR IS ADDED", file_ticket, tickets_path; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/ids.py:next_job_id; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/scripts/build_board.py:fetch_tickets]
Wrong: The command has N14 file a REPAIR ticket from the Mac, but the ticket file lives at `data/personas/{p}/build/tickets.jsonl` on the VM, is written only by `request_build` and `tick.py`, and the board reads a fetched copy.
Fails: Calling `T.file_ticket` on the Mac appends to a Mac-local persona tree the VM never sees, minting a `BLD-MMDD-NN` against a stale ledger that can collide with the VM's next allocation, and the board never lists it.
Costs: A failed acceptance's repair is silently lost or double-numbered; medium.

10. [§ 0 `sys.path.insert(0, ".")`, § 1 driver command, § 3 N13 step 4 `R.mark_landed(name)`, board line `cd /Users/md-homefolder/Desktop/multi-model-mcp`] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:_ROOT, jobs_root; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/registry.py:REGISTRY_PATH, mark_landed; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:_entry_model, check_tier]
Wrong: Every tree-taking call is handed `MAIN` explicitly, but `mark_landed`, `check_tier`, `M.build` and the job directory resolve `_ROOT` from wherever `core.build` was imported, and the command pins only the board's `cd` to the main tree, not the imports.
Fails: Run from a worktree session, N13 applies the patch to MAIN and hand-writes the Red half there, then `mark_landed` raises `RegistryError("no registry row")` against the worktree's registry and the tier gate reads the worktree's `routing_cloud.yaml`, mid-sitting, after Mike's prompts have been spent.
Costs: A wasted N13 sitting ending in the revert line, and a job store split across two trees; medium.
