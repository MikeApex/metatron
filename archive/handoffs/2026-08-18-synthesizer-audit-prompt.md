# Handoff — audit `config/agents/synthesizer.md`: 51 KB of instruction for an agent that writes three sentences

**Run `/metatron-code` first, and read [`.claude/rules/agent-files.md`](../../.claude/rules/agent-files.md)
deliberately before opening the target** — agent files are Red tier (every edit prompts Mike) and
that rule file carries the constraints this audit will otherwise trip over. This is Option C from
`archive/handoffs/2026-08-18-caching-fix-prompt.md` § Options, run on its own clock. **Recommended
model: Fable** — this is a judgement audit, not a mechanical trim.

## The measurement (2026-08-18, verify before cutting)

- `synthesizer.md` is **50,703 chars — 65% of the interactive Synthesizer prompt** (77,084 chars
  total on the measured 16:48 turn). Persona config is 17%, recent context 13%, history 3%.
- It was 43,655 bytes on 08-08 and 51,086 on 08-16 — **+17% in eight days**, a little at a time,
  unmeasured. Until the caching fix lands, all of it is billed on every interactive turn; after
  it lands, it is still the dominant share of cache creation and of every uncached fallback.
- This audit is **orthogonal to the caching fix** (same handoff, Options A/B): it reduces the
  bill on both paths and neither depends on the other. Do not fold them together.

## The job

1. **Reconstruct where the growth came from before judging it.** `git log --follow -p` on the
   file, 08-08 → present. Each addition was made deliberately by some session, usually with an
   incident behind it — per the standing rule, diff what recent sessions deliberately did before
   proposing to remove it. An audit that bulk-deletes scar tissue will be reverted.
2. **Sort every section into three buckets**, using the designated pattern from `ROADMAP.md`
   § D2 → *Agent instruction file slimming — context-file pattern (Option 2)* — do not invent a
   new mechanism:
   - **Keep in the file:** behavioural rules, safety handling, the `[CONTEXT]` block output
     contract, `## Confidentiality`. Non-negotiable rules near the top, output-format
     requirements repeated at the end (the D2 ordering principle).
   - **Move to `config/modules/synthesizer_*.yaml`**, loaded on demand via `read_agent_config`:
     domain data — lists, rubrics, playbooks, worked examples. The file gains one line per
     module ("when [signal], call `read_agent_config('...')`"). No code change needed.
   - **Cut:** duplication, superseded instructions, anything restating what Python now enforces.
3. **Produce the proposal as a document first** — `archive/plans/synthesizer_audit_2026-08-18.md`
   (adjust date to the run): current size, target, per-section verdict (keep/move/cut) with one
   line of reasoning each, and the growth attribution from step 1. **Mike approves before edits
   are applied.** Target from ROADMAP § D2: Synthesizer at 3,500–5,000 tokens is the stated aim;
   treat it as direction, not a hard gate — a section that earns its tokens stays.

## Constraints that are not negotiable

- **`## Enhancement backlog` at the bottom of the file is the ONLY copy** of the Synthesizer's
  enhancement backlog (mirrors were deleted 2026-08-03). It survives verbatim, whatever else moves.
- **The `[CONTEXT]` block contract is load-bearing in Python.** `split_context_block()` /
  `persist_context_block()` in `core/orchestrator.py` parse it on every turn, streaming and
  non-streaming. The instructions producing it change only with a matching test.
- **Do not reintroduce provenance judgement.** The 2026-08-18 research guard withholds
  zero-source answers **in Python** because the Synthesizer softened the `[RETRIEVAL: NONE]`
  marker instead of refusing. Any instruction implying the Synthesizer decides what ungrounded
  content to deliver is a regression.
- **The deliberation-leak filter (tier 5) is the only control for reasoning-in-content**
  (ROADMAP § A7, check 5 notes) — instructions about not narrating deliberation may be *kept*,
  but do not treat instruction text as the fix for that class.
- **Vertex cache floor, `CLAUDE.md` § Infrastructure traps 6:** Vertex will not create a cache
  below 4,096 tokens and fails silently. Synthesizer is on the cached path. Enormous headroom
  today (~19k tokens), but the post-audit prompt size must be checked against the floor anyway —
  `_pad_for_vertex_cache()` is the backstop, not the check.
- **A named tool is a specification** (`.claude/rules/agent-files.md`): any tool name the file
  mentions must remain a tool the Synthesizer is actually granted, and vice versa. Run
  `scripts/check_agent_tools.py` after edits.

## Regression gate (after edits are applied, before closing)

1. `python tests/run_a4_safety.py --suite pipeline` — clinical substance must survive; the
   ROADMAP § D2 slimming item names the A4 hard-fails as the per-slim regression gate.
2. `python tests/run_b1_redteam.py` disclosure suite — `## Confidentiality` behaviour must hold.
3. One live pipeline turn; confirm the `[CONTEXT]` block still parses (no
   `[context_block] no [CONTEXT] block` warning) and, post-caching-fix, that `cache_read`
   still appears — the prompt change creates a new cache hash, which is expected, not a fault.
4. `bash scripts/qa_sweep.sh`.

## Scope

`config/agents/synthesizer.md` (Red — edits prompt Mike), new `config/modules/synthesizer_*.yaml`
(new files, state them in the proposal), the proposal doc, tests. **No `core/` changes.** Deploy
is Denied — hand the commit back to Mike. If the caching-fix window is live at the same time:
different files, but **`git diff` every file before staging** — two chats share this worktree.
