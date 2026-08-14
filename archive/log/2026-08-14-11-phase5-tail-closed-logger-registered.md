### 2026-08-14 (Phase 5 tail closed: logger registered, audit tables fixed) — `b07f5da`, **not deployed**

The two pieces deferred at the previous close-out (`2026-08-14-10-rule-delivery-verified-read-only.md`),
done in a fresh session from a prepared next-session prompt.

**1. `InstructionsLoaded` logger registered**, no matcher, in `.claude/settings.json` — writes to
`.claude/instructions_loaded.jsonl` (gitignored). No `_comment_*` key was added beside it; that
was already shown 2026-08-14 to be rejected by the settings validator, so the rationale stays in
`scripts/hook_instructions_loaded.py`'s own header, per plan.

**2. `scripts/audit_context_load.py:34-49` corrected.** `CONDITIONAL` now lists the five
`.claude/rules/*.md` files with their governed paths, replacing the pre-split description that
would have scored a correct post-split session as wrong. Verified by running the script (not just
compiling it) against a real session: `ROADMAP.md` correctly showed `✗` for a session that hadn't
read it, and all five rule files showed `skipped` — correct, since rule delivery happens via
injection on a governed-path `Read`, not via a separate `Read` of the rule file itself, which is
not something this script's Read-call tracking can see and isn't a defect in it.

**What is still open, and needs a different session (and real elapsed time):** the hook exists
only to answer two questions its own header states — does the Grep *tool* trigger
`path_glob_match` (only Bash `grep` was tested, and it does not), and does rule delivery work
inside a worktree session (files are present on disk, delivery unmeasured from the main tree).
Both need entries to accumulate in `.claude/instructions_loaded.jsonl` from ordinary sessions
first. A next-session prompt for that close-out is at
`~/.claude/plans/context_phase5_close_prompt_2026-08-14.md`, written the same session as this
fragment. It restates the hook's own retirement condition: once both questions are answered,
delete the hook registration, the script, and the log file — a permanent hook logging every
instruction load is the machinery class this plan exists to reduce.

**Phase 4 (the ROADMAP split) was not started**, per the prompt. Nothing depends on it and A7 is
the blocked product gate.

