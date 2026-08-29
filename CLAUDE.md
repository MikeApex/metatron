# Personal AI Life Manager — Developer Context

This file is loaded into every Claude Code session. It describes the project architecture, conventions, and key design principles for the developer (Claude Code). It is NOT the runtime system — that is `core/orchestrator.py`.

> **Ceiling: 300 lines** — a hard limit with deliberate headroom (Mike, 2026-08-14), set when the
> always-on tier was split (810 lines on 08-13, 554 before the split; 279 after). Anthropic's
> stated target is 200; this file's binding keep-list does not fit under it, and a ceiling the
> file permanently violates trains you to ignore the warning. Length does not merely cost more:
> the documented effect is **reduced adherence to the rules already here**, which made this file
> a plausible cause of the under-surveyed edits it was written to prevent. The headroom is for
> recording a new binding rule — not for letting area detail drift back in.
>
> **Nothing was deleted in that split — it moved to `.claude/rules/` with its rationale intact.**
> Before adding here, ask: *is this binding-everywhere, or area-specific?* Area-specific goes to
> the rule file for the area (index below). Only what must survive `/compact` belongs here —
> path-scoped rules are **not** re-injected after compaction; root `CLAUDE.md` is.

---

## What This Project Is

A voice-first personal AI life manager. A director and companion for a human life, not a scheduler or task manager. Built on a thin Python harness with all behavior living in editable config files.

**Core principle:** Config files are the product. Code is infrastructure. If changing behavior requires a code change, that is a design failure.

---

## Mandatory Pre-Edit Context Check

No code, config, or agent-file edit happens in a session until that session has actually read:

1. **`SESSION.md`** — current phase, what's in progress, what's blocked or frozen.
2. **The active roadmap it points to** — currently [`ROADMAP.md`](ROADMAP.md), the abridged live copy: phase gates, freeze states, hard-fail criteria, scheduled refactors. If your work is in an area `ROADMAP.md` states it does not carry, read that area in the full static plan before editing.
3. **Any file-ownership rules in effect** (e.g. `archive/plans/parallel_chats_index_*.md`) — which files are frozen, which track owns them, what "propose, don't edit" applies to.
4. **The current state of the specific file(s) about to be touched** — not a memory of what they contained earlier in this conversation or a prior one.

This applies even to small, well-intentioned additions made in service of a good design
discussion. If `SESSION.md` or the roadmap doesn't clearly resolve whether a file is safe to
edit right now, ask before editing — don't infer permission from the fact that the conversation
reached an implementation-shaped request. **Area-specific cautions — the lifted agent-file
freeze, the `core/orchestrator.py` refactor claim, the domains with named hard-fail criteria —
are in the rule file for each area** and arrive when you read one of its files.

> **This check is now also enforced mechanically.** `scripts/hook_context_gate.py`
> (`PreToolUse` on `Write|Edit`) briefs you on the file you are about to change — its tier,
> governing rule file, open backlog items, recent commits and `archive/log/` decision history —
> **once per file**, and still warns once per session when `SESSION.md`/`ROADMAP.md` are
> unread. It **warns, never blocks**: refusing an edit to enforce a reading habit would
> discard work the user asked for, which is the worse failure. It resolves the repo root
> from the *target path*, so worktree edits are covered — they silently were not until
> 2026-08-14. The prose above is still the rule; the hook is what stops it being skimmed past.

---

## The rules index — what you have not been shown

**This is the map of the context system. Read it as a list of what exists, not what applies.**

Area rules live in `.claude/rules/`. Each declares the paths it governs and is delivered
automatically the moment this session **reads** a file in that area — including during
exploration and planning, which is strictly earlier than the first edit. You do not have to
fetch them, and they cost nothing in sessions that never touch the area.

