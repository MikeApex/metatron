---
description: Run a Build job — the driver names every step and /build spawns it. List what is filed, run a job, run a repair, or review the landed set.
---

Metatron — Build a capability

```
/build [--persona mike]                     list open tickets (fetched) and jobs in flight
/build [--persona mike] BLD-MMDD-NN         run the graph from wherever the artifacts say it is
/build [--persona mike] repair BLD-MMDD-NN  the same, REPAIR mode, dossier first
/build coherence                            the periodic set review
```

`--persona` defaults to `mike`. **Ticket ids are allocated per persona ledger**, so
two personas can mint the same `BLD-MMDD-NN` on one day — the job directory, the
board and the registry row all carry the persona, and a fixture persona's ticket is
never built unless that persona is named.

> **This command is not the runner. `core/build/driver.py` is.** Ask it for the next
> step, run what it names, hand the result back, ask again.
>
> **Every bound below is enforced in code, not by you following this file.** The node
> order, the one retry, the review's send-back, the park states and the channel gates
> are all re-derived from `attempts.jsonl` and the artifacts on disk. What follows
> narrates what the driver does; it is never the thing that makes it happen. If you
> find yourself about to hold a rule in your head — *don't re-spawn*, *delete this
> first*, *stop after two* — that is a defect in the code, not a step for you.

**Nothing here commits, pushes or deploys.** Ever.

---

## `/build` — the board

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp && python3 scripts/build_board.py --persona mike
```

Tickets fetched read-only from the VM, the local jobs with what each is waiting for,
and the run cost. Report it and stop. **`N decided, awaiting deploy` is not a
backlog** — those are answered, and stay open until the deploy carrying their row.

## 0. Open the job

```python
JOB, PERSONA = "BLD-MMDD-NN", "mike"
if not J.read_artifact(JOB, "ticket", PERSONA):      # fetched once, then kept
    from scripts.build_board import fetch_tickets, DEFAULT_SERVER
    rows, note = fetch_tickets(DEFAULT_SERVER, PERSONA)
    row = next((r for r in rows if r.get("job_id") == JOB), None)
    if row is None: sys.exit(f"no ticket {JOB} for {PERSONA} — {note or 'not filed'}")
    J.ensure(JOB, PERSONA); J.write_artifact(JOB, "ticket", row, PERSONA)
