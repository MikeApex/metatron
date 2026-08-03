# 2026-08-03 — Doc drift reconciliation: HTTPS verified live, ephemeral IP removed

*4th window. Short session. Deployed `b83f283`.*

---

## What prompted it

A handoff note from the previous window: CLAUDE.md had documented plain HTTP in
five places including the recreate-from-scratch checklist, while the server has
been serving HTTPS behind a Tailscale cert. That was corrected in the previous
session. The instruction here was to reconcile it — and, more usefully, the
observation that came with it: *drift of this kind only surfaces when someone
actually runs the documented command, so a doc that does not match live is a
backlog entry, not a sign you are holding it wrong.*

---

## Findings

**1. The HTTPS correction did land, and is now verified against live rather than
against the docs.** CLAUDE.md is internally consistent — topology diagram,
prose, Android server address, and the recreate-from-scratch health check all
say `https://metatron-vm.tail0acc5d.ts.net:8001`. Both forms run against the
VM:

| Command | Result |
|---|---|
| `curl https://metatron-vm.tail0acc5d.ts.net:8001/health` | `{"status":"ok"}` |
| `curl http://metatron-vm.tail0acc5d.ts.net:8001/health` | exit 52, empty reply |

The documented command now works as written. That is the only test that
settles this class of question.

**2. The same error was still in the code.** `core/server.py`'s module
docstring said *"Exposes the orchestrator over HTTP on the local network"* and
pointed at `http://<laptop-ip>:8000`, while `__main__` (~line 1122) prefers a
Tailscale `.crt`/`.key` and serves HTTPS whenever one is present. **Fixing the
prose in CLAUDE.md did not prompt anyone to check the code comment saying the
same wrong thing** — worth recording, because that is the generalisable failure,
not the typo. Corrected, including the production URL, the Android-mic-on-HTTP
note, and the missing `--persona` in the `Run:` examples.

**3. A worse instance of the same pattern — the external IP.** Recorded in four
places with three different values:

| Location | Value |
|---|---|
| CLAUDE.md, prose (line 282) | `35.202.250.80` |
| CLAUDE.md, VM table (line 295) | `136.112.188.80` |
| SESSION.md (2026-07-31 entry) | `136.112.188.80` |
| DEV_BACKLOG.md (housekeeping) | `136.112.188.80` |
| **Live, 2026-08-03** | **`34.172.114.36`** |

None were wrong when written. The IP is ephemeral, reassigns on every
stop/start, and there is an active pause/resume workflow — so any literal value
is stale within days *by design*. Updating to a fourth soon-to-be-stale number
would have been the wrong fix. Removed the literal from all four places and
replaced it with the `gcloud compute instances describe ... natIP` lookup.

---

## Decisions

1. **Do not record values with a short half-life.** External IPs and anything
   reassigned on rebuild get a lookup command, not a number. This is now stated
   in the CLAUDE.md VM table and in the backlog entry.
2. **Keep the stale values in the backlog entry's prose**, deliberately — they
   are the evidence for the rule, and stripping them would leave an assertion
   with nothing behind it.
3. **A doc/live mismatch is a backlog entry**, per the instruction that opened
   the session. Written into the backlog as a standing corollary.

---

## Backlog

Filed under `## Open — housekeeping`, framed as the pattern rather than the two
bugs: this drift class is invisible to reading and only fails on execution.
Proposed stronger fix — a smoke script running the handful of *executable*
claims in CLAUDE.md (health check, service status, deploy verification) and
reporting mismatches. `deploy.sh`'s HEAD assertion is that idea applied to a
single claim and is the model to copy. Not built; scoped only.

The pre-existing external-IP entry was rewritten rather than duplicated.

---

## Deploy

`./deploy.sh` → `b83f283`. Clean: fast-forward, no active SSE streams, both
services restarted, health `{"status":"ok"}` after restart.

**The new deploy verification exercised its match path on a real deploy for the
first time** — SESSION.md had flagged it as simulation-tested only. Output:
`Verifying VM is running b83f2836... Verified: VM HEAD matches.`

**Then its failure path fired too — and was wrong.** The third deploy of the
session reported `DEPLOY FAILED ... Whatever you were about to test is running
OLD CODE`. It wasn't. A parallel chat window pushed `88286a7` between this
window's push and the VM's pull, so the VM was strictly **ahead** — running the
pushed commit *plus* one more. `git merge-base --is-ancestor` confirmed the
commit was live.

The assertion tested **exact HEAD equality**, which is the wrong question. The
question is *"is the commit I pushed live?"*, not *"is the VM's HEAD
character-for-character mine?"* Fixed in the same session: `deploy.sh` now tests
ancestry and reports four distinct outcomes — `unverified`, `match`, `ahead`
(success, naming the extra commits), `failed` (commit absent from history). All
four branches exercised through a local harness; syntax checked with `bash -n`.

Worth stating plainly because it is the more expensive kind of bug: **an alarm
that cries wolf on a good deploy is one people learn to ignore**, which costs
exactly the silent-failure detection the assertion was added to provide.
SESSION.md had anticipated the parallel-window ambiguity ("tells you *what* is
live, not *who* deployed it") but not that it would trip the check.

---

## Carried in

The commit also carries pre-existing uncommitted work from an earlier window:
three machine-written Inbox entries from `sync_dev_backlog.py`, and the
*"no agent can read a specific web page"* backlog entry (grounded search ≠ web
access; the three-level fetch/act distinction and its build order). Committed
rather than left dangling; noted in the commit message so it is not mistaken
for this session's work.

---

## Not done

- The smoke script for CLAUDE.md's executable claims — scoped in the backlog only.
- Removing the unused external IP from the VM (~$2.90/mo saving) — still open.
