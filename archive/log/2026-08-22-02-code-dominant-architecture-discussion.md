### 2026-08-22 (Code-dominant architecture — the "built backwards?" discussion)

Design discussion only — no code, no config, no commits beyond this close-out. Mike opened the
question anticipating the v1/alpha refactor: Metatron today is detailed agents on little code,
and the symptoms (repetitive, off-topic, information-flooded responses) prompted the question of
whether it was built backwards — whether goals should be mapped **procedurally in code, with
models as discrete judgment gates**, complex agents like the Synthesizer excepted.

The exhibit was a two-round Opus chat (outside Claude Code): a day-one personal assistant
handling a barbecue-RSVP email. Round one produced a tactical filter (default-attend absent
blockers); Mike's critique — no life goals, no opportunity cost — produced round two, where the
spine inverts to intent-before-feasibility with a portfolio view and a standing allocation
policy. Mike's framing: models have innate inertia toward the reactive.

Claude's position, given as a recommendation: **yes to the inversion.** The transcript's quality
came from enforced ordering, which prose instruction files cannot enforce (procedure in prose is
re-decided every turn — cf. the D2 judgement-consistency variance note); the "compass layer"
requires standing computed state no per-turn prompt can supply; and the incident log has been
voting this way all year (privacy in Python, `filter_output`, the CRM confirm gate, `tone_shape`
schema removal, intake's Python classification). The founding principle "config is the product"
is preserved by splitting: code owns control flow/validation/retrieval/computed state; config
owns gate prompts, thresholds, allocation policy, and voice — but the Key Design Decisions list
must be amended explicitly if this proceeds. Named risks: serial-gate latency (coordinator's
existing blocker), long-tail brittleness (mitigated by falling back to the current agent path).

Recommendations: (1) invert, Synthesizer stays an agent, Coordinator first to become mostly
code; (2) **decide before A8 executes** or pay for A8 twice; (3) pilot the invitation/RSVP flow
rather than deciding wholesale; (4) build the compass layer regardless. Open with Mike:
ask-vs-decide-with-default at thin-evidence gates. **No decision was made** — this feeds the
queued `@session` decision "where code should replace model judgment".

Consultable record: `archive/plans/code_vs_agent_architecture_2026-08-22_discussion.md`.
Rejected framing, for the record: "the project was built backwards" — the fat-agent phase is
what discovered the procedures now worth crystallizing; the agent files are requirements
documents, not waste.

Outgoing SESSION.md handoff (carried): ZDR opt-out obtainable, form + § Section 0 ruling with
Mike; parallel window mid-build on the Vertex cache fix; intake dark until Mike's VM edits; caps
temporarily $150/$250; `[DB-0820-05]` next; `175809e` owes an inert deploy.
