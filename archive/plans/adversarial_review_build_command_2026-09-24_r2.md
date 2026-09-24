*Reviewed: `.claude/commands/build.md` (Build v4.11 phase C), first revision. Model:
Fable (the `adversarial-reviewer` default). Effort: `high`. Date: 2026-09-24.*
*Round 2 of 3 — VERIFY MODE on round 1's ten findings, resumed in the same reviewer.
Verbatim; nothing edited, reordered or softened.*

---

1. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step, _artifact_done, _gate_is_open; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:plan_versions, write_plan] With `brief.md` and `review.json` removed the walk names N10 then N8 against the new version, and the top-of-walk `len(plan_versions) > 2` park still bounds it in code.

2. NEW SHAPE — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step (`failures > MAX_NODE_RETRIES`); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:hash_delta] The kept `channels_before` baseline makes a retry re-detect attempt 1's delta, so the silencing is gone; but "a park, not a retry" is prose only — one recorded `failed` makes the driver hand out N11 attempt 2 on re-entry and § 1 says spawn it, so the park arrives one implementer spawn later than the command states, and § 3's "Do not re-spawn" is exactly the held-in-the-head park state the preamble forbids.

3. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:_artifact_done, _file_for; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:ARTIFACTS] The patch, `gates.json`, `landing` and `acceptance` are each written by a named call under the node whose cursor they are, and `climb`'s three-key validator lookup is no longer applied to code nodes.

4. NEW SHAPE — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/constitution.py:check (`(record.get("routing") or {}).get("allowed_tools")`); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:check_agent_text; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/verify.py:content_gate] `record{}` now exists and its three scanned fields reach `check_record_fields`, but `constitution.check` reads the told-not-granted grant from `record["routing"]["allowed_tools"]`, which the four-field `record{}` does not carry, so `check_told_not_granted` runs with `granted=None` and is skipped — the `granted` the command builds reaches only `check_grants_declared`.

5. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/schemas.py:_check_inventory, _check_ledger_row; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/table.py:_location] A `found` row carrying `inventory.{source,form,coverage.from,coverage.to,completeness,freshness}` and `decision` validates, nothing forbids `decision` on a non-judgment row, and `_location` renders it as `decided: …`.

6. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:MAX_ATTEMPTS_PER_JOB; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:attempts] Five `started` rows per construct job plus one send-back (+3) and two single retries (+4) is 12, under the 16 the driver counts over every row.

7. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/schemas.py:validate_answer_ledger, _check_lacks; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/.claude/agents/build-planner.md § `required_inputs[]`] The set is now a declared plan field the planner is told to emit, and `plan["required_inputs"]` fails loudly rather than silently when absent; `validate_build_plan` still does not check it, but the command no longer depends on that.

8. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:write_patch, _untracked; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/.gitignore:188 `data/personas/*/`] Tracked fixture edits are restored by the `checkout HEAD --` before the diff, and untracked fixture writes are ignored paths that `ls-files --others --exclude-standard` never emits into the patch.

9. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/tickets.py:file_ticket, tickets_path; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/registry.py:new_row `acceptance`] N14 no longer calls `file_ticket` from the Mac; the result goes on the tracked row and into `table.render(…, acceptance)`.

10. CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:_ROOT, jobs_root; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/registry.py:REGISTRY_PATH] `str(J.jobs_root()).startswith(MAIN)` is false for any `metatron-wt-*` checkout because `_ROOT` derives from the imported module's own path, so the assertion fails before a job directory is created.

## NEW

1. [§ 3 N8 send-back steps 1–4, "A second structural finding writes `v3` and the driver parks the job"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step (MAX_PLAN_VERSIONS check, `failures_for` on N8); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:plan_versions]
Wrong: The driver is asked only at step 4, after the planner has been re-spawned and `v3` written, so on the second structural finding the bound is consulted after the third planner run rather than before it — and the `rejected` row recorded at step 1 would already have parked N8 had the driver been asked.
Fails: The session spawns an Opus planner the bound exists to refuse, writes `build_plan.v3.json`, and only then learns the job is parked; no driver-issued `Step` exists for the send-back planner run, so § 2's `record started` has nothing to record against and the retry-product count under-reads it.
Costs: One unbounded planner call per parked job and a crash-rule row that cannot be written; medium.

2. [§ 3 N11 first line `./scripts/new_worktree.sh <slug> --sandbox`, step 2 "This failure earns the one retry"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/scripts/new_worktree.sh:141-145 (`already exists`, exit 1); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:retry_prompt]
Wrong: A `code_checks` failure sends the session back to N11 attempt 2, whose procedure begins by creating the sandbox that step 1 left in place, and the command neither says to reuse `WT` nor what `previous` is in `D.retry_prompt(original, previous, defects)` for an implementer.
Fails: `new_worktree.sh` exits 1 on the existing `../metatron-wt-build-<slug>`, and a session that answers by choosing a fresh slug hands the retry prompt to an implementer in an empty tree with nothing to "fix exactly".
Costs: A stalled retry at best, a from-scratch rebuild presented as a targeted fix at worst; medium.
