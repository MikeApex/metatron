*Reviewed: `.claude/commands/build.md` (Build v4.11 phase C), second revision. Model:
Fable (the `adversarial-reviewer` default). Effort: `high`. Date: 2026-09-24.*
*Round 3 of 3 — VERIFY MODE on round 2's four open items, resumed in the same
reviewer. Verbatim; nothing edited, reordered or softened. This was the last round.*

---

NEW SHAPE 2 → CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step (`failures > MAX_NODE_RETRIES` on the N11 walk); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:failures_for; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:check_channels] On re-entry the driver hands out N11 attempt 2, step 0 re-runs `check_channels` against the kept `channels_before` with no spawn, an uncleared delta records the second `failed`, and the next `next_step` parks on the node bound — the park is now the driver's and costs no model call.

NEW SHAPE 4 → CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/constitution.py:check (`(record.get("routing") or {}).get("allowed_tools")`); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:check_agent_text, check_told_not_granted; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/.claude/agents/build-planner.md § `record{}`] With `record.routing.allowed_tools` present the grant reaches `check_agent_text` as a list and `check_told_not_granted` runs (fail-closed when `registered_tools()` is empty); `check_record_fields` does not scan the `routing` key, so nothing else in the gate is disturbed.

NEW 1 → CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step (NODES order N7→N10→N8→N9; `_artifact_done` for `brief` is `brief.md` exists); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:failures_for counts `rejected`] Keeping `brief.md` and deleting only `review.json` makes the walk pass N7 and N10 as done and stop at N8, where the second `rejected` row makes `failures_for("N8") == 2 > MAX_NODE_RETRIES` and parks before any planner spawn; the hand-built `D.Step("N7", "agent", agent=…, attempt=…)` matches the dataclass signature and `record()` writes it to `attempts.jsonl`.

NEW 2 → CLOSED — [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/scripts/new_worktree.sh:141-145 (`already exists`, exit 1); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:retry_prompt] The retry now says to reuse the existing sandbox and defines `previous` as the implementer's prior report; the unconditional creation line at the top of § 3 N11 still precedes that rule, but it fails loudly against the existing path rather than silently branching.

## NEW

1. [§ 3 N8 send-back step 3 "Record that run against N7 yourself", § 2 "the driver counts THIS"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:next_step lines 178-186 (`_artifact_done` skip precedes the `failures_for` check); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/jobs.py:plan_versions]
Wrong: A send-back planner run whose output fails `climb` records `failed` against a hand-built N7 step, but `next_step` skips N7 as done (`v1` exists) before it ever reads `failures_for("N7")`, so the one-retry bound § 2 says the driver enforces is never consulted for this run.
Fails: The session re-prompts the planner as many times as it judges, each attempt adding two rows, bounded only by the 16-row product cap rather than by the per-node bound every other subagent node has.
Costs: Up to several unbounded Opus planner spawns on a rejected plan before anything parks; medium.

2. [§ 3 N11 steps 1–3 order (channels, then `code_checks`, then `checkout HEAD -- data/personas`), .claude/agents/build-implementer.md § Before you report] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/gates.py:check_channels, is_denied (`data/personas/` prefix), porcelain; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/SESSION.md standing rule "a live gate run dirties TRACKED fixture-persona files"]
Wrong: The fixture cleanup added at step 3 runs after the channel check at step 1, but the implementer is told to run the suites itself before reporting, so any tracked `data/personas/<fixture>/…` file a test dirties is already in `porcelain(WT)` when `check_channels` runs and `is_denied` refuses it as a deny-list write.
Fails: A benign test side-effect the standing rule already names is reported as a boundary violation, the session stops, and on re-entry step 0 refuses it again from the same dirt and the driver parks the job.
Costs: A spurious park on the first job whose tests touch a fixture persona, diagnosed by Mike as an implementer escape; speculative.

3. [§ 3 N8 send-back step 2 "a second structural finding parks here"] [/Users/md-homefolder/Desktop/metatron-wt-v4c-command/core/build/driver.py:MAX_PLAN_VERSIONS, next_step (`"the review sent the plan back"` branch); /Users/md-homefolder/Desktop/metatron-wt-v4c-command/scripts/build_board.py:show_jobs; /Users/md-homefolder/Desktop/metatron-wt-v4c-command/tests/test_build_driver.py "a SECOND send-back parks the job for Mike"]
Wrong: The park now fires through N8's node-retry bound, so `build_plan.v3.json` is never written and the plan-file counter the driver, its docstrings and its tests document as the send-back's durable home never reaches the value that parks.
Fails: The board and `step.detail` report "N8 failed 2 times — one retry per node is the bound" for a job parked by a second structural finding, and anyone unparking it by the documented lever (the plan files on disk) finds two versions and a job that stays parked on `attempts.jsonl`.
Costs: A misdiagnosed park and a recovery path that no longer matches the mechanism; medium.

---
Sweep note: the `project-log` failure the stop gate reports is pre-existing and not attributable to this session. This reviewer has no write tools and edited nothing in either tree; the drift is between `archive/PROJECT_LOG.md` and its `archive/log/` fragment (the "19 commits" sentence versus the `b2b1dc7..HEAD` rewording), present identically in `/Users/md-homefolder/Desktop/multi-model-mcp` and `/Users/md-homefolder/Desktop/metatron-wt-v4c-command`, and it predates the review, the first verify pass and this one.