```

Print the ticket and say what the gap is. Run `/build` from the main tree:
`landing_preconditions` refuses a landing whose job store is a different checkout of
this repo, so a worktree session fails at N13 rather than splitting the job.

## 1. Ask the driver, do what it names, ask again

```bash
python3 -c "import sys;sys.path.insert(0,'.');from core.build import driver as D;print(D.next_step('BLD-MMDD-NN','mike','construct'))"
```

`mode` is `repair` for `/build repair`. `kind` decides who acts: `agent` → spawn it,
`code` → run it here, `gate`/`parked`/`done` → **stop and report `detail`**.

**Six subagent types, not five.** The five `build-*` definitions are Build's own; the
sixth is `adversarial-reviewer` at N8, which Build shares with `/adversarial-review`
and does not own — so it is the one whose output contract crosses layers, and the
only one whose reply needs parsing.

| Node | It is | Hand it | Payload for `D.land` |
|---|---|---|---|
| `N1r` | code, REPAIR only | — | the origin job's question set and ledger, by the id the registry names, plus the correction traces |
| `N2` | `build-inquiry` | the gap, the trigger, the mode, and in REPAIR the dossier — **nothing else** | the reply; `known_capabilities=M.capability_names()` |
| `N4` | `build-librarian` | the question set, `json.dumps(M.build(PERSONA))`, the absolute repo path | the reply; `question_ids=[…]` |
| `N5` | code | — | `{"interview_items": S.open_interview_items(ledger)}` |
| `[N6]` | gate | — | the interview, in chat — below |
| `N7` | `build-planner` | the question set, the **full** ledger, the registry, the repo path; on a send-back also the rejected plan and `step.defects`, via `D.retry_prompt` | the reply; `red_paths=…`, `question_ids=…` |
| `N10` | code | — | the brief — below |
| `N8` | `adversarial-reviewer` | **three lines only** — below | the report as a dict |
| `[N9]` | gate | — | Mike approves → `J.write_artifact(JOB,"approval",…)` |
| `N11` | `build-implementer` | the plan, and the sandbox worktree's **absolute** path | the gate — below |
| `N12` | code | — | `{"refusals": [], "notes": notes, "checks": "ok"}` |
| `[N13]` | gate | — | one sitting — below |
| `N14` | code | — | the acceptance result — **a later session**, below |

**`M`, `B`, `V`, `G`, `D`, `J`, `R`, `S`, `C` are `core.build.{manifest,brief,verify,gates,driver,jobs,registry,schemas,coherence}`.**

## 2. The bookkeeping — two calls, every node

```python
step = D.next_step(JOB, PERSONA, MODE)
D.begin(JOB, step, PERSONA)                       # records only a subagent node
artifact, defects = D.land(JOB, step, payload, PERSONA, upstream=UPSTREAM, **checks)
```

`begin` decides for itself which nodes cost an attempt row, so the product cap cannot
be spent on code nodes and gates. `land` knows each node's landing rule — the three
model artifacts through their validators, the plan through `write_plan`, the brief
and the patch as text — and records the defect list on a failure, so the retry the
driver hands back is already carrying it. **A non-empty `defects` means stop and ask
the driver again; it will name the retry or the park.**

`UPSTREAM` is the artifact this one derives from: the ticket for N2, the question set
for N4, the ledger for N7. At N7 also re-validate the ledger against the plan —
`S.revalidate_ledger(ledger, plan, question_ids)` — which is what makes
`if_user_lacks_it` mandatory on exactly the rows the plan declares as required.

`red_paths` is the subset of the plan's own paths matching a Red or Denied `Edit()`
rule in `.claude/settings.json`; resolve it from that file, never from a list here.

## 3. The nodes that need more than a table row

### `[N6]` the interview happens here, in chat

Put each open item to Mike **in this session**, in his words, then:

```python
ledger = S.record_interview_answer(ledger, question_id, his_answer)
```

That writes the answer where the Planner and the question table both read it, with a
truthful `user`/`interview` inventory — nothing about the shape is yours to decide.
Write the ledger back, set `answered: true` on `ledger_check`, ask the driver again.
**`answer_interview_item` is retired — do not call it.**

### `N10` the brief

```python
estimate = {"subagent_calls": len(J.attempts(JOB, PERSONA)),
            "files_touched": len(plan["files"]),
            "tools_granted": len({s["tool"] for s in plan["information_sources"]})}
B.write(JOB, B.render(ticket, qs, ledger, plan, estimate), PERSONA)
```

Omit the estimate and the brief Mike approves carries no cost section at all.

### `N8` the review, and the send-back

Spawn `subagent_type: adversarial-reviewer` directly, `run_in_background: true`, with
the same three things `/adversarial-review` sends and nothing more: the absolute path
of the job directory's `brief.md`, `high`, and the repo root. **Do not summarise the
plan, explain its intent, name its author or say what you think of it.** The question
table reaches the reviewer by being *in the file it is handed*.

```python
review = B.parse_review(reply)                    # markdown -> the one shape
D.land(JOB, step, review, PERSONA)
B.write(JOB, B.append_review(brief, review), PERSONA)
if review["structural"]:
    step = D.send_back(JOB, PERSONA, review["structural"])
```

**`parse_review` is not optional and there is no hand-parse.** The reviewer replies
in markdown — `Wrong:` / `Fails:` / `Costs:` under `## STRUCTURAL` and `## LOCAL` —
while the brief renders structured findings and the send-back reads a defect list
out of them. One parser produces the shape all three want; reading the reply by hand
is how those three drifted apart in the first place. The brief lands in the **job
directory**, never `archive/plans/`, so nothing tracked is written before `[N9]`.

`send_back` records the rejection, checks the bound, rewinds the cursor and returns
the next step — `N7` if a send-back is still allowed, `parked` if it is not, with the
brief left on disk to read. Judging a finding structural is yours; the reviewer's own
`S`/`L` marks are that judgement already made. Nothing after it is. Local findings do
not send a plan back; they travel with it to `[N9]`.

### `[N9]` Mike approves

