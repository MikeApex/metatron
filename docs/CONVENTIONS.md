# Conventions — phase review, phase testing, file naming

Process conventions that apply at **phase boundaries**, not on every session. Kept out of
`CLAUDE.md` so they are not paid for on every chat.

**Read this when:**
- Opening a new phase, or writing its review.
- Writing or amending a `tests/phase{N}_testing_plan.md`.
- Naming any generated file — report, session archive, analysis doc, plan snapshot, script output.

---

## Phase Review Convention

At the start of every phase, read the previous phase's session archives and the current plan snapshot, then produce a review in this format for each finding:

> **[Finding]** — what changed or was learned
> **→ Implication** — what this means for the plan (be specific: which section, which decision, which future work item is affected)

Checklist of categories to cover in every phase review:
- Model routing: did testing change which model goes where? Are any routing assignments now confirmed, demoted, or written off?
- Data requirements: do any planned Phase N features require more data than will exist? Call out the constraint and its implication explicitly.
- Blocking prerequisites: list them in dependency order, not by importance. What cannot start until what else is done?
- Stale plan elements: anything the plan says that is now outdated, resolved, or superseded?
- Flagged deferrals: anything that was deferred in the last phase but should be revisited now vs. left for later?

If the review produces a vague finding without an implication, rewrite it. A finding without an implication is just a summary, not a review.

---

## Phase Testing Convention

Every development phase must have a testing plan at `tests/phase{N}_testing_plan.md` before that phase begins. Testing plans are intent-driven — they verify that the phase achieved its *purpose*, not just that the built items run. Each plan includes: a statement of phase intent, a prerequisites check, intent verification criteria with explicit pass/fail conditions, and known gaps carried forward.

Testing plans for all phases (including future phases) live in `tests/`. Amend them as gaps are discovered — do not create separate gap documents.

### Testing Cost Convention

Added 2026-08-09, after the Aug 1–8 billing reconciliation found that test-suite runs (A4
clinical hard-fails, B1 red team) accounted for roughly half of that window's Vertex spend —
one persona's test sessions (`sarah_chen`) cost as much as eight days of real production use.
Test-suite cost is not a byproduct to notice afterward; it must be sized before the suite runs.

**Before running any test suite that makes live model calls** (`tests/run_a4_safety.py`,
`tests/run_b1_redteam.py`, an agent behavioral audit, a model-ceiling comparison, or any ad hoc
"run this N times against sarah_chen/danny_park" session) — produce a projected cost:

- **Anchor to a real number, not a guess.** The most recent comparable run's actual cost (from
  its report file, or from `core/spend_guard.py`'s `today_summary()` if the run is imminent) is
  a better estimate than counting scenarios and multiplying by a rate table. If no comparable
  run exists, estimate from call count × expected tokens × the rate in
  `config/modules/spend_guard.yaml`, and say so — an estimate built on a real prior run and one
  built from scratch carry different confidence, and the reader should know which they're
  getting.
- **State the projection before starting**, not after — "this suite ran N checks × ~$X each in
  its last run, ~$Y projected" as part of proposing the run, not as a footnote afterward.

**Projected cost above $1.00 requires Mike's explicit approval before the suite runs.** Under
$1.00, proceed and report the actual cost afterward. This is independent of `spend_guard.yaml`'s
`stop_usd_per_day` — that catches runaway mid-session; this catches a suite that was always
going to be expensive before the first call goes out. A suite denominated in real dollars is a
decision, not a default.

### Three different quantities are called "tokens" — never compare across them

Learned 2026-08-13 during the §10b throughput work, and promoted here from `SESSION.md` on
2026-08-14 so it survives the primer being rewritten. At least three distinct numbers travel
under the name *tokens*, and a figure quoted from one against a budget set in another is
wrong by a large factor, silently:

| Quantity | What it counts | Where it comes from |
|---|---|---|
| `subagent_tokens` | one specialist dispatch only | `tools/subagent.py` |
| raw | every token the provider billed, all agents, all turns | provider usage fields |
| weighted | raw adjusted for cached vs. uncached input rates | `core/spend_guard.py` |

§10b's ~165k figure is the **first** of these, and reading it as the second is the mistake
this note exists to prevent. **State which quantity a number is whenever you quote one** —
a bare token count is not a measurement, and the Testing Cost Convention above depends on
the distinction holding.

### File naming convention

All generated files — test reports, plans, analysis docs, session archives — must have names specific enough to survive alongside similar future files without collision. Include at minimum: purpose, date, and model/provider where relevant.

