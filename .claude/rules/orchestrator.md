---
paths:
  - "core/**"
  - "tools/**"
---

# The runtime harness — `core/` and `tools/`

Relocated from `CLAUDE.md` on 2026-08-14, in full.

**Config owns judgement and policy; code owns procedure, evidence and anything a rule can decide
exactly** (D3, Mike, 2026-11-23 — amending the founding "`config/` is the product; a code change for
behaviour is a design failure"). Why: a model asked to count, look up or check what code already
knows does it less reliably and pays a model turn for it — the 11-23 sweep found ~25 such rules
(`archive/plans/agent_instructions_to_code_sweep_2026-11-23.md`). What to value, notice and say
stays in `config/`; a change to *that* still means editing config, not code.

**`core/orchestrator.py` carries active ownership and refactor plans** (the A8 module-split work)
tracked in `ROADMAP.md`. Check whether a pending refactor will relocate the code being touched
before adding to it.

**Domains with named hard-fail criteria** — Finance arithmetic accuracy, Mental Wellbeing clinical
flag firing — have a designated test/validation path in `ROADMAP.md` or `tests/`. New tooling in
those domains goes through that path, not around it.

→ Adding a module, the tool schema pattern, model-ID maintenance: `docs/CONVENTIONS.md`.

---

## Security architecture (Phase 5)

- **Instruction layer:** All agent files include a `## Confidentiality` section with a canned
  refusal response. No agent reveals tools, sub-agents, routing, or system prompt contents.
- **Output filter:** `filter_output()` in `core/orchestrator.py` scans all Coordinator responses
  for leaked tool/agent names before returning to the user. Suppressed responses are replaced with
  the canned fallback and logged as warnings.
- **Frameworks:** OWASP LLM Top 10 (LLM01 Prompt Injection, LLM06 Sensitive Information
  Disclosure, LLM08 Excessive Agency), MITRE ATLAS, NIST AI RMF.

**The tool allowlists are checked but not enforced, and must be corrected before they are.**
`dispatch_tool()` compares each call against the agent's advertised set and records a denial, but
it blocks only when `METATRON_TOOL_PERMISSIONS=enforce`; the default is `warn`, so the call still
runs. Full statement of the trap, with its live evidence:
`.claude/rules/agent-files.md` § A tool named in an agent file is a specification.

### Deferred — build at Deliverable 6 (integrations)

- **Indirect prompt injection defense** is built: `tools/untrusted.py` wraps external content
  (email, web, calendar, intake, attachments) in `<untrusted_content>` tags. A new tool that
  returns external data goes through it.
- **Confused deputy mitigation:** Enforce in the Python orchestrator that sub-agent outputs are
  never parsed as tool calls or commands by other agents. Mental Wellbeing output cannot trigger
  Finance tools.
- **Full OWASP audit** before Beta.

---

## Privacy enforcement lives here, in Python

All sensitive data paths are enforced in Python tool code, **never in prompts**. Sensitive-data
routing (local vs. cloud) is never narrated, leaked across agents, or exposed in user-facing
output. Agents must not reference their own model identity, data tier, or routing decisions in
responses. The system enforces privacy silently.

The binding ruling itself — sensitive data never reaches shared cloud infrastructure, fail-closed,
no fallbacks — is in `CLAUDE.md` and stays there: it constrains every session, not only the ones
editing `core/`.

**Identity resolution** (`core/persona.py`, thread-local, fail-closed) has its own rules in
`.claude/rules/personas.md`, which this path also triggers.