| Rule file | Governs | Carries |
|---|---|---|
| [`.claude/rules/agent-files.md`](.claude/rules/agent-files.md) | `config/agents/**`, `config/modules/routing*.yaml` | a named tool is a specification; One Home Per Rule Class; the freeze that was lifted; the allowlist trap |
| [`.claude/rules/personas.md`](.claude/rules/personas.md) | `config/personas/**`, `core/persona.py` | the VM owns live persona config; fail-closed identity resolution |
| [`.claude/rules/orchestrator.md`](.claude/rules/orchestrator.md) | `core/**`, `tools/**` | security architecture; the A8 refactor claim; privacy enforced in Python |
| [`.claude/rules/deploy.md`](.claude/rules/deploy.md) | `scripts/**`, `deploy.sh`, `.claude/settings.json` | the four deploy rules bought with incidents; how to probe a permission rule |
| [`.claude/rules/docs-and-logs.md`](.claude/rules/docs-and-logs.md) | `SESSION.md`, `DEV_BACKLOG.md`, `archive/**`, `docs/**`, `.claude/commands/**` | which file holds what; append-vs-replace; ceilings; where a new lesson goes |

**Two limits worth knowing, because they are when the map matters more than the territory.**

1. **High-level structural work may never open a governed file**, so no rule fires. If you are
   doing architecture, refactor planning or cross-cutting review, read the relevant rule file
   deliberately — one tool call. Knowing what you have *not* been shown is what prevents the
   confident wrong decision.
2. **`/compact` drops path-scoped rules and does not re-inject them.** They reload the next time
   a matching file is read. This index survives, because root `CLAUDE.md` is re-injected — so
   after a compaction, treat the rules as absent until you re-read one.

A second, later net catches what both miss: `scripts/hook_context_gate.py` briefs you at the
moment of a `Write`/`Edit` with that specific file's tier, governing rule file, open backlog
items, commits and `archive/log/` history. Rules arrive when you walk into the room; the
briefing taps you on the shoulder as you pick up the pen.

→ Which command to fire and when: [docs/WORKFLOW.md](docs/WORKFLOW.md).

---

## Change tiers — what needs Mike's approval

**`.claude/settings.json` is the authority, not this table.** It is machine-enforced; a second
copy here would go stale and the stale copy would keep being read. Read it there. In summary:

| Tier | Roughly | Behaviour |
|---|---|---|
| **Green / Amber** | `tests/`, `scripts/`, `docs/`, `tools/`, most of `core/` | applied without a prompt |
| **Red** | `config/agents/*.md`, `routing*.yaml`, `core/{router,persona,scheduler,spend_guard}.py`, `git push` | prompts every time — **except `git push`, see below** |
| **Denied** | `config/constitution.md`, `config/personas/mike*`, `data/personas/**`, `.env`, `vertex-key.json`, **`./deploy.sh`** | blocked; must be lifted explicitly |

