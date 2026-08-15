# Development Workflow — which command, when

Five sections. Read it once end to end; after that come back to whichever section matches the
question you actually have. Each is about a page, deliberately — squeezing all of it onto one
page would make it too dense to use, which is the opposite of the point.

| § | If you're asking | Page |
|---|---|---|
| 1 | "What do these commands do again?" | [Command glossary](#1--command-glossary) |
| 2 | "Which one do I fire for this?" | ["I want to…"](#2--i-want-to) |
| 3 | "What does a normal day look like?" | [How a day works](#3--how-a-day-works) |
| 4 | "Why am I being asked to approve this?" | [What needs your approval](#4--what-needs-your-approval-and-why) |
| 5 | "What's actually running right now?" | [Working in parallel](#5--working-in-parallel) |

**The bias, stated once because everything below follows from it:** Metatron is being built as
fast as possible. Mike's bugs and requests outrank machine-generated findings, which outrank
things a development session noticed in passing. Process work that doesn't change what the user
experiences is not work.

---

## 1 — Command glossary

Five slash commands, three of them with modes. Everything else in here is a script you run
directly, a guard that runs itself, or — since 2026-08-14 — a rule file that delivers itself.

### The commands

**`/metatron-code`** — the loader, fired at the start of every session. It syncs the backlog
from the VM (writes to disk, costs no context), then reads `SESSION.md` and `ROADMAP.md`, and
`CODEBASE_INDEX.md` only if the work ahead needs it. Prints one count line and nothing else.
~15k tokens.
*The rule: it never opens `DEV_BACKLOG.md`. The count is the signal — you decide when a pass is
worth paying for.*

**`/metatron-troubleshoot DATE SEQ "what went wrong"`** — one exchange, diagnosed. Pulls the
conversation record, the server logs and the pipeline trace in a single trip to the VM, and
reports what failed and what it meant for you. Cheap.
*The rule: fix it here if you can, and file nothing — a fix that exists is nothing to remember.*

**`/fix <description | DB-id | a troubleshoot finding>`** — make one change, get back one
reviewed diff. Fire it whenever you'd otherwise say *"can you fix X."* No ceremony, no minimum
size. Five steps: classify the change against the approval tiers, check the premise is still
true against today's code, dispatch (a worker for routine work, me for anything sensitive),
review what comes back, then one diff for you to approve once.
*The rules: one task per `/fix`, there is no `/fix-all`, and `/fix` never deploys.*

**`/backlog`** — reads `DEV_BACKLOG.md` in full (~4k tokens), sorts the Inbox into `Now` and
`Later` with you setting the priorities, and checks anything about to be worked against the real
code first. Three extra modes:
- **`/backlog verify`** — re-checks items against today's code, farmed out to up to three
  workers at once, and hands back a single table: fixed / still real / moved / needs your call.
  You read verdicts, not investigations. This is the one that stops the list rotting — a third
  of what was checked in a 2026-08-05 sweep turned out to be describing a world that no longer
  existed.
- **`/backlog deep`** — the above plus merging duplicate items, re-checking all of `Now`,
  sweeping the machine log, and rolling closed items into the monthly archive. Run when the
  counts creep. Occasional, never scheduled.
- **`/backlog attack`** — scores the `Now` list, clusters the top items into up to three groups
  that touch no files in common, shows you the plan, and then starts the workers once you
  approve. You choose what runs; you don't have to ferry the instructions yourself.

*The rule that matters most: no item is acted on, or re-filed, on the strength of its own
description. A 2026-08-05 sweep found about a third of checked items stale — and a stale
description argues for the wrong fix, persuasively.*

**`/archive`** — close a session. Five steps: verbatim transcript, one entry appended to the
project log, `SESSION.md` refreshed, backlog closed-then-filed, and a commit of exactly those
files. Minutes, not a work block.
*The rules: close items before you file new ones; file only what a user would notice or what
blocks the roadmap; the commit stages a named list and pushes for offsite backup — it never
deploys.*

### The scripts — no slash command, run them directly

| Script | What it does | Cost |
|---|---|---|
| `./scripts/qa_sweep.sh` | Nine checks in ~3 seconds: agent tool references, persona consistency, duplicate rules, the project log rebuild, a Python syntax sweep, duplicate backlog IDs, stray debug markers, `CLAUDE.md`/rule-file claims that name a real path, and the deploy-lock invariant | **zero tokens — run it freely** |
| `./scripts/new_worktree.sh <slug>` | Makes a separate, isolated copy of the project for parallel work. `--with-personas` if it needs to run the safety or security suites | free |
| `./scripts/rm_worktree.sh <slug>` | Removes one when its work has landed | free |
| `python3 scripts/sync_dev_backlog.py` | Pulls runtime signals off the VM into the backlog. `/metatron-code` and `/archive` both run it for you | free |
| `python3 ~/.claude/tools/archive_chats.py` | Verbatim transcript capture. Run it mid-session too, not only at close | free |

> **A green sweep is not a test.** `qa_sweep.sh` reads code without running it. It passed the
> error that crash-looped the scheduler after a deploy, and a second one in the commit guard.
> Whatever changed, run the thing that changed.

*There is no `/qa` slash command — the sweep is the script above, and `/fix` calls it for you.*

### The thing that isn't a command at all — area rules

Since 2026-08-14 most of the project's rules are **not loaded at the start of a session**. They sit
in five files under `.claude/rules/`, each declaring which part of the project it governs, and
Claude Code delivers the matching one automatically **the moment a file in that area is read** —
during exploration, not at the edit. You never fire anything; there is no command for it.

| Rule file | Delivered on reading |
|---|---|
| `agent-files.md` | agent instruction files, routing config |
| `personas.md` | persona config, `core/persona.py` |
| `orchestrator.md` | `core/`, `tools/` |
| `deploy.md` | `scripts/`, `deploy.sh`, `.claude/settings.json` |
| `docs-and-logs.md` | `SESSION.md`, `DEV_BACKLOG.md`, `archive/`, `docs/`, the command files |

**Why this is in a doc about commands:** it changes what a session already knows before you ask for
anything, and it has one measured limit worth knowing. **Delivery fires on `Read` and only on
`Read`** — a `grep` survey does not trigger it, and neither does writing a file blind. So a session
that never opens a file in an area gets the *pointer* to the rule (from `CLAUDE.md`'s rules index,
and again from the write-time briefing) rather than the rule itself. In practice that means
high-level or survey-shaped work may need one deliberate read that low-level work gets for free.

---

## 2 — "I want to…"

| …start any session | `/metatron-code` |
| :--- | :--- |
| …change something, fix a bug, make an edit | `/fix <what you want>` |
| …work out why Metatron replied badly | `/metatron-troubleshoot DATE SEQ "what went wrong"` |
| …know what's outstanding, or pick something up | `/backlog` |
| …find out whether the list is still true | `/backlog verify` |
| …tidy a list that's drifting | `/backlog deep` |
| …use a day of parallel capacity | `/backlog attack` |
| …check nothing is obviously broken | `./scripts/qa_sweep.sh` |
| …work on two things at once without them colliding | `./scripts/new_worktree.sh <slug>` |
| …close a session | `/archive` |

Nothing else is a ritual. Ordinary coding is `/metatron-code`, do the work, `/archive`.

**When two of these look like they fit,** the order is: troubleshoot answers *what went wrong*,
`/fix` answers *make this change*, and they chain — a troubleshoot that finds the cause hands
its finding to `/fix`. `/backlog` is for *what should I do next*, which is a different question
from either.

---

## 3 — How a day works

Four shapes. Most days are the first one.

### An ordinary session

`/metatron-code` prints `0 new · 2 inbox · 9 now · 24 later`. Two Inbox entries is not worth a
pass — the count exists so you can decide that without reading the file. Build the thing you
asked for in conversation. Two small nits turn up along the way and are fixed on the spot rather
than written down. `/archive` at the close: transcript, one log entry, the handoff paragraph
rewritten, the backlog item closed against its commit. Five minutes.

### Triage, then work

The Inbox is at five. `/backlog` reads the file, traces the two user-reported entries back to
the conversations they came from — the request text says *what* was asked and never *what you
were trying to do*, and that gap has inverted a decision at least once — then proposes a
priority for all five in one table. You say "1 and 3 to Now, kill 4, rest Later." They get
rewritten into place, the top `Now` item is checked against current code, and the work starts.

### Something misbehaved

The morning check-in listed four pending items again.
`/metatron-troubleshoot 2026-08-13 007 "check-in ignored the brevity rule"` pulls the trace and
shows the preference never reached the Synthesizer's prompt at all. One-file fix, deployed,
backlog item closed. **Nothing filed** — the fix exists.

### Close-out

`/archive`, every session, without exception — but **not always all five steps.** A session that
changed no tracked file and made no commit stops after the transcript: there is nothing true to
write in a log fragment, and `SESSION.md` is still correct. The transcript is never the part
skipped, because it is the only one that cannot be recovered later.

The one rule worth carrying in your head:

> **The project log is appended to. `SESSION.md` is replaced.**

History goes in the log, current state stays in `SESSION.md`, work goes in `DEV_BACKLOG.md`. A
session that closes by adding a new dated section to `SESSION.md` has put it in the wrong file —
that is exactly how it once reached 775 lines, most of it history, loaded on every session start.

### What each file is for

| File | Holds | Written | Read |
|---|---|---|---|
| `SESSION.md` | current state, nothing dated | **replaced** | every session |
| `ROADMAP.md` | live phase gates and tracked items | edited inline | every session |
| `DEV_BACKLOG.md` | Metatron work outside the roadmap, in priority order | curated | `/backlog` only |
| `archive/PROJECT_LOG.md` | dated history, reasoning, rejected options, corrections | **generated from `archive/log/` fragments — never hand-edited** | on demand |
| `archive/backlog_closed_*.md` | closed items with their evidence | appended, monthly | on demand |
| `archive/transcripts/` | verbatim chat | by script | never |

---

## 4 — What needs your approval, and why

You get asked to approve two different kinds of thing, and they feel similar in the moment but
are not.

### Kind one — the change tiers

Some files are riskier to change than others, so who is allowed to change them differs.
`.claude/settings.json` is the authority; this is the plain-language version.

| Tier | Roughly | What happens |
|---|---|---|
| **Green** | tests, scripts, docs, comments, logging | done without asking you |
| **Amber** | most tool and core code, the app front-end, non-routing config | done without asking you |
| **Red** | agent instruction files, routing config, the router/persona/scheduler/spend-guard code, `./deploy.sh`, `git push` | **you are asked, every time** |
| **Denied** | the constitution, your persona files, your data, credentials | blocked outright until you lift it explicitly |

**Why Red is drawn where it is:** those files are where a wrong change is *quiet*. A broken
script fails immediately and loudly. A wrong line in an agent file changes how Metatron talks to
you for weeks without anything erroring. Red is also the line for *who builds it* — Red-tier work
is never handed to a worker, because there the judgement is the work, and a contractor without
the project's history decides wrong, confidently.

**Why deploy is different from everything else.** Every other action here is reversible: a bad
edit is one `git` command away from being undone. Deploying puts code on the live VM that is
running your actual life data, and pushing publishes to GitHub, which is irreversible in the way
that matters — `git add -A` once swept 41 files of journals and clinical logs offsite. That is
why `/fix` never deploys and `/archive` never deploys: deciding *when* is a judgement no command
should make on its own. It is always a separate, deliberate decision, made by you.

### Kind two — the guards interrupting

Four automatic checks run in the background. Two of them can stop something.

| Guard | Fires when | What it does |
|---|---|---|
| **File briefing** | any file is about to be written or edited | **warns, never blocks** — hands over that file's history before the change lands |
| Agent-tool check | an agent file or routing config is edited | reports tools named but not built, or granted but never mentioned |
| Ceiling check | `CLAUDE.md` or a `.claude/rules/` file is edited | reports the new line count against its ceiling, and asks where the rule belongs |
| Commit guard | a file is staged or committed | blocks if a file changed underneath this session since it was read |
| QA gate | a worker finishes | runs the sweep before the worker is allowed to report back |

**The file briefing is new as of 2026-08-14 and replaced a one-line nag.** It used to say the same
sentence for every file — *"you didn't do your reading."* It now answers *what do we already know
about this exact file*: its permission tier, which rule file governs it, any open backlog items
naming it, its last five commits, and excerpts from the decision history in `archive/log/` anchored
on the session that wrote each one. Once per file, so a session editing five files gets five
briefings. New files in a governed area get a briefing too — no history, but the governing rule
named, which is where the rules matter most. The old `SESSION.md`/`ROADMAP.md` warning survives
inside it.

It warns rather than blocks on purpose: refusing an edit to enforce a reading habit would throw
away work you asked for, which is the worse failure. **It also now covers worktrees** — it silently
did not until 2026-08-14, which meant `/backlog attack` workers, the thinnest-context sessions by
construction, got no gate at all.

**The commit guard is the one you'll notice.** It fails closed — when it cannot make sense of a
command, it stops. That is correct by design, but every instance so far has been a routine case
rather than a risky one, including any file written by a script rather than edited directly.
The override is `METATRON_COMMIT_GUARD=off` in front of the command. Two things about *when* it
fires, both observed 2026-08-14: it fires at **stage time**, so `git add` trips it and not only
`git commit`; and it blocks the **first** writer of a contested file, not the second — the later
session re-read the file after both sets of lines had landed, so it stages clean while the earlier
one is stopped. *(Worth knowing: the override was itself broken until 2026-08-13 — it blocked,
printed the remedy, and blocked the remedy.)*

> **Both fixed 2026-08-13 — noted because the earlier text here said they were open.** The
> permission mode meant to cut routine prompts had never actually been in effect (`defaultMode:
> auto` parsed and did nothing); it is now a blanket `allow` list, which is the same policy in a
> form the matcher honours. The *Denied* tier's `Write` hole is closed too — `Edit(path)` rules
> cover every file-editing tool, so the paired `Write(path)` entries were deleted rather than
> kept, since a rule that does not match is indistinguishable from one that does.
>
> **Still true, and it is the live one to know:** `ask` rules gate `Edit` here but **not `Bash`** —
> the VS Code panel never renders a Bash prompt, so those resolve to allow. `./deploy.sh` is
> therefore in the *Denied* tier, and `git push` is knowingly ungated in this harness (it gates in
> the iTerm REPL). Full reasoning: `CLAUDE.md` § Change tiers.

---

## 5 — Working in parallel

### What a worktree is, in non-technical terms

A worktree is a **second complete copy of the project on disk**, with its own copy of every file,
that shares the same history. Two windows working in the same folder collide at the level of
individual lines: on 2026-08-09 a commit that carefully staged only its own filenames still swept
up another session's unfinished routing change, and the deploy put it live while the
instructions governing it sat uncommitted. Separate folders make that class of collision
structurally impossible rather than merely discouraged.

```bash
./scripts/new_worktree.sh app-client        # creates ../metatron-wt-app-client
./scripts/rm_worktree.sh app-client         # removes it when the work has landed
```

Claude Code also has its own built-in way of making one, which does not use these scripts. Either
is fine and they produce the same thing structurally; the scripts are the one to reach for when the
work needs test fixtures, because `--with-personas` is theirs alone. **Rules and briefings both
reach worktree sessions** — confirmed 2026-08-14, and neither did before that day.

Add `--with-personas` if the work runs the safety or security test suites. Without it the test
fixtures in the new copy are **hollow rather than absent** — the folders exist but most of the
files don't, so a suite runs to completion against incomplete data instead of failing loudly.
Your own persona data is deliberately never copied: the VM owns it, and a stale copy on the Mac
is the thing that gets pushed by mistake.

### What spawns workers

- **`/fix`** dispatches one worker for Green and Amber work, into a worktree, given as an
  absolute path. Red-tier work is never delegated.
- **`/backlog attack`** starts up to three after you approve the plan, each with a list of files
  no other worker touches. A group that can't be given its own exclusive file list **is not
  parallelised** — it runs one after another in this window instead.
- **`/backlog verify`** starts up to three as well, but they only read — no worktrees, no edits,
  no commits. They come back with verdicts and this window makes every change.

Cap: **three workers**. A cold worker costs about 32,000 tokens before it does anything at all,
because it has to read itself into the project from nothing. That flat cost is why small work is
faster done here than delegated.

### What the coordinator window still owns alone

Whichever window you're driving is the coordinator. The workers write code; this window owns
everything shared:

- `SESSION.md`, `ROADMAP.md`, `DEV_BACKLOG.md`, the project log, and the command files
- `/archive` — run **once**, folding every worker's handoff into one log entry and one
  `SESSION.md` refresh
- **the deploy — once, after consolidation, by you**

Workers instead write a short handoff file (`archive/handoffs/YYYY-MM-DD-<slug>.md`): what
shipped, the commits, which backlog items to close and with what evidence. `/archive` step 0
looks for those before it does anything, so a worker running it by mistake is caught.

> **One deploy, one window — and as of 2026-08-13 that is a mechanism, not just a convention.**
> The lock used to compute a different path inside each worktree, so both trees could deploy and
> both would push. It now derives from `git rev-parse --git-common-dir`, the one directory every
> worktree agrees on. **Verified by running, not reading:** main tree, worktree-invoked-from-main,
> worktree-invoked-from-itself and a non-git cwd all resolve to the same lock; then the main tree
> held it while a real worktree's copy ran — *DEPLOY REFUSED, exit 1, naming the holding PID*.
> `scripts/check_deploy_lock.sh` in the QA sweep asserts this every run, so a later simplification
> back to a worktree-local path trips a check rather than reaching production.

### Three failure modes, and what stops each

**The list grows faster than it shrinks.** Cause: every session filed everything it noticed —
`DEV_BACKLOG.md` went 197 → 1,658 lines in six days while three separate sweeps ran. Stopped by
`/archive` step 4: close before you file, and the bar for filing is *a user would notice, or the
roadmap is blocked.*

**Machine noise crowds out you.** Cause: tool denials and rule conflicts landed in the same Inbox
as your requests, five copies of one complaint reading as five items. Stopped by routing: runtime
signals go to `## Machine log`, repeats collapse to `×N`, and a signature reaching ×3 escalates
itself into the count line.

**Parallel windows collide.** Cause: disjoint code, shared close-out — every window ran
`/archive` and edited the same three files. Stopped by the coordinator/worker split above, and by
`/archive` step 5 stopping the commit outright if a staged file carries lines this session did
not write.

---

## Standing conventions

- **Command files carry procedure, not history.** When an incident teaches something, the lesson
  goes to the project log and the command gets at most a line. `/archive` reached 196 lines that
  way, most of it scar tissue nobody needed at close-out time.
- **A new lesson no longer defaults to `CLAUDE.md`.** The question is now *what is the smallest set
  of files this governs?* — a single file's past goes to an `archive/log/` fragment and surfaces in
  that file's briefing; one area goes to its `.claude/rules/` file; a repeatable procedure goes to a
  command; and only something dangerous everywhere earns a line in `CLAUDE.md` against its ceiling.
  Nothing was deleted when this split happened on 2026-08-14 — it moved, with its reasoning intact,
  and now arrives later instead of always.
- **No new standing script or hook without naming what it retires**, or the build that will retire
  it. Roughly a third of the scripts here manage the process rather than the product, which is why
  this rule exists.
- **Closed without evidence is not closed** — a commit, a `file:line`, or a named test.
- **Never reserve a backlog ID.** Search for the next free `DB-MMDD-NN` at the moment of writing;
  two windows have minted the same one more than once.
- **Report counts as a before/after difference**, not a bare number. With two windows open, a
  single count is a snapshot of an unknown moment — a real 53 → 48 once read as a regression.
- **Check `git show --stat` after committing**, not just that the command succeeded.
- **New backlog items go to `.claude/backlog_inbox/<slug>.md`**, not straight into the file.
- **`archive/PROJECT_LOG.md` is generated** from the fragments in `archive/log/` — never edit it
  by hand.
