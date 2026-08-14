### 2026-08-14 (the context gate becomes a per-file briefing, and stops skipping worktrees) — `8981862`, **not deployed**

Executed the approved minimal scope of the context-system plan — Phase 1 plus the regrowth
branch, nothing else. Phases 2–5 stay deferred by decision, not oversight. Dev-harness only;
`core/` and `config/` runtime untouched and `./deploy.sh` never invoked.

**What changed.** `scripts/hook_context_gate.py` (201 → 661) replaced its single generic
warning with a per-file briefing: permission tier, governing area, open `DEV_BACKLOG.md` items,
five commits, and up to five `archive/log/` excerpts anchored on the nearest `### ` heading.
Once per file, warn-only, oldest-first truncation. `scripts/hook_agent_tools.py` (+97) gained a
regrowth branch on `CLAUDE.md` and `.claude/rules/*.md` emitting count-vs-ceiling and the
routing question. `CLAUDE.md` § Mandatory Pre-Edit Context Check described the hook as only a
SESSION/ROADMAP warning and was corrected in the same commit (551 → 554).

**The worktree bypass is fixed and was verified against the old code, not asserted.** The root
was resolved from `CLAUDE_PROJECT_DIR`, so a worktree failed `relative_to()` and the hook
returned `None` — `/backlog attack` workers, the thinnest-context sessions by construction, got
no gate at all. Root now resolves from the target path. Ran the pre-change hook and the new one
against the same worktree path: silent before, full briefing after. Membership is checked via
`--git-common-dir`, which every worktree shares with its main tree; tested with a real second
repo containing an identically-named `core/persona.py`, correctly ignored.

**The verification step run before writing code was worth it, and it sharpened the premise
rather than confirming it.** The plan said a fragment-only grep *fails to surface* the
`get_weather` history for `config/agents/logistics.md`. It does not fail — it returns two
08-14 files, both of which are *commentary on the stale worked example*, while the actual
grant/documentation split is four hits in `_history.md`. That is worse than returning nothing,
because it looks like a hit. Fragments are two days deep; the blob holds everything before.

**Three things believed true that testing killed.**

1. **Anchoring repo membership on `__file__` alone.** It returned `None` whenever the script ran
   from outside the tree — found immediately under test. Both `__file__` and
   `CLAUDE_PROJECT_DIR` are now accepted; either alone is a single point of failure.
2. **Truncation "oldest-first" that dropped everything at once.** `DECISION HISTORY` was one
   block, so a tight cap took all five excerpts together. That is not truncation, it is loss.
   Each excerpt is now its own block; `TIER` and `GOVERNED BY` survive down to a 200-char cap.
3. **The regrowth message asserted "this file loads into every session"** — false for a rule
   file carrying `paths:` frontmatter, which is the entire point of Phase 3. A false claim
   inside the one message written to stop rules accumulating where they are not paid for.
   Path-scoped files are now labelled as such, with the cost stated correctly.

**Options rejected, with reasons.** Emitting the planned `.claude/rules/agent-files.md` as the
governing pointer — Phase 3 is deferred and that directory does not exist, so it would be the
`config/frameworks.md` failure this file already documents; the briefing names the live
`CLAUDE.md` section instead and picks up a rule file automatically if one appears. Copying the
ceiling numbers into the hook — a second copy drifts and the stale copy keeps being reported,
so `CEILINGS` is imported from `check_claude_md_claims.py`. One excerpt per *hit* — chose one
per `(file, heading)`, because the heading is the session and one pointer per session is the
useful granularity; the briefing is a pointer into the log, not a substitute for reading it.

**Nothing was retired**, consistent with the standing rule adopted with this plan, and nothing
needed to be: both scripts already existed.

**Verified same-session:** `qa_sweep.sh` 9/9 (3.2s), `check_claude_md_claims.py` 36/36. A sweep
of 97 governed files produced zero non-zero exits and a 6,421-char maximum against the
9,500-char budget, so the cap is headroom rather than a live constraint. Verification 3 and 4
were run as real `Write`/`Edit` calls, not synthetic payloads — both hooks fired in the harness.

