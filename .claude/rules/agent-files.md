---
paths:
  - "config/agents/**"
  - "config/modules/routing*.yaml"
  - "config/modules/routing*.yml"
---

# Agent files and tool grants

Relocated from `CLAUDE.md` on 2026-08-14, in full. These rules cost nothing until a
session opens an agent file or a routing file, which is exactly when they apply.

**The freeze on `config/agents/*.md` was LIFTED ENTIRELY on 2026-08-02** by explicit user
decision, during the SEQ 021 capability-gap review. They are ordinary editable config — no
"propose, don't edit" step, no per-bug exception needed. This supersedes rule 3 of
`archive/plans/parallel_chats_index_2026-06-11.md`, which is historical on this point. The
freeze had been worked around by explicit exception in three consecutive sessions (SEQ 008,
SEQ 002, SEQ 021), which was the reason for lifting it. Normal care still applies: these
files are the product, they are token-sensitive (keep additions short — see the SEQ 002
precedent), and clinical-safety instructions in `mental_wellbeing.md` have named hard-fail
criteria in the roadmap.

---

## A tool named in an agent file is a specification — do not delete it to make a check pass

**Agent files are written ahead of the tools on purpose.** A capability named there before it
exists is the design record: it says what this agent is *for*. So when a tool reference has no
implementation behind it, the order of preference is **build it → grant it → move it to a
deferred section. Deleting the line is the last resort**, and deleting it silently is how a
planned capability disappears with no trace that it was ever wanted. This is the same reading
the project applies to `TOOL_DENIED` events: an agent reaching for a tool it lacks is evidence
of designed intent, not misbehaviour.

What actually went wrong with `web_search` was never the aspiration. It was that the aspiration
sat in **live instruction text** with a mandatory-citation rule attached, so the model could not
tell plan from capability and filled the gap by inventing sources (2026-08-10). **Aspiration is
fine; aspiration the model reads as capability is not.** The fix is to mark it as planned, not
to erase it.

Three states, and each has a different correct response:

| State | Meaning | Do |
|---|---|---|
| Named under a **deferred/backlog/Future** heading | the build queue | nothing — it is working as intended |
| Named in **live instruction text**, not registered | the model reads it as present | build it, or move it under a deferred heading |
| **Granted but never named** | the agent holds a tool it cannot know about | document it, or drop the grant |

That third row is not hypothetical. `logistics` **was** granted `get_weather` in both routing
files on 2026-08-03 while `logistics.md` stopped mentioning weather entirely in the same commit
— and `research_agent.md`, which documented `get_weather` in full, was not granted it. The grant
and the documentation ended up on opposite agents, and nothing noticed for a week. **Fixed
2026-08-10 (`924a66e`); kept as the worked example because it is the rule's evidence, not a live
defect.** Its stale present tense survived in `CLAUDE.md` until 2026-08-14, when it argued a
§10b rehearsal into building a test on a premise four days dead — inside the section warning
that a stale premise argues persuasively for the wrong thing. **A worked example needs a tense
that says whether it is still true.**

**`python3 scripts/check_agent_tools.py`** reports all four classes. Exit 1 only on
live-but-unbuilt. Stdlib plus PyYAML, zero model tokens.

**It runs automatically — you do not have to remember it.** A `PostToolUse` hook in
`.claude/settings.json` fires `scripts/hook_agent_tools.py` after any `Write`/`Edit` to
`config/agents/*.md` or `config/modules/routing*.yaml`, and surfaces only the two actionable
classes. A rule you have to remember is not a control: the `get_weather` split happened *inside
a single commit* and survived a week because nothing re-checked the two halves against each
other.

**Scoped to what changed, deliberately.** An agent-file edit reports on that agent. A routing
edit reads the uncommitted diff and reports only the agents whose block actually moved. The
unscoped version emitted 37 findings on every grant edit — the volume that teaches you to skip
the output, which is the same reason this guard is deliberately **not** wired into the
quality-event stream or `DEV_BACKLOG.md`.

> **Known limit, so nobody over-trusts a clean report.** Detection is regex over backticked
> `lower_snake_case` names, gated on evidence that a name is a *tool* — a call paren, a leading
> bullet, or an invocation verb — because these files are full of parameter names and JSON keys
> in the same notation. An ungated first version reported 34 field names beside 1 real finding,
> which is the ratio that teaches a reader to skip the report. Four bullet-leading JSON keys
> still slip through. Add to `_NOT_TOOLS` when one does; a clean report is evidence, not proof.