He reads `brief.md`, edits the plan file directly if he wants, or refuses. Nothing up
to here has touched the repository.

### `N11` the implementer, and the gate

```bash
./scripts/new_worktree.sh <slug> --sandbox        # -> WT = ../metatron-wt-build-<slug>
```

```python
D.channel_baseline(JOB, WT, MAIN, PERSONA)        # BEFORE the first spawn
# ... spawn build-implementer, handing it WT as an ABSOLUTE path ...
patch, refusals, notes = D.implementer_gate(JOB, WT, MAIN, plan, PERSONA)
```

Its prompt carries the worktree's **absolute** path and forbids relative paths: a
subagent's cwd stays pinned to the main tree, so a relative `Write` lands *there*.

`channel_baseline` is kept, so a retry cannot re-arm a channel with the violation it
just refused. `implementer_gate` restores the fixture trees, reads the four channels,
runs the tests, restores again and writes the patch — in that order, because each
step was a separate defect. A boundary violation **parks the job durably**, leaving
the worktree to be read; a failing check earns the one retry. On a retry **reuse the
sandbox** (`new_worktree.sh` exits 1 on an existing path) and re-enter with
`spawned=False` to re-read the channels at no model cost. The patch closes N11: land
the `gates` artifact and the driver names `[N13]`.

### `[N13]` one tree, one diff, one commit, **one sitting**

Do not start this unless you can finish it. `ALL_FILES = D.all_files(plan)`.

1. `D.landing_preconditions(MAIN, ALL_FILES)` — every path, both halves, plus the
   split-checkout refusal. Any refusal stops N13 before it starts.
2. `D.apply_patch(MAIN, patch, ALL_FILES)`. A conflict parks and has already
   reverted the patch's paths.
3. **Write the Red half yourself, in the main tree** — both routing entries at
   parity, the Coordinator directory line and valid-name paragraph, the generated
   `config/agents/*.md`, the knowledge domain, any scheduler entry. Each prompts
   Mike. Nothing Red is delegated.
4. `ok, lines = D.finish_landing(JOB, MAIN, plan, ledger, agent_text, PERSONA)`.
   It flips the registry row to `landed` — which is what arms the wiring checks —
   runs them and the content gate, and returns what to print: the staging manifest
   and the advisory sweep note, or the failing check and the exact revert command,
   with the job parked. **This is the only point where the routing entries, the
   Coordinator lines, the agent file and the code are in one tree before a commit**,
   so it is the only point the `time_director` shape is caught by a check rather
   than by a reader. Print `lines`.

Then Mike reads one `git diff -- <files>`, stages that manifest, commits and deploys.
Land `landing`, and remove the sandbox with `./scripts/rm_worktree.sh build-<slug>
--force` — **`build-`**, the prefix `--sandbox` registers under.

### `N14` acceptance — a LATER session, after the deploy

Named only once `landing` exists, and the test runs **on the VM** against Mike's data
and a fixture persona with no history — so this is `/build BLD-…` re-entered after
`./deploy.sh`. Land `acceptance`, re-render the table with the result, and report a
failure rather than filing it: `file_ticket` refuses any caller that is not one of
the two VM-side writers, because a ticket minted here lands in a tree the VM never
reads.

## `/build coherence`

`C.corpus(persona)` → `C.render_corpus(...)` → spawn `build-coherence` on it →
`C.report(reply, persona)` → `C.render(...)`. The code pass runs first and is not
advisory; rejected findings are reported **as rejected**.

## The rules

1. **Never commit, never push, never `./deploy.sh`.** Deploy is its own decision.
2. **Never hand a subagent a relative path.** Absolute, always, in every prompt.
3. **A green sweep is not a test.** Run the suites the plan names; say what they said.
4. **Report at each gate and stop.** A gate is where a person decides, not a step to get past.

## Cost

$0 marginal per call on the subscription — what it spends is window, visible to
whoever is in the session. `build_board.py --run-cost` shows the standing cost of
each landed capability; `--abandon BLD-… "<reason>"` records a decision not to build
one, into the working tree for Mike to commit.

*Procedure only. The graph and its reasons: `archive/plans/build_vertical_plan_2026-09-24.md`
§ 3. Incidents go to `archive/log/`.*
