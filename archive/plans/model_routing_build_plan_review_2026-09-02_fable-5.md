# Adversarial review — model_routing_build_plan_2026-09-02.md

*2026-09-02. Reviewer: Fable 5. Brief: hunt for what breaks on execution; no verdict, no fixes.*
*Status at time of writing: Mike has shelved the build ("not pursuing for now"). A complementary
plan from another chat is expected in `archive/plans/`.*

Claims verified against live artifacts during the review: both `CLAUDE.md` files (line counts
confirmed: global 194, project 307), `.claude/settings.json`, `scripts/hook_agent_spawn.py`,
`.claude/rules/deploy.md`, the scripts directory (`qa_sweep.sh` exists; seven hook scripts
confirmed), and whether `~/.claude` is a git repository (it is not).

---

## WILL BREAK

1. **Task 4 versus the plan's own review step.** The plan requires "Review model: Fable 5 at
   `high`" (line 10) and task 4 persists `effortLevel: "medium"` in project settings. The
   document itself establishes that no mechanism raises effort afterwards: hooks "cannot press
   the key" (harness section, item 2), and the advisory in task 7 is explicitly non-enforcing.
   So the review session the plan mandates for this very build runs at `medium` unless someone
   remembers a step the plan never writes down — and the Unseen bullet states who would notice:
   nobody, "adherence is unmeasured by design." The first divergence between the persisted
   default and the routing table is the plan's own QA layer, silently degraded.

2. **Task 9's "commit each task separately" has no repository for tasks 1–3.** Tasks 1–3 write
   `~/.claude/model_routing_policy_2026-09-02.md` and edit `~/.claude/CLAUDE.md`. Verified:
   `~/.claude` is not a git repository, and the plan's own finding #2 states "Exactly one git
   repository with a `CLAUDE.md` exists on this machine" — that repository's CLAUDE.md is the
   project one. The commit step cannot execute for the three tasks that produce the policy
   document and the global binding lines, so the plan's most consequential artifacts end up
   version-uncontrolled while the step that claims to cover them names no producer of a repo
   for them.

3. **Task 3's stated premise is false against the named file.** The plan says "model-routing
   guidance currently lives in *both* `## Plan Mode` and `## Costs`, so a model-choice rule is
   found in either place depending on where you look first. Consolidating fixes that." Verified
   against `~/.claude/CLAUDE.md`: § Costs contains the four cost classes and the standing-cost
   questions and no model-choice guidance at all — every model-recommendation line is in
   § Plan Mode. The displacement is specified against content that is not where the plan says it
   is, and the "one home" justification rests on a duplication that does not exist.

4. **The Unseen bullet's "Nothing here persists between calls… nothing survives a restart" is
   false for task 6.** The hook task 6 extends already writes a per-session ledger —
   `scripts/hook_agent_spawn.py` lines 60–73 append to
   `.claude/.session_state/<session_id>.spawns.log`, creating the directory on first spawn, with
   no expiry and nothing that deletes it; it survives restarts by construction. Task 6's
   per-session spawn-count warning is denominated across invocations of a hook that runs as a
   fresh process each time, so it must read exactly this kind of cross-call state. The global
   § Costs three questions (what deletes it, what happens on restart, which meter reports it)
   are unanswered for the state directory the plan's own mechanism depends on.

5. **The Run bullet's "the only recurring token cost here" is contradicted by task 6.**
   `scripts/hook_agent_spawn.py` lines 50–58 already inject `additionalContext` into the
   transcript on every spawn; task 6 adds correction-or-warning text to that output plus the
   spawn-count warning. That is a recurring per-spawn token cost created by a named task,
   sitting outside the budget's claim that task 7's per-session context is the only one.

## MIGHT BREAK

