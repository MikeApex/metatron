# Model and Effort Routing — build plan

*2026-09-02. Scope: the development environment only. Runtime model selection
(`config/agents/**`, `config/modules/routing*.yaml`) is explicitly out of scope — Mike, 2026-09-02.*

**Execution model: Opus 5 at `medium`.** Document, settings and rule-file work against a settled
brief; the one genuinely uncertain step (Probe 7a) is mechanical. Matches the standing split —
plan and review in Fable, build in Opus (Mike, 2026-08-18).

**Review model: Fable 5 at `high`.** Required to be a different model than the builder, on two
independent grounds: the project's standing split, and the source document's own § 4.

---

## Where this came from

Mike supplied a *Model and Effort Routing Guidelines* document (Parts 0–2) and asked for
development-environment guidelines. Part 0 of that document was a self-executing brief — five
tasks, multi-repo subagent fan-out, propagate a policy block to all repos, encode agent triples,
write two tripwire hooks. This plan replaces Part 0. Three findings drove the replacement.

**1. Part 0's Task 1 is done, and found nothing.** All three audit patterns were run inline
across the live prompt surface — 20 files in `config/agents/`, both `CLAUDE.md` files,
`.claude/`, `SESSION.md`, and the global `~/.claude/` config:

| Pattern | Hits |
|---|---|
| (a) inherited verification instructions | 0 |
| (b) `content[0].text` / thinking-block reconstruction | 0 |
| (c) `thinking: disabled` paired with `xhigh`/`max` | 0 — the repo never sets `output_config` |

Apparent (a) hits were narrative prose in `archive/PROJECT_LOG.md` and `archive/log/` (history,
not instructions), plus two in `tools/caldav.py:432,619` that write "re-verify no overlap exists"
into a *calendar event description for the user* when a conflict check fails at write time — a
human-facing note about a demonstrated failure. Kept deliberately. No `audit.md` is warranted;
a commit line covers it.

**2. "All repos" is one repo.** Exactly one git repository with a `CLAUDE.md` exists on this
machine. `~/Desktop/chat` (Chorus) is neither a git repo nor carries one. Part 0's per-repo
subagent fan-out (tasks 1 and 3) has nothing to distribute.

**3. Subagent effort cannot be set in this harness.** The `Agent` tool takes a `model` override
(sonnet/opus/haiku/fable) and exposes no effort parameter. Part 0 § 0.4 required this be stated
rather than run silently at the default.

---

## Corrections to the source document

Verified against Anthropic's current API documentation. The document is substantially accurate:
both models' rates, the 1M/128k limits, adaptive thinking on by default, all five effort levels
with `high` as default, `output_config: {"effort": ...}`, the cache and batch modifiers, no
long-context surcharge, thinking billed as output against `max_tokens`, and both § 6.3 breaking
changes — including that with thinking disabled Opus 5 can write a tool call into visible text so
the call silently never runs.

Two corrections were raised; **one was accepted, one was rejected by Mike on the live docs**:

- **Accepted — refusal handling is not a Fable discriminator.** § 5 presented it as a reason to
  prefer Opus 5. Opus 5 carries the same safety classifiers, returns `stop_reason: "refusal"` as
  HTTP 200, and has elevated cyber safeguards. Now a universal rule in § 6.4, with § 5 stating
  explicitly that refusal behaviour does not discriminate, so nobody re-derives the old claim.
  Current handling is `fallbacks: "default"` with beta header `server-side-fallback-2026-07-01`
  (the launch-era `-06-01` is superseded), which routes by refusal category rather than pinning a
  substitute model. **Not available on Bedrock, Vertex or Foundry, and rejected on the Batches
  API** — anything on the VM's Vertex path needs the SDK's client-side middleware instead.
- **Rejected — the § 6.1 cache claim stands.** The invalidation table has an explicit effort row:
  changing `output_config.effort` always invalidates message blocks. The bundled copy consulted
  during verification omits that row; the live docs win. Two exemptions came out of reading it
  properly, and § 6.1 is now narrower than either original: setting effort explicitly to the
  model's default is equivalent to omitting it and does not invalidate; and on models supporting
  per-message effort, an effort change carried in a `role: "system"` message inside `messages`
  leaves the cached prefix intact. The pre-warm trap was added — a warm-up at a different effort
  writes an entry the traffic never reads.

**Five omissions to add**, all material to a cost policy: Sonnet 5 is $3/$15 and Haiku 4.5 is
$1/$5 with a 200k window, not 1M (the routing table recommends Sonnet 5 for subagents and never
prices it); Opus 5's prompt-cache minimum is **512 tokens**, down from 1024; Opus 5 draws on a
**separate rate-limit bucket** from the Opus 4.x pool; **Priority Tier excludes Opus 5**; and
Fable 5 **requires 30-day retention and is unavailable under ZDR** — every request 400s otherwise.

