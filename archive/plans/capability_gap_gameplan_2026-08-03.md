# Capability Gap — Gameplan

*Written 2026-08-03. Addresses [agent_capability_gap_2026-08-02.md](agent_capability_gap_2026-08-02.md).*
*Agent-file freeze lifted entirely 2026-08-02 — all items below may edit `config/agents/*.md` directly.*

---

## Effort scale

| Tag | Means |
|---|---|
| **XS** | under 15 min — single edit, no decisions |
| **S** | 15–60 min — mechanical, some judgement |
| **M** | 1–3 hrs — needs decisions and testing |
| **L** | half day+ — design decisions, new moving parts |

Difficulty is rated separately from time, because some XS items carry real risk (a one-line change to enforcement breaks five agents) and some L items are just long (thirteen files of mechanical edits).

---

## Hard ordering constraints — read before resequencing

Only three things in this plan genuinely cannot move. Everything else is preference.

1. **P0 before everything.** The working tree currently holds two sessions' uncommitted work in `core/orchestrator.py`. Building on that means every subsequent change compounds an unresolved merge. This is the only true blocker.
2. **1.1 (fix the allowlists) strictly before 2.1 (enforce them).** Reversing this breaks Logistics, Finance, Physical Health, Relationships and Recreation *simultaneously and silently* — they currently reach past their lists and it works. **This is the one ordering mistake that would cause an outage.**
3. **3.3 (`write_schedule`) after 2.1 (enforcement)** — preferred, not mandatory. Building a new tool after enforcement is live means it gets an allowlist entry as part of its definition rather than as a forgotten follow-up. If built earlier, the allowlist entry must be added deliberately.

Everything else can be reordered to taste.

---

## P0 — Unblock (must be first)

| # | Item | Effort | Difficulty | Notes |
|---|---|---|---|---|
| 0.1 | Close out the parallel chat (Dev Backlog / Synth self-development), then commit both sessions' work and `./deploy.sh` | **S** | Low | Also deploys the four SEQ 021 fixes, which are validated and waiting. `config/agents/synthesizer.md` is modified by that chat — **collision risk with item 1.5 below**, so 1.5 must come after this. |

**Plain:** two chat windows edited the same file. Get that resolved and shipped before starting anything new, or every later change piles onto an unresolved tangle.

---

## Phase 1 — Make stated capabilities match real ones

*The theme: today the agent files promise things the system doesn't deliver. Nothing here adds capability; it removes lies. Cheap, low-risk, and it's the prerequisite for Phase 2.*

| # | Item | Effort | Difficulty | Depends on |
|---|---|---|---|---|
| 1.1 | **Fix `allowed_tools` across all 13 agents** in `routing_cloud.yaml` + `routing.yaml` | **M** | **Medium — this is the judgement call** | P0 |
| 1.2 | Remove `run_subagent` from the nine specialist files | **S** | Low | — |
| 1.3 | Decide `get_environmental_snapshot`: build wrapper over `tools/ambient.py`, or cut the reference from `physical_health.md` | **XS** (cut) / **S** (build) | Low | — |
| 1.4 | Fix `logistics.md` (and any peer) to describe `write_agent_config`'s real key/value contract | **S** | Low | — |
| 1.5 | Add `[TOOL FAILURES]` handling to `synthesizer.md` — never confirm an action listed there | **XS** | Low | **P0** (file collision) |
| 1.6 | Fix stale path in `WRITE_AGENT_CONFIG_SCHEMA` description (`data/config/` → persona-scoped) | **XS** | Trivial | — |
| 1.7 | Enable CalDAV — Google app password, `enabled: true`, hand-copy to VM | **S** | **Medium — external unknown** | — |

**Notes on the two that aren't routine:**

**1.1 is the real work of Phase 1.** The editing is trivial; deciding *what each agent should legitimately have* is not. Thirteen agents, and the current lists are demonstrably wrong in both directions — Logistics names 8 tools it isn't granted. Recommended approach: derive each list from what the agent file actually instructs, not from first principles, then reconcile. Budget the full M.

**1.7 has an external dependency and a real failure mode.** Needs 2FA on the Google account to generate an app password, and Google's CalDAV endpoint is not guaranteed to work with the URL already sitting in `config/personas/mike/caldav.yaml`. Test read *and* write before declaring it done. The file is gitignored, so `deploy.sh` will not carry it — hand-copy via `gcloud compute scp`. **This is the cheapest route to a reminder that actually fires**, which is why it sits in Phase 1 rather than Phase 3 despite belonging to Finding 3.

