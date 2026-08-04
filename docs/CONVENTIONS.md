# Conventions — phase review, phase testing, file naming

Process conventions that apply at **phase boundaries**, not on every session. Kept out of
`CLAUDE.md` so they are not paid for on every chat.

**Read this when:**
- Opening a new phase, or writing its review.
- Writing or amending a `tests/phase{N}_testing_plan.md`.
- Naming any generated file — report, session archive, analysis doc, plan snapshot, script output.

---

## Phase Review Convention

At the start of every phase, read the previous phase's session archives and the current plan snapshot, then produce a review in this format for each finding:

> **[Finding]** — what changed or was learned
> **→ Implication** — what this means for the plan (be specific: which section, which decision, which future work item is affected)

Checklist of categories to cover in every phase review:
- Model routing: did testing change which model goes where? Are any routing assignments now confirmed, demoted, or written off?
- Data requirements: do any planned Phase N features require more data than will exist? Call out the constraint and its implication explicitly.
- Blocking prerequisites: list them in dependency order, not by importance. What cannot start until what else is done?
- Stale plan elements: anything the plan says that is now outdated, resolved, or superseded?
- Flagged deferrals: anything that was deferred in the last phase but should be revisited now vs. left for later?

If the review produces a vague finding without an implication, rewrite it. A finding without an implication is just a summary, not a review.

---

## Phase Testing Convention

Every development phase must have a testing plan at `tests/phase{N}_testing_plan.md` before that phase begins. Testing plans are intent-driven — they verify that the phase achieved its *purpose*, not just that the built items run. Each plan includes: a statement of phase intent, a prerequisites check, intent verification criteria with explicit pass/fail conditions, and known gaps carried forward.

Testing plans for all phases (including future phases) live in `tests/`. Amend them as gaps are discovered — do not create separate gap documents.

### File naming convention

All generated files — test reports, plans, analysis docs, session archives — must have names specific enough to survive alongside similar future files without collision. Include at minimum: purpose, date, and model/provider where relevant.

**Pattern:** `{purpose}_{YYYY-MM-DD}_{qualifier}.{ext}`

Examples:
- `tests/phase4_report_2026-05-19_gpt-4o.md` ✓
- `tests/phase4_report.md` ✗ — overwritten on next run
- `archive/sessions/2026-05-19_phase4_pattern_miner_testing.md` ✓
- `archive/sessions/session.md` ✗ — meaningless after the session

Apply this to: test reports (`run_phase*.py` output), session archives, analysis documents, plan snapshots, and any file a script writes automatically. Generic names like `report.md`, `output.json`, or `plan.md` are not acceptable for generated files.

---
