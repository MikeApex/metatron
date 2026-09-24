### 2026-09-24, fifth (phase C, the plan amended to v4.12, and three things that read correctly and had never been run) — `9339c82`, `52bb929` + this close-out — **nothing deployed; the VM is still at `b2b1dc7`**

Phase C — the five Build subagent definitions and `/build` — plus the plan correction its work
forced. The command is not the runner: `core/build/driver.py` is, and the command can hand out no
step the driver refuses.

**Writing the command was the first thing ever to exercise the driver end to end, and that is the
whole story of the session.** Its review found **ten defects, eight with their fault site inside
`core/build/`** — phase A's package, committed that afternoon with 236 green checks. The suites had
tested the modules as built; nothing had driven the graph.

**A prompt defect made it worse before it made it better.** The phase C prompt said *"nothing in
`core/build/` needs changing — if you think it does, that is a finding"* **and** *"do not
reimplement node order, retry counts, the send-back bound or the park states in markdown."* Both
cannot hold once the driver is the fault site. C obeyed the only instruction available and wrote
prose; the verify round then correctly called it prose. **The remit was widened on Mike's decision
and all eight became code** — `send_back`, `begin`, `land`, `park`, `channel_baseline`,
`implementer_gate`, `finish_landing`, `tree_split`. `build.md` fell **349 → 240 lines**, which was
the agreed signal that a fix had landed in the right layer rather than been narrated. Checks went
336 → 398 across fourteen suites, with the growth exactly where the findings were: `driver` 19→38,
`schemas` 36→47, `gates` 52→60.

**THE SESSION'S LESSON, and it now has three independent instances rather than one anecdote: a
thing that reads correctly and has never been run is not known to work — and reading it harder will
not find the defect.**

1. **The plan's § 3.** Three mechanisms certified by **ten adversarial review rounds** across two
   model families, wrong the moment code ran them: the send-back counted plan files, which only
   exist *after* the Planner has run, so the bound spent the Opus call it existed to refuse; the
   four channels ran at N12, so a retry re-baselined over attempt 1's own refused write and passed
   the change it had just refused; N14 filed a REPAIR from the Mac into a ticket file that lives on
   the VM.
2. **A phase-A fixture was less faithful than the repo in exactly the dimension a finding turned
   on.** The gates fixture ignored `data/personas/` *and tracked nothing under it*. The real repo
   ignores the same path and carries **65 tracked files** under it anyway, because git keeps
   tracking what was tracked before a rule is added — so the case `SESSION.md`'s twice-earned
   standing rule exists for **could not arise in the fixture at all.**
3. **`tools: []` meant "unspecified", not "none".** The harness registered `build-inquiry` — the one
   agent whose entire purpose is judgement in a vacuum (ruling 5) — holding `Read`, `Write` and
   `Bash`, while the description beside it read *"No tools, deliberately."* C's own account of the
   error is the useful part: *"I reasoned about the type and not the predicate"* — `[]` is truthy,
   so it argued the value could not fall through, while the renderer gates on `tools.length > 0`.
   Visible only in the harness's own registration line, which appeared when the files were staged.
   The encoding that works needs **both** `tools:` and `disallowedTools:`, verified by spawning the
   agent rather than by reading the file, with `TodoWrite` as the member deliberately — it reads
   nothing, so a harness that ignored the deny leaves a residue that cannot break the vacuum.

**Mike's ruling on the divergence:** *"if the new code works as well as the planned code, just keep
the new code."* Hence **v4.12** (`52bb929`) — three § 3 corrections in place, each marked and
carrying why, no § 0 ruling touched. *Rejected: reverting the code to match § 3, which would have
re-opened three closed findings.* Leaving § 3 stale was rejected for the stronger reason: a future
session reads it and faithfully re-implements the defect.

**Two coordinating-window failures worth more than the work they nearly spoiled.**

**(a) The cold Fable review found that the review brief was the defective artifact** — four of its
five findings were my scoping errors: I installed the settled plan as the specification while the
code deliberately diverged from it in three places, giving no way to tell "code defect" from "stale
plan"; I confined the reviewer to the worktree and then asked it to audit a closure table that
exists only in main; I removed the only "before" a read-only reviewer can open, making
*"which assertions were loosened"* unanswerable; and my headline check was aimed at a claim nobody
made, having conflated *eight fault sites in `core/build/`* with *eight prose-only promises*. Its
fifth finding was real and is why the pass paid for itself: **N8's output contract disagreed across
three layers** — the reviewer emits markdown, the command indexed `f["wrong"]`, `brief.py` read
`title`/`detail` — with nothing owning the conversion, so the first structural finding of the first
real build would have raised `KeyError`. Now `brief.py:parse_review()` with its own suite.

**(b) A staged snapshot went stale beneath me and would have shipped the bug.** I applied and staged
C's patch; C then fixed `build-inquiry.md` on disk. **The index held `tools: []` while the working
tree held the fix**, and the file on disk read correctly. This is `.claude/rules/deploy.md` rule 4 in
a form that file does not describe — not another session's lines inside a file I staged, but my own
staged copy aging. Caught by diffing the index against the working tree before committing. *The rule
as written says "`git diff <file>` before you stage it"; the missing half is **re-diff after anyone
touches it, including a worker correcting its own content**.*

**Also corrected, and mine:** `PROJECT_LOG.md` carried "19 commits" while its fragment said
otherwise, because I edited the fragment after regenerating the log and never re-ran the generator.
Phase C's sweep reported it as inherited drift; it was inherited *to C* and authored by me.

**Cost.** Phase C ran ≈$30–40 against a widened $25–35. Session total ≈**$75–100** of § 14's
$65–106 with phase F ($10–20) still to come, so **the build finishes over estimate** — driven almost
entirely by phase A's driver needing repair once something finally drove it. Recorded as the price
of the lesson above rather than as an estimating error: nothing cheaper than writing the command
would have exercised the driver.

**State.** Phases 0, A, B-Red, B, D and C committed; nothing deployed. Remaining: **F** (bootstrap
runs 1–3, live walkthrough) and **E** (the deploy, which carries everything in `b2b1dc7..HEAD`, not
Build's commits alone). E's checklist is written with its four pre-flight gates already run green,
and gained one item tonight: a **host marker on the two systemd units**, so `file_ticket`'s refusal
can distinguish Mac from VM instead of trusting its caller — unit files, so rule 3's
`daemon-reload`-before-deploy applies to it and to nothing else in this deploy.

