# Build — the vertical that constructs Metatron's capabilities

*Plan v4.11, 2026-09-24 — v4 revised eleven times the same day; v4.11 is instructional only
(Mike's note on the Coordinator under-filing, § 3 and § 13.14, no mechanism changed) after the adversarial review at
`archive/plans/adversarial_review_build_vertical_plan_2026-09-24.md` (Opus 5, effort high; ten
findings, all addressed, itemised at the end of this header; the verify round then closed all
ten and raised two the revision itself had introduced, addressed in v4.2 below). Supersedes v3.7 (`archive/plans/build_vertical_plan_2026-09-18.md`),
which stays on disk as the record of phases 1–4 and their three review rounds. Written by
Fable 5.1 from a two-session discussion with Mike (2026-09-19 and 2026-09-24); the discussion
itself is in the transcripts and the project log. Every code claim was re-checked against the
working tree at `4ae71a9` plus the uncommitted phase-4 files.*

**What changed from v4 to v4.1, by finding.** (1) The control layer — node order, the one
retry per node, the review's one send-back, the artifact cursor, parking — is **salvaged Python**,
`core/build/driver.py`, not a markdown command; the command calls it and can hand out no step
the driver refuses (§ 3, § 7, § 10, § 12). (2) The implementer never touches a Red file: the
plan's `registration[]` — routing entries, the Coordinator directory line, the generated agent
file, knowledge domains, scheduler — is written by the main session, where the `ask` rules are
measured to prompt; nothing Red is delegated (§ 3 N11, § 7). (3) The harness's deny rules are
`./`-anchored and do not reach a worktree, so the writer's deny list is **salvaged into
`gates.py`** and the driver applies it to the worktree's diff before anything is accepted; the
claim "no second copy" is withdrawn (§ 6, § 12). (4) Nothing is deleted until the new modules
it calls exist: phase 0 is the record commit only; the deletion is phase A's last step, after
`tools/build.py` and `_DEFAULT_JOBS` are re-pointed, with a new sweep check that every
scheduled function resolves (§ 10, § 16). (5) `scripts/check_build_registration.py` is on the
written-fresh list, rewritten before the writer goes (§ 10). (6) The table is rendered before
the review, and the reviewer is spawned on the brief, which carries plan and table in one file
(§ 3). (7) The two state homes are sequenced: a ticket stays open on the VM until its registry
row deploys, so duplicates are refused throughout; the capability and its row arrive in the same
deploy; only `abandoned` lags, bounded by the cap and named on the board (§ 5). (8) The call
table is `manifest._SOURCES`, salvaged from the right file (§ 10). (9) The presence check takes
a source id and uses the salvaged fixed arguments; research reads validate arguments
server-side against per-tool schemas and caps; **no outbound tool sits behind a door** (§ 6).
(10) An `all_personas` variable is the template entry for future personas plus the runtime ask
path for existing ones, stated as such (§ 4).

**What changed from v4.1 to v4.2, by the verify round.** (NEW 1) A build's diff no longer lives
in two trees: after N12 passes, the driver turns the implementer's worktree changes into a
**patch**, the main session applies it to the main tree and writes the Red half there, and Mike
reads one `git diff` and makes one commit — the worktree was only ever the sandbox (§ 3 N12,
N13). (NEW 2) The implementer's worktree is created **`--sandbox`**: no link-back of `.env`,
`vertex-key.json`, `certs/` or `settings.local.json`, so nothing in it reaches the main tree;
and the driver's gate reads three channels, not one — the porcelain for tracked paths, a
before/after hash of the worktree's gitignored deny-list paths, and a before/after hash of the
main tree's credential files (§ 3 N12, § 6, § 12). Residuals: the retry and send-back counts
have a durable home, `attempts.jsonl` in the job directory (§ 3); `/build` spawns the reviewer
agent directly and lands its report in the job directory, so nothing tracked is written before
[N9] (§ 3 N8); the `READ_CAP` sentence is corrected (§ 6); the `all_personas` validation rule
has its assertion (§ 12).

**What changed from v4.2 to v4.3, by verify round 2.** (NEW 1) The wiring checks now run where
both halves exist: after the patch and the Red half land in the main tree, the driver runs
`check_build_registration.py`, `check_agent_tools.py` and the full sweep there and prints the
staging manifest only on green — a `time_director`-shaped omission is refused at N13, not read
off a diff (§ 3 N13, § 12). (NEW 2) The patch is built without a staging verb — `git diff HEAD`
for tracked files plus a `--no-index` diff per untracked file, no `add`, `commit` or `stash` —
so the commit guard's watched verbs are never issued in the worktree, whichever process runs
git; and channel (b) excludes the harness's own `.claude/.session_edits/` manifest so the
implementer's edit records do not trip the deny hash (§ 3 N12, § 12). Named residue accepted:
the deny hash is an enumerated path list, and a `python3 …` grant can in principle write outside
both trees — Mike's read of the single diff and the fact that nothing outside `files[]` ships
are the bound.

**What changed from v4.3 to v4.4, by verify round 3.** Both findings were my gates colliding
with the harness's own bookkeeping. (NEW 1) Channel (b) no longer hashes `.claude/**` with
exclusions — a wildcard over a directory the harness writes markers into (`.session_state/`,
`.session_edits/`) would refuse every build on its first edit. It hashes an **enumerated list**
of the deny list's `.claude` entries — `settings.json`, `settings.local.json`, `agents/`,
`commands/`, `rules/` — and nothing dot-prefixed (§ 3 N12, § 12). (NEW 2) The wiring gate runs
the **capability-scoped** checks, not the whole sweep over a tree another chat shares: the
registration checker for this capability, the agent-tool check over the uncommitted diff (which
is how it already scopes), and a syntax check over `files[]`. The full sweep runs too but is
**advisory** beside the manifest; an unrelated red is reported, never withholds. On a red
wiring gate the driver prints the exact per-file revert command for the manifest's paths, so a
half-landed capability can be taken back out of the shared tree in one line (§ 3 N13, § 12).

**What changed from v4.4 to v4.5, by verify round 4.** (NEW 1) `.git/` is on the salvaged deny
list and was missing from channel (b)'s enumeration — and in a worktree `.git` is a pointer
into the main repository, so a hook written through it runs under Mike's own commit. Channel
(c) now hashes the main repository's `.git/hooks/`, `.git/config` and `.git/info/` and the
worktree's `.git` pointer file before and after N11, and the § 12 row plants a hook to prove
the refusal (§ 3 N12, § 12). (NEW 2) The scoped agent-tool check is
`check_agent_tools.py --agent <name>` — the script's own flag — not the diff-scoped PostToolUse
hook, which exits 0 by design and cannot gate; the header's earlier sentence attributing the
scoping to the script is corrected here (§ 3 N13).

**What changed from v4.5 to v4.6, by verify round 5.** One item: a § 12 test row said the
driver's refusal *restores* the main repository's hook directory. It does not and must not —
channel (c) is a hash and the driver holds no write path into `.git/` anywhere. On a delta the
driver refuses, names the path on the board, and stops; removing a planted hook is Mike's hand.
The row now asserts exactly that, plus that the driver itself made no write under `.git/`
(§ 3 N12, § 12).

**What changed from v4.6 to v4.7, by verify round 6.** One stale phrase: the § 12 Gates row
still said a deny-list hit is refused "with the worktree discarded", a v4.1 leftover. The
mechanism has said since v4.2 that a refusal leaves the worktree in place for Mike to read —
the refusal is exactly when the evidence must survive. The row now asserts the worktree is
untouched after the refusal (§ 12).

**What changed from v4.7 to v4.8, by the fresh cold read** (Fable 5, no memory of the Opus
rounds; `archive/plans/adversarial_review_build_vertical_plan_2026-09-24_cold-fable.md`; its
finding 7 was already closed by v4.7). These six come from the two-chat, multi-persona reality
of this tree rather than from the mechanisms' internal logic. (1) N13 no longer assumes a clean
main tree at the sandbox's base commit: the driver refuses to start it unless every path the
patch touches is clean in the main tree — another chat's dirt *elsewhere* is irrelevant — applies
with `--3way` when HEAD has moved, restores the patch's own paths to HEAD on a conflict (they
were verified clean seconds before), and **N13 is one unbroken sitting** ending in Mike's commit
or the printed revert; hunks are never left in the shared tree (§ 3 N13). (2) The registration
checker cannot see wiring in a worktree that by design has none, so the registry row is written
`status: staged` at N11 and flipped to `landed` by the main session at N13; the checker asserts
wiring only for `landed` rows and `check_build_registration.py` is not what N12 runs — N12 is
code checks; N13 is the wiring and content gate (§ 4, § 3 N12/N13, § 12). (3) The trigger —
`request_build` on the Coordinator in both routing files plus the `coordinator.md` line saying
when to file a gap instead of a `ROUTING_MISS` — is Red work with a phase, a model, a cost line
and a test row, not a word on the deploy line (§ 14, § 16, § 12). (4) A subagent's cwd is the
main tree, so a relative-path write lands there unseen by three channels that watch the sandbox:
the implementer is handed the worktree as an absolute path and forbidden relative paths (the
`/fix` rule), and a fourth channel snapshots the main tree's dirty-path set before and after N11
and refuses on any newly dirty path in `files[]` (§ 3 N12). (5) Ticket ids are allocated per
persona ledger, so everything on the Mac is persona-qualified — `/build --persona mike BLD-…`,
`data/build/jobs/<persona>/`, a `persona` field on the registry row — and a fixture persona's
tickets are never built unless named (§ 5, § 7). (6) `hook_subagent_gate.py` sweeps every
registered dirty worktree at every subagent stop in every window; a parked Build sandbox would
stall every worker everywhere. The sandbox registers under `../metatron-wt-build-<slug>` and
the gate skips that prefix, because the driver runs the sweep at N12 itself; a tool-less Build
subagent handed a pre-existing main-tree red as its stop reason is treated by the driver as done
when its artifact validates (§ 3 N11, § 10).