---

## Phase 2 — Enforce

| # | Item | Effort | Difficulty | Depends on |
|---|---|---|---|---|
| 2.1 | Enforce the whitelist in `dispatch_tool()` — reject a call to a tool not on the calling agent's list | **XS** to write, **M** to verify | **High risk, low complexity** | **1.1 — hard gate** |

**The asymmetry to understand:** the code change is about five lines — pass the agent's allowed set into `dispatch_tool()` and check `name` against it. The *testing* is the work, because this is the first time the permission list will actually do anything. Every agent needs exercising afterwards.

**Plain:** this is installing the real lock. Quick to fit, but you must be certain the right names are on the list first — which is why 1.1 is a hard gate, not a preference.

This is roadmap **Track B / B2 (principle of least privilege)**, so it's already on the plan; this sequences it correctly relative to the config fixes.

**Recommended regression gate** (mirrors the A8 refactor gate): A4 clinical-flag scenarios, server startup, one full multi-specialist pipeline session, and The Book SSE.

---

## Phase 3 — Build the missing capability

*The theme: Finding 3. Today a reminder can be recorded but never delivered.*

| # | Item | Effort | Difficulty | Depends on |
|---|---|---|---|---|
| 3.1 | Grant Logistics `read_agent_config` / `write_agent_config` | **XS** | Trivial | folds into 1.1 |
| 3.2 | Verify end-to-end: ask for a reminder, confirm it lands in the calendar | **S** | Low | 1.7 |
| 3.3 | **`write_schedule` / `list_schedules` / `delete_schedule`** | **L** | **High — design decisions** | 2.1 preferred |
| 3.4 | Store and honour delivery preference (calendar alert vs in-chat) | **S** | Low | 3.3 |

**3.3 is the only genuinely large item in this plan, and it carries three unresolved decisions:**

1. **Where do agent-written jobs live?** Writing into `config/personas/{p}/scheduler.yaml` puts machine edits into a hand-maintained file — one bad write and your morning brief is gone. Recommend a **separate agent-owned job file** that the daemon merges, so the two can never collide.
2. **How does the daemon notice a change?** It currently reads config at start, and the `schedule` library computes `next_run` once at registration. There is already DST-change detection in the main loop that re-registers jobs — **that's the hook to build on**, rather than inventing a new reload path.
3. **One-off vs recurring.** "Remind me on the 15th of every month" is recurring; "remind me on Thursday" is one-off and needs cleanup after firing.

**Plain:** this is the piece that makes Logistics able to keep its promises. It's a day's work, not an afternoon, and most of that is deciding how agent-written reminders coexist with your hand-written schedule without either clobbering the other.

---

## Recommended sequence

```
P0  ── commit + deploy (unblocks everything)
      │
      ├─ 1.7 CalDAV enable ─────────► 3.2 verify reminder works   ← fastest path to value
      │
      ├─ 1.2, 1.3, 1.4, 1.5, 1.6 ──► cleanup, parallelisable, low risk
      │
      └─ 1.1 allowlists ───────────► 2.1 enforce ────► 3.3 write_schedule ──► 3.4
                                     ▲ HARD GATE
```

**If you want one working reminder as soon as possible:** P0 → 1.7 → 3.2. That is an S and an S, plus the deploy — realistically an afternoon, and it covers the credit-card case specifically.

**If you want the system to stop lying about what it can do:** P0 → 1.2/1.4/1.5/1.6 (all XS–S) → 1.1 → 2.1.

**Total if run end to end:** roughly 1.5–2 days of focused work, dominated by 1.1 (M), 2.1's verification (M) and 3.3 (L). Everything else sums to well under half a day.

---

## Deliberately not in scope

- **A8 pre-Alpha refactor.** It will relocate `dispatch_tool()` to `core/tools.py`, which item 2.1 touches. A8 is gated on A7 (blocked), so it isn't imminent — but if A7 unblocks mid-plan, do 2.1 first or expect to redo it.
- **`[background] index log … Extra data`** — open from SEQ 021, unexamined, unrelated to capability.
- **Pre-2026 logs** in `data/personas/mike/logs/` — worth a glance, not part of this.
