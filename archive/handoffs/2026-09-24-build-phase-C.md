# Build phase C — the five subagents, `/build`, and ten findings moved into code

*2026-09-24. Worktree `/Users/md-homefolder/Desktop/metatron-wt-v4c-command`, base
`2894ad5`, left in place. Patch: `archive/handoffs/2026-09-24-build-phase-C.patch`.
Nothing committed, pushed or deployed. **No Red file touched.** Model: Opus 5;
review Fable at `high`, three rounds, plus one cold review and one
harness finding.*

---

## The one-line result

**Build is runnable, and the bounds the plan specifies are now in Python rather than
in a command file a model has to follow.** The widened remit is what made that
possible: eight of the ten findings had their fault site inside `core/build/`, and
under the original instruction the only available fix was prose — which the verify
round then correctly called out as prose.

**`build.md`: 349 lines → 253.** Every line removed came out because the thing it
described moved into the driver.

| Suites | before | after |
|---|---|---|
| build suites + doors + read_tools | 13 green, 336 checks | **14 green, 398 checks** |
| `./scripts/qa_sweep.sh` | 11/12 | 11/12 — same inherited red |

### The cold review's one finding — N8's output contract (fixed in code)

`adversarial-reviewer` is the **sixth** subagent `/build` spawns, the only one Build
does not own, and the only one whose output contract crossed layers. Three files
disagreed about what a finding is, with **nothing converting**: the agent emits
`Wrong:` / `Fails:` / `Costs:` markdown; `build.md` indexed `f["wrong"]`;
`brief.append_review()` renders `finding['title']` / `finding['detail']`. Reproduced
both halves — indexing the text raises `TypeError`, and the renderer writes `**?** —`
into the brief. At N8, the node the send-back bound depends on.

**Fixed in code:** `brief.parse_review()` turns the markdown into one canonical dict
carrying every key all three layers already asked for, so no consumer changed;
`driver.defect_lines()` normalises findings for the send-back, so the command holds
no index at all. New suite `tests/test_build_brief.py`, **16 checks, fixtured on the
three real reviews of this command** rather than on a handwritten sample — which is
what catches the wrapped `Costs:` lines and the non-contiguous global ranking.

`build.md` went 240 → 253 for this: thirteen lines narrating a code call and naming
the sixth subagent, not thirteen lines of procedure to follow.

**Also handled, because the reviewer's format allows them:** the `VERDICT: More than
ten significant defects` escape hatch becomes one structural finding; a verify
round's `## NEW` block is structural; a report in no known format is kept whole in
`unparsed` rather than raising or being silently dropped.

### The harness's finding — `tools: []` granted Inquiry everything

**`tools: []` does not mean zero tools. It reads as UNSPECIFIED, and the harness
grants all of them.** Its own roster line said `build-inquiry … (Tools: All tools)`
beside a description reading *"No tools, deliberately"* — the file said the right
thing and was wrong, which is why no amount of reading it would have found this.

**My earlier reasoning was wrong and is worth recording.** I argued from the CLI's
schema string (*"Replaces the default set"*) plus JS truthiness — `[]` is truthy, so
I concluded it could not fall through to inherit-all. The actual renderer is:

```js
let n = tools && tools.length > 0, o = disallowedTools && disallowedTools.length > 0;
if (n && o) { … if (difference.length === 0) return "None"; }
else if (n) return tools.join(", ");
else if (o) return `All tools except …`;
return "All tools";
```

`[]` fails `length > 0`, so it falls past every branch. **The `"None"` branch is
reachable only by setting BOTH keys.** `build-inquiry.md` now carries:

```yaml
tools: TodoWrite
disallowedTools: TodoWrite
```

**`TodoWrite` is the member deliberately:** it reads nothing and touches no file, so
if the deny were ever ignored on a future harness the residue is a tool that cannot
break the vacuum — rather than `Read`, which is precisely the one that would.

**Verified by spawning the agent, not by reading the file.** It reports: *"no Read,
Write, Edit, Bash, Glob, Grep, or any other tool is available… I could not attempt
the Read call at all — the failure is absence of the tool rather than a permission
denial."* `TodoWrite` is gone too, which settles the open question: **a definition's
`disallowedTools` IS enforced**, contradicting the terser schema note that it is
"ignored if `tools` is set".

