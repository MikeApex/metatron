### 2026-10-24, fourth (the task ledger meets real use; replies stop hanging and stop coming back blank) — `1d824a9`, `c183060`, `e5f3dad`, `4f88d19`, `1d32c4c` — **all deployed by Mike in-session; APK rebuilt and sideloaded**

**Incoming handoff:** `archive/handoffs/2026-10-24-task-ledger-post-deploy-prompt.md` — verify the
ledger's deploy, APK, the recurring-tasks setup prompt, live checks, two decisions.

**The ledger checked out.** `tasks.yaml` imported at the first 00:15 sweep (44 records, not 43 —
the 10-23 Apex re-date ran on old code as close + new record, so the old Apex reads "done");
`obligations.yaml` untouched since 22:15 10-23. Live checks: raise-once, tap (deadline and habit,
twice-daily), spoken completion (plants, "it's raining") and the stale-copy annotation all PASS.
Ambiguous completion **failed** — "I sorted the finance stuff" closed the Schwab review, one of
four finance tasks, none named; Mike reverted it — and passed after the gate below.

**The bigger finding: replies hung and came back blank.** 11:45 a Synthesizer call waited 586 s
(no model client had a timeout anywhere); 12:06 a reply came back blank after 9 min 14 s — eight
rounds of tool calls (`list_tasks` ×3, re-filing what specialists had filed), then the loop fell
through with `result=""`. Measured: tools took 0.64 s of it. Vertex's median speed is unchanged
all month (~8 s per 1k generated tokens); the tail is not (stalls ~0.4% → ~2.5% since 10-20). A
Mac A/B (same prompt, same minutes): Vertex `global` 3 failures + 3 waits >50 s in 14, Developer
API 14/14 in 4–6 s. WebSearch (deny lifted for one search, restored): a 10-21 forum report of the
same symptom; Google's DSQ doc says a 429 is shared load, not a project limit. **Not our account.**

**Built (plan `archive/plans/reply_latency_plan_2026-10-24.md`, Fable 5.1, four review rounds):**
75 s Synthesizer timeout (the month's P99 — Mike's rule) and 300 s elsewhere; one per-ROUND retry
on capacity errors; rounds capped at 4; a 150 s soft deadline; a tools-off final round and a
fixed line, so no turn is blank; `synthesizer.md` batches calls and stops re-reading what it has.
It fired live at 15:03 — a stalled round cut at 75 s and retried. Then: waking-day Today list,
`list_tasks(horizon=)`, "Done, but…" (`done_with_followup`), Drop with a reason, task durations
(stated/estimated, Mike's request), a dated future event no longer marked as a done task's copy,
**a code gate: a model may close a task only when the user's words name it** (Fable chose it over
a bulk-model check), and `write_log`'s description forbids logging a guessed completion.

**Rejected, with reasons:** a hard 180 s turn ceiling (abandoning a running turn writes into the
next one — no per-persona lock; no path for the late reply to the asking phone); delivering the
reply before its writes run (confirm-gated tools return PENDING_CONFIRMATION, the truth check
keys on tool names, `done` closes the bubble); a wrapper-level retry (re-runs earlier rounds'
tools — today's compat fallback had that latent defect, now gated on "nothing dispatched").

**Believed true and wasn't:** "Vertex got slower since 10-23" (the agent's first read) — the
median didn't move, the tail did. "Change (a) is deployed" — it was uncommitted, and `deploy.sh`
ships git. Mike's decisions: fallback = retry only; thinking-budget test = its own session.

**Late additions, same session (`75ad88b`):** the medication safety flag now sits in `ROADMAP.md`
§ 0 clause 8's before-Alpha note; `check_inbox_6h` became a dated backlog check (10-31). The
Franklin virtue review that kept returning is an **ability** gap, not adherence — the ritual file
is injected every evening close and no tool can change it; Mike declined pausing it by hand for
now and asked for a user-requestable pause with limited scope (pause/resume only, the user's words
only). Drafted as untracked `tools/rituals.py`, not wired; carried to
`archive/handoffs/2026-10-25-ritual-pause-and-ledger-followups-prompt.md`. Mike ruled that editing
a day-log entry in conversation should not exist for users; he corrected today's false "Schwab
sorted" log line himself (Claude's VM write was blocked by the auto-mode remote-write guard).

