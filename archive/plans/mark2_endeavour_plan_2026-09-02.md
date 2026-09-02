# Metatron Mark 2 — endeavour plan
*Written 2026-09-02, from the Mark 2 scoping conversation with Mike. **This is a plan, not an
authorization to build.** The rulings in § 0 are Mike's, made in that conversation; everything
downstream of them is proposal. Companion to
[code_dominant_rebuild_notes.md](code_dominant_rebuild_notes.md) — the notebook holds the
architectural thinking, this file holds the endeavour: sequencing, gates, buckets, cost.*

**INTERNAL.** Names the project, its personas and its cost baseline. Not for any outside session
— the scrubbed variant convention is `archive/plans/*_external_*.md`.

---

## 0. What Mike ruled, 2026-09-02

1. **Alpha ships on Mark 2.** Mark 1 is not the ship vehicle.
2. **A7 checks 10 and 12 are skipped** — the 12-specialist behavioural audit and the constitution
   alignment matrix both fold into Mark 2. Neither is run against Mark 1's agent files.
3. **No correction-history corpus.** Most of Mark 1's errors are functions of its construction and
   of poorly-followed directions; a catalogue of them is a distraction. **What replaces it: a test
   suite designed to surface those reported errors in the new build**, so the classes cannot recur
   silently.
4. **Development rules are instated at the outset**, not discovered by failure. Discovery-by-failure
   applies only inside the project layer.
5. **Mike's persona data maintains into Mark 2, including while Mark 1 still runs.**
6. **A full review of the complete Mark 2 file suite happens before any production begins** (§ 4,
   gate G1).
7. **The development pipeline is audited as its own workstream** — § 4b, twelve items. Within it:
   the verbatim transcript stays unconditional; the log fragment becomes *one line of what + commit
   hashes* then the non-derivable half; `SESSION.md` becomes *generated state + one hand-written
   next-step paragraph*; **The Book adapts to Mark 2's fields but keeps its core principle,
   features and data**; and the backlog pipeline becomes a **cross-project standard** living in
   `~/.claude/`, not in Mark 2's repo.
8. **Added 2026-09-02, second pass:** `/metatron-code` is preserved as **`/mark2-code`**, written
   at scaffold time and meant for the post-construction editing phase; the backlog
   `SessionStart` hook **ships from day one and reports zeros on an empty log**; **model selection
   needs a home at session start** so a prompt is routed with a switch rather than from memory
   (requirement recorded, mechanism external — § 4b.6, § 4b.10); and the parallel-window question
   is **resolved, not deferred** (§ 4b.7).

**Consequence of ruling 1, carried explicitly:** A8 (the pre-Alpha refactor of
`core/orchestrator.py`) is **cancelled, not deferred**. It is currently sitting in `ROADMAP.md`
as work a future session would dutifully start. A9's analytics **instrumentation** is rebuilt in
Mark 2; its metric definition ("absorbed work, not engagement") carries over. The Goals
Interviewer overhaul is a Mark 2 build. `tests/run_a4_safety.py` is the one test asset that ports
intact — a runner plus scenarios, architecture-independent.

---

## 1. Three buckets — the spine of this plan

The single largest error in the first draft of this thinking was treating "the rules" as one
thing. They are three, with different consumers, different moments of need, and opposite
treatments.

| Bucket | What it is | Treatment | Delivery mechanism |
|---|---|---|---|
| **Development rules** | `CLAUDE.md`, `.claude/rules/`, commands, hooks, `settings.json` — how Claude Code works on the repo | **Instated day one. Designed, not discovered.** | root `CLAUDE.md` + `settings.json` + two commands |
| **Project rules** | Constitution, behavioural policy, what the runtime obeys | **Keep-list + discovery.** The quarantine file lives here | code path (runtime) + path-scoped rule (sessions) |
| **Operational knowledge** | VM, billing, Vertex, Tailscale — facts about the world | Carried verbatim; not rules at all | root `CLAUDE.md` (silent ones only) + path-scoped rule |

**The delivery principle:** match the mechanism to *when the knowledge is needed and whether its
absence is noticeable.*

- Always needed, or **silently absent** → root `CLAUDE.md` (the only tier re-injected after `/compact`).
- Needed on contact with an area → `.claude/rules/*.md`, path-scoped.
- Needed on failure → a slash command, because no context mechanism fires on "something broke".
- Needed by the running system → **code**. A rule enforced by a failing test needs no discovery.

