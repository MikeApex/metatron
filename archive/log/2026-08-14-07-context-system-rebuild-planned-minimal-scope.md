### 2026-08-14 (Context system: the premise it was built on is obsolete; minimal scope approved)

Planning session. One code change shipped — `CLAUDE.md` 551 → 546, the `HARNESS_BACKLOG.md`
obituary cut to the rule plus a log pointer, because `archive/log/2026-08-14-01`:71 already
held the deletion contract, the eleven-item tally and the dilution reasoning verbatim.

**Why the file regrew.** Traced 507 → 551 across six commits in two days. **All six were dated
incident history, not rules** — two of them the opening and closing of `HARNESS_BACKLOG.md`,
netting +23 lines for a file that existed for one day. Diagnosis: `CLAUDE.md` is the only
auto-loaded file, `PROJECT_LOG.md` is marked *"never — consult deliberately"*, so a session that
just lost work to a stale premise rationally writes the lesson where it is guaranteed to be read.
There is an entry ritual and no exit ritual.

**The founding premise is obsolete, and that is the session's real finding.** Verified against
official docs on v2.1.232: Claude Code has **three** loading tiers and this project uses one.
Path-scoped `.claude/rules/*.md` fire when Claude **reads** a matching file; subdirectory
`CLAUDE.md` loads on demand; a skill's body loads only on invocation. Official target is **under
200 lines**, and *"bloated CLAUDE.md files cause Claude to ignore your actual instructions."* So
the 546-line file is a plausible **cause** of the under-surveyed edits it was written to prevent.
`.claude/rules/` and `.claude/skills/` do not exist here.

**Believed true earlier, wrong:**

1. **`@imports` would fix it.** They load eagerly at launch — "imported files still load and
   enter the context window." The obvious fix does nothing.
2. **My own draft claimed a rule file "can carry its full incident narrative at length, because
   those lines cost nothing until someone opens an agent file."** False — when the rule fires the
   *entire file* injects. That sentence was the plan's pre-authorised regrowth vector, in a plan
   written to stop regrowth.
3. **Phase 1's history channel would work.** It greps `archive/log/`, which holds 13 fragments
   all dated 08-13/14 plus **`_history.md` at 4,369 lines** holding everything before. `get_weather`
   is 4× in the blob. The briefing would have reported "no history" for files with plenty —
   rebuilding the stale-premise failure inside the fix for it.
4. **The context gate covers edits.** [`hook_context_gate.py`:160-163] returns `None` for any path
   outside `CLAUDE_PROJECT_DIR`. A worktree is outside, so **every worktree edit bypasses the gate
   today, silently** — meaning `/backlog attack` workers, the thinnest-context sessions by
   construction, get no gate at all.
5. Fable's review claimed `InstructionsLoaded` was unverified (it is documented and real) and read
   `M CLAUDE.md` as a parallel window's work (it was this session's own edit). Both corrected.

**What the record keeping is worth, measured rather than argued.** Since A7 blocked on 2026-08-05:
**121 commits, 30 touching product, 91 harness/docs only.** Recorded catches attributed to
mechanical checks in `_history.md`: **18** — including a `fetch_url` that would have returned the
Vertex service-account token and a change that would have taken production down. Catches
attributed to narrative docs: **0**. Errors *caused* by a stale narrative premise: **6**. The
method is biased — prevention is invisible, failure is logged — but the asymmetry survives it.
**The checks earn their keep; the narrative about the checks does not.**

**Decisions.** Execute **minimal scope only**: rewrite `hook_context_gate.py` into a per-file
history briefing (including `_history.md`, worktree root resolution from the target path, a
new-file case, and an always-present governing-area pointer that survives `/compact`), plus a
~15-line regrowth branch in the existing `hook_agent_tools.py` emitting count-vs-ceiling and a
routing question at write time. ~65k tokens, one session, self-verifying. Adopted standing rule:
**no new standing harness script or hook without naming what it retires.**

**Rejected, with reasons.** The full plan — deferred, not killed: Phases 2–3 (`CLAUDE.md` → ~180
lines, four `.claude/rules/` files) and Phase 5 stay on file, because product work is the priority
and the minimal two items are the ones that protect it. Phase 4 (ROADMAP split) — surgery on a live
plan mid-A7 with a load-bearing parse anchor, for a saving only `/metatron-code` sees.
`CODEBASE_INDEX.md` retirement — depends on Phase 3 landing first. A `/metatron-code` structural
mode — a mode nobody remembers to invoke is dead weight. Extending `core/rule_classes.py` for the
regrowth check — it is runtime product code on the VM; dev-harness concerns do not belong in `core/`.
Making ceilings fail rather than warn — would fail on four files from day one, and this project has
twice concluded that blocking to enforce tidiness discards work.

**A7 unchanged by decision** — no roadmap edit. Mike works features independently and closes the
Phase before Alpha; the gate is neither deferred on paper nor treated as met. Next work is
`[DB-0810-13]`, not another process improvement.

Plan: `~/.claude/plans/create-a-plan-to-sequential-bachman.md`. Start prompt:
`archive/plans/next_session_prompt_2026-08-14c_context_gate_briefing.md`. **Not deployed** —
dev-harness only.