**Two Claude Code settings keys to add**, both surfaced from the settings schema:
`switchModelsOnFlag` (auto-switch model when safeguards flag a message — the harness analog of the
refusal fallback) and `availableModels` (an allowlist, which is how a routing policy could be
*enforced* rather than recommended).

**Verified, previously unverifiable:** the § 3 Ultracode claim. The `ultracode` settings key reads
"xhigh effort plus standing dynamic-workflow orchestration, session-scoped," matching the document.

**Unverifiable, and it must be labelled as such.** No benchmark figure in the document can be
checked from this machine: CursorBench 3.2, FrontierCode 1.1, GDPval-AA v2, the 8×/3× effort
magnitudes, Artificial Analysis 61-vs-60, the 100M-vs-63M verbosity figure, both launch dates, and
Fable's January 2026 cutoff. `WebSearch`/`WebFetch` are Denied on this project. That makes § 8's
"measure cost per unit from your own telemetry" the only available path, not optional advice — and
§ 9's warning about models lacking self-knowledge applies to the document itself.

---

## What the harness can and cannot do

Settled from the settings schema, and it constrains the design more than the brief assumed.

**A hook cannot change the session's model or effort.** The complete hook output surface is
`systemMessage`, `continue`, `stopReason`, `suppressOutput`, `decision`, `reason`, and
`hookSpecificOutput` (`additionalContext`, `permissionDecision`, `permissionDecisionReason`,
`updatedInput`). None sets model or effort. So "when a chat prompt indicates development, the
correct model takes over" **cannot be automatic.** Three-quarters of it is reachable:

1. **Set in advance — genuinely enforced.** `settings.json` carries `model` and `effortLevel`.
   Limit: **`effortLevel` accepts `low`/`medium`/`high`/`xhigh` only, not `max`** — so the routing
   table's "planning at `max`" can never be a persisted default, only a per-session `/effort max`.
2. **Classify at prompt time — advisory only.** A `UserPromptSubmit` hook can read the opening
   prompt and return `additionalContext` + `systemMessage`, naming the model, the effort, and the
   exact command. It cannot press the key.
3. **Spawned agents — possibly enforced.** `PreToolUse` on `Agent` can return
   `hookSpecificOutput.updatedInput`, rewriting the spawn's `model`. **Unproven here — see 7a.**

---

## Tasks

| # | Task | Touches | Tier |
|---|---|---|---|
| 1 | Write the corrected document to `~/.claude/model_routing_policy_2026-09-02.md`: both corrections, the five omissions, the two settings keys, every benchmark figure labelled unverified-on-this-machine, re-check date 2026-12-01 | new file | — |
| 2 | Add `## Model and Effort Routing` to `~/.claude/CLAUDE.md` — the binding lines only, pointing at the task-1 document | global CLAUDE.md | — |
| 3 | Move the model-recommendation lines out of `## Plan Mode` into that section, so net growth stays near zero and model choice has one home | global CLAUDE.md | — |
| 4 | Set `effortLevel` in `.claude/settings.json` | project settings | Amber |
| 5 | **Probe 7a** — determine whether `updatedInput` is honoured for the `Agent` matcher | throwaway | Amber |
| 6 | Extend `scripts/hook_agent_spawn.py`: correct a spawn's `model` against the table (if 5 passes) or warn (if it fails); add the per-session spawn-count warning | existing hook | Amber |
| 7 | New `scripts/hook_route_advisor.py` — `UserPromptSubmit`, fires once per session | new hook | Amber |
| 8 | Record Part 2 § 5's triple schema and the mandate test in a rule file, applied to no files | rule file | Amber |
| 9 | `bash scripts/qa_sweep.sh` after 6 and 7; commit each task separately | — | — |

### Judgement calls settled

**Task 2/3 — why the split.** Both `CLAUDE.md` files are at their ceilings: global 194 against a
~200 target, project **307 against a hard 300**, with a restructure already owed to session ⑦. Most
of Part 1 is reference (rates, the effort ladder, benchmark evidence, escalation criteria) —
consulted when choosing, not needed every turn. What must be resident is short: default to Opus 5;
effort is the spend dial, not model tier; scoped coding at `medium` and resist raising it; planning
at `max`; review with a different model; re-check 2026-12-01. Task 3 supplies the displacement —
model-routing guidance currently lives in *both* `## Plan Mode` and `## Costs`, so a model-choice
rule is found in either place depending on where you look first. Consolidating fixes that.
**The project `CLAUDE.md` is not touched.**

**Task 4 — `effortLevel: "medium"`, and `model` deliberately left unset.** Global settings already
carry `model: opus`; setting it again per-project would create a second home for one value, which
this project's One Home Per Rule Class rule forbids. `medium` is the routing table's workhorse
setting and the level the document says to resist raising on scoped work.

