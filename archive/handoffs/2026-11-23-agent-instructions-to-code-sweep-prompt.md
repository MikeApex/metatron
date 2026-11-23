Model: Opus 5.5, high effort — a read-only classification across 24 instruction files where the judgement (what is really judgement, what only looks like it) is the work. Fable 5.1 reviews the findings at the end, with a fresh read that isn't anchored on the sweep's conclusions.

# Agent instructions → code: the sweep `[DB-0810-11]` strand (c) never got

You are surveying, not building. This chat reads every runtime agent instruction file, marks each
instruction that would be better done by code, and writes one findings document. **No code, no
config or agent-file edits, no deploy, no backlog filing.** Mike rules on the findings afterwards.

## Why this session exists

"Where should code replace model judgment?" `[DB-0810-11]` was raised by Mike on 2026-08-05. It had
three strands: (a) code looks things up and hands agents the evidence instead of asking them to
recall it; (b) code removes agent calls entirely; (c) a standing code/agent review protocol.
**(c) never got its session.** On 09-02 the item was parked to Mark 2. Mark 2 ended on 11-18, so the
item is now attached to a rebuild that no longer exists. Since August the code-first direction has
been applied one piece at a time in Mark 1, each move justified on its own, and no session has read
the whole instruction set with this question in mind.

Four passes came near it, each with a different lens. **Do not redo them; use what they found:**

1. **The 08-02 capability-gap survey and the 08-03 tool reconciliation** compared what agents are
   told they have with what exists. They aligned instructions to code; they did not move anything.
2. **The 08-27 Synthesizer audit**, one file only. Code-conditional section injection; 52 KB → 41.9 KB.
   **The file is 54 KB again now.** Its key evidence: all six of Mike's 08-21 complaints were rules
   already written in the file and ignored, while every rule moved into Python that month held the
   first time it was tested.
3. **The 11-05 whole-codebase review** (`archive/plans/codebase_review_2026-11-05_fable-5-1.md`)
   looked for defects. Its findings on flags nothing reads (`CONSULT_NEEDED` and others), scan
   preambles for context the specialists never get, and Synthesizer/Coordinator contradictions
   are inputs here. Check their current state rather than re-deriving them.
4. **The 11-18 prompt audit** covered the Claude Code configuration only, not the runtime agents.

## Read first, in order

1. `SESSION.md`, then `ROADMAP.md`. The mandatory pre-edit context check applies even though you
   will not edit anything.
2. `.claude/rules/agent-files.md`. Reading it triggers the rule load; it carries One Home Per Rule
   Class and "a named tool is a specification".
3. `archive/plans/code_dominant_rebuild_notes.md`, all rounds. The method below comes from
   rounds four and five.
4. `DEV_BACKLOG.md` entries `[DB-0810-11]` and `[DB-0808-09]` (specialist turn counts, the measured
   "reads then one write" shape, code-side prefetch as the strong candidate). Read only those two.
5. `archive/log/2026-10-30-01-synth-now-and-next-not-the-day.md` and
   `archive/log/2026-08-27-06-synthesizer-audit-executed.md`, two worked examples of the move.

## Scope

All of `config/agents/*.md` (24 files, about 376 KB), plus `config/modules/synthesizer_*.md`, which
are injected instruction. For each file, read the code that loads it and the tools it is granted
(`config/modules/routing_cloud.yaml` is the live one; `routing.yaml` must stay in parity). Classify
instructions against what the code actually does today, not what the file says.

**Order:** Logistics and Relationships first. They are large (41 KB and 36 KB) and have the highest
turns per call (3.6 and 4.2), so a move there also cuts cost. Then Coordinator, Synthesizer and the
other specialists, then the small single-purpose judges (`task_judge`, `accountability_judge`,
`day_planner`, `project_planner` and similar). Expect few findings in the judges, since they are
already gate-shaped; say so rather than padding.

**Out of scope:** `config/constitution.md` (Tier 0, Denied); `config/personas/**` (the VM owns live
persona config); `.claude/agents/*` (the Claude Code subagents, covered 11-18).

## Method: four bins per instruction

Read each file in full. For every instruction that does work, assign one bin:

