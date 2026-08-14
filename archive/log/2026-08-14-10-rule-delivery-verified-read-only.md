### 2026-08-14 (Phase 5: rule delivery verified, and it is Read-only) — **nothing retired, nothing deployed, hook not registered**

Phase 5 of the context-system plan, in the fresh session it required. The question Phases 2–3
could not answer about themselves — *does a path-scoped rule actually get delivered?* — is
answered yes, with one important qualification the plan did not anticipate. **No retirement was
performed and the `InstructionsLoaded` hook was not registered** (see *Deferred* below).

**Delivery works on Read, and only on Read.** Four measurements, all by direct observation of
what arrived in context rather than by instrumentation:

| Trigger | Rule delivered? |
|---|---|
| `Read` of a governed path | **Yes** — full file content, 3/3 (`SESSION.md`→`docs-and-logs`, `config/personas/pepys.md`→`personas`, `config/agents/logistics.md`→`agent-files`) |
| Bash `grep -rn` over a governed path, six real matches in two files | **No** |
| `Write` to a governed path, in a session that had never read that area | **No** — only the context-gate briefing's pointer |
| Worktree | rule files present on disk; hook briefing fires and names the governing file |

The grep result was the plan's stated load-bearing unknown. **The `Write` result was not in the
plan at all, and it generalises the finding past grep:** any session that surveys or edits an
area without opening a file in it gets the pointer and not the rules. Probed cleanly —
`orchestrator.md` was the one rule not yet loaded, so a `Write` to `core/` in a worktree was an
uncontaminated test; the briefing named `.claude/rules/orchestrator.md` and no rule content
followed.

**This retroactively promotes the context gate's always-present governing-rule pointer from
belt-and-braces to the primary control for edit-only and survey-only sessions.** Phase 1
correction 4 argued for that pointer on `/compact` grounds; the real case is broader. It also
weakens the argument for retiring anything, because retirement assumed rules reach the sessions
that need them.

**Two harness traps found while building, both of the fail-silently class.**

1. **`InstructionsLoaded` is a real hook event** — verified against the docs before writing it
   in, not assumed. It matches on *load reason* (`session_start`, `nested_traversal`,
   `path_glob_match`, `include`, `compact`), and the matcher may be omitted to catch all.
   Checked deliberately because this settings file already records the `defaultMode: "auto"`
   incident: a value the parser accepted and then silently never honoured. The event-specific
   payload fields are **not** documented, which is why the logger records the whole payload —
   an instrument that guesses a key name reports "no data" for a working mechanism.
2. **`.claude/settings.json` accepts `_comment_*` keys only inside `permissions`.** Two edits
   were rejected by the settings validator and rolled back: one adding a comment key under
   `hooks` (its `propertyNames` are an enum of event names), one at the root (rejected despite
   the published schema showing `additionalProperties: {}` — the CLI validator is stricter than
   the schema it publishes). The existing file's heavy `_comment_allow` / `_comment_deny` /
   `_comment_ask` convention makes this an easy trap to walk into, since those all sit inside
   `permissions` and look like a general house style. **Rationale for a hook therefore has to
   live in the hook script's own header, not beside its registration.** The validator caught
   both attempts and reverted them, so nothing landed half-applied.

**What could not be tested, and why it needs a different session.** Three gaps, all the same
shape as the one that forced Phase 5 out of the building session:

- **The Grep *tool*** — unavailable in this session (`ToolSearch` returns nothing for
  Grep/Glob), so only the Bash-grep proxy could be run. `/backlog attack` workers and Explore
  agents survey with the Grep tool. Given `Write` also fails to deliver, the expectation is that
  Grep does not either, but that is inference, not measurement.
- **Rule delivery inside a worktree session** — `.claude/rules/` is discovered at session start,
  so this needs a session actually started in the worktree. Only file presence and hook
  behaviour could be confirmed from the main tree.
- **`/context`** — a CLI built-in, not invocable by a model.

**Deferred, deliberately.** `scripts/hook_instructions_loaded.py` is committed but **not
registered** in `.claude/settings.json`, and `scripts/audit_context_load.py`'s
`EXPECTED`/`CONDITIONAL`/`SUPERSEDED` tables at lines 34-49 still describe the pre-split
architecture. Both were in scope and both are small; Mike's call was to stop rather than rush
the close-out, with the findings recorded first. The script carries its retirement condition in
its own header, per the standing rule in `.claude/rules/deploy.md` that no new hook lands
without naming what retires it — it exists only to answer the two open questions above and is
deleted once they are answered.

**Retirement held.** `CODEBASE_INDEX.md` was the candidate. It is already conditional in
`/metatron-code`, so the saving was always small, and the `Write` finding removes the premise
that rules reliably substitute for it. Its one unique row (agent enhancement backlogs) has still
not moved to `.claude/rules/agent-files.md`, which remains the prerequisite for any later
attempt.

**Phase 4 (the ROADMAP split) was not started**, as the prompt directed. Nothing depends on it
and A7 is the blocked product gate.
