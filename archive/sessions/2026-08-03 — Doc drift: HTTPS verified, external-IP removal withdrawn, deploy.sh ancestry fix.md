# 2026-08-03 — Doc drift: HTTPS verified, external-IP removal withdrawn, deploy.sh ancestry fix

*4th window. Deployed `b83f283`, `56a86f4`, `3492d42`, `c674a91`.*

*Filename note: this log was first written as "…ephemeral IP removed", which
became actively misleading once the removal was withdrawn — it reads as though
the IP was deleted. Renamed. Fitting for a session about docs that mislead
whoever acts on them.*

**One thread, three findings.** It began as a check on someone else's
correction, and each step turned up the same shape of defect one layer further
out: a doc that is accurate about a fact and wrong about what to *do* with it,
failing only when someone acts. The HTTPS note was right and already fixed. The
external-IP note was right about the cost and wrong about the consequence. The
deploy assertion was right about the SHA and wrong about the verdict.

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

## The external-IP item — withdrawn (`3492d42`)

Prompted by a question about what the item actually was and where $2.90 came
from. Answering it properly showed the item was unsafe.

**"Never used" was true for inbound and false for outbound.** Nothing connects
*to* the address — no public ingress, all clients over Tailscale — but it is
the VM's **sole egress path**. Both alternatives checked live, neither exists:

| Check | Result |
|---|---|
| `gcloud compute routers list` | **0 items** — no Cloud NAT |
| `metatron-subnet` `privateIpGoogleAccess` | **False** |

Deleting the access config would have cut Vertex AI (the entire product), the
Tailscale coordination bootstrap that makes the VM reachable at all, `git pull`
on deploy, apt/pip, CalDAV, weather and RSS.

**Pricing verified against the Cloud Billing Catalog API**, not memory. The
published pricing pages are JS-rendered and return nothing to a fetch, so
`cloudbilling.googleapis.com/v1/services/.../skus` was walked with pagination:

| SKU | Rate |
|---|---|
| `External IP Charge on a Standard VM` | **$0.005/hour** |
| `Networking Cloud NAT IP Usage` | **$0.005/hour** |

**Cloud NAT is not a cheaper substitute — it consumes a public IP at the
identical rate**, then adds gateway and per-GB data charges. That is a stronger
result than the "roughly 10×" I first asserted from memory, and it holds on any
usage assumption rather than a guessed volume.

**Two corrections to figures previously stated:**
1. $0.004/hr ≈ $2.92 was wrong (mine, from memory). Catalog rate is $0.005/hr ≈
   **$3.65/mo**. The 2026-07-30 audit's $2.90 was low for the same reason.
2. It accrues **only while the VM runs** — an ephemeral IP is released on stop,
   so a `metatron-pause.sh` window costs nothing.

**The real money is the $24.50 e2-medium line, which pausing already addresses.**

Corrected in three places: DEV_BACKLOG (struck, reasoning kept), SESSION.md
(withdrawn), CLAUDE.md (VM table + a note placed where someone would be tempted
to delete it). Private Google Access is noted as the free first step *if* egress
ever does need to move — it covers Vertex AI only, not GitHub or Tailscale.

---

## `deploy.sh` — ancestry, not equality (`c674a91`)

Four outcomes, deliberately distinct:

| Outcome | Meaning | Exit |
|---|---|---|
| `unverified` | HEAD unreadable | 1 |
| `match` | VM HEAD is exactly the pushed commit | 0 |
| `ahead` | pushed commit is an ancestor — **live**; extra commits named | 0 |
| `failed` | pushed commit absent from history | 1 |

`ahead` succeeds but is not silent — it prints what else is running, because
"something I did not push is also live" is worth knowing before testing against
it. Ancestry and the extra-commit log return in the **same** SSH call, so no
additional round trip.

Verified with `bash -n` and a local harness driving all four branches, rather
than by reading the diff. The real deploy then took `match`.

**Known limitation:** the `ahead` branch is still harness-only. Exercising it for
real needs two windows pushing in sequence, which one window cannot stage. The
logic is a single string comparison, so risk is low — but it has not run against
a live VM, and this log should not imply otherwise.

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
- `deploy.sh`'s `ahead` branch never exercised against a live VM (see above).

## Not to be done

- **Removing the external IP.** Withdrawn, not deferred. If it resurfaces in a
  future session, the answer is in DEV_BACKLOG → housekeeping and in CLAUDE.md's
  VM section; do not re-derive it from the $/mo figure alone, which is what made
  it look attractive twice.
