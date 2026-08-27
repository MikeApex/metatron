### 2026-08-27 (the CRM sweep plan is accepted and filed — deliberately not built) — `archive/plans/crm_sweep_plan_2026-08-27.md`, `DEV_BACKLOG.md`, **not deployed (dev-context only)**

**The planning session the 2026-08-22 handoff asked for ran, and its deliverable is
[`archive/plans/crm_sweep_plan_2026-08-27.md`](../plans/crm_sweep_plan_2026-08-27.md) — accepted
by Mike with an explicit gate: the plan is reviewed with him again before any build session
starts.** Filed as `[DB-0827-03]` (`@waiting` on that review); the build did not start, at his
direction. Session began 08-22, paused, and closed 08-27 — the design was re-verified against
five days of drift before acceptance.

**The design in one line:** nightly bare Flash-Lite extractor (the `intake_extractor` pattern —
empty grant, bare dispatch) over yesterday's conversations + journal → validated proposals into
append-only `crm/proposals.jsonl` → one quiet line in the morning brief (Mike: the first message
must not "jump down the user's throat") → conversational accept → Python applies from the ledger
**by id**, behind a batch confirm tap that is toggleable via config.

**Decisions Mike made in-session:** scope is "anything that can rightly belong in a CRM — facts
from history, and inferences the user can correct — so long as they are reviewed" (both
interaction entries and field fills, additive only, `notes` never a target); review channel is
the morning brief; the apply gate exists but must be switch-off-able.

**Options rejected, with reasons:** reusing WISDOM_PROPOSAL's pipeline — it writes straight into
the live store with no review queue, the exact thing this sweep is forbidden to do (its
Python-parses-relay principle is kept); waiting on `[DB-0818-08]` provenance tiers — the review
step *is* the provenance here (an accepted inference is user-stated, and the ledger row holds
evidence + acceptance for later backfill); proposing merges — even now that `merge_contacts` is
gated and reversible, the sweep stays additive.

**Believed earlier, corrected before acceptance:** the draft carried "merge_contacts ungated, no
unmerge", a `[DB-0822-01]` id collision, and a pending ZDR ruling — all stale by 08-27
(gate + `unmerge_contacts` shipped, ids renumbered and closed as `[DB-0822-03]`/`[DB-0822-04]`,
ZDR refused and ruled). Mike's review instruction to re-check current state caught this drift;
one genuinely new dependency surfaced: `[DB-0827-01]` (declining a confirmation does nothing)
must land before or with the sweep's batch confirm tap.

**Also filed:** `[DB-0827-04]` — field promotion from notes (Mike's 08-19 idea), previously
recorded only inside the planning handoff; gated until notes are rich. Enrichment needed no
filing — `[DB-0826-02]` already holds it. Verified live 08-27 and named in the build plan: two
`tools/crm.py` guards the batch writer needs (`log_interaction` has no dedup; `last_contact`
regresses on a backdated entry).

**Outgoing handoff:** the build is one Opus session after Mike's pre-build review of the plan
doc; `config/agents/crm_sweep.md` and `routing_cloud.yaml` are Red; `./deploy.sh` stays Denied —
hand Mike the commit.
