# Handoff — Accountability Index [DB-0827-09] build outcome (2026-08-28)

*From the Green/Amber spinoff chat (Fable review, Sonnet worker). Merged `c082fb6`. VM deploy
owed (Mike) — `tools/accountability.py`, `tools/analytics.py` both run on the VM.*

## What landed (Green, merged)

The index now answers "which stated intentions actually happened" for the checkable half,
deterministically in code — no model call:

- **[tools/accountability.py](../../tools/accountability.py)** — reads Diarist-logged intentions
  (`intention` + optional `stated_for` in the day logs), joins them against calendar events
  occurred (CalDAV title match) and obligations closed (`what` match). Windows per the decided
  design: `stated_for`+2d grace when parseable, 7d default when undated; trailing-30d
  fulfilment rate that **excludes indeterminate from the denominator** (not evidence either
  way). Verdicts never forced: no structured match → `indeterminate` with a reason
  ("window still open" / "awaiting judgment gate").
- **A9 rollup** — four content-free counts per daily row (`intentions_stated`,
  `intentions_resolved_{fulfilled,unfulfilled,indeterminate}`), wrapped so a failure cannot
  take down the analytics row. The nightly path joins **obligations only** (no CalDAV network
  call from the unattended daemon) — a documented undercount vs. the full CLI report.
- **CLI:** `python3 -m tools.accountability --report` (or `--json`, `--persona`, `--days`).
- Tests: `tests/test_accountability.py` 11/11; analytics regression 9/9.

## Red-tier proposal — NOT built, for the next Red/agent-file session

1. **Judgment-gate agent file** (`config/agents/accountability_judge.md`, `intake_extractor`
   pattern, empty grant): classifies one structurally-indeterminate intention against the
   window's journal/event text → `{"verdict": "...", "reason": "..."}`; `indeterminate` is a
   correct answer; never re-litigates a code-resolved verdict; runs nightly over yesterday's
   post-join leftovers only.
2. **⚠ Routing tier needs a check before this is built:** journal text is Sensitive tier, so
   "Flash-Lite nightly" is only valid on the ZDR-VM basis (Amendment 2026-08-28) — the routing
   entry should say so explicitly. Flagged by the worker, not decided.
3. **Scheduler job line** for `_DEFAULT_JOBS` (Red, `core/scheduler.py`):
   `daily_accountability_judgment_gate` at 05:45 (after the 05:40 analytics rollup), function
   `tools.accountability.run_judgment_gate` (not yet written — lands with the gate).
4. **Weekly retrospective wording** (Synthesizer/retrospective agent text): "six set out, four
   done", naming the open ones; unfulfilled intentions feed `[DB-0809-02]`'s what-to-do-NOW
   opportunistic surfacing, not nagging.

## Discovered gap, decision-shaped — filed here, not fixed

`write_log`'s `_deep_merge` replaces scalar top-level keys, so **a second intention logged the
same calendar day silently overwrites the first**. Fixing it means the Diarist writes a list —
a change to the collection shape (agent file + logger), Mike's call which home takes it.

## Close-out notes

- **`[DB-0828-01]` (verdict audit): at this build's deploy, set its `due:` to deploy date
  + 10 days** — per the item's own @waiting instruction.
- Confirmation suggestion: after deploy, one run of
  `python3 -m tools.accountability --report --persona mike` on the VM; pass = the table renders
  with real intentions and no crash on the live CalDAV path.
