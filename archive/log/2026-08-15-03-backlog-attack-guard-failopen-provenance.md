### 2026-08-15, third (`/backlog attack` round 2: the guard was failing open, and `[DB-0810-13]` gets a design) — `6ad3dec`, `2dfd494`, `c0e2cd8`, `ff8f4cc`, `c8d0c69`, `7da7d50`, `6f200b9`, **deployed**

Incoming state: nine `## Now` items, `[DB-0815-01]` blocking every worktree dispatch, a deploy owed.

**Most of `## Now` could not be attacked, and saying so was the useful part.** Of nine items, four
are blocked on Mike's decision or a clock (`[DB-0809-21]`, `[DB-0810-05]`, `[DB-0810-17]`(b),
`[DB-0814-02]`), one needs VM traces (`[DB-0809-02]`), and Now #1 (`[DB-0810-13]`) spans
`config/agents/**` — Red tier, which `CLAUDE.md` bars from subagent delegation. Two clusters, not
three. Recording the departure from rank explicitly is what the mode asks for; the temptation is to
quietly promote easier items and present a fuller-looking plan.

**`[DB-0815-01]` — the fix was called verified and was not.** `6ad3dec` resolved the root from
`git -C` or the session cwd, tested against a real worktree, and reproduced the exact reported
error before/after. It still left every worker blocked, because **a subagent cannot persistently
`cd`** — it reaches its worktree with `cd <wt> && git add`, and its payload cwd is the *main* tree.
That form was never in the probe. The `[DB-0810-15]` worker finished clean work and lost its commit
to it, which is the second worker in two days to pay this cost.

**Chasing that turned up the serious one: the guard was failing OPEN.** `shlex.split` only sees a
separator already delimited by whitespace, so `echo hi; git add x` tokenised as one segment whose
first token is not `git`; `_git_writes` found no git write and the hook **passed silently on a real
staging command**. Every `;` typed without a leading space disabled the guard entirely. That is the
inverse of the false-block everyone had been complaining about, it was invisible because its
symptom is *nothing happening*, and it would have been found by no amount of investigating the
blocks. Fixed with `shlex(punctuation_chars=True)`, which still honours quoting. `ff8f4cc`, 11/11
probe cases including both fail-open regressions and fail-closed in both trees.

**Rejected: the item's own proposed fix for the second blind spot.** `[DB-0815-01]` suggested
trusting a session's own Bash writes the way it trusts its Edit calls. The manifest holds files
this session wrote via Edit, so re-hashing after any Bash call would absorb a *parallel* session's
lines into this session's baseline — reopening 2026-08-09, the incident the guard exists for, to
remove a one-token override. Mike then ruled out the narrower script→output mapping outright: **"No
manual maintenance here."** Left open deliberately; the automatic alternative (read the other
session manifests already on disk — if nothing else claims the file, it is not a collision) is
recommended and unbuilt.

**`[DB-0810-13]` — diagnosed as a missing-information failure, not a prompt failure.** The
Synthesizer's input is the Coordinator's *directives* plus the specialists' *prose*; tool calls
never travel (`outputs[a] = future.result()`). So when `relationships` aborted the send, nothing in
the Synthesizer's context could contradict "That's sent." **No agent-file edit can fix that**, and
one would test clean and fail in production identically. The fix generalises a mechanism already
here: after the fabricated-sources incident, Python began generating a retrieval provenance line
that `synthesizer.md` treats as *"evidence rather than a claim"*. Action provenance is that,
answering "was this done?". Design committed `c0e2cd8`; Mike confirmed the Python track and that
**the verification is not an LLM task**, which is the whole point. Not built: the ordering
constraint is real — the `synthesizer.md` half must not ship before the Python half deploys, or it
declines to confirm things that did happen.

**Workers.** `[DB-0810-12]` instrumentation landed (`c8d0c69`) — observation-only, verified by
reading the diff rather than the summary; it found a candidate the brief did not anticipate (the
blocking replay is *assumed* to return signed calls and nothing checked) and corrected a false
docstring claiming the Synthesizer never calls tools. `[DB-0810-15]` shipped a language knob
(`7da7d50`) plus a real trap fix: the bench script stripped Cyrillic via `[^a-z0-9\s]`, so every
Bulgarian WER would have read 0%.

**`[DB-0810-15]` rescoped by Mike, and the original framing was too narrow.** The need is a
**per-persona pair of independent settings** — input language and output language, which need not
match — plus translation of content that did not originate in the output language. Voice split out
as `[DB-0815-02]`, `## Later`, low priority, carrying a half nothing had filed: TTS output is
hardcoded English in both voices, and no auto-detect can fix that, because synthesising speech
needs a stored value. Text is unblocked today — the model is already multilingual.

**Two communication rules promoted, both from Mike this session.** An id is not a description: lead
with the plain-language problem before `[DB-XXXX-XX]` (`.claude/commands/backlog.md`). And
`~/.claude/CLAUDE.md` § Reporting Level — report at need-and-project granularity in his
code-builder frame, no fix narration, no layman analogies, never punt a decision without options
and a recommendation. His words: *"entirely too much language explaining the wrong things at the
wrong level of scope."* The existing pair-technical-with-plain memory was amended rather than left
to contradict it.