**Pattern:** `{purpose}_{YYYY-MM-DD}_{qualifier}.{ext}`

Examples:
- `tests/phase4_report_2026-05-19_gpt-4o.md` ✓
- `tests/phase4_report.md` ✗ — overwritten on next run
- `archive/sessions/2026-05-19_phase4_pattern_miner_testing.md` ✓
- `archive/sessions/session.md` ✗ — meaningless after the session

Apply this to: test reports (`run_phase*.py` output), session archives, analysis documents, plan snapshots, and any file a script writes automatically. Generic names like `report.md`, `output.json`, or `plan.md` are not acceptable for generated files.

---

---

## Adding a new module

*Moved here from `CLAUDE.md` 2026-08-13 — it is a recipe consulted when adding a
module, which is the definition of on-demand.*

1. Create `config/agents/{module_name}.md` — agent instruction file
2. Add tools to `tools/{module_name}.py` — Python functions + JSON schemas
3. Add `config/modules/{module_name}.yaml` — settings if needed
4. Register tools in `core/orchestrator.py` → `register_tools()`

No other code changes required.

> Before writing the agent file, read `CLAUDE.md` § *A tool named in an agent file
> is a specification*. Naming a tool you have not built yet is legitimate and is
> the design record — but it must sit under a deferred heading, not in live
> instruction text, or the model reads it as a capability it has.

---

## Tool pattern

Every tool follows this pattern in `tools/`:

```python
def my_tool(param: str) -> str:
    """Does the thing."""
    # implementation
    return result

MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "Does the thing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What param does"}
        },
        "required": ["param"]
    }
}
```

Register by adding `(my_tool, MY_TOOL_SCHEMA)` to the list in
`orchestrator.register_tools()`.

---

## Model version maintenance

Model IDs in `core/orchestrator.py` and `config/modules/routing*.yaml` drift as
providers release new versions. Check and update at the start of each new phase, or
when a provider announces a new model in a session.

| What to check | Where | How |
|---|---|---|
| Anthropic models | `ANTHROPIC_MODEL`, `routing.yaml` cloud_deep | console.anthropic.com/docs/models |
| OpenAI models | `OPENAI_MODEL` | platform.openai.com/docs/models |
| Gemini models | `routing*.yaml` agent entries | **`python3 scripts/check_model_availability.py`** — see below |
| MCP ask_gemini | session-level via `mcp__ask_gemini__set_model` | MCP tool description lists options |
| Ollama | `OLLAMA_MODEL` | `ollama list` on the local machine |

> **The live IDs are in `SESSION.md` § Model IDs, not here.** This table says *where
> to look and how to check*; recording the current values in a second place is how
> they go stale. `SESSION.md` is rewritten every session, so it is the copy that
> stays true.

**For Gemini, "check at the start of each new phase" was not enough, so it is now a script
and a clock.** That instruction is a remembered process and it went stale the way remembered
processes do: on 2026-09-01 the fleet was still routing to a **deprecated**
`gemini-3.1-flash-lite` with three newer Flash generations shipped, and the `SESSION.md` table
was five weeks old. `scripts/check_model_availability.py` answers it in ~20s for well under
$0.001; `[DB-0901-01]` carries the **weekly** `due:` date so it wakes itself at session start.
**Weekly since 2026-09-04, monthly before it** (Mike): 3.8 Flash `404`'d on 09-01 and was
callable on 09-04, so a monthly clock had a 27-day blind spot on a same-price upgrade. The run
is cheap in tokens (~$0.001, most of it free filtering) — the cadence was never limited by cost.
**The date is the floor, not the trigger**: run it on any credible signal a model shipped. The
09-04 adoption came from a launch email, not the clock.

> **Two things a hand-check gets wrong, both observed 2026-09-01.** A model can read `200 GA`
> from the Vertex catalogue and `404` on the `global` endpoint we actually call — true of
> `gemini-3.8-flash` and `gemini-3.5-pro` that day, so **catalogue presence is not
> availability** and only a live call settles it. And the public pricing page is not a
> substitute for the billing SKU catalogue: its context-cache-storage table had no 3.7 Flash
> row at all, while the SKU catalogue published one ($1.00/1M/hour).

**Adopting a new model is never only a string swap.** It needs the `routing*.yaml` entry (Red),
a `config/modules/spend_guard.yaml` pricing entry — an unpriced model bills at the Pro-rate
`default`, and an entry that *exists but omits* `cache_storage_per_hour` bills cache storage at
**zero** — and a re-check of the Vertex cache token floor, which is per-model, not universal.
