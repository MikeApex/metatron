### 2026-08-15, fifth (an approved action now runs; the commit guard learns to attribute) — `2602e2e`, `c3f2ac8`; `2602e2e` **deployed + APK rebuilt**

Two `/fix` runs, both on `## Now` items filed hours earlier by the previous session. Incoming
handoff: `[DB-0810-13]` was diagnosed and its provenance line had immediately exposed
`[DB-0815-03]`; `[DB-0810-12]` was instrumented and awaiting a live occurrence; `[DB-0815-01]`
was down to its Bash-write half.

**`[DB-0815-03]` — an approved action is now carried out, not just recorded (`2602e2e`).**
`POST /confirm` marked a pending record approved and stopped. The design's fourth step — the
agent calling the tool again with `confirm_token` — could never fire: the token is returned
*inside a tool result*, so it lives only in the pipeline session that produced it and is gone
from the model's context by the user's next turn. The approval then expired unspent at the 600s
TTL. `/confirm` now spends it server-side, through the tool's own `consume()`, so single-use,
expiry and the argument fingerprint are unchanged and the model leaves the *execution* path as
well as the consent path. Outcome is written as an ordinary exchange and broadcast, so the user
reads what happened rather than inferring it.

**The item's premise was wrong in one detail, and it mattered.** It said step 4 "has no
trigger". A trigger existed — `static/index.html` nudged the pipeline with "Approved — go
ahead." after every tap — it was simply unspendable. Had the fix been scoped from the item text
alone, that nudge would have survived and kept firing against a server that had already acted.

**Scope was wider than the item, deliberately.** The four *tool schemas* instruct the retry, and
those are what the model reads at call time — more binding than the agent file. `send_email`,
`write_config`, `write_profile`, `write_agent_config` and `synthesizer.md` were all corrected in
the same commit, because leaving them would relocate the failure rather than fix it.
`confirm_token` is now documented as "not for you to set".

**Rejected:** the push notification the item asked for. The tap comes from an open app and the
outcome arrives over the socket, so a push duplicates an on-screen line. Flagged to Mike as a
one-line change if he disagrees; he did not take it.

**Design guard worth keeping:** `_EXECUTORS` is a hard-coded action→tool map. The action name
comes off a JSON file on disk, and resolving it to a callable by name would make that store a
code path.

**`[DB-0815-01]` — the commit guard can tell its own script from another session (`c3f2ac8`).**
Hit live twice in this session before it was fixed: `tools/mail.py` was edited via the Edit tool
(manifest hash recorded) and then again by a `python - <<PY` script, so the guard read *its own*
stale hash as another writer and blocked. The documented override was then refused by the
permission classifier, so the first commit needed Mike's explicit approval — exactly the cost
the item describes.

**The item's own proposed fix stayed rejected; a different one was built.** Trusting a session's
recent Bash writes *writes* to the baseline and would absorb a parallel session's lines,
reopening 2026-08-09. Attribution only *reads*: before blocking, check whether any **other**
session's manifest in `.claude/.session_edits/` records the file at the hash it has **right
now**. Matching on the current hash is what makes it safe — a stale entry carries the old hash
and cannot claim content it did not write.

**Accepted limit, documented in the module:** another session's *Bash* rewrite of a file this
session Edit-wrote now warns where it used to block. That class was already advisory-only when
this session had not written the file, so this narrows one edge to remove a block that fired on
routine work — and a guard that blocks routine work trains the override that disables it.

**`tests/test_commit_guard.py` is new — the first coverage this hook has had across five
corrections**, four of which were fail-open or block-routine-work defects found only by a human
tripping over them. Ten cases against real git trees: the 2026-08-09 incident replayed as case
one, the attached-semicolon and heredoc regressions pinned, stale and corrupt manifests proven
unable to manufacture a collision. Verified *discriminating* by running it against the pre-fix
guard from `git show HEAD:` — the own-tooling case fails there and passes here. A suite that
passes both ways proves nothing.

`tests/test_confirmation_gate.py` gained five cases for the same reason: every existing test
stopped at the gate, which is precisely why the missing half was invisible for eleven days.

**Both `/fix` runs were built here on Opus rather than dispatched.** `[DB-0815-03]` reached
Red (`synthesizer.md`); `[DB-0815-01]` is Green, but a worker would have had to commit a change
to the commit guard *through* that guard, and cannot get the override approved
non-interactively.

**Verification:** confirmation gate 16/16, commit guard 10/10, `qa_sweep` 9/9 twice, plus the
`/confirm` handler driven in-process against a throwaway DB with SMTP stubbed — covering
`to_thread`, `persona_scope` inside the worker thread, the DB row, the broadcast payload, the
404 and the failure path. `c3f2ac8` committed with **no override needed**, which is the guard
fix demonstrating itself on first use.
