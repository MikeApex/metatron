# SessionStart Hook Removal After Compliance Gap Found
**Date:** 2026-07-29
**Session type:** Tooling/config — follow-up test and rollback of the 2026-07-28 SessionStart hook

---

## Context

Continuation of [archive/sessions/2026-07-28 — SessionStart Context Hook and Troubleshoot Slash Command.md](2026-07-28 — SessionStart Context Hook and Troubleshoot Slash Command.md), which left "live hook firing not yet confirmed" as an open item.

## What was found

- Located the prior session via file search (user couldn't recall which chat built the hook).
- Traced a user-reported test ("what is the capital of France?" → "Paris.") through the raw JSONL logs across several session files to find the actual test run (`39e0775d-5f50-407c-b2e7-3a1650c69ac0`, 2026-07-29 11:24 UTC).
- **Confirmed the hook fired correctly**: `SessionStart:clear` hook attachment ran `session_context_primer.py` successfully (exit 0, 47ms), and its `additionalContext` — including the "MANDATORY... no exceptions" Read instruction — was correctly injected.
- **But the model didn't comply**: on the next turn, the assistant answered "Paris." directly with zero tool calls — no `Read` on `SESSION.md` or the roadmap, despite the instruction explicitly covering "even if the message looks basic... unrelated to code."
- Diagnosis: not a hook-plumbing bug. The model's own relevance judgment silently overrode the "no exceptions" procedural instruction for an obviously irrelevant question.

## Options considered

1. Reword the instruction to be epistemic rather than procedural — i.e., frame the project files as authoritative source of truth for the session (user's proposed test case: "if the docs said Berlin is the capital of France, answer Berlin") rather than a checklist step. Discussed as directionally stronger (harder to rationalize around) but risked over-scoping the model's epistemic stance beyond the project.
2. Revised draft narrowed the authority claim to project-specific facts only, to avoid coopting general common sense — user found even this iteration not worth the effort for the task's actual value.

## Decision: rollback

User concluded the tuning cycle wasn't worth it relative to just remembering to prompt for context manually when it matters. Rejected the reworded-instruction edit and instead had the whole mechanism removed:

- Removed the `SessionStart` hook block from `.claude/settings.local.json` (the `Stop` hook / `show_phase_progress.py` is untouched).
- Deleted `.claude/session_context_primer.py`.
- Both files are gitignored — no git history affected.

Going forward: no automatic context injection. Prompt explicitly ("read SESSION.md and the roadmap first") when a session's question is project-state-sensitive.

## Also covered this session

- Reconfirmed usage of `/metatron-troubleshoot <DATE> <SEQ> <ISSUE>` (built in the 2026-07-28 session) — no changes, just a refresher lookup.

## Follow-up: manual context-load slash command

After the hook rollback, user asked for a `/metatron-troubleshoot`-style shorthand instead of full manual prompting each time. Built `.claude/commands/metatron-code.md` — a user-triggered (not automatic) command: `/metatron-code` reads SESSION.md, resolves and reads the current roadmap from SESSION.md's own link, and optionally CODEBASE_INDEX.md if the task needs it. Functionally the same content the old hook injected, but triggered explicitly by the user each time rather than firing automatically — sidesteps the compliance-gap failure mode entirely since there's no competing relevance judgment on an unrelated turn; the user decides when it's needed.

## Open / deferred

- None carried forward — the hook experiment is closed and replaced with `/metatron-code`. If a case arises where even remembering to type the slash command is unreliable, the earlier epistemic-framing hook approach (option 1, further up) is the fallback design to revisit, not a from-scratch rebuild.