1. **Probe 7a's binary conflates four world-states into two observations (task 5).** The
   states: (a) `updatedInput` honoured and the invalid string rejected → error, read correctly;
   (b) `updatedInput` honoured but the unknown model string silently coerced or defaulted →
   success, misread as "ignored"; (c) `updatedInput` genuinely ignored → success, read
   correctly; (d) the decoy spawn errors for a reason unrelated to the model string → error,
   misread as "honoured." State (b) has a live precedent in the same settings file:
   `defaultMode: "auto"` "was accepted by the settings parser and then silently never took
   effect" (`.claude/settings.json` lines 4–6) — this harness demonstrably swallows invalid
   values. In (b), task 6 needlessly degrades to a warning. In (d), task 6 ships a rewrite that
   never runs while its `additionalContext` reports corrections that did not happen — and per
   WILL BREAK 1's observation, nothing measures the discrepancy. Moves to WILL BREAK if the
   probe's error output fails to name the model string, or if any independent case of the
   harness silently defaulting an unknown model value is observed.

2. **Task 4 can silently no-op, and the plan contains no verification step for it.** The
   `effortLevel` value set and the claim that it rejects `max` both come from "the settings
   schema" — but the same file records that schema-accepted values can take no effect
   (`.claude/settings.json` lines 4–6, the `defaultMode` incident, undetected until measured).
   Fires if `effortLevel` is unhonoured, mis-valued, or overridden in this harness; does not
   fire if the key behaves as the schema implies. Task 9 runs `qa_sweep.sh`, which parses and
   "does not execute" — it cannot detect this. Moves to WILL BREAK on any measured-behaviour
   check showing the persisted value not in force.

3. **The probe window changes Agent-spawn behaviour for every session sharing the tree
   (task 5).** Whether the probe edits `scripts/hook_agent_spawn.py` or registers a throwaway
   hook, `.claude/settings.json` and the hook file are shared, and `.claude/rules/deploy.md`
   states "Two chats often run against this one working tree." A parallel session's real spawn
   during the probe window gets its `model` rewritten to the invalid string. Fires if a second
   session spawns an agent while the probe is in place; does not fire in a solo session. Moves
   to WILL BREAK the moment a second session is live at probe time.

4. **Task 7 classifies the opening prompt, and this project's sessions open with slash
   commands.** The standing ritual opens sessions with `/metatron-code` or `/backlog` — prompts
   that carry a command name, not a description of the work. A hook that "fires once per
   session" spends its one firing on text with no routing signal, then never fires on the
   prompt that has one; whether `UserPromptSubmit` fires on slash-command submissions at all is
   also unsettled in the document. Fires for command-opened sessions; does not fire for
   prose-opened ones. Moves to WILL BREAK if session-open practice is confirmed as
   command-first (which `docs/WORKFLOW.md` prescribes).

5. **The spawn-count threshold is consumed before anyone sets it (task 6).** "Proposed at
   **5**, which is Mike's to set" — no task or step obtains that decision, and task 6 is Amber,
   applied without a prompt. Fires if plan approval is not read as Mike setting the number;
   does not fire if approving the plan constitutes ratifying the 5.

6. **The Vertex/Bedrock exclusion's consequence is stranded outside its scope (Corrections,
   first bullet).** "Anything on the VM's Vertex path needs the SDK's client-side middleware
   instead" is a runtime consequence, and the plan's scope line excludes runtime model
   selection. Task 1 records it in `~/.claude/model_routing_policy_2026-09-02.md` — a
   development-environment document — while the runtime's model-config homes are
   `config/modules/routing*.yaml` and project docs. Fires when § 6.4's universal refusal rule
   is implemented on the VM by someone whose reading path never includes a dev-env policy file;
   does not fire if runtime work consults it anyway.

