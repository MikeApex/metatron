# [DB-0810-13] — action provenance: design and diagnosis

*Written 2026-08-15. Design only — **not implemented**, see § Blocked on.*

## The problem in one line

The system tells Mike it did things it did not do. On 2026-08-10 it said an email to Kathaleen
was scheduled, then moved up, then *"That's sent."* Nothing was ever sent.

## Diagnosis — this is a missing-information failure, not a prompt-adherence failure

Read `run_pipeline_session` ([core/orchestrator.py:3180-3196](../../core/orchestrator.py#L3180-L3196)).
The Synthesizer's input is assembled from exactly three things:

1. the user's message,
2. `COORDINATOR ROUTING PACKAGE` — the **directives**, i.e. what specialists were *asked* to do,
3. `SPECIALIST OUTPUTS` — each specialist's **prose**.

`_dispatch_from_coordinator` returns `outputs[agent] = future.result()`
([:3080](../../core/orchestrator.py#L3080)) — the text, and nothing else.

So when `relationships` aborted its `send_email` on a failed CRM lookup and returned prose
implying the mail was on its way, the Synthesizer held: a directive saying *send the email*,
prose implying success, and **zero contradicting evidence**. It said "That's sent" because
nothing in its input could have told it otherwise.

**This is the load-bearing conclusion: no amount of instruction-tightening on the Synthesizer can
fix it, because the fact is genuinely absent from its context.** Any fix that is only an agent-file
edit will appear to work in testing and fail in production the same way.

## The fact exists. It just never travels.

`core/trace.py` already records every tool call per agent: `ToolCallRecord` carries `name`, `args`
and `ok` ([core/trace.py:44-52](../../core/trace.py#L44-L52)), written by `record_tool_call`
([:265](../../core/trace.py#L265)). The orchestrator dispatches the tools, so it knows with
certainty which ones ran. The information is one function call away from the Synthesizer's input
and has never been put there.

## The pattern is already built here, for a different failure

**Do not invent a new mechanism — generalise the one that works.**

After the `research_agent` fabricated sources, a provenance line was added that Python generates
from the retrieval itself:

- `core/orchestrator.py:2294` → `SOURCES (N retrieved): …`
- `core/orchestrator.py:2296` → `[RETRIEVAL: NONE — not checked against any live source]`

and `config/agents/synthesizer.md:109-112` instructs the Synthesizer to read it, with the
principle stated explicitly:

> *"Research does not write it — it is generated from the retrieval itself, so it is **evidence
> rather than a claim**."*

That is exactly the shape [DB-0810-13] needs. Retrieval provenance answers *"was this looked up?"*
Action provenance answers *"was this done?"* — same mechanism, same trust argument, and the
Synthesizer already has the habit of reading a machine-written line differently from model prose.

## Proposed fix — two halves, in this order

**Order matters and is not negotiable.** Deploy rule 2: never add config before the code that
gates it. An instruction telling the Synthesizer to check an `ACTIONS` line that does not yet
exist would make it decline to confirm things that genuinely happened.

### Half 1 — Python (must ship first)

In `_dispatch_from_coordinator`, after each specialist returns, read that specialist's tool calls
off the trace and append a generated line to its output. Sketch, not final:

```
[ACTIONS: send_email(ok), write_log(ok)]
[ACTIONS: NONE — this specialist changed nothing]
```

Design notes:

- **Only state-changing tools belong on it.** A line dominated by `search_contacts` and
  `list_obligations` restates the `is_grounded()` mistake that `core/trace.py:107-118` documents:
  an agent that called `write_log` is *active*, not *grounded*. Reads are not actions. Needs an
  explicit read/write classification, which does not exist yet — that is the real work.
- **`ok=False` must be visible**, not filtered out. A `send_email` that was attempted and failed
  is precisely the Kathaleen case, and it is more informative than silence.
- **Known attribution weakness:** `[DB-0810-02]` — `pop_agent()` does not restore the prior
  thread-local `current_agent`, so a nested `run_subagent` can misattribute a tool call to the
  wrong specialist. Per-agent attribution is therefore not fully trustworthy today; *"was
  `send_email` called at all this request?"* still is. Either fix `[DB-0810-02]` first, or scope
  the line to the request level until it is fixed. **Do not build per-agent attribution on top of
  a known-broken attribution path.**

### Half 2 — `config/agents/synthesizer.md` (Red tier, after half 1 deploys)

A rule in the same voice as the existing provenance rule: never assert that an action was
completed unless it appears in an `ACTIONS` line. Where a directive was issued and the action is
absent, say plainly that it did not happen — do not narrate why, and never name a tool or an
agent (the confidentiality rule is unchanged).

### Explicitly out of scope for this fix

The **invented capability** half. Scheduled sending does not exist — `send_email` has no `send_at`
and nothing wires a scheduler job to a pending draft — yet the system produced "Thursday, August
13th" two turns before the false confirmation. Action provenance stops the *confirmation*; it does
not stop the *invention*. Separate item, needs its own filing.

## Blocked on

`core/orchestrator.py` is the exclusive manifest of the concurrently-running `[DB-0810-12]`
worker (2026-08-15). Half 1 cannot be written until that worker merges. Half 2 must not be
written before half 1 deploys.

## What was verified today, and how

| Claim | Evidence |
|---|---|
| Synthesizer receives directives + prose only | read `run_pipeline_session` :3180-3196 |
| Specialist tool calls are not passed on | `outputs[a] = future.result()` :3080 |
| Tool calls *are* recorded with name/args/ok | `ToolCallRecord` trace.py:44-52 |
| The provenance pattern exists and works | orchestrator.py:2294/2296 + synthesizer.md:109-112 |