**The criterion that sorts keep-list from quarantine, in every bucket:**

> **If the failure a rule prevents is silent, it cannot be quarantined. If the failure announces
> itself, it can.**

This is why the seven infrastructure traps, the billing hard-cap and fail-closed privacy routing
are keep-list on principle rather than by taste — and why most workflow and documentation
machinery is not: when the archive process fails, you find out immediately.

---

## 2. Mark 1 — what remains before the handover

Per the 2026-09-02 capstone close-out ruling
([capstone_cluster_review_2026-08-27.md](capstone_cluster_review_2026-08-27.md)):

1. **Session ⑤** — referent fix `[DB-0826-01]`. Fable, Red, Mike present. Prompt written.
2. **Session ⑥** — three bugs: pending-logged-as-done, `ROUTING_MISS` recording successes, the two
   inbox jobs disagreeing; derived-facts and email-surfacing diagnosis ride along. Opus. Prompt written.
3. **Session ⑦** — capstone remainder: provenance `[DB-0818-08]`, the B4 security slice, clinical-thread
   escalation. Prompt written.
4. **The (M) walkthrough session** — corpus labelling (due 09-09), wisdom store, Darwin key, location
   zones + APK ping, BigQuery export, the Restic off-machine decision. Prompt written.

**Then Mark 1 goes bugfix-only.** No new features, no refactors, no roadmap items. It keeps
running because it is a daily-use tool and because **it is what generates the trace corpus Mark 2
is tested against** — that is not sunk-cost reasoning, the traces are the asset.

**Not done, by ruling 2:** A7 checks 10, 12, check 8's wording, A5b/A5c. **Still owed before Alpha
regardless of vehicle:** the A4 deep re-run — the clinical flags are unverified on 3.7 Flash and
the last clean 6/6 was on a model no longer in the fleet.

---

## 3. Build sequence

### Phase A — Close Mark 1 (in the Mark 1 repo)
A1. Sessions ⑤ ⑥ ⑦ + the (M) walkthrough.
A2. **Incident-derived test specification** (§ 6) — written here, where the incidents are documented.
A3. **The carry-forward dossier** — the last substantive Mark 1 work.
A4. **The quarantine file** — built from the agent instruction files (§ 4).

### Phase B — Redesign, outside Claude Code
B1. **Assemble the packet** — internal, plus a scrubbed external variant. Precedent and template:
    [local_hosting_spec_packet_2026-08-29.md](local_hosting_spec_packet_2026-08-29.md), which
    worked and already carries the internal/external split.
B2. **Run the redesign.** Multi-model; Claude Code's own voice included as a named participant;
    criteria asked of Mike **before** any adjudication.
B3. **Derivation order is fixed and matters:**
    1. **Domain model** — entities, identities, state transitions.
    2. **Persistent record format** — what is written, in what form, append-only vs mutable.
       **Constrained by REQUIREMENT R1 (§ 4b.4): the trace contract The Book and
       `/metatron-troubleshoot` read.** Settled here, not bolted on afterwards.
    3. **Seams** — what code owns vs what needs judgment.
    4. **Gates** — *derived from 3, last.* They are a consequence, not a design input.

> **Mark 1's 392 measured single-call tool-turns are an INPUT to B3, never an output.** They are
> evidence that the current gate placement is wrong and a map of where judgment is exercised
> today. The taxonomy the redesign produces should be free to look nothing like it. The same
> applies to the thresholds question: Mark 2 needs a *standing discipline* — every number standing
> in for judgment gets an owner and a re-check date — not an enumeration of Mark 1's thresholds.

### Phase C — Scaffold Mark 2
C1. **New git repo** (`~/Desktop/metatron2`) — not a branch, not a `v2/` subdirectory. A fresh root
    forces every rule to be re-adopted deliberately, which is the whole point of ruling 4.
C2. Mark 1 mounted as an additional working directory, **write-denied** in Mark 2's `settings.json`.
C3. The file suite of § 4 written in full.
C4. **GATE G1 — full-suite review. Nothing is built before this passes.**

### Phase D — Build
D1. Domain model and persistent record first, with the **Mark 1 importer** written against Mark 1's
    stores as they actually are.
D2. Trace-replay harness (buildable from Phase A onward — it depends on nothing else).
D3. The incident-derived suite from A2 goes in **before** the code it constrains.
D4. Seams, then gates.