> **`ask` is honoured for `Edit` rules here and ignored for `Bash` ones** (measured in both
> harnesses by hand, 2026-08-14). The split is by **tool family**, not by whether a session is
> interactive. So the Red row's file-editing rules genuinely prompt; `git push` does not, and
> runs silently. `deny` is enforced for both families. **`./deploy.sh` is therefore Denied**
> (Mike's decision, 2026-08-14) — it was the only ungated irreversible action.
>
> **Anything that must never happen unattended belongs in the Denied row.** Rule probing, `git push`'s
> inert Red, and the **plan-scoped deny lift** (2026-08-29 — a Denied `Edit`, only during an approved
> plan, only by asking Mike, never constitution/`.env`/keys/`deploy.sh`): [`.claude/rules/deploy.md`](.claude/rules/deploy.md).

The Denied row turns two standing prose rules into mechanism: the constitution is Tier 0, and
**the VM owns live persona config** ([`.claude/rules/personas.md`](.claude/rules/personas.md)).
Red is also the line for *who builds*: Red-tier work is not delegated to a subagent, because
there the judgement is the work.

> **Nothing about this project leaves this machine without Mike saying so first (2026-08-18).**
> `Artifact`, `WebFetch` and `WebSearch` are **Denied**. A session published a full backlog
> inventory — carrying a real family member's first name — to a claude.ai-hosted page, proactively
> and unasked. **"Starts private" is not "stays on the machine":** an artifact is
> access-controlled on third-party infrastructure, which is the precise distinction § Section 0's
> privacy ruling turns on. Worse, **no tool available here can delete one** — the contents can be
> overwritten, the URL cannot be withdrawn except by Mike from claude.ai. An irreversible outbound
> action taken on a default is why this is a deny and not an ask.
>
> **To produce a shareable document, write a file** — `archive/plans/` is the convention. Lift
> this per-occasion if Mike asks for a published page; never to make a task more convenient.

---

## Terminology

Use precise names. Avoid pronouns and generic terms.

| Term | Meaning |
|---|---|
| **Claude Code** | The development interface — the CLI/IDE tool used to build this project. Not the runtime. |
| **Orchestrator** | `core/orchestrator.py` — the runtime brain. Loads config, calls a model API, dispatches tools. |
| **[Model name]** | The specific AI model called at runtime. Always by name: Sonnet 4.6, Haiku 4.5, qwen3:14b, gemini-2.5-flash, gpt-4o. Never "Claude" as a generic runtime label. |
| **[Agent name]** | The instruction file loaded for a session. Always by name: Time Director, Goals Interviewer, Diarist. Not "the agent" generically. |
| **Anthropic / OpenAI / Gemini API** | Cloud APIs for those vendors' models. Name the API, not "the cloud". |
| **Ollama** | Local model server at `localhost:11434`. Runs models like qwen3:14b locally. |

The `--provider` flag in the Orchestrator CLI is a code-level routing argument. In documentation and comments, name the specific API or model instead.

**A backlog id is an index, not a description — never write one bare.** Lead with the problem in
plain language, then the `[DB-XXXX-XX]` id: *"specialists claim an email was sent that never was
`[DB-0810-13]`"*, not *"`[DB-0810-13]`, ease 2, Red tier"*. Applies everywhere the id appears —
ordinary chat, triage tables, cluster plans, close-outs. A bare code makes Mike look the item up
before he can judge it, and in a ten-item table that cost lands ten times.

---

## Four-Tier Goal Hierarchy

| Tier | File | Owned by | Changes |
|---|---|---|---|
| 0 — Tool Constitution | `config/constitution.md` | The tool | Never — shared by every persona |
| 1 — Prime Directive | `config/personas/{persona}/prime_directive.md` | User | Rarely |
| 2 — Mission | `config/personas/{persona}/mission.md` | User | At life transitions |
| 3 — Goals | `config/personas/{persona}/goals.yaml` | User | Frequently |

Tiers 1–3 are per-persona. There is no root-level fallback; identity resolution is fail-closed
and the VM owns the live copies — [`.claude/rules/personas.md`](.claude/rules/personas.md).

Always load in this order. The Constitution is the root context for every agent.

---

## Data Privacy Tiers

| Tier | Examples | Storage | Analysis |
|---|---|---|---|
| Open | Research, general queries with no personal context | Cloud OK | Cloud LLM |
| Sensitive | All goal data (`private_why`, `shareable_what`), activity logs, health, finances, prime directive, mission | Local only | Local LLM only |

The semi-sensitive tier has been collapsed into sensitive. Empirical testing showed that `shareable_what` (instrumental goals) carries sufficient inferential signal to reconstruct `private_why` when combined with behavioral patterns — the privacy boundary between them does not hold in practice. All personal context is now sensitive-tier by default.

Cloud LLMs are used only for fully decontextualized tasks: generic research, writing, or advice with no personal context attached. Enforce at the tool layer, not in prompts.

---

## Design Principles

**Discretion between layers.** Users see output, not process. When building agents, interviews, or inter-model features: the methodology is infrastructure. Never surface which model was called, which framework shaped a question, or how a recommendation was derived — unless that transparency is an explicit design goal of the feature. This applies to agent config files, tool implementations, and orchestrator routing alike.

**Privacy between layers.** Sensitive data routing (local vs. cloud LLMs) is enforced in Python tool code and is never narrated, leaked across agents, or exposed in user-facing output. Agents must not reference their own model identity, data tier, or routing decisions in responses. The system enforces privacy silently.

**The tool surfaces hypotheses, not verdicts.** Interviews, check-ins, and audits produce a working hypothesis about who the user is and what they want — a first draft that gets verified or falsified through daily use and regular re-interviews. Build features with this in mind: output should invite correction, not foreclose it. This framing is internal to the development context and is never surfaced to users.

See `config/constitution.md` for the runtime expression of these principles. *(A companion
config/frameworks.md — unbackticked deliberately, so `scripts/check_claude_md_claims.py` does not
read it as a live path — is **planned, not present**, and has never existed. Do not send a session
to read it; re-add the backticks in the commit that creates it.)*

---

## Coding Conventions

- Python 3.11+
- No frameworks beyond what's needed (FastAPI for server, FAISS for memory, anthropic SDK)
- Flat, readable functions — no premature abstraction
- Type hints on all public functions
- Config files: Markdown for narrative content, YAML for structured settings, JSON for data records
- All sensitive data paths must be enforced in Python tool code, never in prompts

→ Adding a module, the tool schema pattern, model-ID maintenance, phase review and testing
conventions, generated-file naming: [docs/CONVENTIONS.md](docs/CONVENTIONS.md).

### Deploy safety

Four rules bought with real incidents, each with its incident:
[`.claude/rules/deploy.md`](.claude/rules/deploy.md), which fires on anything under `scripts/`.
One is repeated here because it binds **any** session that commits, including one that never
opens a script: **`git diff` every file before you stage it** — staging by filename does not
protect you from another session's lines inside that file, and two chats often run against this
one working tree.

---

## Infrastructure traps

**The seven things that fail *silently* if you don't already know them.** Everything else about
deploy, the VM, Vertex, Tailscale, systemd, billing, env vars, the APK and local dev is in
[docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) — that material fails *loudly*, so you notice
the moment you need it and go find it. These do not.

1. **The VM's external IP looks removable and is not.** Nothing connects *to* it — every client
   arrives over Tailscale — so it reads as dead weight worth deleting for ~$3.65/mo. It is also
   the VM's **sole egress path**: there is no Cloud NAT on `metatron-net` and
   `metatron-subnet` has `privateIpGoogleAccess: False`, so deleting it cuts off Vertex AI, the
   Tailscale bootstrap, `git pull` on deploy, apt/pip and every outbound integration. Cloud NAT
   is not a cheaper substitute — same $0.005/hour plus gateway and per-GB charges. **This was
   recommended as a saving once and was wrong.**
2. **Do not record values with a short half-life.** The external IP reassigns on every
   stop/start. It was written into four places with three different values, none wrong when
   written, and the live value was a fourth. Look it up; don't store it.
3. **A hard-cap billing trip is an outage, not a cost event.** Disabling billing freezes the
   project VPC, and GCE's asynchronous thaw cannot be relied on — it once gave 25+ hours of
   `nic0 is frozen` and a 26-hour outage that ended only by building a new VPC.
   **Thresholds live in `docs/INFRASTRUCTURE.md` § Billing protection — never quote them from
   memory.**
4. **Relink billing *before* writing an override.** The marker lives in a bucket inside the
   project being disabled, so writing it while billing is off fails `403`.
5. **`--persona mike` on both systemd units is load-bearing.** Without it the scheduler resolves
   no persona and writes to the global `data/` tree while the server writes to
   `data/personas/mike/`, splitting the user's history in two.
6. **Vertex will not create a cache below 4,096 tokens, and fails silently when you cross that
   floor.** The 2026-06-24 token-reduction work shrank the Coordinator/Synthesizer prompts under
   it, so every cache attempt failed and every call ran uncached — for a month, with no error.
   `_pad_for_vertex_cache()` absorbs the gap now. **Any future prompt-shrinking pass on
   `coordinator` or `synthesizer`** — the only two agents on the cached path — must re-check
   that real prompt sizes stay clear of the floor.
7. **Tailscale DNS can come up unhealthy after a VM resume**, silently blocking *all* outbound
   DNS, not just tailnet. Symptom: `NameResolutionError` on Google APIs while the metadata
   server is reachable. Check `sudo tailscale status`; fix with
   `sudo tailscale set --accept-dns=false`.

Two more that are one line each: `DEPLOYMENT_MODE=cloud` in `.env` selects
`routing_cloud.yaml` (absent or `local` selects `routing.yaml`), and all `mike` integrations use
the purpose-built account **`diamond.mike.mt@gmail.com`**, not the owner's personal address.

---

## Chat Archiving

**Run `/archive`** — five steps in `.claude/commands/archive.md`, executed rather than remembered.
Two rules to carry, because they apply to every session regardless of what it worked on:

> **`archive/PROJECT_LOG.md` is appended. `SESSION.md` is replaced.** Detail goes in the log;
> only current state stays in the primer. And `PROJECT_LOG.md` is **generated** from
> `archive/log/` fragments — write a fragment, never edit the log.

Transcripts: `~/.claude/tools/archive_chats.py`, run mid-session at the trigger points, and
**never reported as partial**. The rest:
[`.claude/rules/docs-and-logs.md`](.claude/rules/docs-and-logs.md).

---

## Key Design Decisions (don't revisit without good reason)

**This is the only list of these.** `SESSION.md` carried a second one under an almost
identical heading until 2026-08-03; the two had different contents, so whichever you found
first looked like the whole set. Both are merged here.

> **Decision-level statements never name a model provider.** This list said *"Orchestrator
> calls Claude API directly"* long after the runtime moved to Vertex Gemini — and rewriting it
> to say "Vertex" would go stale again the moment routing moves back to self-hosted, which is
> the stated North Star. Providers belong in `config/modules/routing*.yaml`, which is the only
> copy the running system reads. This is the standing *"don't write down values with a short
> half-life"* rule applied one layer up, to decisions.

- **The Orchestrator calls a model API directly** — it does not spawn Claude Code sessions at runtime. Which provider answers is a routing-config choice, not an architectural one.
- **Tools are plain Python functions** registered as tool schemas — no separate MCP server processes at runtime.
- Scheduler daemon invokes orchestrator sessions; the orchestrator itself is stateless between sessions.
- FAISS for memory — prevents context window limits from degrading long-term recall.
- Config files are the product; code is infrastructure. Behaviour changes are config edits.
- **Sensitive data never reaches shared cloud infrastructure — fail-closed, no fallbacks (binding ruling 2026-06-10).** Head layer and all personal-data specialists run local. Ollama down = hard error, never a cloud call. **Amendment 2026-06-18:** a dedicated VM with verified Zero Data Retention (e.g. Vertex AI ZDR) is acceptable during testing — contractual sequestration is a distinct threat model from shared cloud. North star remains architectural security on private hardware; **the VM path is explicitly temporary.** **Clarification 2026-08-09:** that amendment is the project-wide default for the single-user development phase, not a per-feature exception — new sensitive paths on the ZDR VM (e.g. correspondence-derived tone extraction) need no separate ruling. Fail-closed, the north star and the expiry condition are unchanged, and the clarification additionally lapses if the deployment stops being single-user. Full text: `ROADMAP.md` § Section 0.
- **Archive-on-merge:** data is never deleted — it is moved to archive with a `merged_into` pointer.
- `age` encryption in Phase 6 — not before real sensitive data accumulates. Until then, file permissions (`600`) are the protection.
