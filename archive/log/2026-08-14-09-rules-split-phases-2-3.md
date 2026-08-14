### 2026-08-14 (the always-on tier splits into five path-scoped rule files) — `275bc51`, `c1ac03b`, **not deployed**

Executed Phases 2 and 3 of the context-system plan in one commit, as the plan required: a rule
cut from `CLAUDE.md` but not yet firing from `.claude/rules/` is live nowhere. Dev-harness only;
`core/` and `config/` untouched, `./deploy.sh` never invoked. The approved minimal scope
(Phase 1 + regrowth branch) had closed at `8981862` earlier the same day; Mike asked for
re-verification and, absent strong blockers, execution of 2–3.

**What changed.** `CLAUDE.md` 554 → 282. The area rules moved to
`.claude/rules/{agent-files,personas,orchestrator,deploy,docs-and-logs}.md` (547 lines total)
with rationale intact and in places expanded — the compression pressure that had been mangling
it is what the split removes. What stayed in root is what must survive `/compact`: the privacy
ruling, the Denied tier, terminology, the four-tier hierarchy, the seven infrastructure traps,
the design decisions. A **rules index** replaces the relocated sections, so a session never
handed a rule still knows it exists and can read it in one call — the plan's answer to
high-level structural work, and its most important line item.

**Four defects found by re-verifying premises, each of which would have shipped a silently
broken split.**

1. **`_rule_file_for()` could not parse the documented block-list `paths:` form** — only the
   inline one. Probed in a temp tree *before* trusting it: block list returned `''`, inline
   worked. Every rule file written the documented way would have been invisible to the
   write-time briefing, silently, while a hand-tested inline probe passed.
2. **`.claude/*` is gitignored with an allowlist**, so the five rule files would never have been
   committed. `git worktree add` checks out tracked files only — the rules would have been
   **absent from every worktree**, re-creating the exact `/backlog attack` bypass that
   `8981862` had closed hours earlier, in the commit meant to complete it.
3. **Nine stale cross-references** to relocated sections — the `GOVERNED` table, both hooks,
   `check_agent_tools.py`, `/backlog`, `SESSION.md`, and one inside `CLAUDE.md` itself.
4. **`check_named_paths()` read only `CLAUDE.md`**, so the split dropped it 36 → 28 claims. The
   doc-rot class followed the text into the rule files, so the check now does too: **43/43**.

**Believed true and wrong: that ~180 lines was reachable.** The plan's own keep-list
(infrastructure traps, change tiers, terminology, four-tier hierarchy, privacy tiers, design
principles, design decisions) sums past 200 on its own, and that arithmetic was never done when
the target was set. Trimmed everything genuinely compressible, stopped at 282, and reported the
gap rather than deleting safety-binding content to hit a number.

**Options rejected, with reasons.** Moving the infrastructure traps to `deploy.md` to reach 200
— they are the ones that fail *silently*, and the session that trips them (deleting the VM's
external IP, a billing hard-cap) may touch no governed file at all, so nothing would fire.
Setting the ceiling to 200 and living with a standing WARN — a ceiling the file permanently
violates trains the reader to skip the output, the failure this repo documents repeatedly;
**Mike set 300 instead**, a hard limit with headroom for recording a new binding rule, and
`CLAUDE.md`'s own header was changed in the same pass so the two copies cannot disagree.

**`hook_commit_guard.py` blocked its own enabling commit, and that was a real defect.**
`_status()` read `git status --porcelain=v1` without `-uall`, so git collapses untracked files
in a *wholly new* directory to one `newdir/` entry; the five rule files staged by name matched
nothing in the pool, landed in `unresolved`, and the guard failed closed on files with no other
writer. It needed `METATRON_COMMIT_GUARD=off` to land — **an override trained by a false
positive, which is how an escape hatch becomes routine.** A new file in an already-tracked
directory is listed individually, which is why this survived every previous new file. Fixed at
`c1ac03b` and verified against a throwaway repo reproducing the exact shape.

**Not verified, and it cannot be in this session: whether a path-scoped rule is actually
delivered.** `.claude/rules/` is discovered at session start, so reading a governed file here
fired nothing — expected, not a defect. That, and whether a **Grep-only** survey counts as a
read (load-bearing for `/backlog attack` workers and Explore agents), are Phase 5 in a fresh
session. Prompt written to `~/.claude/plans/context_phase5_prompt_2026-08-14.md`. **Nothing was
retired** — `CODEBASE_INDEX.md` still loads, gated behind Phase 5 as the plan requires.

**Phase 4 (ROADMAP split) re-checked and still valid but still deferred**: `ROADMAP.md` is 535
lines, Section 2 is 341 of them, the `metatron-code.md` parse anchor is intact. Nothing depends
on it, and A7 has been the blocked product gate since 2026-08-05 with the last four sessions all
harness work.

**Verified:** `qa_sweep.sh` 9/9, `check_claude_md_claims.py` 43/43, both hooks observed firing
live throughout (the briefing resolved `governed by .claude/rules/docs-and-logs.md`; the
regrowth branch labelled each new file `PATH-SCOPED`), parser probe passes all three YAML forms.

