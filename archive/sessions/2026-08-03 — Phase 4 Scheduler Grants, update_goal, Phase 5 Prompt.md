# 2026-08-03 — Phase 4 Scheduler Grants, `update_goal`, Phase 5 Prompt

Continuation of [Calendar Delivery, Weather Tools, Tool Permissions, VM Backup](2026-08-03%20—%20Calendar%20Delivery,%20Weather%20Tools,%20Tool%20Permissions,%20VM%20Backup.md). That session left Phase 4 one step from complete and the tier-editability inversion found but unfixed. Both are now closed.

**Deployed:** `2f74cd2`, `8e2983f`.

---

## What was built

### Phase 4 — scheduler write access (complete)

`write_schedule` / `list_schedules` / `delete_schedule` granted to Synthesizer and Logistics in both `routing.yaml` and `routing_cloud.yaml`. The tools shipped last session registered and compiling but allowlisted to nobody, so nothing could call them — a deliberate safe resting point, now released.

The previous attempt at this edit silently no-opped because a parallel session added `read_profile`/`write_profile` to the same lines mid-edit and the matched string no longer existed. The rewrite is line-based with an assertion on the line's shape, then a `yaml.safe_load` verification — it cannot fail silently the same way.

Tested before deploying, against `sarah_chen`:

- Every cap refuses with a message naming what to drop — 6 recurring agent jobs, 6h minimum interval, 10 live user-facing reminders. Also verified: both-args, past one-off, missing title, bad horizon, bad action.
- A one-off created **after** the daemon had started was picked up on the next 30s mtime tick, fired exactly once, and removed itself from the file. This is the case that would otherwise fail silently — a reminder set at 09:00 for 10:00 that never arms until the next deploy.
- A name collision between an agent job and the user's own `scheduler.yaml` resolves in the user's favour, with a log line saying so. An agent cannot redefine the morning brief.

`fire_session` was stubbed for the loop test rather than paying for a real pipeline session to prove a 30-second timer.

### Two agent instructions named an impossible action

`synthesizer.md` and `logistics.md` both instructed the model to create recurring reminders with `write_config` — which permits only `prime_directive.md` and `mission.md`. The call returns `Error: not allowed`, which under the old code the user never saw. **This is the SEQ 021 failure shape sitting in the files**, unfired only because nothing had asked for a recurring reminder since. Both now point at `write_schedule`.

`synthesizer.md` additionally claimed *"All tools available to specialist agents are also available to you directly if needed."* False under the per-agent whitelist, and in warn mode it produces a logged denial rather than a refusal the model can act on. Replaced with the true statement: reach a specialist's capability by calling that specialist.

### Tier-editability inversion — closed

The architecture did the opposite of what the user described ("mission and prime directive editable but rarely; goals rewritten in an ongoing manner"). Both directions fixed:

- **`update_goal(action, horizon, goal_id, ...)`** — new in `tools/goals.py`. Adds, updates, completes or removes **one** goal. `write_goals` replaces a whole horizon, so updating one daily goal meant resending the entire daily list and silently deleting anything omitted — unusable for an ongoing add/complete cycle. `complete` sets `status: completed` plus a `completed_on` date and keeps the goal; `remove` is for abandoned or mistaken entries and says so in its own return value. Ids auto-generate per horizon (`q`/`w`/`d` prefix, lowest free number). The goal is located by searching every horizon, so a wrong `horizon` argument corrects itself rather than reporting a goal missing that is plainly there.
- **Granted to the Synthesizer** — the agent that is present when a goal is actually finished or taken on, mid-conversation. Also to `goals_interviewer`, which already holds the stronger tool, so this adds a safer path rather than new authority. `write_goals` stays with the interviewer alone, its schema now stating outright that omission deletes.
- **`write_config` keeps the previous version** before overwriting `prime_directive.md` / `mission.md`. Held by the agent that runs on every exchange, and the write is a full replacement, so an unasked-for rewrite of Tier 1 was unrecoverable. Backup is skipped when content is unchanged and never blocks a write the user did ask for. `config/personas/*/*.bak` added to `.gitignore` — these hold Tier 1–2 content.

Instruction-level guardrail added alongside: *"Never write either without the user having asked for the change in terms they would recognise as a change."*

---

## Findings

1. **The server serves HTTPS, and `CLAUDE.md` said HTTP in five places** — including the recreate-from-scratch checklist and the verification `curl`. Found because a post-deploy health check against `http://localhost:8001` failed. The VM listens on HTTPS 8001 with the publicly trusted Tailscale cert for `metatron-vm.tail0acc5d.ts.net`; `static/index.html` uses that name. Corrected. The `cleartext`/`allowMixedContent` Capacitor flags are leftovers from the HTTP era and are no longer relied on.
2. **Grounded search is not web access.** The user asked whether Google Search grounding covers direct site access and acting on their behalf. It does not, and the three levels are worth keeping distinct: grounded search (built) chooses its own sources and cannot open a named URL; direct fetch (missing) reads a specific page; agentic browsing (missing) acts. The jump from level 2 to level 3 is a risk-class change, not a workload change — at level 2 a hostile page can only *say* things to the model, at level 3 it can cause the model to *do* things with the user's credentials.
3. **An orphan `config/personas/_dedup_check.md`** (leading underscore, fails the persona name regex) was making `check_personas.py` exit non-zero. Nothing referenced it; removed during the session. Now exits 0.

---

## Decisions

- **Phase 2 of the capability-gap plan (agent-file reconciliation) is CLOSED, not done** — user decision. Net removals were already zero, and the remaining question is now answered continuously by the warn-mode denial log rather than in a batch. Marked in [capability_gap_gameplan_2026-08-03.md](../plans/capability_gap_gameplan_2026-08-03.md). Flipping permissions to enforce moves into Phase 5, where it belongs as the E1 gate.
- **Phase 5 starts in a fresh chat**, opening with `/metatron-code`. Prompt written: [phase5_prompt_2026-08-03_security_web_email.md](../plans/phase5_prompt_2026-08-03_security_web_email.md). Order is authentication → enforce → injection defense → `fetch_url` / `read_email` → scoped acting-on-behalf.
- **The user is running live conversations and pushing issues to `DEV_BACKLOG.md`** in parallel with development. The backlog inbox outranks the plan.

---

## Open

- End-to-end test of the scheduler through a real conversation — not done here, because the tools only earn their keep if the model reaches for the right one (calendar for a fixed date, scheduler for a judgement call). That is a live-usage test.
- Location sharing — phone app permission plus calendar-derived inference. GPS agreed sensitive-tier, local-only, coarsened.
- Everything in the Phase 5 prompt.

---

## Process notes

- Parallel-session activity continued throughout: `synthesizer.md` changed on disk mid-edit, a stray `scripts/check_rule_overlap.py` appeared, and the orphan persona fixture vanished between two commands. No damage, but every routing-config edit this session was written to fail loudly rather than match a string.