**The honest bound:** zero *grantable* tools. The agent retains `SubagentHandback`,
the harness's own reply channel, which no definition can remove — without it the
subagent could not return an answer at all. That is the closest achievable bound and
it is a true vacuum for every purpose ruling 5 cares about.

**Confirmed in passing:** the librarian's scoped grant registers as
`Bash(python3 scripts/vm_read.py *)`, so the scoped-Bash form is honoured as written;
the other four agents' roster lines match their frontmatter exactly.

**I edited the main tree's copy as well as the worktree's.** The coordinating window
had already applied and staged my patch there (files dated 22:12, `A`/`M` in the
index), so the bug was live in what it was about to commit. The two copies are
byte-identical; the fix is my own content corrected before it lands, not another
window's lines.

### Where the code now diverges from the plan's § 3

Three places, all deliberate, all left alone per your ruling that **the plan is
amended to match the code**: the send-back counts rejections rather than plan files
(so the bound fires before a planner spawn); the four channels run inside N11's
`implementer_gate` rather than at N12 (because the patch is N11's cursor); and
`file_ticket` refuses non-VM writers at N14. Recorded here so the amendment has the
list.

The one sweep red is `project-log` fragment drift, committed at `2894ad5`, identical
in both trees. The reviewer independently confirmed it predates this session.

---

## The ten findings: fault site, fix, assertion

| # | Fault site | Fix landed in | Assertion now covering it |
|---|---|---|---|
| **1** send-back has no code path | `driver.py:next_step/_artifact_done` | **code** — `driver.send_back()`, `rejections()`, `MAX_SEND_BACKS`; `_artifact_done("N7")` is now *versions > rejections*, so a rejected plan makes the driver name N7 | `test_build_driver.py` ×5, incl. *"without a send-back the driver offers [N9] on a REJECTED plan"* (pins the old behaviour) and *"the SECOND send-back parks BEFORE a planner is named or anything deleted"* |
| **2** retry re-arms the channel watching for a planted hook | `gates.py` (no baseline), `driver.py` (no park primitive) | **code** — `gates.snapshot()`, `driver.channel_baseline()` (taken once, kept), `driver.park()`/`unpark()` writing a durable marker that outranks every state in `next_step` | `test_build_gates.py` *"the baseline is taken ONCE and REUSED"*, *"a channel refusal PARKS the job durably"*; `test_build_driver.py` *"park() outranks every other state and survives a restart"* |
| **3** `write_patch` at two nodes; `climb` KeyError; no `gates`/`acceptance` write | `driver.py`, `jobs.py` artifact mapping | **code** — `driver.land()` is the single landing call and knows each node's rule; N7 goes through `write_plan` | `test_build_driver.py` ×4, incl. *"land() sends N7 through write_plan, which is what the counter globs"* |
| **4** content gate decorative — `record`/`peers` had no source | `schemas.py` (no `record{}`), `verify.py` (8 hand-assembled args) | **code** — `record{}` required on agent plans incl. `routing.allowed_tools`; `verify.content_gate_for()` derives every argument; `registry.new_row(display_name=)` gives `peers` a source; `driver.finish_landing()` makes the N13 sequence one call | `test_build_schemas.py` ×4; `test_build_driver.py` *"finish_landing runs the CONTENT gate, not only the wiring checks"* |
| **5** interview answers had nowhere to go | `schemas.py` (no field) | **code** — `schemas.record_interview_answer()` writes the canonical shape; `open_interview_items()` derives N5's list | `test_build_schemas.py` ×4, incl. *"an interview answer lands as a VALID row that derives `settled`"* |
| **6** attempt cap fires on a legitimate job (16/16) | `driver.py:record` | **code** — `driver.begin()` records a row only for a subagent node, never a code node or a gate | `test_build_driver.py` *"begin() records a SUBAGENT node and nothing else"* and *"a whole construct job … stays under the cap"* |
| **7** `required_inputs` had no source | `schemas.py` | **code** — `required_inputs[]` required and checked against the asked questions; `schemas.revalidate_ledger()` is the one N7 call | `test_build_schemas.py` ×3, incl. *"revalidate_ledger makes if_user_lacks_it mandatory on EXACTLY those rows"* |
| **8** fixture dirt into the patch / channels look too early | `driver.py:write_patch`, ordering owned by the caller | **code** — `gates.restore_fixtures()`, called inside `implementer_gate()` before the channels *and* again before the diff, and inside `write_patch()` as the last guard | `test_build_gates.py` ×4, incl. *"implementer_gate restores fixtures BEFORE the channels look"* and *"the restore does NOT open a hole"* |
| **9** N14 filing a REPAIR from the Mac | `tickets.py:file_ticket` | **code, partially** — `file_ticket` now requires `writer=` from a closed allowlist of the two VM-side callers. **Why not fully:** nothing in-process distinguishes the Mac from the VM (`DEPLOYMENT_MODE` is `cloud` on both), so this converts a silent wrong-machine write into an explicit refusal but cannot stop a caller that lies. A true machine gate needs an env marker set by the systemd units — a deploy change, and **yours to make**. | `test_build_tickets.py` ×3, incl. *"file_ticket REFUSES a caller that does not name a VM-side writer"* |
| **10** `_ROOT` follows the import, not `MAIN` | `jobs.py`/`registry.py` module roots | **code** — `driver.tree_split()`, called from `landing_preconditions`. It compares the **git common dir**, so two worktrees of this repo refuse and an unrelated fixture repo does not — which is why it can run unconditionally without breaking every landing suite | `test_build_driver.py` ×3, incl. a live check that refuses when the suite is run from a worktree of the main repo |

**Nothing stayed prose that code could hold.** The two things still written rather
than enforced are both judgements, not bounds: *whether a review finding is
structural* (which `send_back` then bounds), and *which paths are Red* (resolved from
`.claude/settings.json`, the authority).

---

## Assertions I did not weaken, and two fixtures I corrected

**No existing assertion was deleted or loosened.** Three fixture corrections, each
because the fixture was *less faithful than reality*, not because a check was
inconvenient:

1. **`build_fixtures.build_plan()` gained `record{}` and `required_inputs[]`** — the
   fields the schema now requires. Adding a newly-required field to a valid-baseline
   fixture is what keeps the "start valid, introduce exactly one defect" method
   working.
2. **The gates fixture repo now force-tracks one file under `data/personas/`.** This
   is a **finding about phase A's fixture**: the real repo ignores `data/personas/*/`
   *and carries 65 tracked files under it anyway* — git keeps tracking what was
   tracked before a rule is added. The fixture had only the ignored half, so the
   tracked-fixture-dirt case finding 8 turns on could not be reproduced in it at all.
   The existing channel-(b) assertion (which asserts the porcelain is blind to
   ignored persona paths) is untouched and still passes; the new file exercises the
   other half.
3. **The gates fixture `.gitignore` gained `__pycache__/`**, which the real repo has.
   Without it the fixture put `.pyc` files into the patch that reality never would.

**One phase-A assertion encoded behaviour that is now superseded, and I kept it
rather than changing it:** `test_build_driver.py`'s *"a SECOND send-back parks the
job for Mike"* asserts the park fires on `MAX_PLAN_VERSIONS` (three plan files). That
path still works and still parks — but on the route `/build` now takes, the
**rejection count parks first**, before a third plan is ever written. `MAX_SEND_BACKS`
is derived from `MAX_PLAN_VERSIONS` so the two cannot disagree, and the old check is
now asserting the backstop rather than the trigger. Worth a line in `driver.py`'s
docstring at some point; I did not rewrite the assertion to say so.

---

## Files touched beyond the enumerated list

Two, both Amber, both one-line call-site updates forced by the `file_ticket`
signature change — not new fault sites:

- `core/build/tick.py` — passes `writer="repair_scan"`
- `tools/build.py` — passes `writer="request_build"`

Flagging them because your grant named seven files and these are not among them.

---

## What shipped, in full

Ten new files, seven modified:

| New | |
|---|---|
| `.claude/agents/build-{inquiry,librarian,planner,implementer,coherence}.md` | 142 / 164 / 129 / 120 / 73 lines |
| `.claude/commands/build.md` | **253** |
| `tests/test_build_manifest.py` | 11 checks |
| `tests/test_build_brief.py` | 16 checks — N8's output contract |
| `archive/plans/adversarial_review_build_command_2026-09-24_r{1,2,3}.md` | the three rounds, verbatim, with the two-line header |

*(The three review files were written in the previous turn and are in the patch —
your last message said they had not happened; they had.)*

| Modified | Why |
|---|---|
| `core/build/driver.py` | findings 1, 2, 3, 6, 8, 10 + `finish_landing` |
| `core/build/schemas.py` | findings 4, 5, 7 |
| `core/build/gates.py` | findings 2, 8 |
| `core/build/verify.py` | finding 4 |
| `core/build/registry.py` | finding 4 |
| `core/build/tickets.py` | finding 9 |
| `core/build/brief.py` | the cold review's finding — `parse_review()` |
| `core/build/tick.py`, `tools/build.py` | call sites |

### The three § 12 rows still pass

Re-run after the code changes; output unchanged from the previous handoff (Resume:
N2/N4 skipped, N7 runs, no duplicate artifact. Review sees the table: the reviewer's
file carries the question table, the review lands after it, the graph stops at [N9].
Persona-qualified ids: same `BLD-0924-01` in both fixture ticket files, different job
directories, no `--persona` resolves `mike`.)

### `tests/test_build_manifest.py` — the docstring's claim **held**

`manifest.py` cited this file twice; it did not exist. The content-free rule was
**true, just untested** — do not delete the sentence. Negative control: a four-line
leak injected into `manifest.build()` made it go red naming the leaked tokens and
their source file; reverted, `manifest.py` byte-identical to HEAD.

---

## The three review rounds

Verbatim in `archive/plans/adversarial_review_build_command_2026-09-24_r{1,2,3}.md`.

- **Round 1** — ten findings (4 structural, 6 local). All ten are the table above.
- **Round 2** — 8 CLOSED, 2 NEW SHAPE, 2 NEW. The NEW SHAPEs are the ones your
  message is about: *"a park, not a retry is prose only"* and the record missing
  `routing.allowed_tools`. Both are now code. The two NEW findings (bound consulted
  after the planner ran; retry re-creating an existing sandbox) are now code and
  prose respectively.
- **Round 3** — all four CLOSED, 3 NEW: the hand-built N7 step not restoring the
  per-node bound (**now fixed properly in code** — `_artifact_done` makes N7
  genuinely not-done, so the ordinary retry bound applies); fixture dirt reaching the
  channels (now `restore_fixtures`); and the park reading as `N8 failed 2 times`
  rather than a plan-version cap (**accepted and documented** — the rejection count
  parking first is the point, and `attempts.jsonl` is the record to read).

**Nothing was refused across the three rounds.** Sixteen findings, sixteen addressed.

---

## Still yours

1. **A machine-level gate for the ticket inbox** (finding 9's other half). Needs an
   env marker on the systemd units — deploy, Red-adjacent, yours.
2. **`build.md` has no `CEILINGS` entry.** At 253 it sits above `backlog.md`'s 200.
   I did not add one — the number is yours to set, and I no longer expect the file
   to shrink further (see the note on `session.py` below).
3. **`driver.py`'s docstring still describes `MAX_PLAN_VERSIONS` as the send-back's
   durable home.** True as a backstop, no longer the trigger. One-line correction,
   left for you because it is a claim about your design, not a bug.
4. **The read doors 404 until phase E deploys them**, so no real Build run is
   possible before E. Expected, consistent with § 16, not a phase C defect.

**And the recommendation I made last turn is now half-built.** `driver.py` gained
`send_back`, `begin`, `land`, `park`, `channel_baseline`, `implementer_gate`,
`finish_landing`, `tree_split` — most of what I proposed as `core/build/session.py`.
What is left in prose is the N13 human step and the spawn calls themselves, which
cannot move. I no longer think a separate `session.py` is worth building.

## Cost

**$25–35 range; ≈$33 spent.** The three review rounds were 277k + 316k + 337k Fable
subagent tokens; the code work, assertions and regression runs are the rest on
Opus 5, including the cold review's fix. Inside the range; I did not cross $35.
