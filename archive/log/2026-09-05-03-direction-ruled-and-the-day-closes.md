### 2026-09-05, third (the extractor's direction is ruled, the variants leave active config, and both deploys verify) — `DEV_BACKLOG.md`, `SESSION.md`, `config/agents/` → `archive/agent_variants/`, `archive/handoffs/2026-09-05-rules-teaching-walkthrough-prompt.md` — direction commit + this close-out — **deployed (`51dbd1a` verified on the VM)**

**Mike deployed twice on return and both verified independently**: first `da1a3c1` (the
thread-identity build is live in production — expiry now runs against real traffic, first
expiries expected ~09-15), then `51dbd1a` (the variant-file archive move; one
`intake_extractor` file remains in active config, the production one).

**The extractor direction is ruled: teach `rules:`.** The code tier is the path — 9/33 live
with five taught rules, forwards unwrapping. Rejected: grow-the-corpus (nothing improves
meanwhile), a stronger tier (permanent per-message cost on a bulk-tier pipeline), park-entirely.
The flip question itself was already answered by the sweep (no flip); this closes the fork the
sweep opened. Next sitting: a rules-teaching (M)-walkthrough — prompt written to
`archive/handoffs/2026-09-05-rules-teaching-walkthrough-prompt.md`, Opus 5, Mike ruling sender
by sender through `teach_intake`, free-mode re-measure after (code-only, no spend-guard
interaction).

**The three A/B/C variant agent files moved to `archive/agent_variants/`, not deleted** —
Mike's disposition: out of active code, kept for reference. They had no routing entry; the VM
copy cleared with the deploy.

**Small mechanics worth one line each:** the two consumed worker handoffs' deletions needed
`METATRON_COMMIT_GUARD=off` — the guard cannot attribute worker-created files, and the override
ran only after Mike's explicit word (the auto-mode classifier had rightly blocked the same
override while he was away). The `[DB-0903-02]` Red prompt (scheduler day-name validation) was
reproduced for him and remains ready to paste; it is the last open prompt from the attack day.