### Phase E — Cutover
E1. Mark 2 passes trace replay and the incident suite.
E2. State export → import → Mark 2 becomes sole writer; **Mark 1 goes read-only the same hour.**
E3. Mark 1's VM decommissioned on a named condition (§ 7).

---

## 4. The Mark 2 file suite, and the review gate

### Proposed layout

```
CLAUDE.md                      ~80 lines, always loaded, survives /compact
.claude/settings.json          permission tiers — machine-enforced
.claude/rules/operations.md    governs deploy.sh, scripts/**, infra/**
.claude/rules/config.md        governs config/** — Tier 0 and binding policy
.claude/commands/archive.md    three steps, not five
.claude/commands/seen-before.md  greps the quarantine index by symptom
docs/OPERATIONS.md             full VM / billing / Vertex / Tailscale reference
docs/MARK1_QUARANTINE.md       unloaded; consulted only on failure
```

**Root `CLAUDE.md` carries four things and no more:**
1. What the project is; the dev rules — tiers, archiving, backlog, reporting level.
2. **The silent traps, inline** — sole-egress external IP, the billing hard-cap outage, Vertex's
   4,096-token cache floor, Tailscale DNS after resume. Four or five lines. These cannot be
   discovery-gated.
3. **The map** — one line each for `docs/OPERATIONS.md`, the quarantine file, the mounted Mark 1
   tree. Naming what exists, not loading it.
4. The `/compact` warning: path-scoped rules are dropped and do not return until a matching file
   is read.

**Day-one development rules (ruling 4):** permission tiers with the `deny` row intact (keys,
`deploy.sh`, persona data, nothing leaves the machine); the operational knowledge doc; **archiving
cut from five steps to three** — verbatim transcript, one append-only log, and `SESSION.md`
**generated from log fragments by script** rather than hand-written; one backlog file with items
that must exit and nothing filed unasked; reporting level, terminology, file-link and numbered-list
conventions.

**Deliberately NOT day one — and this is a claim being tested, not an oversight:** the
rules-directory split, a context-gate hook, ownership freezes, read-first lists. All of those
compensate for a codebase that cannot be reasoned about statically — you could not grep who emitted
`ROUTING_MISS` because the emitter was `synthesizer.md`; you could not test the seam between a
scheduler job and a sink allowlist, so `daily_calendar_dedup_audit` ran correctly and did nothing
for eight days. A code-dominant repo removes the reason for that machinery. **In the development
bucket, a rule that has to be earned back is a diagnostic that the architecture underdelivered —
notice it loudly rather than patch it quietly.**

**The quarantine file** holds what Mark 2 is *not* adopting from the project layer — principally
the twelve specialist instruction files and the head-layer agents. Each entry: the rule verbatim
(never paraphrased — paraphrase is where rationale gets sanded off); the incident that bought it,
named by what a user saw; the mechanism it took in Mark 1; and where known, why it may not apply.
**Indexed by symptom, not by topic** — it is consulted in the ten minutes after a failure, so the
lookup key is "what just happened". Write-once and frozen at creation: Mark 2's own lessons go to
Mark 2's live rule surface, never here. If it is being appended to, Mark 1's `CLAUDE.md` has been
rebuilt in a different directory.

**Project-layer keep-list, carried verbatim:** `config/constitution.md` (Tier 0, unchanged); the
binding privacy ruling and fail-closed routing incl. the ZDR refusal; the four built-and-standing
constraints (outbound messaging, `tone_shape`, obligations-as-data, scheduler maintenance jobs).

### GATE G1 — full-suite review before any production begins

**Mike's requirement, ruling 6. No Mark 2 production code is written until this passes.** The
review reads the complete suite *as a set*, not file by file — the failure mode being guarded
against is a collection of individually-sensible files that together say something nobody chose.

Checklist:

1. **Every file in § 4's layout exists and has been read end to end**, plus the Phase B design
   outputs (domain model, record format, seam list, gate list) and the Mark 1 importer spec.
2. **No rule appears in two places.** Mark 1 carried two different "key design decisions" lists
   under near-identical headings for months; whichever you found first looked like the whole set.
3. **Every rule is on the correct tier by the silence criterion** — anything whose absence is
   silent is in root `CLAUDE.md`, not in a path-scoped rule.
4. **Every day-one rule names what it prevents.** A rule that cannot name its failure is a
   preference and belongs in the quarantine file, not the suite.
