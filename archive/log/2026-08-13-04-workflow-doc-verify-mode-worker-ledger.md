### 2026-08-13 (throughput §8 and §5 — the workflow doc, `/backlog verify`, and a ledger that says what a worker actually costs)

Phases 8 and 5 of the development-throughput plan (`~/.claude/plans/jaunty-kindling-clarke.md`),
run in the window that had just finished §10a. No runtime code, nothing deployed. A parallel
window ran the settings/permissions work (H5, the `Write` deny hole, H2) throughout and had not
reported back when this closed.

**§8 — `docs/WORKFLOW.md` rewritten for the person using it** (`c82ed47`). 149 → 304 lines, five
sections: command glossary, a goal→command lookup, the four shapes a day takes, what needs Mike's
approval *and why deploy is different from everything else*, and what a worktree is in
non-technical terms. Three things it deliberately does not say, all for one reason — a capability
named in live instruction text gets read as present, which is the failure `CLAUDE.md` already
documents against `web_search`:

1. **`/backlog verify` was left out** until it existed. Plan §8's line about updating
   `backlog.md` for verify mode was moved to §5, where it was actually built an hour later.
2. **`/qa` is documented as `./scripts/qa_sweep.sh`**, because no slash command exists. The plan
   counts nine commands; there are five plus scripts. Writing the ninth into the glossary would
   have invented it.
3. **Two open harness defects got a line each**, because they change what Mike should do today:
   only deploy from the main tree (the lock is blind across worktrees), and the prompt reduction
   is unrealised (`defaultMode: auto` is not in effect — its detector fired again mid-session,
   unprompted, while writing the section that describes it).

**A parallel window hand-edited the generated `PROJECT_LOG.md`, and `qa_sweep` caught it six
minutes later** (`9ee4057`). `a7e2e6b` appended a ~50-line entry directly to the file, which has
been generated from `archive/log/` fragments since `fcac265`. The next rebuild would have
discarded it silently, including the three corrections it records. Moved verbatim into a `03`
fragment; rebuild is byte-identical to the committed file. It was one byte off first: each
fragment owns its own trailing blank line and the builder deliberately does not normalise that,
so an omission surfaces as drift rather than being quietly patched — the design working as
intended, one commit after it was written. **This is the first defect on this plan found by a
guard rather than by a person**, which is the whole point of building guards.

**§5 — `/backlog verify`** (`83e77a2`). Fans verification out to workers and returns one verdict
table; `deep` calls it as its step 3, which is what makes `deep` cheap enough to run when counts
drift; `attack` now spawns its own workers after Mike approves the cluster plan, via
`new_worktree.sh` rather than `isolation: "worktree"`.

**The plan's own dispatch shape was wrong and was corrected while building it.** §5 specified one
Sonnet worker per item. It was written before the flat cold-start cost was measured: ten items
would be ten briefings. Batched across three workers instead.

**Then it was run, on one real item, because twelve defects on this plan have appeared only under
execution and none by reading.** A Sonnet worker verifying `[DB-0810-09]` came back with
`file:line` evidence for every claim, answered a question the item had left open for three days —
**`ROUTING_MISS` is emitted from nowhere in the codebase**, surviving only as docstring prose, so
collecting it would wire up a dead type — and found a type the item missed: `CALENDAR_DUPLICATE`
is emitted live at `tools/calendar_audit.py:190` and is not in `WANTED`. Both recorded in the
item itself, not in a session narrative, which is where findings go to be lost. It also wrote
nothing, which is the one guarantee with no mechanism behind it: `qa_sweep.sh` checks seven
specific things, not tree cleanliness, and the `SubagentStop` gate excludes the main tree from
its dirty-worktree sweep. The prohibition in the brief is the entire control, and the command
file now says so.

**The worker cost 58,879 tokens against a ~42k estimate**, which retired the flat-32k model the
batching argument rested on. Mike's response was the right one: if dispatch decisions turn on a
cost number, that number has to be measured rather than asserted, and items should be scoped with
an estimate *before* dispatch so each worker runs a sensible context lifetime.

**`scripts/worker_ledger.py` — the data was already there.** Claude Code writes every subagent's
usage into the session transcript, so the ledger reads what already happened: no hook, no worker,
no model tokens, and it works retrospectively across all 112 sessions this project has run.
**Rejected: instrumenting the `SubagentStop` hook**, which would have cost a worker per
measurement to discover whether the payload even carries usage, and would only ever have
measured runs made after it shipped.

**It found defect 13 on its first run, in itself.** The transcripts carry **two** usage formats —
older sessions use `<subagent_tokens>N</subagent_tokens>` element tags, newer ones a plain
`subagent_tokens: N` block — and the first version matched only one. It reported **3 worker runs
out of 41 and looked entirely plausible doing it**: a clean table, sensible aggregates, a
confident floor of 49,902. A partial match is not a partial result here, it is a wrong one. The
fix (a tolerant two-format regex) is written but **had not been re-run when the session closed**
— it is uncommitted-verified, not verified.

**Left open deliberately**, all recorded in `HARNESS_BACKLOG.md` or the handoff prompt: the two
de-duplications Mike approved (`backlog.md`'s dispatch block is a near-verbatim copy of
`fix.md`'s, which is the exact stale-copy hazard `CLAUDE.md` § *One Home Per Rule Class* exists to
prevent; and the `gcloud journalctl` invocation belongs in `docs/INFRASTRUCTURE.md`), the
`CLAUDE.md` ceiling raise for `backlog.md` (187 lines against a recorded ~130 — growth by
capability, a fourth mode, not narrative creep), and wiring the ledger into `verify` as a
pre-dispatch estimate plus a post-run actual.

**§10b was not run and must not be, yet.** H5 is one of its five named hypotheses and
Verification check 1 is explicitly blocked by it, so running the rehearsal before the settings
window lands would spend 40–60k and still owe a rerun.