**What changed from v4.8 to v4.9, by the cold reviewer's verify round.** (NEW 1) `git apply
--3way` implies `--index`, so the moved-HEAD branch staged what it applied and the printed
`git checkout -- <path>` would have restored the applied content from the index, not HEAD. Now:
the cleanliness precondition covers **every path in `files[]`, both halves** — the Red targets
`routing*.yaml` and `coordinator.md` included, the 2026-08-09 file among them; after a
`--3way` apply the driver runs `git reset -q -- <paths>` so the index matches HEAD and the
hunks sit unstaged; and the revert line is `git checkout HEAD -- <path>` (from HEAD, never the
index) plus `rm` for new files, then `git reset -q -- <paths>` — correct in both branches and
after a conflict (§ 3 N13). (NEW 2) Channels (a) and (d) read `git status --porcelain -uall`,
the commit guard's own lesson: without `-uall` a new file in a new directory collapses to
`dir/`, which matches nothing — a false park on the first capability that adds a package, and
a hole in channel (d) (§ 3 N12, § 12).

**What changed from v4.9 to v4.10, by the cold reviewer's second verify round.** One item:
`git apply --3way` is not atomic — new files and clean hunks land before the conflicting hunk
stops it — and the conflict-park restore used only the checkout form, which cannot remove a
file that does not exist at HEAD. The conflict park now runs **the same full revert as the
wiring gate**: `git checkout HEAD --` for pre-existing paths, `rm` for the patch's new files,
`git reset -q --` for all of them; one function, `driver.revert_landing(paths)`, used in both
places so the two cannot drift (§ 3 N13, § 12).

**Why a new file and not a correction.** v3 rested on three rulings — all of Build runs on the
VM, landing is an overlay because nothing on the VM may write a tracked file, and the executing
session is removed because nothing on the VM writes code. Mike reversed the premise under all
three on 2026-09-19/24: **Build is development, not execution.** It runs where development runs,
in Claude Code on the Mac, on the subscription, with Mike committing and deploying what it
produces. Once that is true, the overlay, the writer's tracked-file refusal, the VM-side runner
and the per-job dollar tripwire are answers to a question nobody is asking. Mike's rule for that
case (2026-09-24): *legacy decisions rendered obsolete by larger planning decisions are removed,
so the tail does not wag the dog.* This document therefore says, for every piece phases 1–4
built, whether it is kept, changed or deleted (§ 10).

---

## 0. Rulings this version is built on (Mike, 2026-09-19 → 2026-09-24)

1. **Build is development, not execution.** User use and the systems supporting it are
   execution and run on the VM. Build — Inquiry, Librarian, Planner, review, implementation —
   runs in Claude Code on the Mac, on Mike's subscription. **Vertex is not the place to accrue
   Build's cost**; no Build node calls a Vertex model. Reverses v3 ruling 0.1.
2. **Consistency decides** (criteria ranked 2026-09-19: consistency > {cost, autonomy} >
   privacy). The same models that write every agent file and every tool write Build's outputs,
   inside the same ecosystem of rules, skills and review. **The four Build agents are Claude
   Code subagent definitions, not runtime agent files.** Models (Mike, 2026-09-24, replacing
   the 08-18 plan-in-Fable rule generally): **plan in Opus, review in Fable, build in Opus** —
   Inquiry, Librarian, Planner and Implementer on Opus 5; adversarial review and coherence on
   Fable 5. The reviewer is then a different model from the planner, which is the independence
   the review is for.
3. **Build produces code.** After Mike approves a plan, an implementation pass in a worktree
   writes the code, the tests, the agent file and the wiring, in one diff. Reverses v3 ruling
   0.3; `kind: tool`, `function_job`, `check`, `context_block` are back in v1, and the
   `needs_tool` brief is gone.
4. **Mike commits and deploys.** Implementation stops at a reviewed diff in the worktree — the
   `/fix` contract. The overlay landing path is **retired**, with everything that existed only
   to serve it (§ 10). Everything Build makes lands as ordinary tracked files.
5. **Inquiry works in a vacuum.** It sees the gap and nothing about what data exists. The point
   is to find where existing data is inadequate, even when the decision is then taken on
   incomplete data. The Librarian is the locator and produces an **inventory** — what exists,
   in what form, over what period, how complete, how fresh, and what is missing — with a fifth
   verdict, **external**, for answers obtainable only from outside the persona's data.
6. **Every question travels.** Settled or not, each question's row reaches the Planner and
   is cited by it, and the generated agent's "where to find your information" section is
   written from those rows. The reviewer sees the whole question table beside the plan.
7. **Two verdicts per row.** What the Librarian found *for this persona*, and what the
   capability does *for a user who lacks it*. A history is asked for, never assumed and never a
   variable; a profile fact becomes a variable; an external source states its failure
   behaviour.
8. **The plan is reviewed before Mike sees it.** `/adversarial-review` of the BuildPlan replaces
   the Planner's advisory self-read (v3's N8b). Its findings travel with the plan.
9. **Mike starts each build by hand** for now; a poller can come later. The under-$1 API
   allowance for single steps is recorded as a parameter with no consumer.
10. **Privacy.** Build's data reaches Anthropic through the same subscription that already sees
    every development session. Recorded in `ROADMAP.md` § Section 0 (§ 8 below); the terms
    check is done and recorded, and does not gate.
11. **The Mac searches the VM through read doors.** Read tools run on the VM where the data
    is; only results cross. Built as the Librarian needs them, starting from its read set.
12. **Wired, then tested on the VM.** The grant and the Coordinator entry ship in the same diff
    as the code; acceptance runs on the VM after deploy, on Mike's data and on a fixture
    persona with no history.
13. **`core/build/` is rebuilt, with salvage, not adapted** (Mike, 2026-09-24). The v3 modules
    were reviewed and fixed three rounds *for the VM-and-overlay premise*, and their docstrings,
    persona-scope handling, job binding and tests all encode it. Adapting them is the case
    ruling 4's tail-and-dog rule describes. The premise-free pieces are carried across by copy
    (§ 10) — including the runner's control layer and the writer's deny list, which know nothing
    of where they run; everything else is written fresh against this plan; the old package is
    deleted as the last step of phase A, after a record commit of the phase-4 tree and after
    every caller has been re-pointed.

---

## 1. Context — what Build is for (unchanged)

Metatron's capability surface is fixed by hand. The Coordinator chooses among the specialists
named in `coordinator.md`; when something arrives that fits none of them a `ROUTING_MISS` is
written and waits for a human. Build is the consumer of that signal: it takes a gap and returns
a capability, moving Mike from author to approver. The four standing requirements from v3
carry over on their own merits — trace contract, coherence review, rebuildable state,
constitution alignment at generation time — and § 2's three constraints (altitude, latency,
tiering) are unchanged and not restated here; read them in v3.7 § 2.

**Mike's five-step picture (2026-09-24), which this plan is written to match:** Coord flags what
it cannot do; Inquiry writes the ideal questions; the Librarian finds what exists and what is
missing; the Planner presents one plan — the agent file, where it gets its information, new
variables, the code, and the Coordinator access; Implementation executes on approval and it is
tested on the VM.

---

## 2. The shape — what runs where

```
 VM (execution)                              Mac (development, Claude Code)
 ─────────────────────────────               ──────────────────────────────────────────
 request_build → tickets.jsonl  ──fetch──►   /build  picks a ticket
 build_tick: REPAIR counter,                    N2 Inquiry        (subagent, no tools)
   dispatch counts                              N4 Librarian      (subagent; read doors)
 read doors: /monitor/tool                   ◄──doors──  [N6] interview, in chat
   (allowlisted read tools,                     N7 Planner        (subagent; reads the code)
    presona-bound, results only)                N8 review         (/adversarial-review)
 registry: config/build/registry.yaml           [N9] Mike approves — plan + question table
   (tracked, deployed)                          N11 Implementation (subagent, worktree)
                                                    code · tests · agent file · wiring · sweep
 ./deploy.sh (Mike)            ◄──commit──      [N13] Mike reads the diff, commits, deploys
 acceptance on the VM, two personas             N14 close — registry row in the same diff
