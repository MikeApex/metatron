### 2026-08-13 (the ledger that measured nothing, `/backlog verify` scoping, harness reconcile)

Throughput close-out from the window that owned §8/§5 follow-through while the other window ran
§1. Two more defects, both found by running. No runtime code, nothing deployed
(`3fc6489`, `daf314d`, `b4abdde`, `6368311`, `7285d94`, `7147293`, `fa69900`).

**`worker_ledger.py` reported 3 worker runs and the real number is 13 — and the committed "fix"
for this had changed nothing.** The previous session diagnosed it as a too-narrow regex and
widened it to accept both text formats. That diagnosis was wrong, so the widened regex found
exactly the same 3 records. **The formats were never the problem; the location was.** Ten of
thirteen completions live in a `tool_result` block at `message.content[].content[].text`, joined
by that block's `tool_use_id` *field* — there is no `<tool-use-id>` tag anywhere in the new
shape. The old code `continue`d past every record carrying a dict `message`, so those ten were
skipped before any regex ran. Found by walking the JSONL and asking where the string actually
was, rather than reading the regex a second time.

**The expected number in the briefing was also wrong** — "~40 runs" came from grep hits on the
literal `subagent_tokens`, of which 143 exist and most are this script's own source and
documentation echoed back into transcripts when the file is read or edited. Chasing 40 would
have meant loosening the extractor until noise was counted as data. Both extractors now demand
proof of a genuine completion payload (`<task-notification>` wrapper, or an `agentId:` line).
Real figures: **13 runs, floor 30,023, median 49,902, worst 108,792**; haiku median 31,888
(n=4), inherited 64,081 (n=8), sonnet 58,879 (n=1).

**The H5 fallback detector's silence was not success, and the briefing said it would be.** The
instruction was that the detector prints on every `Write` when auto mode is not in effect, so
its absence is the signal that H5 landed. It stayed silent for a different reason:
`_configured_mode()` returned `None` because the other window had already removed `defaultMode`
from `settings.json` mid-session. Trusting the stated signal would have declared H5 fixed off a
check that could not fire. Established by instrumenting the hook to dump a real payload —
`permission_mode: default` was present all along. **A silent no-op and a pass look identical
from outside; only the payload distinguishes them.**

**H2 verified rather than assumed.** The lock block was run from a real worktree and from the
main tree: both resolve to `…/multi-model-mcp/.git/.deploy.lock`, and the raw `--git-common-dir`
output is indeed the relative string `.git` from the top level, which the fix handles. Mutual
exclusion confirmed by a second `mkdir`. The `rm -rf` cleanup was *denied by the deny rule* —
incidental live evidence that `deny` still outranks H5's new blanket `Bash` allow.

**`/backlog verify` gained pre-dispatch scoping** (Mike's requirement: items "scoped in advance
with a cost estimate so that each worker runs an optimal context lifetime"). Estimates now come
from the measured per-model medians above, with an actual-vs-estimate line in the close-out so
they calibrate rather than ossify. Added the missing split rule: **screen for checkability
before splitting** — an item a worker cannot reach is not a small item but an unanswerable one,
and `[DB-0810-13]` needs VM traces, so a worker handed it burns a full briefing to report that
it could not look.

**Two de-duplications, and the ceiling that followed.** The dispatch block was a near-verbatim
copy of `/fix` step 3; `/fix` owns it now. The `journalctl` invocation moved to
`docs/INFRASTRUCTURE.md`, whose scope was widened the same day to own exactly that. Net −20
duplication, +26 scoping, landing at 196 lines. **The approved ceiling of ~170 was therefore
written before the content existed, and was set to 200 instead** — recording 170 would have
logged a ceiling the file was already over on the day it was set, which is how a ceiling stops
being checked.

**Rejected:** committing `HARNESS_BACKLOG.md` while the other window's `H8` sat uncommitted in
it, and committing `CLAUDE.md` while that window's staged `H7` hunk was in the index — both are
the 2026-08-09 interleave, where staging by filename sweeps a parallel session's lines. Waited
instead, then carried `H8` with explicit attribution once that window had archived without it.
**Also rejected:** running §10b's check 1 or the H7 `ask` test from this window. Both are
non-interactive-blind — `ask` resolves to ALLOW here, so a missing prompt is the expected null
result whether the mechanism works or not.

**§10b deferred by user decision, with its budget corrected from ~40–60k to ~165k.** The plan's
figure rested on the flat-32k worker model retired the same day; three cold workers at measured
medians is ~165k. Run 2 additionally needs a second live window. Deferring was the call rather
than half-running it: checks 4 and 10 remain the two failures this plan exists to make
impossible, and neither has been observed. Next-session prompt written to
`archive/plans/next_session_prompt_2026-08-13_throughput_10b.md`.

**That prompt was then reordered on Mike's challenge — backlog and the code-not-rules audit go
*before* §10b.** The first draft followed §10's own instruction to run the integration test
before building more. Three things outrank it, one of them safety: **run 2 attempts
`./deploy.sh` from both windows, and per H7 that is ungated in a non-interactive session**, so
it would really deploy to the VM twice; `[H8]`'s token-accounting hook is the direct fix for why
§10b was deferred at all (its budget was a guess); and run 1 needs a real Green item, which
comes from a triage pass. The counter-argument is kept in the prompt rather than buried:
§10 exists because building before integration-testing produced five defects reading never
found. It resolves only because H8's items are **checks on existing mechanisms**, adding no new
surface — and the prompt says that if one grows into a new component, §10b goes first again.

**Harness backlog reconciled: 11 opened, 8 closed, 3 open** — H6 moved out of `## Open`, where
its own text already said RESOLVED and a reader would have taken it as live. `/archive`'s
unverified push closed: step 5 now asserts `HEAD == origin/main` and prints the stranded commit
count, tested both directions, and **its first real run reported a true failure.** The file
**does not retire with this build**, which its contract calls a failure — recorded as such
rather than closing three live items to make the rule come out even. A first pass at the
reconciliation note wrote "five closed" directly above a parenthetical listing eight; the
parallel window got the count right by re-reading the file instead of trusting its own earlier
note, which is the same lesson twice in one day.
