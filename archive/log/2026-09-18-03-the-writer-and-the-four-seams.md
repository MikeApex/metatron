### 2026-09-18, third (Build phase 3 — the writer, the four seams, and two gates that were inert)

Phase 3 of the Build vertical, executed from `archive/plans/build_vertical_plan_2026-09-18.md`
§ 16 as specified, no scope beyond it. **Build can now write, and what it writes is loadable and
verifiable.** Three new suites at 61 checks (writer 27, seams 19, verify+constitution 15), the
phase 1–2 suites unchanged at 117, `qa_sweep` now **11/11** — check 11 is new.
**Not committed: the implementation diff is on the working tree at Mike's instruction, for a
review pass. Not deployed** — phases 1–6 reach the VM as one deploy.

Incoming state was *"Next: Build phase 3 (writer + the four overlay seams; seam 2 is Red and is
not delegated)"*, with phase 6 established as a prerequisite for run 1 and Mike's § 15 rulings
binding phases 3–5. That is unchanged; phase 4 is next.

**What landed.** `core/build/writer.py` (the choke point: three path rules, the grant allowlist,
the ceiling, the undo journal), `core/build/overlay.py` (one loader, four seams),
`core/build/constitution.py`, `core/build/verify.py`, `scripts/check_build_registration.py`,
`config/modules/build.yaml`, an `overlay_capability/1` validator in `schemas.py`, `--overlay DIR`
on the three checks that could not see an overlay file, and check 11 in `qa_sweep.sh`. Seam 2
(`core/router.py`, Red) was written in the main session through the **Edit tool deliberately** —
a Bash heredoc would have edited the same bytes while bypassing the Red-tier permission prompt,
and saving a prompt is not worth defeating the control.

**Two gates were built to the spec and were inert or self-defeating. Both are corrections to the
plan, not to the code that implemented it.**

1. **The constitution gate made every valid agent file invalid.** Check (a) requires the
   canonical confidentiality clause *verbatim*; check (b) forbids architecture narration — and
   the clause contains the words "specialist sub-agent", which is exactly what
   `_ARCH_NARRATION_RES` matches. Every compliant file failed, and the only way to satisfy both
   would have been to ship an agent with no confidentiality clause: the one thing the module
   exists to prevent. The Confidentiality section is now excised before the narration scan.
   **Found by the first end-to-end run, not by reading the code** — which is the argument for
   the happy-path test existing before the refusal tests.

2. **Reusing `check_agent_tools.py`'s regex inherited its blind spot into a security gate.** The
   plan specifies the writer run *"the same regex `check_agent_tools.py` already runs"*, and that
   regex has a documented evidence gate: a tool name needs a call paren, a bullet lead, or an
   invocation verb *immediately* before it. So an agent file whose verb sits on the previous line
   names `send_email` invisibly. Tolerable on a tracked file, where an ungated version reported 34
   field names beside 1 real finding. Not tolerable here, because `allowed_tools` filters schemas
   while `dispatch_tool()` checks nothing — `logistics` called `write_agent_config` three times in
   production without the grant and the dispatcher executed each. **Scan 1 is kept** (so tracked
   semantics cannot drift) and **scan 2 added**, which drops the evidence gate and keys on a
   stronger fact instead: the token must be a name `register_tools()` actually registers. That is
   why it cannot reintroduce the false positives — `open_threads` and `precursor_by` are field
   names, not registered tools.

3. **A third gate could report but not fail.** `check_agent_tools.py` exits non-zero only on
   class 1 (named-but-not-built); class 2 (named-but-not-granted) is advisory, because on a
   tracked file the fix is a human adding the grant. A *generated* agent has no such human, so
   `--overlay` now makes class 2 fatal.

**Rejected, with the reason.** *Injecting generated names as a context block* (seam 3) — already
rejected in the plan and re-confirmed in code: it leaves the system prompt saying the name is
invalid and a context block saying it is valid, on a model whose own `_AGENT_NAME_MAP` comment
records it cannot reliably copy the existing list. The valid-name sentence is rewritten at prompt
assembly instead, in memory; `coordinator.md`'s sha256 is asserted unchanged. *Letting
`PersonaError` propagate from the overlay loader* — it would make a tracked agent's routing raise
where it does not today, a change to the Red-tier path rather than an inheritance; the write side
refuses instead, and the asymmetry is stated at both ends. *Setting `budget.per_job_usd` in the
new `build.yaml`* — it would silence `cost.budget_notice()` without answering it; the figure comes
from what run 1 costs.

**Carried, not a defect: generated capabilities inherit the accepted quick→bulk-tier reach.** A
record's `routing.cloud` entry carries no `local: true` (only `routing.local` does), and nothing
in `routing_cloud.yaml` is marked local — so `complexity: quick` reaches a generated capability
exactly as it reaches `mental_wellbeing`. That is the risk Mike reaffirmed on 2026-09-05, now
inherited rather than newly created. Recorded because the record's `local: true` reads like
protection it does not provide on the VM.

**Outside the plan, at Mike's request mid-session:** `~/.claude/show_usage.py` hardcoded
`CONTEXT_WINDOW = 200_000` and reported **95%** on a session running `opus[1m]` that had already
carried 236,769 tokens — past its own denominator, while reading as "about to compact". It now
resolves the window from the configured model (the only place the `[1m]` suffix survives; the
transcript records a bare `claude-opus-5`), cross-checks against observed usage, gates the
promotion on model family so a mid-session `/model` switch cannot under-report, and prints the
denominator: `19% of 1M`. Backup at `show_usage.py.bak-2026-09-18`.

**Owed:** the § 14 second-model review of phase 3 (Fable 5) — the one phase the plan singles out
for it, and not yet run. **Deployed: NO.** Commits: this close-out only; the phase 3 diff is
deliberately uncommitted.
