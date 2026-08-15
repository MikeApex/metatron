### 2026-08-15 ([DB-0810-13] built and closed — and the provenance line immediately found a second, worse bug) — `0a3706c`, `cbe7d94`, `1831730`, `b2163fa`, **deployed**

Incoming handoff: `[DB-0810-13]` was diagnosed the session before, with the design committed at
`c0e2cd8` and a binding order — the Python half deploys before the `synthesizer.md` half is
written, or the Synthesizer starts declining to confirm things that genuinely happened.

**Half 1 — the Synthesizer now receives what actually ran.** `core/actions.py` classifies all 71
registered tools as actions or reads; `_action_block()` in `core/orchestrator.py` reads the trace
after dispatch and appends an `ACTIONS EXECUTED THIS REQUEST` block to the Synthesizer's input in
both pipeline paths. Same trust argument as the retrieval provenance line: Python generates it, so
it is evidence rather than a claim, and no model is asked whether an action happened.

**The real work was the classification, and the reason is documented at `core/trace.py:107-118`.**
A line listing `search_contacts` and `list_obligations` would repeat the `is_grounded()` mistake —
an agent that read the calendar has not changed it. One place, no per-agent knowledge.
`tests/test_action_provenance.py` fails if a registered tool is in neither set, so the next tool
added forces a classification instead of silently vanishing from the line. That test is the
control; the sets themselves are just data.

**Two scoping decisions, both departures from the committed design.** The design said attach per
specialist inside `_dispatch_from_coordinator`; Mike's instruction scoped it to the request,
because `pop_agent()` does not restore the previous `current_agent` (`[DB-0810-02]`) and
per-specialist attribution would be built on a known-broken path. So the block is built *after*
dispatch returns instead — which also excludes the fire-and-forget Diarist automatically, since it
runs on its own trace and is still running when the block is read. A line whose contents depended
on thread timing would not be evidence of anything.

**Rejected: filtering `ok=False` out.** An attempted-and-failed send is the Kathaleen case and is
more informative than silence. Failure means `ok=False` **or** a result beginning `"Error"` —
`dispatch_tool` sets `ok=False` only when it raises or the args will not bind, so a tool returning
its own error string still records `ok=True`. `_failed_tool_calls()` already made this distinction
and it was reused rather than re-derived.

**Verified live before half 2 was written**, which is what the ordering rule bought: `NONE` on a
request that changed nothing, `write_log — completed` twice, no reads on the line. Half 2 then
went into `synthesizer.md` § What you receive — absence stated first, confidentiality restated
inline because the natural way to obey the rule is to explain how you know. Post-deploy,
`write_calendar_event`, `update_calendar_event` and `close_obligation` all landed correctly and
**both actions were confirmed to Mike**, which is the evidence half 2 is not over-firing — the
specific risk the ordering rule existed to prevent.

**The line's first real find, within an hour: `[DB-0815-03]`.** Mike tapped Approve on a test
email; the reply said it was still waiting for approval; the line showed `write_log` alone with no
`send_email`. `tools/confirm.py` documents four steps and **step 4 has no trigger** — `POST
/confirm` only marks the record approved, and a grep of every consumer outside `confirm.py`
returns the two server endpoints and the four tools that *create* pending records. Nothing reads
an approved record back; it expires at the 600s TTL having done nothing. Every gated tool is
affected, not only email. Filed at `## Now` #2 with the proposed fix (execute server-side at
`/confirm`, which takes the model out of the execution path as well as the consent path) and the
rejected alternative (inject approved-pending actions into the next session's context — keeps the
current shape but still depends on the model choosing to re-call, and on the user sending another
message at all).

**A second find, unrelated and worse in kind:** the `[DB-0810-12]` probe shipped that morning was
interpolating the `AgentRecord` itself, whose repr carries `context_sections` — so its first live
firing wrote the entire assembled system prompt, constitution and persona config to `journalctl`
in plain text. Fixed to log the agent's name (`cbe7d94`); the probe still captured everything it
was built for (`pos=12:turn=1:src=stream_delta_fallback:tools=run_subagent`), which is the live
occurrence `[DB-0810-12]` had been waiting for. Mike captured seven days of warnings to the
MacBook and vacuumed the VM journal. **Journal cleanup is all-or-nothing** — `journalctl` deletes
only from the oldest end, so the newest entries cannot be removed without removing everything;
traces and conversations are files under `data/` and were unaffected.

**The commit guard produced its second false positive of the day.** Eight `## Now` headers were
renumbered with a `python3` one-liner rather than a tracked edit, so the guard read the file as
another writer's. The diff was checked line by line before overriding, and the override itself had
to be run by Mike — the permission classifier blocks `METATRON_COMMIT_GUARD=off` regardless of
authorisation. That is a second data point for `[DB-0815-01]`'s remaining half; a standing
permission rule was considered and rejected as treating the symptom.

Commits: `0a3706c` (Python half), `cbe7d94` (log leak), `1831730` (half 2), `b2163fa` (backlog).
All deployed and verified on the VM.