- **A. Code can do this exactly.** Deterministic matching, arithmetic, dates, ordering, dedup,
  lookups, format checks, "always call X before Y". Example: the "over and out" sign-off detected
  in Python.
- **B. "Don't use X" → stop passing X.** A rule telling a model to ignore data it is given. Example:
  Synth seeing now/next instead of the whole day (10-30).
- **C. Flag protocols → parse them in code.** The agent emits a token and a reader is meant to act
  on it. Example: `HORIZON_ITEMS` is parsed; `CONSULT_NEEDED` is not.
- **D. Real judgment.** Tone, reading intent, weighing values, interviewing. It stays in the file.
  Say so in a single line and move on.

Then, for each A/B/C finding:

1. **Silent or loud?** This is the 09-02 sorting rule: if nobody would notice the instruction being
   ignored, the written rule is the only control. Rank silent failures first.
2. **Evidence that it is being ignored**, if any exists: traces, quality events,
   `USER_CORRECTION`, earlier incidents in `archive/log/`. Read the VM only through
   `scripts/vm_read.py`. Do not run live model calls; this session has no budget for them. An
   unevidenced finding is allowed, but label it unevidenced.
3. **The shape of the move**, following the "over and out" template: a deterministic trigger, the
   work preserved, any safety veto in code (clinical flags `MUST_SURFACE` / `CLINICAL_CONCERN` /
   `MEDICATION_MISSED_CRITICAL` veto any skip, without exception), and one fixed-cost exit.
4. **Tier and files.** Use `.claude/settings.json`. A move that touches a Red file (an agent file,
   the routing files, `core/router.py`, `persona.py`, `scheduler.py`, `spend_guard.py`) must say so.
   Red work is never delegated to a subagent.
5. **What the move costs or saves**, at whatever precision you have: turns per call, tokens per
   turn, latency.

**Traps to avoid:**
- A model-judged step is not a defect by default. The test is whether a rule could make the same
  decision exactly, not whether code could approximate it. A fuzzy match that replaces an exact
  judgment adds failure modes.
- A flag nothing reads may need a reader, or the instruction may need deleting. Say which, and why.
- If an instruction contradicts another file, the finding is One Home Per Rule Class, not a move to
  code. Report it separately and briefly.
- Do not re-raise anything in `SESSION.md` § Do not re-open.

## Deliverable

Write one file: `archive/plans/agent_instructions_to_code_sweep_2026-11-23.md` (use the actual date
if later). It contains:

1. **A lead section, written for Mike.** Open with what a user would notice getting better, then
   how many findings and where they cluster. Name each defect by what a user would see, not by its
   cause. Every backlog id is preceded by the problem in plain language.
2. **A ranked findings table:** silent first, then by evidence, then by size of win. Columns: what
   the user sees · bin · file:line · evidence · move shape · tier · cost/saving.
3. **Per-file notes:** one short block per agent file. Files with nothing to move get one line.
4. **Three or four build clusters.** Group findings into buildable units, each with a build budget,
   the recommended model, and whether it needs a deploy. Do not write the build plans.
5. **Decisions for Mike**, each with options, the trade-off and a recommendation. This includes what
   happens to `[DB-0810-11]` (close it into this document, or keep it open as the standing
   protocol) and to the rebuild notebook (retire it into this document, or keep appending to it).
   The notebook's own retirement condition can no longer fire.

Then stop and present the lead section and the decisions in chat, numbered. **Do not file backlog
items**; Mike decides what gets filed. Propose the Fable review as a separate prompt, written in
full and carrying its own model line, that hands the reviewer the findings document and the agent
files, without your reasoning summary.

## Budget

- **Build (this session):** about 600–900k weighted input-token equivalents. That covers reading
  about 376 KB of agent files, the loading code and the routing files, and some trace reads through
  `vm_read.py`. Roughly two to three hours. If you are past halfway through the budget and still in
  the specialists, report the partial table and ask before continuing.
- **Run / ancillary:** none. Nothing ships from this session.
- **Fable review afterwards:** about 200–300k, reading the findings and spot-checking against the files.
- **Unseen:** none. No live calls, no persistent state created.

Run `python3 ~/.claude/tools/archive_chats.py` after the findings document is written, then
`/archive` at close.
