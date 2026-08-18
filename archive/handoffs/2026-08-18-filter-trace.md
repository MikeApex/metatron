# Handoff — 2026-08-18, worker `wt/filter-trace`

**Shipped.** Two user-visible defects closed. (1) The Book no longer misattributes tool calls made
after a nested subagent returns — `push_agent()` now records the agent that was current at push
time and `pop_agent()` restores it. (2) A complaint that names a tool now gets a real answer:
`filter_output()` takes the user's own turn and exempts, **in tier 1 only, per term, for that one
turn**, an identifier the user typed first. Tiers 2–4 are untouched, so a probing question still
gets nothing — any answer to *"what does `write_config` do?"* trips architecture narration or the
sentence-level gate. `user_text` defaults to `None`, which reproduces the old behaviour exactly.

**Files:** `core/trace.py`, `core/orchestrator.py`, new `tests/test_trace_agent_stack.py` (11
checks) and `tests/test_filter_user_echo.py` (20 checks), plus a one-line anchor fix in
`tests/test_context_user_text_plumbing.py` whose source-inspection count read 4 once the same
`is_proactive` guard appeared at the filter call sites.

**Commit:** see `git log` on `wt/filter-trace` — one commit, "Restore the parent agent on pop, and
let a complaint name a tool".

**Two deliberate deviations from the brief, both worth reading.**

1. **The four "workarounds" are not workarounds and were kept.**
   `core/orchestrator.py:1697/1811/2700/3660` capture `_parent_agent` and call
   `_tr._set_current_agent(_parent_agent)` *inside the worker closure*, not after dispatch returns.
   They seed a **new thread's** empty thread-local from the parent. `pop_agent()` cannot do that —
   thread-locals do not cross threads — so removing them would silently drop every parallel
   specialist and parallel tool call from the trace again, which is the bug `3660`'s own comment
   says it was added to fix. The brief's premise that they became redundant is wrong.
2. **`push_agent()` keeps its existing return type.** The brief specified returning the previous
   agent for `pop_agent()` to take back; both existing callers *do* use the return value
   (`_agent_rec = push_agent(...)` → `pop_agent(_agent_rec)`), so a tuple return would have churned
   them. The parent is stored on the `AgentRecord` instead: whatever record you pop restores
   whatever was current when that same record was pushed, so the two cannot desynchronise. The
   field is `repr=False, compare=False` and is not serialised — asserted in the new test.

**Backlog — close these, with this evidence.**

- **`[DB-0810-02]`** — close. `tests/test_trace_agent_stack.py` covers nested restore, three-deep
  unwind, restore-after-exception, correct attribution of a tool call made after a subagent
  returns, and that the parent link never reaches the trace file. 11/11.
- **`[DB-0808-05]`** — close. `tests/test_filter_user_echo.py` reproduces Exchange 027 and asserts
  the reply survives, plus six checks that the prober path still fails. 20/20.

**Three items to file (all outside this manifest, none touched).**

1. **`tests/run_b1_redteam.py:423` — promote `FILTER-EXCH027` from `INFO` to gated.** It still calls
   `filter_output(exch027, "synthesizer")` with no `user_text`, so it still reports "still
   suppressed"; it needs the user turn passed and the expectation inverted.
2. **`core/actions.py:28-30`** — its docstring declines per-agent attribution "until [DB-0810-02] is
   fixed". The blocker is gone. Request scope now rests on Mike's 2026-08-15 decision alone;
   widening it is a product question for him, not a repair. (`_action_block()`'s docstring in
   `core/orchestrator.py` already says this.)
3. **Pre-existing failure, not mine:** `tests/test_action_provenance.py` is 9/10 —
   `fetch_rendered`, `import_contacts_file` and `merge_contacts` are registered but classified in
   neither `ACTION_TOOLS` nor `READ_TOOLS` in `core/actions.py`. Confirmed against a stashed tree.
   A state-changing tool can currently run without appearing on the ACTIONS line — that is exactly
   the `[DB-0810-13]` failure the test was built to prevent.

**Tested.** `py_compile` on both files. Run and passing: the two new suites, plus
`run_b1_redteam.py --suite filter` (**88 checks, GATE: PASS** — the brief said 86; the list has
grown), `test_instruction_leak_filter.py` (12/12), `test_translate_output.py`,
`test_context_user_text_plumbing.py`, `test_analytics_rollup.py`, `test_context_block_repair.py`,
`test_commit_guard.py`, `test_clinical_threads.py`. **Not exercised — needs a live model:** the
`disclosure` suite (15/15) and the `deputy` suite; both call `run_pipeline_session()`. The three
filter call sites and the trace fix are all on the live pipeline path, so **disclosure must be
re-run before this deploys.**

**For `SESSION.md`.** Not deployed. `core/` changed, so this needs `./deploy.sh` to reach the VM.
Two backlog items close; `FILTER-EXCH027` promotion and the `core/actions.py` classification gap
are the two follow-ups.
