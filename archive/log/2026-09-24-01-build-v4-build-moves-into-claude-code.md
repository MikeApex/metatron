### 2026-09-24 (Build v4 — Build moves into Claude Code; ten review rounds to a clean pass)

Planning session on Fable 5.1, opened 09-19 as a hosting question (which model runs the four
Build agents) and finished 09-24 as a new plan: `archive/plans/build_vertical_plan_2026-09-24.md`
v4.11, superseding v3.7 and the 09-17 v2 (`mossy-noodling-valiant`) in their entirety. Nothing
built, nothing deployed; three plan files and two doc edits are this session's whole diff.

**The turn.** The 09-19 brief offered four hosting options and asked for a criteria ranking
first. Mike ranked consistency > {cost, autonomy} > privacy; the session wrote a plan straight
from the ranking and Mike rejected it as premature — the ranking opened a discussion, it did not
close one (memory: `ranking-opens-discussion`). The discussion produced a position wider than
any option: **Build is development, not execution.** It runs in Claude Code on the Mac on the
subscription; Vertex is for user-facing execution only; Mike starts each build, approves the
plan, commits and deploys. That reverses v3's rulings 0.1 (all on the VM), 0.2 (overlay landing)
and 0.3 (no executing session), so it is a new file, not a correction.

**Rulings (§ 0, thirteen).** Inquiry in a vacuum — the manifest is the Librarian's; the Librarian
is a locator producing an inventory (found / inadequate / ask user / external / absent), with
two verdicts per row: for this persona, and for a user who lacks it (a history is asked for,
never a variable). Every question travels to the Planner and into the agent file; a code-written
question table sits beside the plan for Mike. Adversarial review replaces the Planner's
self-read. The four Build agents are Claude Code subagent definitions. `core/build/` is rebuilt
with salvage, not adapted — Mike's rule: **obsolete mechanisms are removed, the tail must not wag
the dog** (memory: `remove-obsolete-legacy-decisions`). Model rule changed generally: **plan in
Opus, review in Fable, build in Opus** (`docs/WORKFLOW.md`, replacing 08-18); the build runs at
effort xhigh.

**Options rejected.** Vertex for all four (fails consistency); Planner-only on Claude (no privacy
gained, consistency lost); all four as headless `claude -p` calls with an MCP for the Librarian
(a v4 that keeps the VM premise; and `--bare` reads only an API key, so the subscription route
cannot use it); developer-invoked nodes (kills autonomy for nothing); keeping the overlay for
config-only capabilities (two landing paths); adapting the v3 modules (their docstrings and
tests encode the VM premise).

**Believed true, turned out wrong — by the reviews.** The harness's deny/ask rules reach a
worktree (they are `./`-anchored; they do not); `git status` sees the paths the deny list names
(gitignored, it cannot; `-uall` also needed); `git apply --3way` leaves hunks unstaged (implies
`--index`); the runner was VM-premise code (its control layer is not, and is salvaged); the
subagent-stop gate only sweeps the stopping worker's tree (it sweeps every dirty worktree in
every window); a subagent's cwd is its worktree (it is the main tree). Ten rounds: Opus reviewer
seven (ten findings, then two, two, two, one, one, none), fresh Fable cold read three (seven,
then two, one, none). Both files in `archive/plans/`.

**Handoff carried in.** Phase 4 uncommitted by instruction; v4's phase 0 is that record commit,
by Mike. The two v3 build windows are abandoned (transcripts captured first). Next: paste
`archive/plans/build_v4_walkthrough_prompt_2026-09-24.md` into a new Opus window.

