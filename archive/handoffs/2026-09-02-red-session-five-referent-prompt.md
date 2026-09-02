# Red session ⑤ — the referent fix (launch prompt, Mike to review before use)

Model: Fable 5. Red-tier judgement work on `config/agents/coordinator.md` and the structural
referent design — the build-in-Opus split does not apply, and Red work is never delegated to a
subagent.

**Budget:** ~2–3h wall-clock with Mike present. Build cost is one supervised session; run cost
is near-zero (the structural fix adds a small code-generated context block per turn — a few
hundred input tokens on the bulk tier, well under $0.01/day); no standing resources created.
Probe re-runs cost pennies (Flash-Lite suite calls).

---

/metatron-code Red session ⑤ — the last Red build of the capstone: **"undo that" resolves to
the wrong thing ([DB-0826-01])**. Mike present. Everything here is already measured and ruled —
this session builds, verifies, and stops.

**What the user sees:** a short referring turn after an action — *"undo that merge"*, *"now set
it back to Iva"*, *"approved"* — is resolved against the wrong referent. Five instances on
record (08-10, 08-15, 08-18, 08-26, and 08-29's declined-email re-proposal), all quoted in the
item.

**The ruled fix path (2026-08-28, probe-measured):** Flash-Lite reproduces the class 6/12 on
`tests/run_coord_model_probe.py` Suite B-hard; Pro sweeps it 12/12 but the flip is declined on
latency. **Fix the Coordinator with structural referent context** (the `tools/turn_context.py`
pattern — the previous turn's action/referent handed to the model as code-generated evidence),
preferred over instruction-only, because Pro's winning move was following a rule
`coordinator.md` already states and Flash-Lite ignores.

Work in order:

1. **Re-run Suite B-hard first** — the fleet moved to `gemini-3.5-flash-lite` on 09-01 and the
   6/12 baseline is from the old model. Get today's number before building against it.
2. **Build the structural referent block** (core/tools code, Amber): the immediately-prior
   turn's action, its object, and its outcome (incl. declined/pending state — the 08-29
   instance resolved to a *declined* email) injected as evidence the Coordinator receives per
   turn. Fail-open on an unbound thread (missing block = today's behaviour, never an error).
3. **Any `coordinator.md` wording is Red** and prompts Mike per the ritual. Keep it to pointing
   at the block, not a new rule — the existing rule being ignored is the finding.
4. **Verify:** Suite B-hard re-run — the pass condition is the ask-rate on ambiguous referents
   rising, not just the score; plus the five recorded instances replayed as spot checks where
   reproducible.
5. **A4 is suspended (ROADMAP § Section 0 pt 8, amended 2026-09-02)** — no A4 run rides this.
   The regression gates that do: `tests/run_coord_model_probe.py`, the pipeline suite if
   `_dispatch_from_coordinator` is touched.

Close by updating the item with the numbers (before/after ask-rate). **The work owes a commit,
then a deploy** — say so explicitly at close; a "deploy complete" with uncommitted work shipped
nothing once already. /archive at close.