5. **Root `CLAUDE.md` is under its ceiling** and every pointer in its map resolves.
6. **The keep-list is complete** — constitution, privacy ruling, the four standing constraints,
   the silent traps — checked against Mark 1 rather than from memory.
7. **The quarantine file's symptom index is usable**: pick five real Mark 1 incidents at random and
   confirm each is findable from the symptom a user would have reported.
8. **`settings.json` deny row verified by probe, not by reading** — `ask` is honoured for `Edit`
   rules and ignored for `Bash` ones; anything that must never happen unattended is `deny`.
9. **The incident-derived suite (§ 6) exists and fails against an empty repo** — a test that has
   never been observed to fail proves nothing.
10. **The hook set is reviewed as part of the suite** — Mark 1 ran eight invocations across six
    events totalling 2,262 lines, a second rule surface as large as `.claude/rules/`. Each hook in
    Mark 2 names the failure it prevents or it does not ship.
11. **The deny-lift question is re-probed, not assumed** (§ 4b.2) — does hook-`allow` override a
    `settings.json` deny in the current harness? Mark 1's answer was no, measured 2026-08-29.
12. **Mike reviews and signs off.** Recommended model: **Fable 5** for the review pass, run by a
    session that did not write the suite.

---

## 4b. The development pipeline — audited (Mike, 2026-09-02)

*Mark 1's dev surface is larger than § 4 implied: `CLAUDE.md` (307) + `.claude/rules/` (600) +
five commands (748) + **eight hook invocations across six events totalling 2,262 lines** +
`docs/WORKFLOW.md` (377) + a 946-line backlog sync — call it **5,200 lines of machinery**. This
section audits it. Twelve items; 1–4 are Mike's, 5–12 were found in the audit and are approved.*

### 1. Archiving — cut the duplication, not just the step count

**The real triple-work is inside step 2, not in the step count.** `/archive` instructs the
session to carry the outgoing `SESSION.md` handoff paragraph into the log fragment, so one
session is narrated twice by hand — while the JSONL transcript already holds every event
verbatim and `git log` + the diff already hold what changed.

**Rule for Mark 2:** *the fragment's length goes to what git cannot hold* — the why, options
rejected with the reason, and anything believed true earlier that turned out wrong.

**Mike's decisions, 2026-09-02:**

- **Fragment format: one line of *what* + commit hashes, then the non-derivable half.** Not
  dropped entirely — cheap insurance so the log reads standalone when a commit message is thin,
  without re-narrating the diff. Target ~8–15 lines, from Mark 1's 20–40.
- **`SESSION.md`: generated state + one hand-written next-step paragraph.** The script assembles
  what is built / in progress / blocked from fragments, git and the backlog; Mike gets one
  human paragraph of intent, which no script can infer. This is what killed the 775-line drift
  in another project, and it is also the only real answer to the parallel-window collision on
  that file (§ 4b.7).
- **The verbatim transcript stays, unchanged and unconditional (Mike, restated 2026-09-02).**
  It runs **even when the session changed nothing** and even when every other step is skipped —
  it is the only step that cannot be recovered afterwards, and it is already free. No condition,
  no exception, no judgment call about whether the session was worth capturing.

**Resulting shape — three steps:** transcript (script) → decisions-only fragment (hand) →
regenerate log + primer, commit (script). Backlog close-and-file folds into the fragment rather
than standing as its own step.

**Not a duplicate, keep:** the transcript *and* the fragment (different granularity; nobody
re-reads JSONL), and `PROJECT_LOG.md` being **generated** from fragments — that is Mark 1's fix,
not its bulk.

### 2. Plan-scoped permission lift — do not rebuild Mark 1's hook

**Mark 1 built exactly this and PROVED IT DOES NOT WORK.** `scripts/hook_deny_lift.py`
(2026-08-29, 140 lines): a `PreToolUse` hook allowing Denied-tier `Write`/`Edit` on named paths
during an approved plan, expiry-scoped by a gitignored `deny_lift.json`. **Probed the same day
with Mike present: the `settings.json` deny wins — hook `allow` does not override it.** It fails
closed at every layer, including refusing to create its own lift file. It is inert, still
registered in `settings.json`, with a live open decision in
[`.claude/rules/deploy.md`](../../.claude/rules/deploy.md) about retiring it.

**Mark 2's approach, in order:**

1. **Make fewer things need lifting.** Mark 1 denies `Edit(./data/personas/**)` wholesale —
   which would block Mark 2's own importer on day one. Route all persona writes through a single
   module, make **that module** Amber, deny everything else. The tier boundary does the job the
   lift was invented for.
