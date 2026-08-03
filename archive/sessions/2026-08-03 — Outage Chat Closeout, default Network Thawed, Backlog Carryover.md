# 2026-08-03 — Outage Chat Closeout: `default` Network Thawed, Backlog Carryover

Closing session of the chat that ran 2026-07-30 → 08-03. The outage and cost-control work is written up separately in [2026-07-31 — Billing Cap Trip, VPC Freeze Recovery, Two-Tier Cost Control.md](2026-07-31%20—%20Billing%20Cap%20Trip,%20VPC%20Freeze%20Recovery,%20Two-Tier%20Cost%20Control.md). This covers only the verification pass and what came out of it.

Commit `48e17da`, pushed. Nothing deployed — documentation only.

---

## `networks/default` has thawed — the outage is fully over

Verified by creating a probe instance on `default`, which came up `RUNNING` on `10.128.0.4`, then deleting it. Google restored the network at some point between 07-31 and 08-03, past their own 3–5 business day estimate but without further intervention.

Consequences:

1. The support case can be closed.
2. **`CLAUDE.md:339` is stale** — still warns *"The `default` network in this project may still be frozen — check before using it."* It now warns future sessions off a network that works. *(User already aware; not fixed here.)*
3. `metatron-vm` stays on `metatron-net`. No reason to move it back, and moving it would mean another rebuild.

---

## Backlog carryover — the two items that were still mine to close

**Unsurfaced opportunities → new entry, `Open — needs building` › *Troubleshooting signal*.**

It had existed only as a line of SESSION.md prose since 2026-07-29 and had never been carried into `DEV_BACKLOG.md`. Once the backlog became the single change-request list on 08-02, that made it the one item at real risk of aging out silently.

The entry records why the obvious approach fails — **you cannot diff against a ground truth nobody wrote down**, so richer tracing does not produce this signal — and three routes:

| Route | Cost | Catches | Limit |
|---|---|---|---|
| Reason code on the `·` feedback dot | ~free, hook already exists | Misses the user notices | Biased sample; misses the worst cases |
| Retrospective sweep | Tokens | Misses the user never saw | Same class of model grades its own output |
| Close the loop on `open_threads` / `follow_ups` | Low | Threads that go quiet unresolved | Narrow, but the only hard signal |

Recommended 1 + 3 together; hold 2 until there is enough history to justify the tokens.

**D2 item 5 → amended, not duplicated.** The backlog entry at `DEV_BACKLOG.md:105` was already correct (Coordinator = 1 turn, `logistics` = 8, re-measured 08-02). What was missing: **the roadmap itself has never been corrected.** `archive/plans/phase5_to_future_roadmap_2026-06-10.md:519` still reads *"6-turn / 88K cumulative token loop"* and still prescribes a `coordinator.md` instruction change — so anyone reading the plan without the backlog gets a fix aimed at the wrong component.

Deliberately did **not** edit the roadmap body. It is a dated plan snapshot; rewriting it would erase what was believed at the time. Whoever works the item should rewrite it from measurement and note the supersession there. The correction is verified twice (07-29 traces, 08-02 re-measurement), so it is not waiting on evidence.

---

## Verified state at close

| | |
|---|---|
| Health | `{"status":"ok"}` over Tailscale |
| Instance | RUNNING on `metatron-net` |
| `networks/default` | **thawed**, probe-tested |
| Budgets | $70 soft / $150 hard |
| Git | local + origin `48e17da`, tree clean |

---

## Outstanding, user-acknowledged

1. `CLAUDE.md:339` stale frozen-network warning
2. `stop-billing` source still not in the repo (`infra/stop-vm/` shows the pattern)
3. APK sideload

**Withdrawn — do not act on it.** The "unused external IP, ~$2.90/mo saving" I recommended on 07-31 and repeated in the 08-03 verification pass is **wrong**, and a parallel window caught it: the IP is unused for *inbound* but is the VM's **only egress path**. There is no Cloud NAT (`routers list` → 0) and Private Google Access is `False`, so removing it would kill Vertex AI, Tailscale bootstrap, deploys and every outbound call. Cloud NAT needs a public IP at the same hourly rate plus gateway and data charges, so it costs strictly more. The real figure is ~$3.65/mo, and it stops accruing while paused.

The error was reasoning from *"nothing connects inbound"* to *"the IP is unused"* without checking egress. Worth remembering as a shape: an unused-looking resource on a working system usually has a load-bearing role nobody wrote down.

---

## Note for next time

The near-loss of the unsurfaced-opportunities item is the transferable lesson: **when a tracking convention changes — here, SESSION.md prose → `DEV_BACKLOG.md` as the single list — items recorded under the old convention do not migrate themselves.** Worth a sweep of SESSION.md prose for other open items that predate 08-02 and were never carried over.