```

**The VM keeps four jobs and nothing else:** filing tickets (`request_build`, and the code-written
REPAIR trigger at ×3 corrections), serving the read doors, counting dispatches for the registry's
run line, and running the capability once deployed. **The VM never runs a Build model call.**

**The Mac holds the job.** Artifacts — question set, answer ledger, plan, review, question table —
live under `data/build/jobs/BLD-…/` on the Mac: gitignored (one new line), persona-derived, and
kept because the ledger is the capability's specification and REPAIR reads it back. This is the
first persona-derived data the Mac holds by design; ruling 10 covers it, and the standing rule that
persona *config* is VM-owned is untouched — nothing here is loaded by the runtime.

**State is in two places, deliberately.** The ticket file on the VM is the inbox. The tracked
registry (`config/build/registry.yaml`, committed with the capability) is the state — which ticket
became which capability, when, at what version, and `abandoned` rows for tickets Mike closed
without building. The VM reads the deployed registry for dedupe windows and REPAIR eligibility;
the board joins the two. No write path from the Mac to the VM exists or is added.

---

## 3. The node graph

The rule that generates it is unchanged: a node is an agent only if its output is a judgement
no procedure can produce; everything else is code. What changed is *who runs the agents*:
Claude Code subagents, spawned by a `/build` command **that takes its every step from
`core/build/driver.py`** — the runner's control layer, salvaged (§ 10). The driver reads the
job's artifacts, decides the next node, enforces the one retry per node and the review's one
send-back from durable artifact counts, parks the job on a second failure, and refuses to hand
out a step from a gate state. The command spawns what the driver names and records what came
back; a model cannot skip a park or add a retry, because the driver will not name the step
(review finding 1). **The counts have a durable home:** the driver appends one row to
`data/build/jobs/BLD-…/attempts.jsonl` — node, attempt number, outcome, defect list — *before*
it names a step, and every bound is re-derived from that file, so a failed node that wrote no
artifact still counts and a lost session cannot reset anything.

```
 request_build (tool: Coordinator; theme routers later)
        │                              ┌────────── HUMAN GATES ──────────┐
        ▼                              │ start · N6 interview · N9 approve · N13 commit │
 N0 ticket (VM) ─► /build BLD-… ─► N2 INQUIRY ─► N4 LIBRARIAN ─► N5 ledger check ─► [N6]
    (code)         (Mike, Mac)       (subagent)     (subagent,        (code)
                                     in a vacuum     read doors,
                                                     presence check)
    ─► N7 PLANNER ─► N10 table+brief ─► N8 REVIEW ─► [N9] ─► N11 IMPLEMENT ─► N12 gates+sweep
       (subagent)     (code)             (/adversarial-         (subagent: Amber/    (driver, on the
                                          review, on the         Green files in the   worktree diff)
                                          brief file)            worktree; main
                                                                 session: Red files)
    ─► [N13] Mike commits, deploys ─► N14 acceptance on the VM, two personas ─► registry row

 N1r dossier (code, REPAIR only)      NC coherence (subagent, periodic, /build coherence)