7. **The hook-output-surface claim is attributed to evidence that cannot contain it.** "What
   the harness can and cannot do" opens with "Settled from the settings schema" and then
   asserts "the complete hook output surface" — but a settings-file schema describes
   `settings.json` keys, not the JSON fields a hook may emit on stdout. The completeness claim
   outruns the named evidence, and it load-bears the central design conclusion ("cannot be
   automatic") that shapes tasks 6 and 7. Fires if the surface is incomplete in a way that
   permits setting model or effort; the `effortLevel`-rejects-`max` claim is legitimately
   schema-territory, but rests on the same unverified single source (see MIGHT BREAK 2).

8. **Task 6 requires `updatedInput` and `additionalContext` to compose in one hook response,
   which nothing establishes.** The current hook returns `additionalContext`
   (`scripts/hook_agent_spawn.py` lines 50–58); task 6 adds an `updatedInput` rewrite to the
   same PreToolUse output. Probe 7a as designed validates `updatedInput` alone, so a pass does
   not cover the combined shape. Fires if the harness honours one field and drops the other
   when both are present.

9. **Task 2's binding lines encode conclusions the corrections section labels unverifiable.**
   "Scoped coding at `medium` and resist raising it" and "effort is the spend dial" derive from
   the 8×/3× effort magnitudes, which appear in the unverifiable list ("No benchmark figure in
   the document can be checked from this machine"). Task 1 labels them; task 2 promotes their
   consequences to always-on rules with no label travelling. Fires if the magnitudes are wrong
   in a direction that changes the workhorse setting; § 8's telemetry path is named as the only
   check but no task consumes it.

## CANNOT BE ANSWERED FROM THE DOCUMENT

1. **The Fable 5 retention constraint against Section 0 (Corrections, fifth omission; task 2's
   binding lines).** Fable 5 "requires 30-day retention and is unavailable under ZDR." The plan
   institutionalizes Fable for planning and review (line 10, the standing split, the "review
   with a different model" binding line), and dev sessions in this project routinely carry
   sensitive-tier persona data in context — persona files were modified in the working tree at
   review time. The question: does dev-environment Fable traffic carrying sensitive-tier data
   sit inside Section 0's ruling, whose testing amendment turns specifically on verified ZDR?
   To close, the document would have to state the data-handling terms the dev environment's
   Anthropic traffic runs under and whether Section 0 covers development sessions or only the
   runtime.

2. **Task 6's mapping source.** The hook corrects a spawn's model "against the table" — the
   document never states where the hook reads the table from. Task 1's document is prose in
   `~/.claude/`; a mapping hardcoded in the hook is a second home for the routing policy, the
   exact One Home Per Rule Class violation task 4 invokes to justify leaving `model` unset. To
   close, the document would have to name the machine-readable source and its update path at
   the 2026-12-01 re-check.

3. **Task 3's line enumeration.** "The model-recommendation lines" is never enumerated.
   § Plan Mode couples them to two rules with their own triggers: "Every plan includes a budget
   and a model recommendation" (the plan-approval checklist) and the 2026-08-29 rule that every
   ready-to-paste prompt carries a model line. Whether those move, stay, or split determines
   whether the approval checklist keeps its model item and whether the prompt rule keeps its
   triggering context — and the net-zero line arithmetic (194 against ~200) depends on the same
   unmade enumeration. To close, the document would have to list the lines that move and the
   lines that stay.

4. **Task 7's once-per-session mechanism.** A `UserPromptSubmit` hook runs as a fresh process
   per prompt; firing once per session requires either persisted state (which the Unseen bullet
   denies creating) or transcript inspection. The document states the behaviour and not the
   mechanism. To close, it would have to say how the hook knows it already fired.

5. **Task 8's `paths:` line.** Rule files inject on read of a matching path, and the
   docs-and-logs rule requires paths to be enumerated deliberately. A rule file "applied to no
   files" with no matching paths is never delivered to any session — the mandate test would be
   recorded where the delivery mechanism cannot surface it. To close, the document would have
   to state which paths the task-8 rule file declares, or name the mechanism by which it ever
   loads.

6. **"Current handling is `fallbacks: "default"` with beta header
   `server-side-fallback-2026-07-01`" (Corrections, first bullet).** Current handling *where*?
   This project's runtime fleet is Gemini on Vertex; no system named in the plan is identified
   as the one carrying this configuration. To close, the document would have to name the system
   whose handling this describes.