**Fix the tool allowlists *before* enforcing them.** The per-agent whitelist filters
`tool_schemas` but not `tool_handlers`, and `dispatch_tool()` does no whitelist check — so an
agent that is merely *told* about a tool can still call it. Proven live: `logistics` is not
granted `write_agent_config`, called it three times in production, and the dispatcher executed
each. **Every "told-but-not-offered" capability therefore works by accident.** Enforcing
least-privilege without first correcting the allowlists breaks all of them at once, silently.
Correct the lists, verify, then enforce. (Permissions shipped in warn mode 2026-08-03 — that
ordering is why.)

---

## One Home Per Rule Class

Every behavioural instruction lives in exactly one place. This is not tidiness. When the same
rule sits in two files, editing one leaves the other stale, and the stale copy keeps firing —
silently, because nothing reads both.

**Which layer owns what:**

| Layer | Owns | Scope |
|---|---|---|
| `config/agents/*.md` | judgement — what to notice, what to raise, how to weigh evidence, how to speak | every persona |
| `config/personas/{p}/scheduler.yaml` | *when* a proactive session fires, and its opening prompt | one persona |
| `core/scheduler.py` | mechanism only — the gate stack, never content | every persona |
| `config/personas/{p}.md` | this user's personal style preferences | one persona |
| `config/personas/{p}/profile.yaml` | stable facts about who the user is | one persona |

**The rule that gets broken:** a personal preference is generalised upward into an agent file,
and the persona copy is never deleted. On 2026-08-03 five of Mike's preferences — never say
"enjoy", stop repetitive reminders, don't over-weight sleep, only check in when quiet, keep
check-ins brief — sat in **both** `config/personas/mike.md` and `config/agents/synthesizer.md`.
Both were written the same afternoon and nothing noticed.

**So: promotion deletes the original.** When a persona rule is generalised into an agent file or
a scheduler prompt, remove the persona copy in the same pass — after confirming the replacement
is actually live on the VM, not merely committed on the Mac. A persona file may still hold a
*refinement* of a universal rule; if it does, word it so the difference is the only thing it
states.

### Two kinds of preference — ask which one it is

**Mike is currently the only user, so most of what he states as a preference is actually him
authoring the general design.** These read identically at the point of capture and belong in
different layers, so the question has to be asked explicitly rather than inferred:

| | Goes in | Test |
|---|---|---|
| **Design** — how Metatron should behave for anyone | `config/agents/*.md` | Would a second user want this too? |
| **Deviation** — how *this* user differs from that | `config/personas/{p}.md` | Would it be wrong to impose on a second user? |

Default to **design**. A preference filed as a deviation when it was really design is the
expensive direction: it never reaches the agent layer, so every future persona starts without it
and the same instruction gets rediscovered one user at a time — while the copy in the persona
file competes with whatever the agent file says instead. Filing design as a deviation is also
what generated the 2026-08-03 duplicate set above.

Worked example: *"keep check-ins to two sentences"* was captured as a Mike preference. It is
design — nobody wants an unfocused check-in — and once written into `synthesizer.md`
§ Scheduled session conduct as guidance, the persona and scheduler copies had to go (2026-08-09).
What genuinely remains a deviation is narrower and phrased as difference: *don't over-weight
sleep*, *never say "enjoy"*.

When it is unclear, ask. "Is this how you want Metatron to work, or how you want it to work for
you?" is one question and it resolves the layer.

**Three checks, at different speeds:**

1. **Write time** — `write_persona` calls `check_new_rule()` (`core/rule_classes.py`) and appends
   a warning to the tool result when a new preference restates an existing rule. It **warns,
   never blocks**: refusing a write to keep the file tidy would discard something the user
   actually said, which is the worse failure.
2. **Daily** — `daily_rule_audit` (`tools/rule_audit.py`), a `function:` scheduler job costing
   **no model tokens**. Catches what the write-time check cannot see: rules added by hand in a
   development session, which is how the 2026-08-03 set arose. Findings become `RULE_CONFLICT`
   quality events and reach `DEV_BACKLOG.md` through the existing sync. Each is reported once — a
   daily re-report of the same finding trains the reader to ignore it.
3. **On demand** — `python3 scripts/check_rule_overlap.py [--persona NAME]`, the interactive
   sweep for a development session. Run it on the VM to check `mike`, whose files are VM-only.

**Known limits, so nobody over-trusts the output.** Detection is class-based regex plus word
overlap. Recall on the real 2026-08-03 set is 5/5, but the *partner* it names is a starting
point, not a verdict — lexical scores at this scale picked the wrong partner three times in five.
The flagged preference is the reliable part. `CLASSES` in `core/rule_classes.py` is incomplete by
construction; add a class when a duplicate slips through rather than treating a clean report as
proof.
