# Build v4 — the coordinating-window prompt

*Written 2026-09-24 at the close of the v4 planning session. Paste the block below into a new
Claude Code window on the Mac. It is the only prompt Mike types by hand; every phase window's
prompt comes out of the session it starts.*

---

Model: Opus 5, effort xhigh. This is a coordinating window: it plans the build, writes the per-phase prompts,
does the one Red phase by hand with me approving each edit, and builds nothing else itself.
Review sits in Fable through /adversarial-review; build sits in Opus in the phase windows.

/metatron-code first.

## What you are coordinating

Build v4.11 — `archive/plans/build_vertical_plan_2026-09-24.md`. Read it in full before
anything else; it is 997 lines and every section binds. Then read the two review files that
cleared it, for the verdicts and the reasons, not to re-review it:
`archive/plans/adversarial_review_build_vertical_plan_2026-09-24.md` (Opus, seven rounds) and
`archive/plans/adversarial_review_build_vertical_plan_2026-09-24_cold-fable.md` (Fable, cold
read, three rounds). Both ended clean. The plan's § 0 rulings are Mike's and are not reopened
here; the header paragraphs record what each review round changed and why, so if a phase window
asks "why is it built this way", the answer is there. The model rule is in `docs/WORKFLOW.md`
§ Which model runs which kind of session: plan in Opus, review in Fable, build in Opus.

## Your job, in order

1. **Confirm the tree state before phase 0.** `git status --porcelain` and `git log --oneline
   -3`. The tree carries the uncommitted phase-4 work and, possibly, another chat's headset
   files (`.gitignore`, `android/**`, `scripts/{check_apk_sync.sh,renew_cert.sh}`,
   `tests/test_turn_source_marker.py`, `DEV_BACKLOG.md`). Phase 0 commits the phase-4 files
   only, and I make that commit: prepare the exact manifest for me, `git diff` every file, and
   stop.
2. **Write the phase prompts, all of them, into one file:**
   `archive/plans/build_v4_phase_prompts_YYYY-MM-DD.md`, one `## Phase X` heading each, in this
   order: 0, A, B, B-Red, D, C, E, F. Each prompt is complete and self-contained — a window
   that receives it has none of this conversation. Each carries, in this order:
   - its **model on the first line** (`Model: Opus 5, effort xhigh.` for 0, A, B, C, D — Mike's
     choice for the build, 2026-09-24; B-Red and E are this
     window's own work and get a checklist, not a prompt; F is a walkthrough script I run live);
   - `/metatron-code first`;
   - the plan sections that bind the phase, by number, and any § 12 verification rows it must
     satisfy, quoted in full — the phase window must not paraphrase an assertion;
   - the exact files it creates, changes and deletes, from § 10, with the salvage table's
     "carry by copy" rows named where they apply;
   - the standing rules: build in a worktree from `./scripts/new_worktree.sh <slug>`; run what
     you changed, a green sweep is not a test; **never** `git commit`, `git push`, or
     `./deploy.sh`; Red files (`config/agents/*.md`, `config/modules/routing*.yaml`,
     `core/{router,persona,scheduler,spend_guard}.py`) are not touched in a phase window —
     if a phase seems to need one, stop and say so;
   - the handoff: end with `python3 ~/.claude/tools/archive_chats.py`, then a file
     `archive/handoffs/YYYY-MM-DD-build-phase-<X>.md` — what shipped, which § 12 rows passed
     with their output, what was left open — and the worktree left in place for me to read;
   - the phase's cost estimate from § 14, so the window knows when it is over budget.
3. **Hand me the prompts one at a time as I ask for them**, in full, never "the earlier one
   plus a change". After each phase window reports, read its handoff, `git diff` its worktree,
   and tell me whether the phase closed against its § 12 rows or what is left. I merge and
   commit; you never do.
4. **B-Red is yours, by hand, in this window:** `request_build` on `coordinator`'s
   `allowed_tools` in both routing files, and the `coordinator.md` § Tools available line
   written by the shape of request the plan's § 3 note specifies — every edit prompts me, that
   is the control working. Then `python3 scripts/check_agent_tools.py --agent coordinator` and
   the under-filing fixture row from § 12. Do this after phase A lands, before C.
5. **Sequencing.** 0 → A → B → B-Red → D → C → `/adversarial-review` of C's command (Fable,
   `high`) → E → F. A and B may run in parallel in separate worktrees only if I say so; default
   is sequential, because A deletes the old package and B moves `probe.py` behind the door,
   and one tree at a time is how this project avoids the 2026-08-09 shape.
6. **Phase E is mine.** Prepare the deploy checklist: the record commit is in, phases 0–D and
   B-Red merged and committed, `./scripts/qa_sweep.sh` green including the new
   `scheduler-functions-resolve` check, then `./deploy.sh`, then on the VM: the read door
   answers a presence check for `mike`, `build_tick` resolves in the scheduler log, and
   `request_build` files a ticket from a fixture turn. I run every command; you write them
   with the machine named (MacBook or VM) and full paths.
7. **Phase F is a walkthrough, not a list** — runs 1 to 3 from § 11, steps prepared in advance
   with me executing live: `/build --persona mike BLD-…` for run 1 (`home_care`), the induced
   REPAIR for run 2, the weekend-correspondence policy for run 3, each acceptance run on my
   data and on a fixture persona. Write the script for it when C has been reviewed clean.
8. **Track cost against § 14** — actual per phase from each window's handoff, beside the
   estimate. Say when a phase runs over before the next one starts.

## Rules for this window

- No code here except B-Red. No commit, push or deploy, ever, from this window.
- Do not summarise the plan back to me; point me at section numbers.
- Do not reopen the § 0 rulings or the two reviews' closed findings. A phase window that
  disagrees with the plan reports it in its handoff; the decision is mine.
- Every prompt and checklist states the machine and full paths for any command.
- Run `python3 ~/.claude/tools/archive_chats.py` after each batch of prompts is written and
  after each phase closes; `/archive` once at the end of the whole build, folding the phase
  windows' handoffs.

Start with step 1.