**Task 5 — probe design.** Have the hook rewrite `model` to an **invalid** string on an inert
decoy spawn. Honoured → the spawn errors; ignored → it succeeds. A clean binary signal with no
live effect, per the standing discipline of probing with an inert decoy rather than the real
command. This is not optional caution: `scripts/hook_deny_lift.py` was built on `PreToolUse`
returning `allow`, probed with Mike present on 2026-08-29, and found **completely inert** — the
settings deny wins, and whether the hook's output was overridden or never consulted is
indistinguishable from outside. Same mechanism, same family, unproven twice would be careless.
**If 5 fails, task 6's rewrite degrades to a warning and is worth reconsidering entirely.**

**Task 6 — the agent-count tripwire, corrected.** Part 2 § 3's ceiling is a *design-time* constraint
on the Mark 2 cluster ("adding an agent past the ceiling requires removing one or amending the
architecture document"). No such cluster exists, so nothing in a session can enforce it — that
half defers with task 8. The buildable analog is a different control: a per-session spawn-count
warning. Proposed at **5**, which is Mike's to set.

**Part 2 § 3's other tripwire is not built.** "A conditional that encodes a *preference* rather than
a *fact* belongs to an agent" is a judgement call; a regex approximating it would fire constantly
on the seven existing hooks. It goes in the rule file as a review line.

**Task 8 — why the triples are deferred.** Part 2 § 5 targets a development cluster of Opus
architects, Sonnet builders and Haiku pipeline agents. There is no `.claude/agents/` in this
project or globally; only built-in agent types exist. The 20 files in `config/agents/` are the
runtime system, whose model choice already lives in `config/modules/routing*.yaml` and which the
source document's own scope line excludes. The `mandate` field is a design test, not
documentation — it does real work when the cluster is being designed, and none applied to nothing.
The destination is now concrete: `archive/plans/mark2_endeavour_plan_2026-09-02.md`, which is the
read-first for any rebuild work.

### Standing rule overridden

`.claude/rules/deploy.md` carries, since 2026-08-14: *"No new standing harness script or hook
without naming what it retires, or the build that will retire it."* Tasks 6 and 7 add machinery
and name no retirement. **Mike overrode this manually on 2026-09-02**, recorded here so the rule is
not eroded silently — it remains in force for everything else. Worth noting the plan walked into
the failure the source document warns about in Part 2 § 4: *"any model reviewing a process
recommends adding structure, because additions are easy to justify and deletions require
conviction."* Task 6 folds the spawn-count guard into an existing hook partly for this reason.

---

## Cost budget

- **Build** — one session, Opus 5 at `medium`. Tasks 1–4 and 8 are drafting against a settled
  brief. Tasks 5–7 are a probe plus two small Python edits. Single-digit dollars.
- **Run** — the two hooks fire per session (task 7) and per `Agent` spawn (task 6). Both are local
  Python doing string matching; no model calls, no network, no standing process. Cost is
  milliseconds of latency, not tokens. **Task 7 adds `additionalContext` to the first prompt of
  every session** — a handful of tokens per session, forever, and the only recurring token cost here.
- **Ancillary** — `effortLevel: "medium"` (task 4) changes token volume on every turn in this
  project, in both directions depending on the work. This is the largest cost effect in the plan
  and it is a *behavioural* change, not an infrastructure one. Nothing else creates storage,
  egress, retries, or a slower path.
- **Unseen** — none created. Nothing here persists between calls: no cache, index, warm pool,
  reserved instance, subscription, or scheduled job. Nothing needs an owner or an expiry, and
  nothing survives a restart. **What no meter reports** is whether the routing policy is actually
  followed — the advisory hook recommends and cannot enforce, so adherence is unmeasured by design.
  The `availableModels` allowlist is the only mechanism that would make it enforceable, and it is
  deliberately not proposed here.

**Re-check 2026-12-01, or immediately on any new Opus / Sonnet / Fable release** — carried from the
source document, and § 8's own rule: a routing table with no expiry becomes a table describing
models that no longer exist.

---

## For the adversarial reviewer

Brief to hunt, not to approve. The specific targets:

1. **Task 5's probe design.** Does an invalid model string actually produce a distinguishable
   failure, or could it fail for an unrelated reason and be misread as "honoured"?
2. **Task 2's binding lines.** They must be self-sufficient for the common case, because a
   reference document that is only *pointed at* gets read only when someone remembers to.
3. **Task 3's displacement.** Does moving the model lines out of `## Plan Mode` break the
   plan-budget rule that surrounds them?
4. **`effortLevel: "medium"` as a project default.** The routing table wants `xhigh` for
   long-horizon agentic coding and `max` for planning — sessions here do both. Is a single
   persisted default the wrong shape?
5. **The advisory hook's honest value.** It cannot switch the model. Is a per-session token cost
   forever worth a recommendation both parties can ignore?
6. **What this plan adds that should instead be removed.** Applied to the plan itself.