2. **When a lift is genuinely needed, edit the deny list — and make the restore mechanical and
   loud.** A `plan-lift` script writes the change plus an expiry marker; a `SessionStart` hook
   restores expired lifts and prints a banner while one is in force. Mark 1 rejected editing the
   deny list because a forgotten restore is *silently* invisible — **that objection dies the
   moment the restore is scripted and the in-force state is announced every session.**
3. **A `NEVER_LIFT` floor no plan touches** — constitution, keys, `deploy.sh`. Mark 1's rule
   already defines this; carry it verbatim.

**G1 addendum:** re-probe whether hook-`allow` has gained precedence in the current harness
*before* anyone assumes either way. Five minutes, not a design decision.

### 3. Backlog pipeline — a cross-project standard, and it does not live here

**Structural point: a standard is not a Mark 2 artefact.** It lives at the user level
(`~/.claude/commands/`, `~/.claude/CLAUDE.md`) with per-project data files. Putting it in Mark 2's
repo guarantees the drift already seen with `archive_chats.py`, which the global `CLAUDE.md`
carries an explicit warning about.

**Standardise (proven and portable):** one `BACKLOG.md` per project; **the two-source split** —
what Mike said vs. what the runtime noticed, which is what stopped five copies of one complaint
ranking alongside a tool denial; items must exit; nothing filed unasked; closed items to a dated
file with evidence.

**Opt-in modules, not standard:** the 946-line VM sync; `verify`; `deep` clustering sweeps;
`attack` parallel dispatch with worktrees and handoff files.

**One module should shrink structurally rather than port:** `verify` exists because items rot —
the file cannot tell you whether a bug is still real. **In a code-dominant repo with the
incident-derived suite (§ 6), a bug item is closed by a test going red→green**, not by a
re-verification sweep. Same "rule becomes mechanism" move, applied to the backlog.

**Target: roughly one third of Mark 1's surface.** Drafted **before** Mark 2's repo exists, so
Mark 2 is the standard's first consumer rather than its source.

### 4. The Book persists — as a requirement on Mark 2, not a port

[`tools/metatron_monitor.py`](../../tools/metatron_monitor.py) — 1,273 lines of Textual TUI, fed
by [`core/trace.py`](../../core/trace.py) (429) and the server's `/monitor/*` SSE endpoints;
local-only, never deployed. **Mike's ruling: the Book adapts to Mark 2's fields, but its core
principle, features and the data it provides remain.**

> **REQUIREMENT R1 — the trace contract.** Mark 2's persistent-record design (Phase B3 step 2)
> must emit a per-request trace stream carrying, at minimum, what the Book renders today:
> per-request records, correct **nested attribution** (which agent/gate actually made a call),
> timing, token and cost fields, and a live stream endpoint. **This is settled before the record
> format is designed, not after.** It is a good constraint — it forces observability into the
> architecture instead of bolting it on, and it overlaps directly with § 5's record work.

**Port the interface, refit the reader.** Do not carry 1,273 lines forward on faith against a new
schema. Instructive history: a recurring class of Book defects was **attribution loss** — a nested
`run_subagent` credited to the wrong agent, calls running untraced and never appearing at all.
Those are model-dominant-architecture bugs; an explicit call graph largely dissolves them.

### 5. Troubleshooting is the same requirement, not a second one

`/metatron-troubleshoot` (185 lines) diagnoses a single exchange by date and sequence — a second
reader over the same trace format. Scope it **with** § 4b.4 under R1 as one observability
requirement, not two ports.

### 6. `SessionStart`, `/mark2-code`, and where model selection lives

Mark 1's `SessionStart` fires **one** thing: `sync_dev_backlog.py` (the counts line). It carries
**no** model selection and does **not** load context — `/metatron-code` is a *typed command* that
re-runs the sync and then reads `SESSION.md` → roadmap → `CODEBASE_INDEX.md`, deliberately not a
hook, because context loading should not be paid for in sessions that do not need it. Mark 2 keeps
that separation, plus three rulings from Mike (2026-09-02):

- **`/mark2-code` is preserved as the Mark 2 equivalent of `/metatron-code`** — and it is
  explicitly **for the post-construction editing phase**, not only for the build. It is written
  when the file suite is (§ 4, gate G1), not retro-fitted later.
