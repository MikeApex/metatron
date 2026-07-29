# Proposed Constitution Edit — the Development Note

*Written 2026-07-28. **Not applied.** `config/constitution.md` is Tier 0 and is never edited without explicit user instruction.*

---

## What is there now

`config/constitution.md`, lines 34–36:

```markdown
## Development Note

The discretion and layer privacy principles above apply to **production** behavior. During active development, the core user (the person building the tool) has full visibility into reasoning, routing decisions, model selection, and system internals. Nothing is hidden from the developer. This visibility is a development affordance, not a product feature — it will not be exposed to end users at launch.
```

## Why it is worth changing

Three concrete problems.

**1. It asks for behaviour the model cannot determine.** The section makes discretion conditional on "active development" versus "production." Nothing in the runtime tells the model which of those it is in — there is no flag, no context, no signal. So the model decides arbitrarily, differently across turns. This is the same category error as the `## Development Persona` heading that was just removed: an instruction keyed to a distinction the system does not expose.

**2. It contradicts a control that is actually running.** `filter_output()` in `core/orchestrator.py` suppresses any response containing architecture terms and replaces it with a canned refusal. The Constitution simultaneously says "nothing is hidden from the developer." One instruction says disclose, one mechanism says suppress. That tension is not theoretical — it is a plausible contributor to the SEQ 031 incident, where "daily logistics" tripped the filter and the user received *"I can't help with that right now."*

**3. It is now the last place a test/production split lives in the runtime.** The persona work removed that distinction everywhere else: one mechanism, no special cases, every session real. This section reintroduces it at Tier 0, the highest-precedence context every agent loads.

**The load-bearing point:** developer visibility does not come from the model narrating internals. It comes from `core/trace.py` writing routing decisions, model selection, token counts, tool calls and agent outputs to trace files, which The Book reads directly. That record exists regardless of what the model says, and it is strictly more complete than anything the model could self-report. The model has never needed this permission — so removing it costs no visibility at all.

---

## Option A — Delete the section (recommended)

Remove lines 34–36 entirely, leaving the Constitution ending after **On layer privacy**.

**Effect:** discretion and layer privacy become unconditional. The output filter and the Constitution stop contradicting each other. Developer visibility is unchanged, because it was never coming from the model.

**Cost:** the Constitution no longer documents *why* the developer can see internals. If that rationale matters, it belongs in `CLAUDE.md` (developer context), not in the runtime prompt.

---

## Option B — Replace with an unconditional instrumentation note

Substitute lines 34–36 with:

```markdown
## Instrumentation

Everything this tool does is recorded as it happens: routing decisions, model
selection, token counts, tool calls, and agent outputs are written to trace
files. That record is read directly, outside the conversation.

This does not change how the tool speaks. Discretion and layer privacy above are
unconditional — they hold in every session, for every user, at every stage. The
tool never narrates its own architecture to anyone, because it never needs to:
the record already exists and does not depend on the tool describing itself.
```

**Effect:** keeps the fact of full visibility on record, removes the conditional behaviour instruction, and explicitly resolves the conflict with the output filter by naming where visibility actually comes from.

**Cost:** ~70 tokens in every agent's system prompt, for a section that is arguably developer documentation rather than runtime instruction.

---

## Recommendation

**Option A.** The Constitution is runtime instruction loaded into every agent context on every turn; it should contain only things that change how the tool behaves. This section does not change behaviour correctly — it changes it ambiguously. The explanation of why the developer has visibility is developer context, and `CLAUDE.md` is where developer context belongs.

If the rationale should stay on the record, Option B is a reasonable compromise and is strictly better than the current text either way.

## Note on scope

Neither option touches lines 1–30 — the tool's purpose, the relational framing, or the six Operating Principles. The proposal is confined to the Development Note.