```

**Gone from v3:** N1 manifest as Inquiry's input (ruling 5 — the manifest is the Librarian's,
§ 4), N3 probe-and-condense as a node (the presence check is a door the Librarian calls; the
Librarian condenses as it reads), N8b self-review (ruling 8), the writer's apply/verify as the
landing (ruling 4), `awaiting_approval` on cost (no dollar tripwire on a subscription, § 8).

**N2 Inquiry — in a vacuum.** Input: the gap text, the trigger, the mode, and in REPAIR the
dossier. **No manifest, no data, no tools.** Output: the Question Set, ordered spine, altitude
disposition, depth. The compass rule and its fixture are unchanged (v3.7 § 4, § 15). What leaves
the artifact: `candidate_sources` and `manifest_fingerprint` — Inquiry cannot name sources it has
not seen. `depth: triage` survives, but the policy match that justifies it is made by the
Librarian, not Inquiry: Inquiry may *propose* triage; the Librarian confirms a standing policy
covers the class or the job runs at `standard`.

**N4 Librarian — locator, then adjudicator (Mike's ruling 1 of 2026-09-18, unchanged).** Input:
the Question Set, the manifest (what sources exist, as ids and descriptions — built by code from
the registered tool set and the persona tree's structure), the standing policies. Tools: the
read doors (§ 6), including the presence check. For each question it produces the **inventory
row** (§ 4). It reads as much as it needs; there is no reading ration. A broken read is
troubleshot before it is recorded (ruling 2 of 09-18); a poison pill — the plan cannot be built
honestly without the data — is raised to Mike; otherwise the row carries a deferred binding.

**N5 ledger check (code).** Validates the ledger, computes `interview_items` (every row whose
verdict is `ask_user`) and stops at **[N6]** if any exist. The interview happens **in the build
session, in chat** — Mike is the reviewer sitting in front of it. `answer_interview_item` and
its Synthesizer grant are retired (§ 10).

**N7 Planner — plans, never creates (ruling 4 of 09-18, unchanged).** Input: the Question Set
and the full ledger (ruling 6), the registry, and **read access to the codebase** — it must
direct the new agent at the correct existing tools and code, which means opening them. Output:
the BuildPlan (§ 4), citing a question id and a ledger row at every decision gate; a plan with an
uncited gate fails validation.

**N10 the question table and brief (code) — rendered BEFORE the review.** From the ledger and
the plan, never written by a model: one row per question — id, text, class, verdict for this
persona, location or answer, behaviour when a user lacks it, status, and the plan items that
cite it. Two derived sections: **questions that shaped nothing** and **plan items no question
supports.** The brief is one file carrying the plan, the table, the cost estimate and the
risks. It is not redacted — the reader is Mike in his own session; v3's redaction existed for a
brief written on the VM.

**N8 review.** `/build` spawns the **`adversarial-reviewer` agent definition directly**, with
the same three-line prompt `/adversarial-review` sends — the brief's path, `high`, the repo root
— and nothing else, so the table reaches the reviewer by being in the file it is handed
(finding 6). The driver lands the report in the job directory, not in `archive/plans/`, so
nothing tracked is written before [N9]; the `/adversarial-review` command itself stays what it is,
a tool for plans. Fable. The two ranked blocks are appended to the brief by the driver. A structural finding sends the plan back to N7 once (rung 2, the rejected plan plus
the findings, then N10 again); a second failure parks the job for Mike. The send-back count is
the number of `build_plan.v*.json` artifacts on disk, so it survives a lost session.

**[N9] Mike approves**, edits the plan file directly if he wants (the plan-mode convention), or
refuses. Nothing before this point touched the repo.

**N11 Implementation — two writers, split by tier (finding 2).** The plan's `files[]` is
partitioned by the tier table in `.claude/settings.json` at N7, and a plan that puts a Red
path in the implementer's half fails validation.

- **The implementer subagent (Opus 5), in a sandbox worktree** — `scripts/new_worktree.sh
  --sandbox <slug>`, a new flag: links `.venv` only, and **does not link back `.env`,
  `vertex-key.json`, `certs/` or `.claude/settings.local.json`** (verify NEW 2), so a write to
  any of those paths inside the worktree creates a local file that goes nowhere. It writes the
  Amber and Green files: code, tests, the acceptance test, the registry row. Its Bash grant is
  the test and sweep commands (`python3 …`, `pytest …`, `./scripts/qa_sweep.sh`, `git diff`,
  `git status`); it never runs `deploy.sh`, `git push`, `git commit` or `git add`. **Its prompt
  carries the worktree's absolute path and forbids relative paths** — a subagent's cwd stays
  pinned to the main tree (`hook_commit_guard.py`'s own note), so a relative `Write` lands
  there; the `/fix` command's rule for workers, applied here (cold read 4). The sandbox is
  registered under `../metatron-wt-build-<slug>`, a prefix `hook_subagent_gate.py` skips (cold
  read 6, § 10): the driver runs the sweep at N12 itself, and a parked sandbox must not stall
  every other window's workers at their stop.
- **The main session** — the `/build` session Mike is in, where the `ask` rules are measured to
  prompt — writes the plan's `registration[]` block **in the main tree, after the patch lands
  (N13)**: both routing entries, the Coordinator directory line and valid-name paragraph, the
  generated `config/agents/*.md`, the knowledge-domain entry, any scheduler entry. Each prompts
  Mike as it is written. Nothing Red is delegated, which is CLAUDE.md's standing rule and needs
  no measurement of whether a subagent's prompt reaches him.

**Denied files are denied by a channel that can see them.** The harness's rules are
`./`-anchored to the main tree and do not reach `../metatron-wt-<slug>` (finding 3), and
`git status` cannot see gitignored paths (verify NEW 2) — which is where the credentials and the
persona trees are. So the writer's hardcoded deny list is salvaged into `gates.py` and the
driver applies it at N12 through **four channels**: (a) `git status --porcelain -uall` in the
worktree for tracked and untracked paths — `-uall`, because without it git collapses untracked
files in a new directory to one `dir/` entry that matches neither `files[]` nor the deny list
(the commit guard's own recorded lesson; cold verify NEW 2); (b) a recursive hash of an **enumerated** list of
deny-list paths inside the worktree — `.env*`, `*key*.json`, `certs/`, `config/personas/**`,
`data/personas/**`, `.claude/settings.json`, `.claude/settings.local.json`, `.claude/agents/`,
`.claude/commands/`, `.claude/rules/`, **and the worktree's `.git` pointer file** — taken
before N11 and again after. **Never a wildcard over `.claude/`**: the harness's own hooks write
markers there on the implementer's behalf (`.claude/.session_state/` from the context gate,
`.claude/.session_edits/` from the commit guard — verify round 3), and a wildcard would refuse
every build at its first edit; (c) the same hash over the
main tree's `.env`, `vertex-key.json`, `certs/`, `.claude/settings.json`,
`.claude/settings.local.json`, **and the main repository's `.git/hooks/`, `.git/config` and
`.git/info/`** (verify round 4: a worktree's `.git` is a pointer into the main repository's
common directory, so a hook written at `<wt>/.git/hooks/pre-commit` lands in the shared hook
path and runs under Mike's commit at N13 — the one deny-list path no other channel can see, and
the sandbox flag cannot remove the pointer because a worktree cannot exist without it), before
and after, as the belt in case a link-back exists that the sandbox flag missed. The repository
has no custom hooks and no `core.hooksPath` today, so the expected delta is none; **(d)** the
set of dirty paths in the **main tree** (`git status --porcelain -uall`, same reason) before
N11 and after — a
path newly dirty in the main tree that is in the implementer's half of `files[]` is the
signature of a relative-path write that missed the sandbox, and refuses; other newly dirty paths
are another chat's and are reported beside the result, never refused (cold read 4). **Channels
(b) and (c) detect; they never restore.** The driver holds no write path into `.git/`, the
credential files or the persona trees, in either tree: on a delta it refuses the job, prints
the exact paths that changed, and stops. What to do about a planted hook or a changed
credential file is Mike's hand, with the path in front of him (verify round 5). Any delta in (b) or (c), any path in (a) outside the implementer's
half of `files[]` or on the list, or a `files[]` path newly dirty in (d), refuses the job.

**N12 gates and sweep (driver, on the worktree) — code checks only.** The four-channel check
above first; a refusal parks the job with the worktree **left in place** for Mike to read, and
the board prints the offending paths. Then the capability's own tests and a py-compile over
`files[]`, then `./scripts/qa_sweep.sh` in the worktree. **What N12 does not run, and why:**
the content gates on the agent file and `check_build_registration.py` — the agent file, the
routing entries and the Coordinator lines are Red and are not in this tree by design (cold read
2), so those checks belong to N13. Sweep check 11 passes here because the registry row the
implementer wrote carries `status: staged`, and the checker asserts wiring only for `landed`
rows (§ 4). A failure returns to
N11 once with the defect list; a second failure parks the job, worktree in place. **On a pass,
the driver writes the patch without a staging verb (verify round 2, NEW 2):** `git -C <wt>
diff HEAD --binary` for tracked files, plus `git -C <wt> diff --no-index --binary /dev/null
<path>` for each path in `git -C <wt> ls-files --others --exclude-standard`, concatenated into
`data/build/jobs/BLD-…/implementation.patch`; then it verifies the patch's path set equals the
implementer's half of `files[]`. No `add`, `commit` or `stash` is ever issued in the worktree,
so `hook_commit_guard.py`'s watched verbs never fire there — chosen so the step is correct
whether or not the guard parses the driver's subprocess calls. The worktree's job is done; it holds no commit and is removed
by Mike after N13 with `rm_worktree.sh --force`, the patch being the copy that makes the force
safe.

**[N13] one tree, one diff, one commit, one sitting (verify NEW 1; cold read 1).** The main tree
is shared by two chats and its HEAD moves, so the driver refuses to start N13 unless: **every
path in `files[]`, both halves,** is clean in the main tree (`git status --porcelain -uall --
<paths>` empty) — the Red targets included, because `routing*.yaml` and `coordinator.md` are
exactly the files another chat is most likely to hold uncommitted lines in, and the main session
is about to write into them (cold verify NEW 1); another chat's dirt in *other* files is not
Build's concern and is left alone. Then the patch is applied: plainly if HEAD is still the
sandbox's base commit; with `--3way` if it has moved, **followed at once by `git reset -q --
<paths>`**, because `--3way` implies `--index` and would otherwise leave the hunks staged past a
commit guard that watches `add`, `commit` and `stash` but never `apply`. Either way the working
tree carries the hunks unstaged and the index equals HEAD. A 3-way conflict parks the job —
and because `--3way` is not atomic (new files and clean hunks land before the conflicting one
stops it), the park runs **the same full revert the wiring gate prints**, one function
`driver.revert_landing(paths)` in both places: `git checkout HEAD -- <path>` for every path
that exists at HEAD, `rm` for every path the patch added, then `git reset -q -- <paths>` —
verified clean seconds earlier, so the restore is exact — and nothing else touched (cold verify
round 2). Then the main session writes the Red half of `files[]` there — where the harness's `ask`
rules prompt and its deny rules hold — flips the registry row to `landed`, and runs the gates
below. **N13 is one unbroken sitting**: it ends either in Mike's commit or in the printed
revert being run, never with Build's hunks left in the shared tree for another window's
`git add` to sweep into an unrelated commit — the 2026-08-09 shape.
**Then the content and wiring gate, in the main tree (verify round 2, NEW 1; scoped by round
3, NEW 2; cold read 2):** the driver runs `core/build/gates.py`'s content gates on the generated
agent file and record fields (§ 6) and the **capability-scoped** wiring checks over the main
tree, where both halves now exist — `scripts/check_build_registration.py --capability <name>`
against the now-`landed` row, `scripts/check_agent_tools.py
--agent <name>` (the script's own scoping flag; the diff-scoped behaviour is the PostToolUse
hook `hook_agent_tools.py`, which exits 0 by design and cannot gate — verify round 4), and a
py-compile over `files[]` — and **prints the staging manifest only when those are green.** The
full `./scripts/qa_sweep.sh` runs as well and is reported **beside** the manifest as advisory:
an unrelated red another chat left in the shared tree — a duplicate backlog id, a dev marker —
is named, never withholds, because the gate attributes by dirtiness and cannot tell whose fault
it is (`hook_subagent_gate.py`'s own recorded limit). This is the only point in the pipeline where the routing
entries, the Coordinator lines, the agent file and the code are in one tree before a commit,
so it is the only point the `time_director` shape — an agent file and a consequence line with
no routing entry — can be caught by a check rather than by a reader. Red on the wiring gate
parks the job, nothing is staged, and the driver prints two things on the board: the failing
check, and **the exact per-file revert command for the manifest's paths** — `git checkout HEAD
-- <path> …` for every pre-existing file, **from HEAD and never from the index**, `rm` for the
new files, then `git reset -q -- <paths>` — so a half-landed capability can be taken back out
of a tree another chat may be using, in one line, correct whether the apply was plain or 3-way,
and without `git checkout .`, which the harness denies (cold verify NEW 1).

Mike reads **one** `git diff -- <files[]>` — exactly the capability, both halves; another
chat's dirt outside `files[]` is neither shown nor staged — stages the explicit manifest the
driver printed, commits, and deploys. The `/fix` contract, with the patch as the only thing that crossed from the sandbox.
`hook_commit_guard.py` meets the stage here, in the main tree: patch-applied files were written
by `git apply` rather than by this session's Edit tool, which the guard's own attribution
places in its WARN branch, not BLOCK; if it blocks anyway, the override is
`METATRON_COMMIT_GUARD=off`, documented in `docs/WORKFLOW.md`, and phase C's end-to-end test
records which branch fired.

**N14 acceptance on the VM, then close.** The acceptance test the plan wrote runs on the VM
against Mike's data **and** against a fixture persona with no history (ruling 7, § 12). The
registry row was committed at N13; N14 records the acceptance result beside it on the next
commit, or files a REPAIR if it failed.

**The Coordinator has to define the need in the first place — Mike's note, 2026-09-24, and
the risk the whole vertical rests on.** Nothing downstream can build a capability for a gap
the Coordinator answered shallowly instead of filing. The Coordinator runs on the bulk tier,
reads a closed list, and its recorded failure is *doing the arithmetic itself* from stale
context (the plant-watering runs of 09-11/14/15) rather than saying nothing owns this. So the
filing condition in `coordinator.md` (phase B-Red) is written by **shape of request**, not by
"if you cannot answer": a request whose class no specialist's directory entry owns; a request
that needs a standing judgement over a history (a last-done date, a cadence, a running total)
that no specialist performs; a scheduled prompt that reached no specialist; a correction the
user has made before. Each of those files a gap **even when a plausible answer is available
from context** — a plausible shallow answer is the failure, not the fallback. And the
Coordinator-and-subagent vertical is reviewed against a fixture set of requests, half of which
should file and half of which should route, before run 1 (§ 12 Trigger row); the review that
matters is of the *instruction*, and it is cheap to repeat whenever `coordinator.md` changes.

**REPAIR.** Unchanged in mechanism: the code-written correction attribution on the VM
(`tools/turn_referent.is_exchange()`, one definition, both readers) collapses corrections to one
signature per capability and files a `repair` ticket at ×3 in 14 days, carrying the signature
and the traces. What changed: the dossier's origin Question Set and Answer Ledger are on the
Mac, so N1r reads them from `data/build/jobs/` by the origin job id the registry names.

**NC coherence.** `/build coherence` assembles the corpus by code (one-liners, registration rows,
surface maps, from the registry and the tracked files — no overlay to read) and a subagent
reviews it; findings still name two capability ids and an artifact or are rejected.

---

## 4. The artifacts

All carry `schema`, `job_id`, an upstream fingerprint, `generated_at`; validators in
`core/build/schemas.py`, revised.

### QuestionSet — v3.7 § 4 minus the manifest

Unchanged: the ordered spine, the eight classes, `disposition` with evidence, `depth`,
`declined_to_ask[]`, the hard constraints on ordering, and the transcript fixture. **Removed:**
`candidate_sources`, `manifest_fingerprint`, `policies_consulted[]` (Inquiry has not seen them).
**Added:** `proposed_depth` (Inquiry's own proportionality call, confirmed or overridden at N4).

### AnswerLedger — the inventory

```
rows[] (one per question, settled or not), interview_items[], variable_proposals[], surface_map,
policies_matched[]
LedgerRow:
  verdict (this persona):  found | inadequate | ask_user | external | absent
  inventory:               source · form (log|journal|profile|wisdom|calendar|contacts|conversation|
                           external:<name>) · coverage {from, to} · completeness · freshness ·
                           gap (what is missing, in words)
  kind:                    history | profile_fact | external | judgment
  if_user_lacks_it:        ask | degrade:<how> | refuse:<message> | n/a      ← ruling 7
  judgment rows:           decision · decision_options[≥2] · assumption · assumption_falsifier
  home:                    data_home · variable_scope: all_personas|this_persona|query_only · variable_name
  external rows:           source_name · access (api|feed|web) · key_needed: bool · per_call_cost ·
                           carries_personal_context: bool · on_failure
  status (code-derived):   settled | to_ask | external_pending | missing
```

**Hard:** one row per question · `kind: history` may never carry `variable_scope` (a history is
asked for and then accrues; it is not a variable) · `kind: profile_fact` requires `variable_scope`
and `variable_name` · every `external` row states `on_failure` and `carries_personal_context` ·
every `judgment` row has ≥2 options · `if_user_lacks_it` is required on every row the plan marks
as a required input.

**Where a declared variable lives, under ruling 4:** `this_persona` → `config/personas/{p}/
profile.yaml` **via the existing `write_profile` tool at runtime on first use**, never by the diff
(the file is VM-owned and Denied); `query_only` → the wisdom store the same way; `all_personas`
→ **two things, because the template reaches no existing persona** (finding 10 —
`tools/profile.py` resolves the persona's own file with no template fallback, and
`config/templates/profile.yaml` is read only by `scripts/new_persona.sh` at creation): the
template entry, tracked, in the diff, so future personas start with the field; **and** the
capability's `if_user_lacks_it: ask` path, which creates it through `write_profile` on first use
for every persona that exists today, `mike` included. A plan declaring `all_personas` without
that ask path fails validation. Uniqueness is checked against the live home through a read
door, not against a Mac copy.

### BuildPlan — every kind admitted

```
capability{id, kind, one_line, replaces[], execution_mode, latency_budget_ms, theme,
           disposition, disposition_evidence, generalizes_to}
kind: agent | tool | policy | function_job | context_block | check   ← all v1 (ruling 3)
disposition: extend | new | split | policy                             ← extend and split are back:
                                                                          a tracked-file edit is now ordinary
information_sources[]   ← one per ledger row the capability reads: row id, tool, arguments,
                           and if_user_lacks_it — THIS is the agent file's "where to look" section
integrations[]          ← one per external row: source, key registration (an (M) item), cost
                           per call and per month, privacy tier of the outbound query
surface_map[] (required) · files[] (tracked paths) · registration[] · tests[] · acceptance{two
personas} · variables[] · state_record{} · risks[] · citations[] (question id + row per gate)
estimate{}  (code-written: subagent calls expected, files touched, tools granted)
```

**`registration[]` is the tracked matrix again**, and it is one diff rather than one record.
The registry row is written by the implementer with **`status: staged`** and flipped to
**`landed`** by the main session at N13 once the Red half is in the tree; the checker asserts
routing parity, the Coordinator entry and the agent file **only for `landed` rows**, which is
how one script can pass in a sandbox that holds no wiring and fail in a main tree that is
missing some (cold read 2). The run line's `expected` and `actual` are `None` on the row from
the start, which satisfies the run-line assertion:
both routing entries at strict parity, the Coordinator directory entry and valid-name paragraph
**edited on disk** (seam 3's prompt-assembly rewrite is retired with the overlay), the
knowledge-domain entry, the consequence line, the confidential-name entry. `scripts/
check_agent_tools.py` and `check_build_registration.py` assert parity and completeness in the
sweep — the `time_director` half-wiring is the standing evidence that a checklist needs a check.

**`integrations[]` is new (ruling 5, external).** An outbound source with a key is an (M) item —
Mike registers it — so the plan says so before approval, not after. An outbound query that carries
personal context is on the § Section 0 line and the plan must say which side it is on; the
Research Agent's decontextualised path is the model.

**The question table** is a rendering, not an artifact: code writes it from the ledger and the
plan at N10 and again at N14 with the acceptance result.

### Policies

`kind: policy` is unchanged in content (v3.7 § 4). **Home:** `config/build/policies/{persona}/
{id}.yaml`, tracked, in the diff. Reason: a policy is a standing decision Build wrote and Mike
approved, not runtime state — it is not more sensitive than the persona preferences already in
tracked agent files, and the VM has no writer for it. Consulted by the Librarian at N4 (the
`triage` confirmation) and by the capability at runtime. *Stated as a decision open to reversal
if a policy ever carries content Mike would not commit.*

---

## 5. Tickets, jobs, registry, board

**VM — `data/personas/{p}/build/tickets.jsonl`**, append-only: `request_build` rows and REPAIR
rows, `BLD-MMDD-NN` ids allocated by replaying the day under a lock. A ticket has one state on
the VM, **open**, until the deployed registry carries its row. Caps: `max_proposed: 12`,
`max_jobs_per_day: 4` for filing. Dedupe: fingerprint refused against an open ticket, a registry
row `landed` within 14 days, or `abandoned` within 72 hours. **Sequenced against the deploy
(finding 7):** a ticket decided on the Mac stays open on the VM until the next deploy, so the
same fingerprint is refused the whole time — nothing is re-filed. A capability and its `landed`
row reach the VM in the *same* deploy by construction, so REPAIR eligibility can never lag the
capability it counts for. What does lag is `abandoned`: until the deploy that carries it, the
ticket counts toward `max_proposed`. Bounded by the cap, and the board prints *"N decided,
awaiting deploy"* beside the open count so the cost is visible rather than read as gaps still
waiting. The `BUILD_PROPOSED` quality event
beside each ticket reaches `DEV_BACKLOG.md` § Inbox through the existing sync — the second record
until Build earns trust.

**Mac — `data/build/jobs/<persona>/BLD-…/`**: the artifacts, each written `*.tmp` then
`os.replace()`. **Persona-qualified everywhere on the Mac** (cold read 5): ticket ids are
allocated per persona ledger on the VM, so two personas can mint the same `BLD-MMDD-NN` on one
day; `/build` takes `--persona` (default `mike`), the job directory, the board and the registry
row all carry the persona, and a fixture persona's tickets are never built unless that persona
is named. Acceptance on a fixture persona exercises the landed capability, not the trigger. **The
artifact is the resume cursor**: `/build BLD-…` re-entered finds the artifacts present and skips
those nodes — the only state a lost session needs. Plus `data/build/index/` — Build's own FAISS
index of every question ever asked, for dedupe (unchanged from v3, relocated).

**Tracked — `config/build/registry.yaml`**: one row per capability: name, kind, ticket, job id,
version, landed date, acceptance result, `execution_mode`, `latency_budget_ms`, run line. Written
by N11 in the diff. `docs/BUILD_REGISTRY.md` is rendered from it by the sweep.

**Board — `scripts/build_board.py`**: joins the VM ticket file (fetched) with the registry and the
local jobs; `--tickets`, `--jobs`, `--registry`, `--run-cost`, `--abandon BLD-…` (writes the
`abandoned` registry row into the working tree for Mike to commit). No `--refuse`, `--approve`,
`--resume` — those were VM-state commands and the session is the state now.

**Two surfaces for Mike:** `tools.build.context_block()` in conversation — now reads the ticket
file and the registry and says only *"N gaps filed, waiting for you to start a build"* — and the
board in Claude Code.

---

## 6. What guards the output now

The writer's *landing* job is gone. Its *content* job survives as `core/build/gates.py`, run at
N12 on the worktree and re-run by `check_build_registration.py` in the sweep:

| Gate | Kept from | Rule |
|---|---|---|
| Constitution | `constitution.py` | required sections, `max_lines: 220`, no narration, no provider name, the charset rule on display names |
| Name collision | writer | a new name ∉ either routing file ∪ `config/agents/*.md` stems; display name ∉ the Coordinator's closed list, collapsed and case-folded |
| Told-not-granted | writer | the agent file names no tool outside its grant — bare-word scan against the live `register_tools()` set |
| Grants outside the read set | writer, **softened** | not refused: **listed in the plan's `risks[]` and in the brief**, and the gate fails if a grant in routing is absent from `risks[]`. Mike's approval is the control; a refusal list was the control for an unattended landing |
| Path rules | writer, **salvaged** | `DENY_PREFIXES/DENY_EXACT/DENY_GLOBS` from `writer.py:189-209`, applied by the driver at N12 through three channels — the porcelain for tracked paths, a before/after hash of the worktree's gitignored deny-list paths, a before/after hash of the main tree's credential files (verify NEW 2) — plus "every changed path is in the implementer's half of `files[]`"; the sandbox worktree has no link-backs to hit. Kept as code because the harness's rules are `./`-anchored and do not reach a worktree, and because `.claude/settings.json`, `core/build/`, `*key*.json` and `config/modules/build.yaml` are on the writer's list and not the harness's (finding 3). `check_build_registration.py` asserts the list, as before |
| Record fields | writer | `directory_entry`, `unavailable_consequence`, `display_name` scanned for confidential identifiers against the live registry |

**The four load seams are retired** with the overlay: `load_agent`, `_load_routing`, the
Coordinator prompt rewrite, `_CONTEXT_SENSITIVE`/`domain_agent_map` fallbacks. Generated
capabilities are tracked files the runtime loads exactly as hand-written ones. **This closes
v3's Ancillary cost of re-caching the Coordinator per landing**: the prompt changes at deploy,
when it changes anyway.

### The read doors

One endpoint on the VM server beside `/monitor/file`, two modes, same bearer as
`sync_dev_backlog.py` mints, Tailscale-only like every monitor route, persona-bound from the
query (finding 9 shapes both):

- **`GET /monitor/tool?presence=<source_id>`** — the presence check. Takes a **source id**, not
  arguments: the server runs the fixed, code-chosen call from the salvaged `manifest._SOURCES`
  table (the D4 repairs intact) and returns `{state, count, window}`, no content. This is
  `probe.py` moved to the VM, with its injection answer unchanged — *the model names a source,
  code chooses the call.*
- **`GET /monitor/tool?name=…&args=…`** — a research read. The name must be in the Librarian's
  read set (v3.7 § 6.3's list plus `search_conversations` and `read_journal_range` once built)
  **minus the seven live feeds — no outbound tool sits behind a door**, so content the Librarian
  reads cannot compose a call that leaves the machine. The arguments are validated server-side
  against a per-tool schema with caps (window ≤ 90 days, `k` ≤ 50, `max_entries` ≤ 200; beneath
  them the wisdom store's own `READ_CAP`, the one read tool that defines one), and anything
  else is refused with the schema. What
  remains model-chosen is *which* of the persona's own data to read and how much, which ruling
  1 already grants.

The Mac client is `scripts/vm_read.py`, the Librarian subagent's only Bash form. **Built as
needed** (ruling 11): run 1 needs `get_log_window`, `read_wisdom`, `search_memory`,
`list_schedules`, `read_profile`; the allowlist grows by a line per run.

**Privacy consequence, stated once:** whatever crosses a door is in the build session and
therefore reaches Anthropic. Ruling 10.

---

## 7. The subagents and the command

`.claude/agents/`, the convention `adversarial-reviewer.md` set (frontmatter: `name`,
`description`, `model`, `tools`):

| File | Model | Tools | Why |
|---|---|---|---|
| `build-inquiry.md` | Opus | **none** | judgement in a vacuum; the compass rule — its ordering is enforced by the validator, so the model's job is question content; the spine abstract from v3.7 § 15 |
| `build-librarian.md` | Opus | `Read, Grep, Bash(python3 scripts/vm_read.py *)` | research with tools; reads as much as it needs |
| `build-planner.md` | Opus | `Read, Grep, Glob` | plans, never creates; arranges recorded options against code it opens — build-shaped, not open-ended planning |
| `build-implementer.md` | Opus | `Read, Edit, Write, Bash, Grep, Glob`, worktree only | build against a settled plan; **Amber and Green files only** — the Red half of `files[]` is the main session's (§ 3 N11) |
| `build-coherence.md` | Fable | `Read` | reads the set |
| `adversarial-reviewer.md` | Fable | exists | unchanged |

Plan in Opus, review in Fable, build in Opus — `docs/WORKFLOW.md`'s split as Mike re-ruled it
on 2026-09-24. All on the subscription. **No agent names its model in its body**, and none
reaches a Vertex model.

**`/build`** — `.claude/commands/build.md`:

```
/build [--persona mike]                    list open tickets (fetched) and jobs in flight
/build [--persona mike] BLD-MMDD-NN        run the graph from wherever the artifacts say it is
/build [--persona mike] repair BLD-MMDD-NN same, REPAIR mode, dossier first
/build coherence                           the periodic set review
```

The command is not the runner; `core/build/driver.py` is. The command asks the driver for the
next step, spawns the subagent or runs the code node it names, hands the result back, and
repeats; it stops where the driver says a human gate is, applies the patch and writes the Red
half of `files[]` in the main tree at N13, and never commits, pushes or deploys.

---

## 8. Budget, routing, privacy

**Budget.** No dollar tripwire: Build bills nothing per token. Bounds that remain, **each
enforced by the driver from durable artifact counts, not by the prompt** (finding 1): one rung-2
retry per node, the review's one send-back, one N12 return per job, `max_jobs_per_day` on the
VM, and the subscription's window — which surfaces as a rate-limited session Mike is sitting in
front of. **Measured, not guessed:**
`scripts/worker_ledger.py` already measures worker cost from transcripts; `/build` writes a
`session_cost` line per job from the same source, so the board's `--run-cost` shows what each
build consumed and the placeholder-limit machinery (`cost.py`, `$2.50`, `approve_limit`) is
retired with nothing to bound. **The under-$1 API allowance** (ruling 9) is recorded as
`build.yaml: api_allowance_usd_per_step: 1.00` with no consumer; a future poller running Inquiry
alone on the VM would be the first.

**Routing.** The Build agents have **no routing entries** — they are not runtime agents.
`resolve_model("build_inquiry")` raising is now correct, permanently. Generated capabilities
carry ordinary entries in both routing files, at parity, `model_ref`-free (a tracked entry names
a model like every other; the model-ID maintenance convention in `docs/CONVENTIONS.md` covers it).

**Privacy — the ROADMAP § Section 0 entry, in the 08-26/08-28 form:**

> **Amendment 2026-09-24 — Build runs in Claude Code on the development subscription (Mike's
> ruling; criteria ranked consistency > {cost, autonomy} > privacy, 2026-09-19).** Build is
> development, not execution. Its inputs — the persona's data read through the VM's read doors,
> the answer ledger including verbatim interview answers, the generated plans — reach Anthropic
> through the same subscription and account that already carry every development session on this
> project. Mike's basis: *"Anthropic already gets it from the current development scheme."* The
> control is unchanged from 08-26: his own judgement about what he puts in. **Not a runtime
> path:** no persona data reaches Anthropic from the VM, and the Orchestrator still calls no
> Claude model and spawns no Claude Code session. Unchanged: fail-closed routing, the north star,
> decontextualisation for open-tier work, and the single-user expiry — Mike can gate his own data
> and nobody else's, and this lapses the moment the deployment stops being single-user. The
> subscription's data terms were noted, not verified from primary sources, by decision.

`CLAUDE.md` § Key Design Decisions needs **no change**: the Orchestrator does not spawn Claude
Code sessions at runtime, and Build is not runtime.

---

## 9. Librarian's substrate

Unchanged from v3.7 § 9 in what is missing: no conversation search, one-date journal reads.
**`search_conversations` and `read_journal_range` are still built before run 1**, by ordinary
development (`/fix`), and enter the read-door allowlist. Build's own FAISS index stays, on the
Mac. The main FAISS reindex is still its own item.

---

## 10. Files — the rebuild, and what is salvaged from phases 1–4

**Step 0 — commit the phase-4 tree as the record.** Phase 4 is uncommitted by instruction, and
the review rounds' fixes to files that *survive* (`tools/turn_referent.py`, `tools/logger.py`,
`core/build/probe.py`) sit in the same unstaged diff as files that go. One commit first — `git
diff` each file, the headset chat's files excluded — so the deletion is a reviewable, reversible
diff rather than a mix of unstaged removals and unstaged keeps.

**Step 1 — the old package goes whole, LAST, at the end of phase A** (finding 4): only after
`tools/build.py` imports the new ticket store, `_DEFAULT_JOBS["build_tick"]` points at the new
`core.build.tick`, and `scripts/check_build_registration.py` is rewritten (finding 5) — so the
ticket inbox, the REPAIR counter and sweep check 11 are never dark, not for a commit. A new
sweep check, `scheduler-functions-resolve`, imports every `_DEFAULT_JOBS` function so a dangling
dotted path fails the sweep instead of being swallowed by `fire_function` every 30 minutes.
What goes: `core/build/` (19 modules, ~8,700 lines), the twelve
`tests/test_build_*.py` suites, `scripts/build_board.py`, `scripts/build_brief.py`, and the hook
lines phase 4 threaded into shared files: the four load seams (orchestrator `load_agent`,
Coordinator prompt rewrite, `_CONTEXT_SENSITIVE`/consequence fallbacks; `core/router.py`
`_merge_overlay_routing` — **Red, prompts, not delegated**; `tools/wisdom.py` `domain_agent_map`);
the cost seam in `core/trace.py`; the four Build agent names in `_ALWAYS_CONFIDENTIAL`;
`answer_interview_item` in `register_tools()` and its Synthesizer grant; the `--overlay` flags
on three check scripts; `config/modules/build.yaml`'s ceiling and autonomy blocks. **Outside
Build, the only behaviour that changes is the removal of the four seams' fallbacks**, which
nothing tracked ever reached. Regression gates that must still pass after the seams come
out, each already named by the roadmap: `tests/test_a4_complexity_threading.py`,
`tests/test_turn_referent.py`, `tests/test_synth_module_injection.py`,
`tests/run_knowledge_routing.py --persona danny_park`, `./scripts/qa_sweep.sh`, and a clean
server start with one full pipeline turn.

**Kept in shared files because they are runtime, not Build:** the code-written correction
attribution in `core/orchestrator.py`, `tools/turn_referent.is_exchange()` and its readers, the
logger's per-fact event write (D10), `request_build` and `context_block` in `tools/build.py`,
the `build_tick` scheduler entry (reduced to the REPAIR counter and dispatch counts), and the
`BUILD_PROPOSED` label in `scripts/sync_dev_backlog.py`.

**Salvaged by copy into the new package — premise-free, hard-won:**

| Piece | From | Why it does not know where it runs |
|---|---|---|
| the Question Set, ledger-row and plan validators, minus the removed fields | `schemas.py` | rules about artifact shape; the compass-rule ordering is the one to keep exactly |
| the transcript fixture and its test | `tests/fixtures/inquiry_rsvp_2026-09-17.md`, `test_build_spine.py` | the only real pass/fail pair, produced before the rule existed |
| the id allocator | `ids.py` | replay-under-lock, no state |
| Build's question index | `index.py` | a FAISS index over questions; relocates to the Mac |
| the constitution check | `constitution.py` | reads an agent file, knows nothing of landing |
| the policy record shape and resolver | `policy.py` | home changes, shape does not |
| the presence-check call table | **`manifest.py`'s `_SOURCES`** after D4 (finding 8 — it was never in `probe.py`) | the fixed, code-chosen call per source with the three rounds' argument repairs in its comments — moves to the VM behind the door |
| the control layer | `runner.py`: node order, `MAX_NODE_RETRIES`, the retry-product cap counted from durable rows, the artifact-is-cursor rule, the park states, `NodeOutcome` | knows nothing of where a model call comes from; `_ask()` becomes "name the step" and the rest is `driver.py` (finding 1) |
| the deny list | `writer.py:189-209` `DENY_PREFIXES/DENY_EXACT/DENY_GLOBS` | path rules do not care who writes; applied by the driver to the worktree diff (finding 3) |

**Written fresh against this plan:** `core/build/{tickets,jobs,tick,manifest,doors,table,brief,
registry,coherence,gates,verify}.py` (with `driver.py` and `gates.py` carrying the two salvaged
blocks above) · `scripts/{build_board,vm_read}.py` · **`scripts/check_build_registration.py`,
rewritten as the tracked-file checker** — routing parity, the Coordinator directory entry and
valid-name list, knowledge domains, the registry row and run line, the deny list (finding 5) ·
the `scheduler-functions-resolve` sweep check · the door in `core/server.py` · the `--sandbox`
flag on `scripts/new_worktree.sh` (no credential link-backs, registers as
`metatron-wt-build-<slug>`; deploy-rule file, Amber) · the `metatron-wt-build-` skip in
`scripts/hook_subagent_gate.py:_dirty_worktrees` (the driver sweeps the sandbox at N12; a parked
one must not stall other windows' workers — cold read 6) · **the trigger, Red, main session:**
`request_build` on `coordinator`'s `allowed_tools` in both routing files and the
`coordinator.md` § Tools available line saying when to file a gap rather than a `ROUTING_MISS`
(cold read 3 — v3.5's C3, whose owner this plan had deleted with phase 5) · `.claude/agents/build-{inquiry,librarian,planner,implementer,coherence}.md` ·
`.claude/commands/build.md` · `config/build/registry.yaml` · `config/build/policies/` ·
`config/modules/build.yaml` (caps and the API allowance only) · one `.gitignore` line for
`data/build/` · `tests/test_build_{schemas,spine,tickets,tick,jobs,driver,doors,table,registry,
gates,coherence}.py`.

**Untouched:** `config/constitution.md` · `deploy.sh` · `.claude/settings.json` ·
`core/spend_guard.py` · `core/persona.py`.

---

## 11. Bootstrap — runs 1–3, unchanged in substance

Run 1 `home_care` (config-only, over existing read tools — the same gap, § 11 of v3.7), run 2 the
induced REPAIR, run 3 the weekend-correspondence policy. **What changes:** run 1's code work, if
the Planner finds any, is done by N11 rather than deferred; `may_create_agent_files` no longer
exists — Mike's approval at [N9] and his commit at [N13] are the ceiling; and each acceptance
runs on two personas. **Run 4+, the tier**, is unchanged and still due at four leaf capabilities.

---

## 12. Verification

| Piece | Command | Proves |
|---|---|---|
| Schemas | `python3 tests/test_build_schemas.py` | v3's assertions that survive, plus: a `history` row with a `variable_scope` fails; a required input with no `if_user_lacks_it` fails; an `external` row without `on_failure` fails; a Question Set carrying `candidate_sources` fails; a plan gate without a citation fails; a plan declaring an `all_personas` variable whose row lacks `if_user_lacks_it: ask` fails (verify residual 10) |
| Compass rule | `python3 tests/test_build_spine.py` | unchanged: turn 2 fails, turn 4 passes |
| Driver | `python3 tests/test_build_driver.py` | a node that fails validation is retried exactly once, then the job parks; a second review send-back parks; a job at a gate state yields no step; a job whose N2 and N4 artifacts exist resumes at N7 with no step for either; the counts are re-derived from `attempts.jsonl` after the process is restarted, including a failed node that wrote no artifact (finding 1, verify residual 1) |
| Sandbox and patch | `python3 tests/test_build_gates.py` (worktree half) | a `--sandbox` worktree contains no symlink to `.env`, `vertex-key.json`, `certs/` or `settings.local.json`; a write to `<wt>/.env` changes the main tree's `.env` hash by nothing and is refused by channel (b); a write to `<wt>/data/personas/x/profile.yaml` is refused by (b) with no porcelain line; a relative-path write that lands a `files[]` path in the main tree is refused by (d), including one inside a directory that did not exist before, while an unrelated path dirtied in the main tree by a second process is reported and not refused (cold read 4, cold verify NEW 2); a legitimate new package `tools/<cap>/__init__.py` named in `files[]` passes channel (a) rather than parking as `tools/<cap>/` (cold verify NEW 2); a harness marker written under `<wt>/.claude/.session_state/` or `<wt>/.claude/.session_edits/` is NOT refused, while an edit to `<wt>/.claude/settings.json` or a new file under `<wt>/.claude/agents/` IS (round 3 NEW 1); a file written to `<wt>/.git/hooks/pre-commit` — which lands in the main repository's hook path — IS refused by channel (c) with that path named in the refusal, and the driver made no write of its own under the main repository's `.git/` (asserted by hashing the directory before the driver runs and after it refuses, with the planted file then removed by the test, not the driver) (round 4 NEW 1, round 5 NEW 1); the patch's path set equals the implementer's half of `files[]`, applying it to a clean main tree reproduces the worktree byte-for-byte, and the git commands the driver issued in the worktree contain no `add`, `commit` or `stash` (verify NEW 1, NEW 2; round 2 NEW 2) |
| Wiring gate | fixture main tree after patch + Red half, with one routing entry deleted | the driver refuses to print the staging manifest, naming the missing entry, and prints the per-file revert line; restore it → manifest printed; same with the Coordinator directory line removed and with the agent file naming a tool outside its grant (round 2 NEW 1). Then plant an unrelated sweep red (a duplicate `DB-` id in a fixture backlog) → the manifest is still printed, with the red reported beside it (round 3 NEW 2) |
| Gates | `python3 tests/test_build_gates.py` | every content assertion from `test_build_writer.py` that is not an overlay rule, on a fixture worktree, **plus the path rules**: a worktree diff touching a deny-list path is refused with the worktree left in place and byte-identical after the refusal, the path named on the board; a changed path outside the implementer's half of `files[]` is refused; a plan with a Red path in the implementer's half fails validation before N11 (findings 2, 3); a routing grant absent from `risks[]` fails |
| Doors | `python3 tests/test_build_doors.py` | `presence=<id>` runs the salvaged fixed call and returns no content; an argument outside the per-tool schema or over its cap → 400 with the schema; any live-feed name → 403 (finding 9) |
| Tick | `python3 tests/test_build_tick.py` | three corrections against a registered capability file one repair ticket; `scheduler-functions-resolve` fails on a dangling `_DEFAULT_JOBS` path and passes on the tree (finding 4) |
| Question table | `python3 tests/test_build_table.py` | every ledger row appears once; an uncited question lands in "shaped nothing"; a plan item with no citation lands in "unsupported"; the acceptance column is empty until N14 |
| Registry | `python3 tests/test_build_registry.py` | a `landed` row within 14 days refuses a same-fingerprint ticket on the VM; `abandoned` within 72 h likewise; dispatch counts exclude ticks and the landing day (unchanged) |
| Resume | start `/build BLD-…`, kill the session after N4, restart | N2 and N4 skipped, N7 runs; no duplicate artifact |
| Implementer boundary | a plan naming `config/constitution.md` or `.env` in `files[]` | the plan fails validation before N11; a fixture worktree hand-edited past it is refused by the driver at N12 on the deny list through whichever channel sees the path, and the change never reaches the main tree — **neither the harness nor `git status` is relied on for gitignored paths inside a worktree** (finding 3, verify NEW 2) |
| Review sees the table | run N7 → N10 → N8 on a fixture job | the file handed to `/adversarial-review` contains the question table; the review lands in the brief after it (finding 6) |
| Registration check | `python3 scripts/check_build_registration.py` on a tree with a routing entry in one file only, and on one with an agent file and no routing entry | exit 1 naming the gap, both cases — the `time_director` shape (finding 5); the same tree with the row at `status: staged` → exit 0, so the sandbox passes and the main tree fails on exactly the same script (cold read 2) |
| Trigger | `python3 scripts/check_agent_tools.py --agent coordinator`; then a fixture Coordinator turn on a request nothing routes | `request_build` named and granted, neither class flagged; the turn ends in a `request_build` call with a non-null gap and a ticket at `proposed` in that persona's file (cold read 3) |
| **Under-filing** (Mike, 2026-09-24) | `tests/fixtures/build_trigger_requests.yaml`: ≥ 12 requests, half that should FILE (a cadence judgement over a log with a plausible stale answer in context; a class no directory entry owns; a scheduled prompt no specialist takes; a repeated correction) and half that should ROUTE (ordinary specialist requests, including deep ones a specialist does own) — run through the real Coordinator on the bulk tier | every should-file request ends in `request_build`, none of the should-route ones does; the failing case to watch is a should-file request answered from context — that is the plant-watering shape and it is a FAIL even when the answer is correct. Re-run whenever `coordinator.md` changes |
| Landing pre-checks | main tree with a `files[]` path dirtied by hand — once a patch path, once `config/modules/routing.yaml`; then a clean tree whose HEAD is one commit past the sandbox's base | first two: N13 refuses to start, naming the path; third: the patch applies with `--3way`, **`git diff --cached` is empty afterwards** and `git diff -- <files[]>` equals the sandbox's diff; a planted conflict in a patch that also ADDS a new file parks the job with `git status --porcelain -uall -- <files[]>` empty afterwards — the new file removed, the pre-existing paths byte-identical to HEAD, the index clean; the printed revert line, run on a tree after a 3-way apply plus the Red half, leaves the same status empty; both use `driver.revert_landing` (cold read 1, cold verify NEW 1, round 2 NEW 1) |
| Sandbox stop gate | a parked `metatron-wt-build-x` with a failing sweep, then any other subagent stopping | the other subagent's stop is not blocked by the Build sandbox; a build subagent handed a pre-existing main-tree red as its stop reason still yields a validating artifact the driver accepts (cold read 6) |
| Persona-qualified ids | two fixture personas each filing on the same day | the same `BLD-MMDD-NN` in both ticket files; `/build --persona a BLD-…` and `--persona b` open different job directories; `/build BLD-…` with no persona resolves `mike` (cold read 5) |
| End to end | `request_build` on the VM → `/build BLD-…` → approve → patch → Red half → one commit → deploy → acceptance | run 1 lands as tracked files from one tree; the wiring gate ran green in the main tree before the manifest was printed; the single `git diff` before the commit shows exactly `files[]`, both halves; the commit guard's branch (WARN or BLOCK) on patch-applied files is recorded; The Book renders the capability's dispatch; acceptance passes on `mike` and on the fixture persona, where the "ask" branch fires |

---

## 13. Risks a reviewer will attack

1. **"The Mac now holds persona-derived data."** Conceded and chosen (ruling 10). Bounded to
   `data/build/`, gitignored, and the commit guard's manifest rule already stops a stray `git add`.
2. **"An implementer with Edit and Bash in a worktree is the executing session v3 removed."**
   Yes, with four controls v2 lacked: Mike's approval of a plan that names every file, the
   driver's diff gate against `files[]` and the salvaged deny list, no Red file in its half,
   and Mike's own commit. The worktree cannot deploy.
3. **"The subscription window is unmetered."** Conceded. Measured after the fact from
   transcripts; rate limiting is visible to the person in the session. Recorded in § 14.
4. **"Rebuilding throws away tested code."** Yes: three review rounds on a package whose
   premise is gone. Adapting would be worse — a session opening `jobs.py` reads a paragraph about
   resume cursors on a 30-minute tick and designs around it. What was premise-free is salvaged
   by copy (§ 10); the rest was correct for a design nothing will run. Mike's rule.
5. **"The Librarian with a search tool will read everything."** By ruling, it reads as much as
   it needs. The bound is the session, which Mike is in.
6. **"Inquiry in a vacuum will ask for data that cannot exist."** That is the design: the
   Librarian's `absent` verdict is the finding, and `if_user_lacks_it: ask` is the answer.
7. **"Policies as tracked files leak preferences into git."** Open to reversal (§ 4); no policy
   is committed without Mike reading the diff.
14. **"The Coordinator will answer shallowly and never file."** (Mike, 2026-09-24.) The inverse
    of 13.9's over-filing, and the one that leaves value on the table silently — no event, no
    ticket, a plausible answer. Countered by writing the filing condition by request shape
    (§ 3), by the under-filing fixture in § 12 run before run 1 and after every
    `coordinator.md` change, and by REPAIR's correction counter, which catches the case where
    the shallow answer was wrong. **It does not catch a shallow answer that was right**, which
    is why the fixture's should-file cases include ones with a correct answer in context.
8. **"Two state homes will disagree."** The registry is the only state; the ticket file is an
   inbox. A ticket with no deployed registry row is open, by definition, and refuses its own
   fingerprint until the deploy — the disagreement is bounded to `abandoned` rows counting
   toward the cap, and the board names it (§ 5).

---

## 14. Cost

| Phase | Contents | Model | Est. |
|---|---|---|---|
| 0 | the phase-4 record commit — nothing deleted | main session | $1–2 |
| A | the new `core/build/` package: salvage by copy (validators, fixture, ids, index, constitution, policy, `_SOURCES`, the driver's control layer, the deny list), then tickets, tick, jobs, manifest, table, brief, registry, gates, verify — fresh, with tests; `check_build_registration.py` rewritten; `tools/build.py` and `_DEFAULT_JOBS` re-pointed; **then** the deletion, the seams out (`core/router.py` in the main session — Red), and the six regression gates green | Opus 5; the router seam in the main session | $24–34 |
| B | the read door on `core/server.py`, `probe.py` behind it, `scripts/vm_read.py`, auth, tests | Opus 5 | $8–12 |
| B-Red | **the trigger**: `request_build` granted to `coordinator` in both routing files, the `coordinator.md` § Tools available line (when a gap is filed instead of a `ROUTING_MISS`), `check_agent_tools.py` green on both — Red, prompts, not delegated (cold read 3) | main session | $2–3 |
| C | the five subagent files and `/build` | Opus 5, reviewed by `/adversarial-review` (Fable) before it runs a real ticket | $12–18 |
| D | `search_conversations`, `read_journal_range` — `/fix`, ordinary development | Opus 5 | $4–7 |
| — | `/adversarial-review` of this plan before A, and of C's command before E | Fable 5 | $4–8 |
| E | deploy: door, tick, `request_build` grant, registry — Mike | — | — |
| F | bootstrap runs 1–3 as one walkthrough, Mike present; each run is a Build session | Fable/Opus per § 7 | $10–20 |
| | **Total** | | **$65–106** |

Phases 1–4 of v3 cost $52–78 as estimated; what survives of them is listed in § 10.

**Run.** $0 marginal per Build call on the subscription. The VM gains one endpoint that runs
only when asked. A landed capability costs what any specialist costs, on Vertex, at dispatch —
the registry's run line still counts it. Nothing new persists between calls; the job
directories on the Mac grow by kilobytes per job.

**Ancillary.** A door call moves a tool result over Tailscale instead of running in-process —
the same tool, one hop. Seam 3's per-landing Coordinator re-cache is gone. Worktrees per build
are removed by `rm_worktree.sh` after commit.

**Unseen.** The subscription window shared with development — no meter in the repo reports it,
`worker_ledger.py` measures it afterwards. Mike's review time at N9 and N13 — the deliberate
cost of ruling 4. Named so neither is mistaken for zero.

**Model:** plan in Opus 5, review in Fable 5, build in Opus 5 (Mike, 2026-09-24); the
routing-file, router and scheduler edits (Red) are made in the main session, not by a subagent.

---

## 15. The reference transcript

Unchanged: v3.7 § 15. The abstract lives in `build-inquiry.md`; the verbatim pair is the
fixture; n = 1 and every run adds a pair.

---

## 16. Execution order

```
Review   /adversarial-review archive/plans/build_vertical_plan_2026-09-24.md
Phase 0  commit the phase-4 tree as the record — nothing deleted          ← main session
Phase A  the new core/build/ package — salvage by copy, the rest fresh, with tests;
           check_build_registration rewritten; callers re-pointed; THEN the deletion
           and the seams out (router: main session, Red); six regression gates green
Phase B  the read door · presence check · vm_read.py · tests
Phase B-Red  the trigger: request_build on the Coordinator (both routing files) + the
           coordinator.md line — main session, Red                        [cold read 3]
Phase C  the five subagents · /build                                   ← Opus
           ↳ /adversarial-review of the command before it runs a real ticket
Phase D  search_conversations · read_journal_range                     ← /fix
Phase E  ./deploy.sh — Mike; 0, A, B, B-Red, D reach the VM as one deploy
Phase F  runs 1–3 as one walkthrough; Mike starts each with /build
Later    the tier (due at four leaf capabilities) · the FAISS reindex · a poller that
         starts /build on a new ticket · a second read-door consumer
```

Phases A–E land nothing user-visible. The first thing Mike sees is run 1.