- **The backlog `SessionStart` hook persists from day one and reports zeros on an empty log.**
  The mechanism ships with the repo even though Mark 2's backlog starts empty — "`0 new · 0
  inbox · 0 now · 0 later`" is the correct output, not a reason to omit the hook. (Content is
  *not* migrated: Mark 1's 1,447 lines are re-filed only where a Mark 2 would still get it
  wrong.)
- **Model selection needs a home at session start**, so a prompt is routed to the right model
  with a switch rather than by memory. **This plan records the requirement and does not design
  the mechanism** — Mike is building a universal one separately (§ 4b.10). What is known about
  the harness today, to be re-probed at G1 rather than trusted:

  | Mechanism | What it does | Status |
  |---|---|---|
  | `model` in `settings.json` | sets the session default | works, but it is one value for all work |
  | agent-definition frontmatter | per-subagent model | works |
  | `Agent` tool `model` override | per-dispatch model | works |
  | slash-command frontmatter `model:` | per-command model — **what § 4b.10 wants** | **unverified — probe it** |
  | a `SessionStart` hook switching the model | route by prompt at session open | **believed not supported — probe it** |

  If per-command frontmatter works, § 4b.10's "model field where the work is dispatched" is a
  one-line change per command and needs nothing else. If it does not, the fallback is that each
  command *states* its model in its first line and the switch is manual — which is what Mark 1
  does in prose today, and is the thing being fixed.

Two defects found in the audit, both to fix on day one:

- The hook lives in **`.claude/settings.local.json` — machine-local, untracked, absolute path
  hardcoded.** It does not survive a clone. Move to tracked settings with `$CLAUDE_PROJECT_DIR`.
- **The eight hook invocations (2,262 lines) are a second rule surface** as large as
  `.claude/rules/`, and were missing from § 4's count. Several exist for reasons a code-dominant
  repo removes. **G1 must review the hook set as part of the suite.**

### 7. Parallel windows — worktrees are the answer, one layer up from where they run now

**Already solved for workers, not for humans.** `/fix` step 3 and `/backlog attack` create a
worktree per dispatched worker with an exclusive file manifest. What collides is **Mike's own
parallel chat windows**, which share the main tree — that is what the `git diff`-before-staging
rule, `/archive`'s dirty-file check and the ownership index all guard.

**It is not a global variable**; there is no setting that grants each window a worktree. It is a
launch-time practice, adopted as convention: **start a second window in a worktree, not at the
repo root.** Doing so retires most of the collision rules mechanically rather than writing them
down.

**The one thing a worktree does not fix is `SESSION.md`** — a single shared state file both
windows want to replace. That constraint survives any tree layout, and is a second, independent
argument for generating the primer (§ 4b.1).

**Resolution for Mark 2 — three parts, all cheap, and together they retire the collision rules
rather than restating them:**

1. **A `newwindow` script** that creates and enters a worktree, so the convention is a command
   rather than a discipline. A convention nobody can forget to follow is a mechanism.
2. **A collision-triggered warning at `SessionStart`, with an offer — not an automatic worktree.**
   Each session writes a live marker for its tree; if another is already present, the session says
   so in one line at open and offers to relocate. Mark 1 discovered its collisions at `/archive`
   time, the latest possible moment; this moves discovery to the earliest.

   - **A session's working directory is fixed at launch**, so a hook cannot spin off a worktree
     for the session it runs in. `newwindow` (part 1) is the launch-time mechanism; this is the
     safety net for when it was not used.
   - **In-session relocation is available** — the harness exposes an `EnterWorktree` tool, so a
     session that started in the shared tree can move. **Probe at G1** alongside the two
     model-selection probes (§ 4b.6); it is untested here.
   - **Collision-triggered, not every window.** A worktree per session means a *merge* per
     session, and single-window days are the common case. Paying a merge to prevent a collision
     that is not happening is a cost with no matching risk. Guard the actual condition.
   - **The marker needs an owner and an expiry or it degrades into noise.** A crashed session
     leaves a stale marker; a warning that fires forever gets ignored, which is worse than no
     warning because it trains you past the real one. The `Stop` hook removes the marker;
     `SessionStart` clears markers past a threshold as stale.
3. **The generated primer (§ 4b.1)** removes the last hand-written shared file, which is what
   made a collision *destructive* rather than merely annoying.

**What this deletes from the day-one rule surface:** the ownership-index pattern, `/archive`'s
dirty-file preamble, and most of the `git diff`-before-staging prose. **`git diff` before staging
survives as a rule regardless** — it also guards against staging a file whose other lines you
never read, which has nothing to do with parallel windows.

### 8. `/fix` is the atomic unit and belongs in the standard

One change, one reviewed diff (155 lines in Mark 1). Cross-project, same home as § 4b.3 —
`~/.claude/commands/`, not Mark 2's repo.

### 9. Docs-as-tests — carry the pattern

`scripts/check_claude_md_claims.py` verifies every backticked path in the docs exists;
`check_agent_tools.py` does the same for tool grants. This is "rule becomes mechanism" applied to
documentation, it is cheap, and it caught real drift. Into the cross-project standard.

### 10. Model selection per command — external input, placeholder here

Model choice currently lives as **prose in `SESSION.md`** ("plan and review in Fable, build in
Opus"), where it can drift from the decision that set it. **Mike is building a universal model
mechanism in a separate chat and it will exist before this is built out.** What this plan needs
from it: **a per-command model field** (command frontmatter, or whatever that mechanism defines),
so the choice is declared where the work is dispatched. **Do not design a second mechanism here.**

### 11. One home for the standard, and the anti-drift rule

`~/.claude/commands/` and `~/.claude/CLAUDE.md` are the single home; projects **reference, never
copy**. State it as a rule *with its incident* — the duplicated `archive_chats.py`, which the
global `CLAUDE.md` already warns about — because copying is what everyone does by default.

### 12. A dev-side cost meter

The budget in § 7 covers this endeavour and names the double-VM run cost, but **nothing measures
what development itself costs per week.** By the standing rule that a cost no meter reports will
be read as safety, this is the one currently-unmeasured class. Low priority; named so it is not
mistaken for zero. `hook_session_tokens.py` is the existing per-session half to build on.

---

## 5. Persona data — findings and cutover

**Finding, measured 2026-09-02: the data is not in the shape the migration wants, and the
authoritative copy is not on the Mac.**

- **The Mac copy is a local-dev remnant** — four trace files (one empty, one from June), one
  journal day from 2026-06-26, three log files, a nine-entry FAISS index. The live data is on the
  VM. Replication from the VM is Mark 2's first infrastructure piece.
- **`data/personas/**` is `deny`-listed for `Edit` only. `Read` is allowed** — no permission lift
  is needed to read it.
- **Thirteen append-only streams exist** (`core/trace.py`, `tools/logger.py`, `context_tracker`,
  accountability, calendar_audit, calendar_reconcile, crm_sweep, intake, location, travel_watch,
  rule_audit, the persona audit, server) — but they are thirteen logs with thirteen schemas and no
  common envelope. **There is no single event log.**
- **The trace stream is a conversation log, not a domain event log.** A record is
  `trace_id / ts / user_input / synth_response / pipeline / grounded` — it says a turn happened,
  not that an obligation was created or a contact merged. CRM state cannot be rebuilt from it.
- **~25 modules persist authoritative mutable state via whole-file `json.dump`**; the substantive
  eight are `crm.py` (20 write sites), `intake`, `accountability`, `context_tracker`, `confirm`,
  `wishes`, `baselines`, `wisdom`. `context.json` is the pattern in miniature — `open_threads`,
  `patterns`, `follow_ups`, `held_items`, current state with no history behind it.
- **One thing already holds the target shape:** the FAISS index is genuinely derived —
  `memory/metadata.json` carries text, source and date per vector, so the index rebuilds from it.

**Decision: accept a point-in-time state export at cutover; Mark 2 is event-sourced from day one.**
The rejected alternative was retrofitting event emission into Mark 1 now — it breaks the
bugfix-only freeze, touches exactly the modules holding live data, and buys replayable history
only from today forward. An event log's value is forward: it makes *Mark 2's* derived state
rebuildable.

**Phasing — there is never a dual-write window**, now because no format could support one:

1. Mark 1 sole writer and sole authority; Mark 2 reads a replica of the VM tree.
2. Mark 2 replays traces and diffs against Mark 1. This is the only use of real data during the build.
3. Cutover: export → import → Mark 2 sole writer, Mark 1 read-only the same hour.

---

## 6. Tests instead of a corpus (ruling 3)

The deliverable is a suite that **fails on Mark 2 if a Mark 1 error class recurs**, written from
the incidents already documented in `archive/PROJECT_LOG.md` and the backlog — not a catalogue of
bad turns. Seed set, each traceable to a named incident:

1. **Entity resolution produces duplicate people** — Jon / Jonathan / Jonathan Whitfield as three
   contacts via `_find_by_name` substring matching; the Jonas quadruplication; the Eva/Iba
   correction cluster (×4).
2. **A merge cannot be undone, or lands on the wrong one of three same-named people** — `[DB-0826-01]`.
3. **A derived fact is stated inconsistently across runs** — the exercise hiatus described three
   different wrong ways across 08-30 → 09-02, `[DB-0822-06]`.
4. **A flag reaches the user verbatim** — the clinical-flag pipeline inversion: substance present,
   raw token absent.
5. **The agent's own deliberation is emitted as the answer** — the 2026-08-12 check-5 failure.
6. **An event emitter is invisible to static analysis** — assert the call graph is greppable;
   `ROUTING_MISS` was declared dead on a code grep while an instruction file still emitted it.
7. **A scheduled job runs correctly and its output is discarded** — the eight-day
   `daily_calendar_dedup_audit` seam failure.
8. **Work is reported done that never happened** — pending-logged-as-done, `[DB-0829-01]`.

Each must be **observed failing before the code that satisfies it exists** (G1 item 9).

---

## 7. Cost budget

**Build (this endeavour, excluding Mark 2's own construction):**

| Item | Model | Estimate |
|---|---|---|
| Incident-derived test specification | Fable 5 | $5–8 |
| Carry-forward dossier | Fable 5 | $8–15 |
| Quarantine file (extraction + symptom index) | Sonnet 5 build, Fable review | $4–6 |
| Redesign packet, internal + scrubbed external | Opus 5 | $3–5 |
| Mark 2 scaffold (§ 4 suite) | Opus 5 | $5–10 |
| Cross-project dev standard (§ 4b.3, 8, 9, 11) — lives in `~/.claude/` | Fable 5 | $6–10 |
| The Book / troubleshoot refit against the new schema (§ 4b.4–5) | Opus 5 | $8–12 |
| **G1 full-suite review** | **Fable 5**, session that did not write the suite | $5–8 |
| Outside redesign | multi-model, priced in that medium | — |

**Run:** Mark 1 stays deployed throughout, so **~$63/mo is paid twice over** from the moment
Mark 2 has a VM. This is the standing cost the plan creates, billed by wall-clock time, and no
per-request meter will report it.

**What deletes it:** the Mark 1 decommission condition. Proposed shape — *Mark 2 handles a full
week of real days with no fallback to Mark 1* → Mark 1's VM stops the following day. **Mike is
handling this manually (2026-09-02); it is not tracked as an owed item here.** Recorded so the
standing cost is not mistaken for zero.

**Ancillary:** replication of the VM persona tree (small — the live tree is well under 1 GB);
trace retention must not be pruned during the transition (131 MB total today; keep all of it).

**Unseen:** two live systems means two sets of scheduled jobs firing against the same calendars,
inboxes and CRM sources. **Mark 2's scheduler must be inert until cutover** — a maintenance job
that writes is a second writer regardless of what the storage design says.

**Model recommendation for execution overall:** plan and review in **Fable 5**, build in **Opus 5**
(Mike's standing split, 2026-08-18). Red-tier work is not delegated to a subagent.

---

## 8. Open and owed

1. **Prompts not yet written:** the outside-redesign packet cover prompt, and the G1 review prompt.
   Each carries its model on its first line when written.
2. **Handled by Mike manually, deliberately not tracked here (2026-09-02):** the Mark 1
   decommission condition, and recording the A8 cancellation in `ROADMAP.md`. `ROADMAP.md` is
   left untouched by this plan and still reads as though A8 is live work — that is known, not an
   oversight.
4. **The cross-project development standard (§ 4b.3) is a separate deliverable** with its own
   home (`~/.claude/`) and its own timing — drafted **before** Mark 2's repo exists, so Mark 2 is
   its first consumer rather than its source. It is not gated on this plan.
5. **Mark 1 owes a decision on `scripts/hook_deny_lift.py`** — retire it or leave it dormant. It
   is registered in `settings.json` and inert; the open decision is recorded in
   `.claude/rules/deploy.md` and predates this plan.
6. **The universal model mechanism (§ 4b.10) is external to this plan** and is expected to exist
   before build-out. This plan consumes it; it does not design it.
7. **This file's retirement condition:** when Mark 2's repo is created and G1 passes, this plan
   folds into Mark 2's own planning surface and closes.
