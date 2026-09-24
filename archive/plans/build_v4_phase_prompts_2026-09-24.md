# Build v4.11 — per-phase window prompts

*Written 2026-09-24 by the coordinating window. Each `## Phase X` section below is a complete,
self-contained prompt for a fresh Claude Code window that has none of the coordinating
conversation. Order: 0, A, B, B-Red, D, C, E, F (plan § 16).*

**Plan:** `archive/plans/build_vertical_plan_2026-09-24.md` v4.11 — 998 lines, every section binds.
**Reviews that cleared it** (read for "why is it built this way", never to re-review):
`archive/plans/adversarial_review_build_vertical_plan_2026-09-24.md` (Opus 5, seven rounds) and
`archive/plans/adversarial_review_build_vertical_plan_2026-09-24_cold-fable.md` (Fable 5, cold
read, three rounds). Both ended clean at v4.10; v4.11 is instructional only.

**Model rule** (`docs/WORKFLOW.md`, Mike 2026-09-24): plan in Opus, review in Fable, build in Opus.
**Red-tier work is never delegated to a phase window or a subagent** — it is done in the
coordinating window with Mike approving each edit.

| Phase | Whose window | Model | § 14 est. | Status |
|---|---|---|---|---|
| 0 | Mike, by hand | — | $1–2 | **index staged, commit not yet made** |
| A | phase window | Opus 5, xhigh | $24–34 | prompt below |
| A-Red | coordinating window | — | (in A's $24–34) | **carve-out — see § A-Red note** |
| B | phase window | Opus 5, xhigh | $8–12 | pending |
| B-Red | coordinating window | — | $2–3 | pending |
| D | phase window | Opus 5, xhigh | $4–7 | pending |
| C | phase window | Opus 5, xhigh | $12–18 | pending |
| E | Mike, deploy checklist | — | — | pending |
| F | Mike, live walkthrough | per § 7 | $10–20 | pending |

---

## Phase 0 — the record commit (Mike, by hand; not a window prompt)

**This phase is a commit, not a build.** Plan § 10 step 0 and § 14: *"the phase-4 record commit —
nothing deleted."* Its purpose is that phase A's deletion becomes a reviewable, reversible diff
rather than a mix of unstaged removals and unstaged keeps. **Phase 0 has no test gate** — Opus
review finding 5 was closed by reducing phase 0 to the record commit only.

### The manifest — 26 paths, verified by diffing every file in the tree

The tree at `6189d96` carries two chats' uncommitted work. All 23 modified files were diffed and
all 14 untracked paths inspected. Assignments:

**Modified, staged whole (14) — pure phase 4:**
`archive/plans/build_vertical_plan_2026-09-18.md` (the v3.5–v3.7 corrections) · `core/actions.py` ·
`core/build/jobs.py` · `core/build/manifest.py` · `core/build/probe.py` · `core/build/schemas.py` ·
`core/build/writer.py` · `core/scheduler.py` · `scripts/sync_dev_backlog.py` ·
`tests/test_build_jobs.py` · `tests/test_build_probe.py` · `tests/test_turn_referent.py` ·
`tools/logger.py` · `tools/turn_referent.py`

**New, staged whole (11):**
`core/build/brief.py` · `core/build/coherence.py` · `core/build/registry.py` ·
`core/build/runner.py` · `scripts/build_board.py` · `scripts/build_brief.py` ·
`tests/test_build_brief.py` · `tests/test_build_coherence.py` · `tests/test_build_registry.py` ·
`tests/test_build_runner.py` · `tools/build.py`

**Split, staged by patch (1): `core/orchestrator.py` — 10 hunks of 12.**

> **Why it could not be staged by filename.** Two of its twelve hunks are the headset-mode chat's:
> a `source: str = "ui"` parameter on `run_pipeline_session_stream`, and the
> `start_request_trace(..., source=source)` call that consumes it. The **committed**
> `core/trace.py:188` `start_request_trace` takes no `source`. A commit carrying that call raises
> `TypeError` on **every streamed turn**. The patch that drops exactly those two hunks is
> `phase0_orchestrator_phase4only_2026-09-24.patch`, applied with `git apply --cached` so the
> working tree keeps the headset lines unstaged.

**Excluded — the headset-mode chat's, 11 paths:** `.gitignore` · `DEV_BACKLOG.md` ·
`android/app/src/main/AndroidManifest.xml` · `android/app/src/main/java/` (3 files) ·
`core/server.py` · `core/trace.py` · `docs/INFRASTRUCTURE.md` · `scripts/check_apk_sync.sh` ·
`scripts/renew_cert.sh` · `static/index.html` · `tests/test_turn_source_marker.py`

### Two corrections to SESSION.md found by the diffing

1. **`core/trace.py` is listed as a phase-4 file. It is not.** Its uncommitted diff is 100% headset
   (the `source` field); phase 4's per-job cost seam in that file is **already committed** at HEAD
   (`core/trace.py:291-297`).
2. **Three headset files SESSION.md does not name were dirty:** `core/server.py` (turn-source
   marker), `docs/INFRASTRUCTURE.md` (TLS cert renewal + the 09-19 outage), `static/index.html`
   (the headset toggle).

### Verified state as of this writing

Index holds exactly the 26 paths (`+7,075 / −68`). `core/orchestrator.py` is `MM` — phase-4 hunks
staged, the two headset hunks unstaged, confirmed by reading both halves. No headset path is
staged. **The commit has not been made.**

### Commands — MacBook, run in a terminal you type into

```bash
# 4. the commit (steps 1-3 already ran)
cd /Users/md-homefolder/Desktop/multi-model-mcp && git commit -F - <<'MSG'
Build phase 0: the phase-4 tree as the record

The v3 Build package as three review rounds left it, committed unchanged so
phase A's deletion is a reviewable, reversible diff rather than a mix of
unstaged removals and unstaged keeps (plan v4.11 section 10 step 0).

core/orchestrator.py is staged at 10 of its 12 hunks: the headset-mode chat's
`source` parameter and its start_request_trace call are left unstaged, because
the committed core/trace.py does not accept that argument and the commit would
raise TypeError on every streamed turn.
MSG
```

---

## Phase A-Red — carve-out for the coordinating window (NOT the phase A window)

**Phase A needs two Red-tier edits. They are not in the phase A prompt and must not be.** The plan
says so twice — § 14: *"the routing-file, router and scheduler edits (Red) are made in the main
session, not by a subagent"*; § 16: *"the seams out (router: main session, Red)"* — and CLAUDE.md's
standing rule is that Red-tier work is never delegated.

1. **`core/scheduler.py:742`** — `"function": "core.build.runner.tick"` is re-pointed to
   `core.build.tick`. This must land **before** the old package is deleted (§ 10 step 1, Opus
   finding 4: the REPAIR counter must never be dark, not for a commit).
2. **`core/router.py:70,73`** — `_merge_overlay_routing` removed, along with its
   `from core.build.overlay import routing_entries` at `:100`. One of the four retired load seams.

**A third item named in § 10 does not exist in the tree.** § 10 says to remove
`answer_interview_item` *"in `register_tools()` and its Synthesizer grant"*. Verified: the grant is
in **neither** `config/modules/routing.yaml` nor `routing_cloud.yaml` — phase 4 never wired it. So
the removal is `register_tools()` only, which is `core/orchestrator.py` (Amber) and belongs to the
phase A window. Nothing Red is owed there.

---

## Phase A

```
Model: Opus 5, effort xhigh.
```

/metatron-code first.

You are building **phase A of Build v4.11**: the new `core/build/` package — salvage by copy, the
rest written fresh, with tests — then re-pointing every caller, then deleting the old package and
its seams. Nothing user-visible ships in this phase. Nothing deploys.

### Read before you write anything

1. **`archive/plans/build_vertical_plan_2026-09-24.md` — in full.** It is 998 lines and every
   section binds. The header paragraphs record what each of ten review rounds changed and why, so
   if you find yourself asking "why is it built this way", the answer is in the header or in
   `archive/plans/adversarial_review_build_vertical_plan_2026-09-24.md` /
   `..._cold-fable.md`. Those two reviews ended clean — **read them for reasons, never to
   re-review the plan.**
2. **The sections that bind this phase specifically:** § 0 (all thirteen rulings — they are Mike's
   and are not reopened), § 3 (the node graph: what `driver.py` must enforce, N11/N12/N13's four
   channels and the patch), § 4 (the artifacts and their hard rules — what the validators assert),
   § 5 (tickets, jobs, registry, board), § 6 (the content gates and the salvaged deny list), § 10
   (the exact kept/changed/deleted list — this is your file manifest), § 12 (verification — the
   rows quoted below), § 14 (cost), § 16 (execution order).
3. **`SESSION.md` and `ROADMAP.md`** — loaded by `/metatron-code`; the Mandatory Pre-Edit Context
   Check in `CLAUDE.md` requires both before any edit.

### Preconditions — check these first and stop if they do not hold

- `git log --oneline -1` shows **`505b254 Build phase 0: the phase-4 tree as the record`** — the
  record commit, 26 files, `+7,075 / −68`. That commit is your base. If HEAD is behind it, phase 0
  has not been made — **stop and say so**; the entire deletion step depends on it existing. If HEAD
  is *ahead* of it, another chat has committed since: that is fine, note the hash in your handoff.
- The main tree also carries an unrelated chat's uncommitted headset-mode work in `.gitignore`,
  `DEV_BACKLOG.md`, `android/**`, `core/server.py`, `core/trace.py`, `docs/INFRASTRUCTURE.md`,
  `scripts/check_apk_sync.sh`, `scripts/renew_cert.sh`, `static/index.html`,
  `tests/test_turn_source_marker.py`, and two hunks of `core/orchestrator.py`. **None of it is
  yours. Do not stage, revert, or edit any of it.**

### Work in a worktree

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && ./scripts/new_worktree.sh v4a-package
```

This creates `/Users/md-homefolder/Desktop/metatron-wt-v4a-package`. **Use that absolute path for
every edit.** A subagent's cwd stays pinned to the main tree, so a relative-path write lands there
instead (`scripts/hook_commit_guard.py`'s own recorded note).

> **The slug deliberately does not begin with `build-`.** One of your own deliverables is a
> `metatron-wt-build-` prefix skip in `scripts/hook_subagent_gate.py`. A worktree named
> `build-something` would be skipped by the gate you just wrote, so your own work would go unswept.

### The work, in this order — the order is a review finding, not a preference

**Opus review finding 4: nothing is deleted until the new modules its callers need exist.** The
ticket inbox and the REPAIR counter must never be dark, not for a single commit.

1. **Salvage by copy** into the new package — the nine rows of § 10's salvage table, below.
2. **Write fresh**: `core/build/{tickets,jobs,tick,manifest,table,brief,registry,coherence,gates,
   verify,driver}.py`. (`doors.py` is phase B — do not write it.)
3. **Rewrite `scripts/check_build_registration.py`** as the tracked-file checker: routing parity,
   the Coordinator directory entry and valid-name list, knowledge domains, the registry row and run
   line, the deny list. It must assert wiring **only for `landed` rows** — a `staged` row passes in
   a sandbox that holds no wiring and the same script fails in a main tree missing some (cold read
   2). This is Opus finding 5: the rewrite comes **before** `writer.py` is deleted, because sweep
   check 11 calls this script.
4. **Add the `scheduler-functions-resolve` sweep check** — imports every `_DEFAULT_JOBS` function
   so a dangling dotted path fails the sweep instead of being swallowed by `fire_function` every 30
   minutes.
5. **Re-point `tools/build.py`** to the new ticket store (it currently does
   `from core.build import jobs as J` at `:56` and `:154`).
6. **Add the `--sandbox` flag to `scripts/new_worktree.sh`**: links `.venv` only, and does **not**
   link back `.env`, `vertex-key.json`, `certs/` or `.claude/settings.local.json`; registers as
   `metatron-wt-build-<slug>`.
7. **Add the `metatron-wt-build-` prefix skip** to `scripts/hook_subagent_gate.py:_dirty_worktrees`.
8. **STOP and report.** Two Red edits belong to the coordinating window and must land before you
   delete anything: the `core/scheduler.py` `build_tick` re-point and the `core/router.py`
   `_merge_overlay_routing` removal. **Say in your handoff that you have reached this point.** Do
   not touch either file. If Mike tells you the Red half has landed in the main tree, continue.
9. **Then the deletion**, and only then — see the delete list below.
10. **Then the six regression gates**, all green.

### Files — from § 10, exactly

**Salvaged by copy — premise-free, hard-won. Copy, do not rewrite:**

| Piece | From | Note |
|---|---|---|
| Question Set / ledger-row / plan validators, minus the removed fields | `core/build/schemas.py` | **the compass-rule ordering is the one to keep exactly** |
| the transcript fixture and its test | `tests/fixtures/inquiry_rsvp_2026-09-17.md`, `tests/test_build_spine.py` | the only real pass/fail pair; produced before the rule existed |
| the id allocator | `core/build/ids.py` | replay-under-lock, no state |
| Build's question index | `core/build/index.py` | FAISS over questions; relocates to the Mac |
| the constitution check | `core/build/constitution.py` | reads an agent file, knows nothing of landing |
| the policy record shape and resolver | `core/build/policy.py` | home changes, shape does not |
| the presence-check call table | **`core/build/manifest.py`'s `_SOURCES`** | **not `probe.py` — Opus finding 8.** Carries the D4 argument repairs in its comments: `get_log_window` start/end window, `search_memory`'s required `query`, `read_archive`'s required category, `read_intake_queue`'s domain, `read_agent_config`'s `agent_name`, `read_email`'s `count`, and the seven `live: True` rows. **Losing these is the exact defect class three review rounds were spent finding.** |
| the control layer | `core/build/runner.py` — node order, `MAX_NODE_RETRIES` (`:101`), the retry-product cap counted from durable rows, the artifact-is-cursor rule, the park states, `NodeOutcome` (`:109`) | `_ask()` (`:229`) becomes "name the step"; the rest is `driver.py` (Opus finding 1) |
| the deny list | `core/build/writer.py:189-209` — `DENY_PREFIXES` (`:189`), `DENY_EXACT` (`:195`), `DENY_GLOBS` (`:206`) | path rules do not care who writes; goes into `gates.py` |

**Deleted — LAST, after step 8's Red half lands:**

- `core/build/` — the old 19 modules, whole
- the twelve `tests/test_build_*.py` suites
- `scripts/build_board.py`, `scripts/build_brief.py` (you write a fresh `build_board.py`)
- the seams phase 4 threaded into shared files:
  - `core/orchestrator.py`: the `load_agent` seam, the Coordinator prompt rewrite, the
    `_CONTEXT_SENSITIVE` / consequence fallbacks, the four Build agent names in
    `_ALWAYS_CONFIDENTIAL`, and `answer_interview_item` in `register_tools()`
  - `tools/wisdom.py`: `domain_agent_map`
  - `core/trace.py`: the per-job cost seam at `:291-297`
  - the `--overlay` flags on three check scripts
  - `config/modules/build.yaml`: the ceiling and autonomy blocks (leave only the caps and
    `api_allowance_usd_per_step: 1.00`)

**Kept in shared files — these are runtime, not Build. Do NOT remove them:**

- the code-written correction attribution in `core/orchestrator.py` (`_corrected_agents`,
  `_HEAD_AND_ROOT_AGENTS`, `_handle_user_correction(coord_output, persona)`)
- `tools/turn_referent.is_exchange()` / `last_exchange()` and both their readers
- the logger's per-fact event write and `_NEVER_DEDUPED` (D10)
- `request_build` and `context_block` in `tools/build.py`
- the `build_tick` scheduler entry, reduced to the REPAIR counter and dispatch counts
- the `BUILD_PROPOSED` / `BUILD_CHECK_FAILED` labels in `scripts/sync_dev_backlog.py`

**Untouched, absolutely:** `config/constitution.md` · `deploy.sh` · `.claude/settings.json` ·
`core/spend_guard.py` · `core/persona.py`.

> **§ 10's own claim, which is also your acceptance criterion:** *"Outside Build, the only
> behaviour that changes is the removal of the four seams' fallbacks, which nothing tracked ever
> reached."* If you find a second behaviour change outside Build, that is a finding — report it,
> do not absorb it.

### The § 12 verification rows this phase must satisfy — quoted verbatim, do not paraphrase

| Piece | Command | Proves |
|---|---|---|
| Schemas | `python3 tests/test_build_schemas.py` | v3's assertions that survive, plus: a `history` row with a `variable_scope` fails; a required input with no `if_user_lacks_it` fails; an `external` row without `on_failure` fails; a Question Set carrying `candidate_sources` fails; a plan gate without a citation fails; a plan declaring an `all_personas` variable whose row lacks `if_user_lacks_it: ask` fails (verify residual 10) |
| Compass rule | `python3 tests/test_build_spine.py` | unchanged: turn 2 fails, turn 4 passes |
| Driver | `python3 tests/test_build_driver.py` | a node that fails validation is retried exactly once, then the job parks; a second review send-back parks; a job at a gate state yields no step; a job whose N2 and N4 artifacts exist resumes at N7 with no step for either; the counts are re-derived from `attempts.jsonl` after the process is restarted, including a failed node that wrote no artifact (finding 1, verify residual 1) |
| Sandbox and patch | `python3 tests/test_build_gates.py` (worktree half) | a `--sandbox` worktree contains no symlink to `.env`, `vertex-key.json`, `certs/` or `settings.local.json`; a write to `<wt>/.env` changes the main tree's `.env` hash by nothing and is refused by channel (b); a write to `<wt>/data/personas/x/profile.yaml` is refused by (b) with no porcelain line; a relative-path write that lands a `files[]` path in the main tree is refused by (d), including one inside a directory that did not exist before, while an unrelated path dirtied in the main tree by a second process is reported and not refused (cold read 4, cold verify NEW 2); a legitimate new package `tools/<cap>/__init__.py` named in `files[]` passes channel (a) rather than parking as `tools/<cap>/` (cold verify NEW 2); a harness marker written under `<wt>/.claude/.session_state/` or `<wt>/.claude/.session_edits/` is NOT refused, while an edit to `<wt>/.claude/settings.json` or a new file under `<wt>/.claude/agents/` IS (round 3 NEW 1); a file written to `<wt>/.git/hooks/pre-commit` — which lands in the main repository's hook path — IS refused by channel (c) with that path named in the refusal, and the driver made no write of its own under the main repository's `.git/` (asserted by hashing the directory before the driver runs and after it refuses, with the planted file then removed by the test, not the driver) (round 4 NEW 1, round 5 NEW 1); the patch's path set equals the implementer's half of `files[]`, applying it to a clean main tree reproduces the worktree byte-for-byte, and the git commands the driver issued in the worktree contain no `add`, `commit` or `stash` (verify NEW 1, NEW 2; round 2 NEW 2) |
| Wiring gate | fixture main tree after patch + Red half, with one routing entry deleted | the driver refuses to print the staging manifest, naming the missing entry, and prints the per-file revert line; restore it → manifest printed; same with the Coordinator directory line removed and with the agent file naming a tool outside its grant (round 2 NEW 1). Then plant an unrelated sweep red (a duplicate `DB-` id in a fixture backlog) → the manifest is still printed, with the red reported beside it (round 3 NEW 2) |
| Gates | `python3 tests/test_build_gates.py` | every content assertion from `test_build_writer.py` that is not an overlay rule, on a fixture worktree, **plus the path rules**: a worktree diff touching a deny-list path is refused with the worktree left in place and byte-identical after the refusal, the path named on the board; a changed path outside the implementer's half of `files[]` is refused; a plan with a Red path in the implementer's half fails validation before N11 (findings 2, 3); a routing grant absent from `risks[]` fails |
| Tick | `python3 tests/test_build_tick.py` | three corrections against a registered capability file one repair ticket; `scheduler-functions-resolve` fails on a dangling `_DEFAULT_JOBS` path and passes on the tree (finding 4) |
| Question table | `python3 tests/test_build_table.py` | every ledger row appears once; an uncited question lands in "shaped nothing"; a plan item with no citation lands in "unsupported"; the acceptance column is empty until N14 |
| Registry | `python3 tests/test_build_registry.py` | a `landed` row within 14 days refuses a same-fingerprint ticket on the VM; `abandoned` within 72 h likewise; dispatch counts exclude ticks and the landing day (unchanged) |
| Registration check | `python3 scripts/check_build_registration.py` on a tree with a routing entry in one file only, and on one with an agent file and no routing entry | exit 1 naming the gap, both cases — the `time_director` shape (finding 5); the same tree with the row at `status: staged` → exit 0, so the sandbox passes and the main tree fails on exactly the same script (cold read 2) |
| Implementer boundary | a plan naming `config/constitution.md` or `.env` in `files[]` | the plan fails validation before N11; a fixture worktree hand-edited past it is refused by the driver at N12 on the deny list through whichever channel sees the path, and the change never reaches the main tree — **neither the harness nor `git status` is relied on for gitignored paths inside a worktree** (finding 3, verify NEW 2) |
| Landing pre-checks | main tree with a `files[]` path dirtied by hand — once a patch path, once `config/modules/routing.yaml`; then a clean tree whose HEAD is one commit past the sandbox's base | first two: N13 refuses to start, naming the path; third: the patch applies with `--3way`, **`git diff --cached` is empty afterwards** and `git diff -- <files[]>` equals the sandbox's diff; a planted conflict in a patch that also ADDS a new file parks the job with `git status --porcelain -uall -- <files[]>` empty afterwards — the new file removed, the pre-existing paths byte-identical to HEAD, the index clean; the printed revert line, run on a tree after a 3-way apply plus the Red half, leaves the same status empty; both use `driver.revert_landing` (cold read 1, cold verify NEW 1, round 2 NEW 1) |
| Sandbox stop gate | a parked `metatron-wt-build-x` with a failing sweep, then any other subagent stopping | the other subagent's stop is not blocked by the Build sandbox; a build subagent handed a pre-existing main-tree red as its stop reason still yields a validating artifact the driver accepts (cold read 6) |

**Use fixtures for all of the above.** Every row is satisfiable without `/build` existing. Rows
**deferred to later phases, not yours, and not a failure of this phase**: Doors (phase B), Trigger
and Under-filing (B-Red), Resume and Persona-qualified ids (C — both need the `/build` command),
End to end (F).

### The six regression gates — all green before you report done

These are named by § 10 and by `ROADMAP.md`. They prove the seam removal broke nothing:

```bash
cd /Users/md-homefolder/Desktop/metatron-wt-v4a-package
python3 tests/test_a4_complexity_threading.py
python3 tests/test_turn_referent.py
python3 tests/test_synth_module_injection.py
python3 tests/run_knowledge_routing.py --persona danny_park
./scripts/qa_sweep.sh
python3 core/server.py --persona mike --port 8042   # clean start, then ONE full pipeline turn
```

`run_knowledge_routing.py` is the only check that the knowledge pre-fetch survives and it exercises
`run_pipeline_session_stream` — the path a module move is most likely to break.

### Standing rules — these are not negotiable

1. **Build in the worktree at `/Users/md-homefolder/Desktop/metatron-wt-v4a-package`, by absolute
   path.** Never a relative path.
2. **Run what you changed. A green sweep is not a test.** `qa_sweep.sh` runs `py_compile`, which
   parses but does not execute — it has passed a `NameError` that crash-looped the scheduler after
   a deploy.
3. **Never `git commit`, never `git push`, never `./deploy.sh`.** Mike commits and deploys.
4. **Do not touch a Red file:** `config/agents/*.md`, `config/modules/routing*.yaml`,
   `core/router.py`, `core/persona.py`, `core/scheduler.py`, `core/spend_guard.py`. **This phase
   genuinely needs two of them** (`core/scheduler.py`, `core/router.py`) — that is step 8's stop
   point, and those edits are made in the coordinating window with Mike approving each one. If any
   other Red file appears necessary, **stop and say so.**
5. **Nothing about this project leaves this machine.** No `WebFetch`, no `WebSearch`, no published
   artifact. To produce a shareable document, write a file under `archive/`.
6. **If you disagree with the plan, report it in the handoff.** Do not re-litigate § 0's rulings or
   the closed findings of either review. The decision is Mike's.

### Cost

**§ 14 budget for this phase: $24–34** — the largest phase in the build. It covers the salvage, the
eleven fresh modules and their tests, the `check_build_registration.py` rewrite, the caller
re-points, the deletion, and the six regression gates. **If you pass $34, say so in the handoff
rather than continuing quietly.** There is no per-token bill on the subscription; the real bound is
the rate-limit window Mike is sitting in front of.

### Handoff — how this phase ends

1. Capture the transcript:
   ```bash
   python3 ~/.claude/tools/archive_chats.py
   ```
2. Write the patch, so the work can land in one tree in one commit — this mirrors the plan's own
   N12 mechanism and issues no staging verb:
   ```bash
   WT=/Users/md-homefolder/Desktop/metatron-wt-v4a-package
   OUT=/Users/md-homefolder/Desktop/multi-model-mcp/archive/handoffs/2026-09-24-build-phase-A.patch
   git -C "$WT" diff HEAD --binary > "$OUT"
   for f in $(git -C "$WT" ls-files --others --exclude-standard); do
     git -C "$WT" diff --no-index --binary /dev/null "$f" >> "$OUT" || true
   done
   ```
3. Write `archive/handoffs/2026-09-24-build-phase-A.md` covering:
   - **what shipped** — the file list as built, against § 10's manifest
   - **which § 12 rows passed, with their command output pasted** — not "tests pass"
   - **the six regression gates**, each with its result
   - **what was left open**, and anything where you disagreed with the plan
   - **the cost against $24–34**
   - **whether step 8's Red stop was reached and when**
   - **a landing note**: three of your target files are held dirty in the main tree by the
     headset-mode chat — `core/orchestrator.py`, `core/trace.py` and `.gitignore`. Your worktree
     branched from `505b254`, which is clean of all three, so this does not affect your build. State
     in the handoff **which hunks of those three files your patch touches, by line range**, so Mike
     can see at a glance whether they overlap the other chat's lines before he applies the patch.
     `.gitignore` is the one to be explicit about: your single `data/build/` line may land adjacent
     to that chat's additions.
4. **Leave the worktree in place** for Mike to read. Do not run `rm_worktree.sh`.

---

## Phase B

```
Model: Opus 5, effort xhigh.
```

/metatron-code first.

You are building **phase B of Build v4.11**: the **read doors** — one endpoint on the VM server that
lets a Librarian subagent running on the Mac read the persona's data where it lives, with only
results crossing. Nothing user-visible ships. Nothing deploys.

### Read before you write anything

1. **`archive/plans/build_vertical_plan_2026-09-24.md` — in full** (998 lines, every section binds).
   Reasons behind any mechanism are in the header changelog or in
   `archive/plans/adversarial_review_build_vertical_plan_2026-09-24.md` and `..._cold-fable.md`.
   **Read those for reasons, never to re-review the plan** — both ended clean.
2. **Binding for this phase:** § 0 rulings 10 and 11 (privacy, and "built as the Librarian needs
   them"), § 2 (what the VM keeps), § 6 **§ The read doors — this is your specification**, § 9
   (the Librarian's substrate), § 10 (the written-fresh list), § 12 (the Doors row, quoted below),
   § 14 (cost).
3. **`SESSION.md` and `ROADMAP.md`**, loaded by `/metatron-code`.

### Preconditions

- `git log --oneline -1` shows **`224e5d4`** or later. Phases 0, A and B-Red are committed:
  `core/build/` is the new 16-module package, the old one is gone, and `request_build` is granted
  to the Coordinator and the eight category agents.
- **`core/build/doors.py` does not exist. Phase A deliberately skipped it — it is yours.**
- `core/server.py` is clean. A parallel chat committed its headset work at `3066d66`; if it has
  gone dirty again, **`git diff core/server.py` before you touch it** and stay out of its hunks.
- **Phase D may be running in another window at the same time.** It builds `search_conversations`
  and `read_journal_range` in `tools/` and registers them in `core/orchestrator.py`. You do not
  share a file with it — but see § The allowlist below, which is where the two phases meet.

### Work in a worktree

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && ./scripts/new_worktree.sh v4b-doors
```

Everything goes in `/Users/md-homefolder/Desktop/metatron-wt-v4b-doors`, **by absolute path** —
a subagent's cwd stays pinned to the main tree, so a relative write lands there instead.

### What you are building — § 6, exactly

**One endpoint on the VM server beside `/monitor/file`, two modes.** Same bearer token
`scripts/sync_dev_backlog.py` already mints, Tailscale-only like every `/monitor` route, and
**persona-bound from the query**.

**Mode 1 — the presence check.** `GET /monitor/tool?presence=<source_id>`

Takes a **source id, not arguments**. The server runs the fixed, code-chosen call from
`core/build/manifest.py`'s `_SOURCES` table and returns `{state, count, window}` — **no content**.
This is the old `probe.py` moved to the VM with its injection answer unchanged, and that answer is
the point: **the model names a source, code chooses the call.** A corpus carrying an injected
instruction can influence what is *named*, never what is *called*.

`_SOURCES` already carries the D4 argument repairs and the seven `live: True` rows. Phase A
salvaged it verbatim. Do not rewrite it.

**Mode 2 — a research read.** `GET /monitor/tool?name=…&args=…`

- The name must be in the Librarian's read set — v3.7 § 6.3's list — **minus the seven live feeds.
  No outbound tool sits behind a door**, so content the Librarian reads can never compose a call
  that leaves the machine. A live-feed name is a **403**.
- **Arguments are validated server-side** against a per-tool schema with caps: window ≤ 90 days,
  `k` ≤ 50, `max_entries` ≤ 200. Beneath those, the wisdom store's own `READ_CAP`
  (`tools/wisdom.py:345`) — the one read tool in the set that defines its own. Anything outside the
  schema or over a cap is a **400 carrying the schema**, not a bare rejection.
- What stays model-chosen is *which* of the persona's own data to read and how much, which ruling
  11 already grants.

**The Mac client is `scripts/vm_read.py`** — the Librarian subagent's only permitted Bash form.

### The allowlist — where this phase meets phase D

**Write the allowlist already naming `search_conversations` and `read_journal_range`.** § 6 says the
read set is "v3.7 § 6.3's list plus `search_conversations` and `read_journal_range` **once built**".
Phase D builds them; you list them. Until they exist the door correctly refuses them as unregistered
— that is the right behaviour, not a bug, and your tests should assert it.

Ruling 11 is "built as needed": **run 1 needs `get_log_window`, `read_wisdom`, `search_memory`,
`list_schedules`, `read_profile`.** The allowlist grows by a line per run; do not pre-build the rest.

### Files

**Create:** `core/build/doors.py` · `scripts/vm_read.py` · `tests/test_build_doors.py`
**Change:** `core/server.py` — the new endpoint only, beside `/monitor/file`
**Delete:** nothing.

`config/agents/*.md`, `config/modules/routing*.yaml`, `core/router.py`, `core/persona.py`,
`core/scheduler.py`, `core/spend_guard.py` are **Red and not yours.** This phase should need none
of them; if one seems necessary, **stop and say so**.

### The § 12 row this phase must satisfy — verbatim, do not paraphrase

| Piece | Command | Proves |
|---|---|---|
| Doors | `python3 tests/test_build_doors.py` | `presence=<id>` runs the salvaged fixed call and returns no content; an argument outside the per-tool schema or over its cap → 400 with the schema; any live-feed name → 403 (finding 9) |

**Add three assertions of your own**, because the row above does not cover what the endpoint is:
auth — a request with no bearer, and one with a wrong bearer, is refused; **persona binding** — a
request bound to persona A cannot read persona B's data; and **the not-yet-built case** — an
allowlisted name whose tool does not exist yet is refused as unregistered rather than 500ing.

### Standing rules

1. **Work in `/Users/md-homefolder/Desktop/metatron-wt-v4b-doors`, by absolute path.** Never relative.
2. **Run what you changed. A green sweep is not a test** — `py_compile` parses without executing and
   has passed a `NameError` that crash-looped the scheduler after a deploy.
3. **Never `git commit`, never `git push`, never `./deploy.sh`.**
4. **No Red file.** If one seems needed, stop and say so.
5. **Nothing leaves this machine** — no `WebFetch`, no `WebSearch`, no published artifact.
6. **A live gate run dirties tracked fixture-persona files** (`data/personas/danny_park/…`);
   `.gitignore` does not untrack what was committed before the rule. `git checkout HEAD --` them
   before you generate the patch, or they ride into the commit.
7. **Disagree with the plan in the handoff, not in the code.** § 0's rulings are Mike's.

### Cost

**§ 14 budget: $8–12.** Say so in the handoff if you pass $12 rather than continuing quietly.

### Handoff

1. `python3 ~/.claude/tools/archive_chats.py`
2. The patch — no staging verb is issued, deliberately:
   ```bash
   WT=/Users/md-homefolder/Desktop/metatron-wt-v4b-doors
   OUT=/Users/md-homefolder/Desktop/multi-model-mcp/archive/handoffs/2026-09-24-build-phase-B.patch
   git -C "$WT" diff HEAD --binary > "$OUT"
   for f in $(git -C "$WT" ls-files --others --exclude-standard); do
     git -C "$WT" diff --no-index --binary /dev/null "$f" >> "$OUT" || true
   done
   ```
3. `archive/handoffs/2026-09-24-build-phase-B.md` — what shipped; the § 12 Doors row and your three
   added assertions **with their output pasted**; what was left open; cost against $8–12; and
   whether `core/server.py` was clean when you touched it.
4. **Leave the worktree in place.**

---

## Phase D

```
Model: Opus 5, effort xhigh.
```

/metatron-code first.

You are building **phase D of Build v4.11**: two read tools the Librarian needs and the system does
not have — **`search_conversations`** and **`read_journal_range`**. This is ordinary development,
the `/fix` shape, not Build machinery. Nothing user-visible ships. Nothing deploys.

### Read before you write anything

1. **`archive/plans/build_vertical_plan_2026-09-24.md` § 9 (the Librarian's substrate), § 6 (the
   read doors — your two tools enter its allowlist), § 10, § 14.** The rest of the plan is context
   rather than binding for this phase; § 9 is four lines and is the whole specification, which is
   deliberate — these are ordinary tools.
2. **`docs/CONVENTIONS.md` § adding a module and § the tool + schema pattern.** This phase is two
   new tools registered the normal way; follow the existing pattern rather than inventing one.
3. **`SESSION.md` and `ROADMAP.md`**, loaded by `/metatron-code`.

### Preconditions

- `git log --oneline -1` shows **`224e5d4`** or later.
- **Phase B may be running in another window at the same time.** It builds the read doors and
  lists your two tool names in its allowlist *before they exist*, which is correct — the door
  refuses an unregistered name until you land. You share no file with it.
- You **do** share `core/orchestrator.py`'s `register_tools()` with nothing else right now, but
  check `git status` before you start: if another chat holds uncommitted lines in it,
  `git diff core/orchestrator.py` and stay out of their hunks.

### Work in a worktree

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && ./scripts/new_worktree.sh v4d-readtools
```

`/Users/md-homefolder/Desktop/metatron-wt-v4d-readtools`, **absolute paths only**.

### What is missing, and where it goes

**`search_conversations` — there is no conversation search at all today.** Conversation turns live
in a per-persona SQLite database (`core/server.py:62`, `DB_PATH = data/conversations/metatron.db`,
with per-persona directories at `data/personas/{p}/conversations`). Verify the actual storage shape
before designing against this sentence — it is a pointer, not a specification.

**`read_journal_range` — journal reads are single-date today.** `read_journal` lives in
[`tools/diarist.py`](tools/diarist.py). A range read is the natural sibling; follow that module's
existing conventions rather than starting a new one.

**Both must be registered** in `core/orchestrator.py`'s `register_tools()` — schema list and
handler map — like every other tool.

### Two constraints that are easy to miss

1. **These are read tools for a research pass, so they need caps.** Phase B's door enforces its own
   (`k` ≤ 50, `max_entries` ≤ 200, window ≤ 90 days), but a tool that returns an unbounded corpus
   when called directly is a problem the door happens to be hiding. Give each a sane default and a
   hard ceiling, and say what you chose in the handoff.
2. **Do not grant them to any agent.** They enter the **read-door allowlist**, which is phase B's
   file, not `allowed_tools` in a routing file. Routing files are Red and are not yours. Registering
   without granting is class 2 in `check_agent_tools.py` — advisory on a tracked tree, which is the
   correct state here.

### Files

**Create or change:** `tools/diarist.py` (or a sibling module, your call — say which and why) ·
whatever module `search_conversations` belongs in · `core/orchestrator.py` `register_tools()` ·
tests for both.
**Delete:** nothing. **Red files:** none — if one seems needed, stop and say so.

### Verification

§ 12 gives this phase **no row of its own** — the two tools are proven through phase B's Doors row
once both have landed. So write your own tests and say in the handoff what they assert:

- each tool returns what it claims on a persona with data, and an empty result rather than an error
  on one without
- the cap holds: a request for more than the ceiling returns the ceiling, not everything
- a range read spanning dates with no journal entries does not error
- both are registered — `register_tools()` returns them in the schema list and the handler map

### Standing rules

1. **Work in `/Users/md-homefolder/Desktop/metatron-wt-v4d-readtools`, by absolute path.**
2. **Run what you changed. A green sweep is not a test.**
3. **Never `git commit`, never `git push`, never `./deploy.sh`.**
4. **No Red file** — `config/agents/*.md`, `config/modules/routing*.yaml`,
   `core/{router,persona,scheduler,spend_guard}.py`.
5. **Nothing leaves this machine.**
6. **A live test run dirties tracked fixture-persona files.** `git checkout HEAD --
   data/personas/…` before generating the patch.
7. **Disagree in the handoff, not in the code.**

### Cost

**§ 14 budget: $4–7.** Say so if you pass $7.

### Handoff

1. `python3 ~/.claude/tools/archive_chats.py`
2. The patch:
   ```bash
   WT=/Users/md-homefolder/Desktop/metatron-wt-v4d-readtools
   OUT=/Users/md-homefolder/Desktop/multi-model-mcp/archive/handoffs/2026-09-24-build-phase-D.patch
   git -C "$WT" diff HEAD --binary > "$OUT"
   for f in $(git -C "$WT" ls-files --others --exclude-standard); do
     git -C "$WT" diff --no-index --binary /dev/null "$f" >> "$OUT" || true
   done
   ```
3. `archive/handoffs/2026-09-24-build-phase-D.md` — what shipped, the caps you chose and why, your
   tests with their output, what was left open, cost against $4–7.
4. **Leave the worktree in place.**

---

## Phase C

```
Model: Opus 5, effort xhigh.
```

/metatron-code first.

You are building **phase C of Build v4.11**: the **five Build subagent definitions and the `/build`
command** — the layer that actually drives the graph phase A built. This is the last phase before
the deploy. Nothing user-visible ships and nothing deploys, but this is the phase that makes Build
runnable, so it gets its own adversarial review before it touches a real ticket.

### Read before you write anything

1. **`archive/plans/build_vertical_plan_2026-09-24.md` — in full** (998 lines, every section binds).
   Header changelog and the two review files (`adversarial_review_..._2026-09-24.md`,
   `..._cold-fable.md`) hold the reasons behind every mechanism. **Read them for reasons, never to
   re-review the plan** — both ended clean.
2. **Binding hardest here:** § 3 **the node graph, in full — this is your specification**, every node
   N2→N14 including the four channels at N12 and the one-sitting rule at N13; § 0 (all thirteen
   rulings, especially 2 on models, 5 on Inquiry's vacuum, 6 on every question travelling, 8 on the
   review, 11 on the read doors); § 4 (the artifacts your agents produce); § 7 (**the agent table and
   the command's four forms**); § 12 (three rows, quoted below); § 14; § 16.
3. **`.claude/rules/docs-and-logs.md`** — it governs `.claude/commands/**`. The rule that binds you:
   **command files carry procedure, not history.** When an incident teaches something the lesson goes
   to `archive/log/` and the command gets at most a line. `archive.md` is capped at 150 lines and
   `backlog.md` at 200 in `CEILINGS`; `build.md` has no entry yet, which is not licence to sprawl.
4. **`.claude/agents/adversarial-reviewer.md`** — the convention your five definitions follow:
   frontmatter `name`, `description`, `model`, `tools`, then the body. Copy its shape.
5. **`SESSION.md` and `ROADMAP.md`**, loaded by `/metatron-code`.

### Preconditions

- `git log --oneline -1` shows **`2894ad5`** or later. Phases 0, A, B-Red, B and D are committed:
  the 16-module `core/build/` package, the read doors, `request_build` on the Coordinator and the
  eight category agents, and `search_conversations` / `read_journal_range`.
- **`core/build/driver.py` already exists and is tested (19 checks).** You are not writing the
  runner. Read it before you write the command.
- Nothing in `core/build/` needs changing. If you think it does, that is a finding for the handoff.

### Work in a worktree

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && ./scripts/new_worktree.sh v4c-command
```

`/Users/md-homefolder/Desktop/metatron-wt-v4c-command`, **absolute paths only**.

### The five agent definitions — § 7's table, exactly

| File | `model:` | `tools:` | What it is |
|---|---|---|---|
| `.claude/agents/build-inquiry.md` | `opus` | **none** | judgement in a vacuum — the gap text, trigger, mode, and in REPAIR the dossier. **No manifest, no data, no tools.** Carries the compass rule and the spine abstract from v3.7 § 15 |
| `.claude/agents/build-librarian.md` | `opus` | `Read, Grep, Bash(python3 scripts/vm_read.py *)` | locator then adjudicator; reads as much as it needs, no ration |
| `.claude/agents/build-planner.md` | `opus` | `Read, Grep, Glob` | plans, never creates; opens the code to direct the new agent at the right tools |
| `.claude/agents/build-implementer.md` | `opus` | `Read, Edit, Write, Bash, Grep, Glob` | builds against a settled plan, **Amber and Green files only** |
| `.claude/agents/build-coherence.md` | `fable` | `Read` | reads the landed set |

**Three rules on the definitions, each from the plan:**

1. **No agent names its model in its body** (§ 7). The frontmatter carries it; the prose must not.
2. **None of them reaches a Vertex model.** These are Claude Code subagent definitions on Mike's
   subscription, not runtime agent files — ruling 1. They have **no routing entries** and
   `resolve_model("build_inquiry")` raising is permanently correct (§ 8).
3. **The implementer's prompt carries the worktree's ABSOLUTE path and forbids relative paths.** A
   subagent's cwd stays pinned to the main tree, so a relative `Write` lands there — this is the
   `/fix` rule and cold read 4. Its Bash grant is the test and sweep commands only; it never runs
   `deploy.sh`, `git push`, `git commit` or `git add`.

### The command — `.claude/commands/build.md`

Four forms (§ 7):

```
/build [--persona mike]                    list open tickets (fetched) and jobs in flight
/build [--persona mike] BLD-MMDD-NN        run the graph from wherever the artifacts say it is
/build [--persona mike] repair BLD-MMDD-NN same, REPAIR mode, dossier first
/build coherence                           the periodic set review
```

**The single most important property, and the one a reviewer will attack first: the command is NOT
the runner. `core/build/driver.py` is.** The command asks the driver for the next step, spawns the
subagent or runs the code node the driver names, hands the result back, and repeats. It stops where
the driver says a human gate is. **A model cannot skip a park or add a retry, because the driver
will not name the step** — that was Opus finding 1, and the whole control layer was salvaged into
Python for exactly this reason. Do not reimplement node order, retry counts, the send-back bound or
the park states in markdown.

**What the command does that the driver cannot:**

- **[N6] the interview happens in chat**, in the build session, with Mike in front of it.
  `answer_interview_item` is retired — do not call it.
- **[N8]** spawns the **`adversarial-reviewer` agent definition directly**, with the same three-line
  prompt `/adversarial-review` sends — brief path, `high`, repo root — and nothing else. The report
  lands in the **job directory**, not `archive/plans/`, so nothing tracked is written before [N9].
- **[N11]** spawns the implementer into `./scripts/new_worktree.sh --sandbox <slug>`.
- **[N13]** applies the patch to the main tree, writes the **Red half of `files[]` there** — where
  the harness's `ask` rules prompt Mike — flips the registry row `staged` → `landed`, and runs the
  driver's wiring gate. **One unbroken sitting**, ending in Mike's commit or the printed revert.
- **It never commits, pushes or deploys.** Ever.

`--persona` defaults to `mike`; the job directory, the board and the registry row all carry it
(cold read 5).

### Also in this phase: `tests/test_build_manifest.py`

**It does not exist, and `core/build/manifest.py`'s docstring cites it twice** as the thing enforcing
the content-free rule — *"still enforced by `tests/test_build_manifest.py`'s grep of every profile
value"*. So the rule that keeps the manifest safe to render into a prompt has no test while the
docstring asserts it does. Phase D found it; § 12 gives manifest no row.

**It belongs here** because the manifest is rendered into the Librarian's prompt, which is what you
are writing. Write it: assert the manifest a Librarian receives contains **no persona values** — ids,
descriptions and shapes only — by grepping every value from a populated fixture persona against the
rendered output. If you conclude the docstring's claim is wrong rather than merely untested, say so
in the handoff; do not quietly delete the sentence.

### The § 12 rows this phase must satisfy — verbatim, do not paraphrase

| Piece | Command | Proves |
|---|---|---|
| Resume | start `/build BLD-…`, kill the session after N4, restart | N2 and N4 skipped, N7 runs; no duplicate artifact |
| Review sees the table | run N7 → N10 → N8 on a fixture job | the file handed to `/adversarial-review` contains the question table; the review lands in the brief after it (finding 6) |
| Persona-qualified ids | two fixture personas each filing on the same day | the same `BLD-MMDD-NN` in both ticket files; `/build --persona a BLD-…` and `--persona b` open different job directories; `/build BLD-…` with no persona resolves `mike` (cold read 5) |

All three are runnable on fixture jobs without a real ticket and without a deploy. **The End-to-end
row is phase F's, not yours.**

### The exit gate — this phase is not done when the files exist

`/adversarial-review .claude/commands/build.md` **in Fable at `high`**, per § 14 and § 16: *"reviewed
by `/adversarial-review` (Fable) before it runs a real ticket."* Run it, put the two ranked blocks in
your handoff, and **address or explicitly refuse each finding**. A phase C that has written the
command but not survived its review is not finished.

### Standing rules

1. **Work in `/Users/md-homefolder/Desktop/metatron-wt-v4c-command`, by absolute path.**
2. **Run what you changed. A green sweep is not a test.**
3. **Never `git commit`, never `git push`, never `./deploy.sh`.**
4. **No Red file** — `config/agents/*.md`, `config/modules/routing*.yaml`,
   `core/{router,persona,scheduler,spend_guard}.py`. Note `.claude/agents/` and `.claude/commands/`
   are **not** Red; `config/agents/` is. If a Red file seems needed, stop and say so.
5. **Nothing leaves this machine.**
6. **A live gate run dirties tracked fixture-persona files** — `git checkout HEAD --` them before
   generating the patch.
7. **Disagree in the handoff, not in the code.** § 0's rulings are Mike's and the two reviews' closed
   findings are not reopened.

### Cost

**§ 14 budget: $12–18**, which includes the `/adversarial-review` pass. Say so if you pass $18.

### Handoff

1. `python3 ~/.claude/tools/archive_chats.py`
2. The patch:
   ```bash
   WT=/Users/md-homefolder/Desktop/metatron-wt-v4c-command
   OUT=/Users/md-homefolder/Desktop/multi-model-mcp/archive/handoffs/2026-09-24-build-phase-C.patch
   git -C "$WT" diff HEAD --binary > "$OUT"
   for f in $(git -C "$WT" ls-files --others --exclude-standard); do
     git -C "$WT" diff --no-index --binary /dev/null "$f" >> "$OUT" || true
   done
   ```
3. `archive/handoffs/2026-09-24-build-phase-C.md` — what shipped; the three § 12 rows **with output
   pasted**; the `test_build_manifest.py` result and whether the docstring's claim held; **the
   adversarial review's two ranked blocks and your response to each finding**; what was left open;
   cost against $12–18.
4. **Leave the worktree in place.**

---

## Phase E — the deploy checklist (Mike's hands; not a window prompt)

**`./deploy.sh` is Denied-tier** (`.claude/rules/deploy.md`): it pushes, SSHs the VM, pulls, runs
`pip install -r requirements.txt`, restarts the scheduler immediately, then drains in-flight SSE
streams for up to 3 minutes before restarting the server. Mike runs it. No session does.

**This is a catch-up deploy with Build inside it, not a Build deploy.**

> **CORRECTED 2026-09-24 by asking the VM instead of the record: the VM is at `7bca654`, NOT
> `b2b1dc7`.** It is four commits further on — the two calendar-invitation fixes of 09-09/09-10 and
> their archive commits — deployed on ~2026-09-10 with no fragment recording it. `b2b1dc7` then
> propagated as "where the VM is" through five `archive/log/` fragments, `SESSION.md` and this file,
> three of those tonight and by me. **This is `CLAUDE.md` § Infrastructure traps rule 2 — do not
> record a value with a short half-life — applied to a deploy SHA, and it failed in exactly the
> shape that rule describes.** Everything below is re-verified against `7bca654`.

The real range is **32 commits**. Count it at deploy time rather than trusting this number:

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && git rev-list --count 7bca654..HEAD
```

**Consequence to hold onto:** if the VM misbehaves afterwards, Build is one of ~30 suspects. The
checks below are ordered so the general health of the catch-up is established *before* the three
Build-specific probes, so a failure can be attributed.

### Every remote command here goes through the IAP tunnel — plain `ssh` does NOT reach the VM

**Corrected 2026-09-24 after `ssh metatron-vm` was actually run and returned
`Permission denied (publickey)`.** Since the 2026-07-31 VPC rebuild `metatron-net` has no public SSH
ingress — only tcp:22 from the IAP range `35.235.240.0/20` (`deploy.sh:115-118`). Every remote
command below is written out in full in this shape:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command '<the remote command>'
```

**Do not shorten it to a shell variable.** zsh does not word-split an unquoted parameter expansion,
so `$VM 'cmd'` runs the whole string as one command name and fails.

**The VM's checkout is `~/multi-model-mcp`, not `~/metatron`** (`deploy.sh:120`). Three commands
below named the wrong path and have been corrected.

**No pasteable block here carries a `#` comment,** inline or on its own line — `interactive_comments`
is unset in this shell, so `#` is an argument, not a comment. Two inline ones were removed from the
health block for that reason.

### Pre-flight, on the MacBook — all four re-verified at `75744e5`, and re-runnable

**1. Nothing untracked that committed code imports.** This is `.claude/rules/deploy.md` rule 4's
sharpest form: a tracked file already exists on the VM so a pull updates it, but an **untracked** one
does not exist there at all — so committing a tracked file that imports an untracked one deploys an
`ImportError`. On 2026-08-20 two sessions each held a half of `core/orchestrator.py` importing a
module the other had not committed.

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && git status --porcelain -uall | grep '^??'
```
Expect only `archive/handoffs/*.patch`. Any `.py` in that list is a stop.

**2. What the VM will actually pull imports — checked against a clean export, not the working tree.**
The working tree can import fine on files the VM will not receive. The only honest check:

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp \
  && D=/tmp/metatron-headcheck-$(date +%s) && mkdir -p "$D" && git archive HEAD | tar -x -C "$D" \
  && cd "$D" && METATRON_AUTH_PASSWORD=dummy-for-import-check python3 -c "
import sys; sys.path.insert(0,'.')
for m in ('core.orchestrator','core.server','core.scheduler','core.router','core.trace','core.auth',
          'core.build.driver','core.build.doors','core.build.tick','core.build.tickets',
          'core.build.manifest','core.build.gates','core.build.registry','core.build.table',
          'core.build.brief','core.build.coherence','core.build.verify','core.build.jobs',
          'core.build.schemas','core.build.index','core.build.policy','core.build.constitution',
          'core.build.ids','tools.build','tools.conversations','tools.diarist','tools.subagent'):
    __import__(m)
print('all import cleanly from a clean HEAD export')"
```

> **The dummy password is required, not a shortcut.** `core/server.py` refuses to import without
> `METATRON_AUTH_PASSWORD`, and `.env` is gitignored so a clean export never has it. Without the
> dummy this check reports a false failure every single time. **The VM's own `.env` already carries
> the var** — auth landed in `11a166d` on 2026-08-04, before `b2b1dc7` — so this is an artefact of
> the export, not a deploy gap. Checked, not assumed.

**3. Every scheduled job resolves.** `fire_function` swallows a dangling dotted path silently, every
30 minutes, which is what sweep check 12 exists for. Run it from the clean export as well:

```bash
cd "$D" && METATRON_AUTH_PASSWORD=dummy python3 scripts/check_scheduler_functions.py
```
Expect `0 finding(s) — 12 function job(s) checked`.

**4. The sweep, on the MacBook main tree.**

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && ./scripts/qa_sweep.sh
```
Expect 12/12 including `scheduler-functions-resolve`. **It parses; it does not execute** — which is
why checks 2 and 3 exist above it.

### Two rules that do NOT apply this time, checked so they are not carried as worry

- **Rule 3, `daemon-reload` before the deploy:** no `.service` or `.timer` file changed in
  `7bca654..HEAD` (re-checked against the corrected baseline). The cert-renew timer the headset chat
  added lives on the VM and is not deployed
  from this repo. **Nothing owed.**
- **`requirements.txt` is unchanged** in the range, so `pip install` is a no-op and no new dependency
  can be missing on the VM.

### A deploy-only gate this phase owes — the host marker

**`core/build/tickets.file_ticket` refuses any caller outside `TICKET_WRITERS`, and that refusal
cannot currently tell the Mac from the VM.** `DEPLOYMENT_MODE` is `cloud` on both, so nothing
in-process distinguishes them; the refusal converts a silent wrong-machine write into an explicit
one and cannot stop a caller that lies. Phase C found this and correctly stopped rather than faking
the rest (plan § 3 N14, v4.12).

**The real gate is a host marker on the two systemd units, which only a deploy can set.** Add it as a
**drop-in**, not by editing the unit text: `docs/INFRASTRUCTURE.md` § Systemd units carries both unit
files verbatim and its rebuild step says to write that text to `/etc/systemd/system/`, so an in-place
edit would be silently reverted by the next rebuild. A drop-in is one file, survives a unit rewrite,
and is removed by deleting it.

Run this **first, before `./deploy.sh`** — rule 3, because `deploy.sh` restarts both units and an
edited-but-unreloaded unit applies at the worst possible moment:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command 'sudo mkdir -p /etc/systemd/system/metatron-server.service.d /etc/systemd/system/metatron-scheduler.service.d && printf "[Service]\nEnvironment=METATRON_HOST=vm\n" | sudo tee /etc/systemd/system/metatron-server.service.d/host.conf /etc/systemd/system/metatron-scheduler.service.d/host.conf && sudo systemctl daemon-reload && systemctl show metatron-server metatron-scheduler -p Environment'
```

`sudo tee` takes both paths in one call and writes the same two lines to each. The trailing
`systemctl show` is the confirmation, and it is valid precisely because the marker is an
`Environment=` directive — `show -p Environment` does **not** report `EnvironmentFile=` contents, so a
marker put in `.env` instead would be invisible to this check and to any later audit.

> **RAN 2026-09-24. Both units now report
> `Environment=PYTHONUNBUFFERED=1 METATRON_HOST=vm`.** The marker is live. A drop-in is applied
> after the main unit, so it also wins over `.env`; nothing there sets `METATRON_HOST`, so there was
> no conflict to resolve.

> **This output also proves `docs/INFRASTRUCTURE.md` § Systemd units is STALE, and it was my source
> for the expectation above.** That doc's `[Service]` stanza carries
> `Environment=METATRON_PERSONA_STRICT=0` and `Environment=METATRON_PERSONA_FALLBACK=mike` and no
> `PYTHONUNBUFFERED`; the live units carry the reverse. **Not a blocker and not new** — those two
> variables select `core/persona.py`'s *audit mode*, and `core/persona.py:33`'s own docstring says
> *"Strict is the default. Deployments opt out explicitly, never implicitly."* The machine running
> strict is the safer state and the intended end of that transition, so the doc documents a
> migration aid that is over. **But a VM rebuilt from that doc would silently re-enable audit-mode
> fallback**, which is exactly the fail-open the variable pair exists to make deliberate. Fix it in
> the same pass as the drop-in line owed below.

**Owed after the marker is confirmed live:** one line in `docs/INFRASTRUCTURE.md` § Systemd units
recording the drop-in, or a VM rebuild from that doc drops the marker and `file_ticket`'s gate fails
closed on the VM it is meant to permit.

> **This is a unit-file change, so rule 3 DOES apply to it** — unlike the rest of this deploy, where
> nothing under `7bca654..HEAD` touches a `.service` or `.timer`. Do the `daemon-reload` first.

The matching code half — `file_ticket` also requiring `METATRON_HOST=vm` — is **not written**, and
should not be until the marker is actually on the units: config before its gate is rule 2 inverted,
and a `file_ticket` that requires a variable nothing sets refuses every legitimate VM write. **Order:
marker on the units → `daemon-reload` → deploy → confirm the variable is live in both units'
environment → then the code half, as ordinary development.**

Re-run the same check **after** the deploy — `deploy.sh` restarts both units, and the marker
surviving that restart is the thing the code half will depend on:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command 'systemctl show metatron-scheduler metatron-server -p Environment'
```

### Rule 2 — the config key and its gate, stated because it is the one live behaviour change

`build_tick` is `enabled: True` at `interval_minutes: 30` and **starts running the moment the
scheduler restarts.** Rule 2 says config never ships before the code that gates it; here they ship
together in the same commit range, which is the correct shape. What it will do: read the registry,
find no capability registered, and return — `config/build/registry.yaml` is empty until run 1 lands.
So the first live behaviour is a no-op every half hour, by construction. **Named so it is conscious
rather than discovered in a log.**

### The deploy

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && ./deploy.sh
```

Watch for the SSE drain message. A drain timeout is reported and the restart proceeds anyway.

### Post-deploy, on the VM — general health first

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command 'cd ~/multi-model-mcp && git log --oneline -1 && systemctl status metatron-server metatron-scheduler --no-pager | head -20'
```

The first line of that output must equal the Mac's `git rev-parse --short HEAD`. Then, **from the
MacBook** — this one goes over Tailscale and needs no tunnel:

```bash
curl -s https://metatron-vm.tail0acc5d.ts.net:8001/health
```

**Pass: `{"detail":"Authentication required."}`** — a 401 with the cert validating is the healthy
answer, and `-k` is deliberately absent. Run pre-deploy 2026-09-24 and it returned exactly that, so
the client path is known good going in; a change here after the deploy is attributable.

> **`curl` WITHOUT `-k` is the diagnostic.** `-k` skips exactly the cert validation that fails, so
> a `curl -k` that returns 401 says "healthy" during a total client outage. That cost a 26-hour
> chase on 2026-09-19.

Then one ordinary turn through the app, which also closes phase A's owed **(M)**:

- Open `https://metatron-vm.tail0acc5d.ts.net:8001`, persona **`mike`**, ask anything.
- **Pass:** a coherent reply carrying real context, no stack trace in
  `sudo journalctl -u metatron-server -n 50`.
- This is the `--persona mike` pipeline turn that **cannot run on the Mac in any tree**, because
  `config/personas/mike*` is VM-only. Phase A ran it as `danny_park` and that is all a worktree can do.
- **Also newly live here:** the headset chat's `source` field. Turns now record whether they started
  from the UI or a headset press; before this deploy they did not.

### Post-deploy, the three Build probes

1. **The read door answers a presence check for `mike`.**
   ```bash
   cd /Users/md-homefolder/Desktop/multi-model-mcp && python3 scripts/vm_read.py --persona mike presence log
   ```
   Expect `{state, count, window}` and **no content**. A door that answers `no_data` for everything
   looks identical to one that is working — so check `count` is non-zero for `log`, which `mike` has
   years of.
2. **`build_tick` resolves in the scheduler log.**
   ```bash
   gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
     --tunnel-through-iap --command 'sudo journalctl -u metatron-scheduler --since "40 min ago" | grep -i build_tick'
   ```
   **Three different lines match that grep, so read the prefix, not the presence of a line.**
   `core/scheduler.py:512` prints each outcome distinctly:

   - `[scheduler] [mike] build_tick: <string>` — **PASS.** The string reports nothing registered,
     because `config/build/registry.yaml` is empty until run 1 lands.
   - `[scheduler error] [mike] build_tick: <exception>` — **FAIL.** `fire_function` catches every
     exception and logs it, so a broken tick produces a line containing `build_tick` and looks like
     a hit. `ModuleNotFoundError` here is what the re-point from `core.build.runner.tick` was for.
   - `[scheduler] [mike] skipping build_tick — <reason>` — a gate held it. Should not happen:
     `respect_quiet_hours: False` is set on the job (`core/scheduler.py:750`), checked because the
     deploy is running at 22:45, inside quiet hours, which would otherwise have held it and made
     this probe fail for the wrong reason.

   **No `ModuleNotFoundError`, and no persona error either** — `build_tick()` is called with no
   arguments inside `with persona_scope(persona)`, so `persona_data_dir(None)` resolves from the
   thread-local rather than raising under strict mode. Traced, not assumed.
3. **`request_build` files a ticket from a fixture turn.** Ask the app something no specialist owns
   and that needs a standing judgement over a history — *"when did I last water the fig?"* is the
   recorded shape. Then:
   ```bash
   gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
     --tunnel-through-iap --command 'tail -3 ~/multi-model-mcp/data/personas/mike/build/tickets.jsonl'
   ```
   Expect one row at `proposed` with a non-null gap. **A plausible answer with no ticket is the
   failure** — that is the under-filing case § 13.14 names, and it is a FAIL even if the answer was
   right.

### If it goes wrong

`deploy.sh` has no rollback. The VM is a git checkout, so:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command 'cd ~/multi-model-mcp && git checkout 7bca654 && sudo systemctl restart metatron-scheduler metatron-server'
```

**The target is `7bca654`, and this is where the stale SHA would have done real damage:**
`git checkout b2b1dc7` — what this line said until it was corrected — would have taken the VM *back*
past four commits it is already running, reverting the calendar-invitation fixes, during an incident.
A rollback is the one command nobody re-derives while reading it. That returns the VM to its
pre-deploy commit. **It does not undo `pip install`** — irrelevant here,
since `requirements.txt` is unchanged. Do not `git reset --hard` on the VM; the checkout is enough
and leaves the fetched objects in place for a retry.

---

## Phase F

Pending. Bootstrap runs 1–3 as one live walkthrough with Mike executing — run 1 `home_care`, run 2
the induced REPAIR, run 3 the weekend-correspondence policy, each acceptance on Mike's data and on a
fixture persona. **Written once C has been reviewed clean**, per the coordinating brief.
