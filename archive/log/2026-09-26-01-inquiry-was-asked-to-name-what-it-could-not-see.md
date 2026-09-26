### 2026-09-26 (Inquiry invented an owner because the file demanded one; run 1 stopped after the first stage) — **nothing committed, nothing deployed**

Phase F1 run 1 started, produced two defects at its first stage, and was stopped by Mike to fix
them. This window was the F1 worker; Mike asked it to close the record itself, overriding the
prompt's "do not archive out" — noted so the coordinating window does not double-write.

**The trigger was hand-filed, twice, and the live attempt was never made.** `BLD-0926-01` filed
with the gap written as the whole of household upkeep; Mike stopped it before any stage ran and
re-scoped to *a tool to determine when the plants at home need watering*. `BLD-0926-02` is the live
job. Both wrote their ticket row and `BUILD_PROPOSED` event correctly, so the plumbing held twice.
Abandoning `BLD-0926-01` wrote **the first row ever into `config/build/registry.yaml`**, so the
dedupe path finally has something to refuse against. Mike declined to put a question to the live
app, so § 12's Trigger row keeps its second half open and **no verbatim should-file case exists**.

**The capability is named `plant_watering`, not the `home_care` of plan § 11.** In the four-layer
graph `home_care` is the shape of a *category* agent; this is a tier-3 leaf. Naming the leaf for its
job means a later category is a new file plus a routing line, not a rename across two routing files,
an agent file and a registry row.

**Believed true and wrong: the fig-question diagnosis.** Phase E recorded the Coordinator's refusal
to file on *"when did I last water the fig?"* as a judgement defect and "the vertical's premise"
failing. It is at minimum incompletely diagnosed. A **daily `plant_watering_check` scheduled job
exists**, agent-created 2026-08-05, running on `coordinator`, doing exactly that standing judgement;
and `logistics.md:41` claims *"weekly (watering plants, grocery run)"* while its directory entry
claims *"if something needs to happen in the world, Logistics owns it"*. So filing shape 1 cannot
fire for household upkeep at all, and shape 2 asks the Coordinator to rule against a job it runs
itself. A conflict between two config files is a sufficient explanation — consistent with `4f0a6c3`
moving the rule into the procedure and changing nothing. Plant watering is also the **only**
household task with real history in the 90-day log window, so the prompt's "a task with a history"
requirement was only satisfiable by the contaminated family.

**DEFECT 1, and the root cause was not the one I first named.** Inquiry cited *"the Time Director as
the agent that owns time-anchored prompting"* as **the stated architecture**. Time Director has been
RETIRED since 2026-05-28, is in neither routing file, and is literally the `time_director` shape the
wiring gate exists to catch. A source audit of the live agent (its context intact; the artifact
already landed, so the audit could not alter it) established it made **zero tool calls** and got the
name from two auto-injected files: `CLAUDE.md:140`, a terminology table naming it as an example, and
**`MEMORY.md`** — *"Synthesizer (integration/response, Time Director built in); **not yet
implemented**"*. So the evidence was **contradicted**, not merely absent. Its own words: *"No text
stated it. I inferred it from the name. I inflated a name into a role."* A second unsourced
inference sat in the same clause.

**My first diagnosis — that the injected context was the cause — was incomplete.** The real cause is
that the agent file **required** it: *"Your evidence must name an existing specialist and say why it
does not cover this."* A stage with no tools and no manifest was told to name a member of a list it
was never shown. The injection supplied raw material; the field created the demand. And the guard
would have passed it anyway: `manifest.capabilities()` reads `config/agents/*.md` stems, and its
docstring names `time_director` by name as the reason — deliberately conservative against `new`
slipping through, permissive in exactly the direction that failed. Inquiry's own summary of why
nothing caught it: *"I complied with the field ban and then committed the same offence in prose, in
a free-text field nothing validates."*

**DEFECT 2, structural and worse: there is no path back from a clean-but-wrong artifact.** The one
retry fires only on validation defects; `send_back` covers the review alone; position is derived
from whether the artifact exists on disk. No `rewind`, `reset` or `discard` in `driver.py`. The only
routes back are hand-deleting an artifact — the move `.claude/commands/build.md` names as a code
defect rather than a step — or abandoning and re-filing, which the dedupe refuses for an identical
gap. Run 1 proceeded rather than forcing a route back because the false clause is **inert
downstream**: no question depends on it, the Librarian builds rows per question, the Planner holds
Read/Grep and is tree-validated, and the reviewer's job is exactly a wrong premise.

**Inquiry rewritten around Mike's original prompt, chunk by chunk.** An experienced executive
assistant on their first day, reasoning with no data in hand; the source list is *scaffolding to
ground the questions, not a possession*, which resolved the contradiction in paragraph 3 rather than
paragraph 1. Removed: the disposition and its evidence, `proposed_depth`, the "who produced the gap"
line, a phantom `kind: orienting` field name, and a claim to state the ordering rule twice.
**The altitude answer did not leave Build — it left the one stage that cannot answer it:** the
Planner's `capability.disposition` already carries it and holds the tools to check it. The
boilerplate-evidence guard moved there with the claim rather than being deleted. `known_capabilities`
is still accepted by the validator and no longer consulted, so `driver.land` and `/build` are
unchanged. 153 → 141 lines; chunks 3–5 uncompressed against a ~55 target.

**Rejected: removing `feasibility` and `surface` from the spine.** Every question that drifted above
its paygrade was one of those two classes. But the drift was caused by an injection about to be
plugged, and removing them breaks two things — the validator requires a `surface` question, and
`test_build_spine.py`'s compass fixture exists precisely to stop `feasibility` preceding `intent`.
Rebind the definitions first, seal the vacuum, measure again. Deferred, not dismissed.

**Bench test 1 (2.1.233, injections still leaking): VALID, 0 defects, 23 questions.** Invention
fixed — where it needed to know what exists it *asked*. Better assistant questions appeared that the
first run never reached: is any plant irreplaceable, is the real ask delegation, over-watering kills
houseplants as reliably as drought, build nothing and add one line to a surface he already reads.
**But the drift survived**: six questions still quote the project's files, three verbatim, and it
calls the employer **"he"** — from a prompt carrying no name and no gender. **Better instructions
stopped the invention and cannot stop the knowledge.** That is the measurement justifying the
upgrade, not an argument for it.

**The vacuum is sealed structurally, pending a version bump.** `omitClaudeMd: true` added to the
agent's frontmatter — requires Claude Code ≥ 2.1.271, measured on 2.1.233, and on an older build it
is **silently ignored**, which is the one way bench test 2 could measure nothing while appearing to
pass. `includeGitInstructions: false` deliberately NOT set: global only, and a list of filenames
cannot produce a false architectural claim. The environment block is unsuppressible on any version.
**`MEMORY.md` reaching a subagent contradicts the documentation** and is a reportable bug if it
survives the upgrade.

All fourteen Build suites pass (353 checks) and `qa_sweep` is 12/12 after the schema change.
Uncommitted: seven files of work plus two new records. Next session's prompt and the four things
bench test 2 must check: `archive/plans/inquiry_rewrite_2026-09-26.md`.

