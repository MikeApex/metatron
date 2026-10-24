# Ritual pause build + task-ledger follow-ups (launch prompt)

Model: Opus 5.5. Build work with one Red-tier grant and an agent-file line; Fable 5.1 reviews the
diff before commit (the pattern that caught nine defects in the 10-24 reply-latency build).

**Budget:** ~45–75 Mike-minutes; ~1–2M Opus tokens on the subscription (mostly cache reads) plus
one Fable review pass (~0.3–0.5M). Run-cost delta: zero — three tools, no new model calls, one
small YAML file per persona.

**Why this session exists:** on 2026-10-24 Mike found the Franklin virtue review keeps returning
to the evening check-in although he has asked several times to drop it "for the time being".
Diagnosis (verified on the VM): an **ability** gap, not adherence —
`config/personas/mike/evening_ritual.md` is injected by `core/orchestrator.py` `_owned_rituals()`
into every evening close and no tool can change that, so each request was agreed to in one reply
and gone the next night. The same file carries the morning catch-up clause. Mike: build a pause
Metatron can set on request, but **"ensure users have limited scope to change things that they
otherwise didn't initiate and that Metatron did."**

---

/metatron-code Ritual pause build, Mike present. Read first: `archive/PROJECT_LOG.md` § 2026-10-24,
fourth (what the previous session built and why); `archive/plans/reply_latency_plan_2026-10-24.md`
§ 12–12a (the close gate — its turn fields `close_gate` / `user_turn` / `user_text` are what the
pause's "only the user's words" rule reuses); `tools/rituals.py` (an **untracked, untested draft**
from 10-24 — review it, do not trust it).

1. **Build the ritual pause.** Scope rules, all three binding (Mike's limited-scope instruction):
   - pause and resume only — no tool edits, rewrites or deletes a ritual file; a pause is a
     separate record (`data/personas/{p}/ritual_pauses.yaml`), so resuming restores it exactly;
   - only on a user turn with the user's words as evidence — refused on scheduled turns (reuse
     the close gate's turn fields; no bound turn = direct call, allowed);
   - only rituals that exist (`X_ritual.md` → id `X`; unknown ids refused with the real list).
   Wiring: `_owned_rituals()` skips paused ids (pass the persona's paused set in from
   `load_config`); register `pause_ritual` / `resume_ritual` / `list_rituals` in
   `register_tools()`; classify them in `core/actions.py` (two actions, one read —
   `tests/test_action_provenance.py` fails otherwise); **Red:** grant all three to `synthesizer`
   in both `config/modules/routing*.yaml`, and one line in `config/agents/synthesizer.md` § Tools
   ("when the user asks to drop or skip part of a check-in for a while, pause_ritual — never
   promise to skip it without calling it"). Run `scripts/check_agent_tools.py`.
   Tests (synthetic persona, live meters stubbed): pause hides the evening ritual from an
   `evening_close` config and leaves `manny_school_ritual` alone; resume restores it byte-
   identical; a scheduled turn's pause is refused; unknown id refused; the ritual file is
   unmodified after pause/resume. Then a Fable 5.1 review of the diff; resolve to agreement;
   commit only this session's files (another window often has uncommitted work — `git diff`
   each file); Mike deploys.
   **Live check with Mike:** he says "drop the virtue review for now" → trace shows
   `pause_ritual("evening", …)`; that evening's close carries no virtue list; the next morning
   offers no catch-up. **Do not pause it on his behalf** — he chose not to on 10-24 ("I don't
   want to mess with the morning ritual yet"); the build only makes his request stick when he
   makes it.

2. **Verify what 10-24 left in flight** (each from a trace or a VM file, read-only):
   a. Mike's day-log correction landed: `data/personas/mike/logs/2026-10-24.json`
      `finance.investment_notes` is null.
   b. **Task durations** (`e5f3dad`): at least one task now carries `minutes` with
      `minutes_source: stated` after Metatron asked; no estimate overwrote a stated figure.
   c. **Round count:** recent user turns' Synthesizer rounds — 10-24 the merge turn still made
      one redundant `list_tasks` call. If that pattern holds across a day, propose the wording
      fix; do not edit without Mike.
   d. **Close gate** (`4f88d19`): any `error: not recorded` refusal in traces since deploy —
      read each; a legitimate completion refused is the known paraphrase limit (plan § 12.3);
      report the rate.

3. **Dated items already in `DEV_BACKLOG.md` — work any that are due, leave the rest:** sweep's
   first habit rows (10-25), plants due (10-27), Vertex stall re-check and the `check_inbox_6h`
   redundancy check (10-31), gym adherence (11-02), correspondence suggestion (11-07). Undated,
   each its own session: the Synthesizer thinking-budget A/B; the user-adjustable day boundary
   (plan § 6.4); and plan § 5.3 (measure post-reply bookkeeping before moving it) — not built.

4. **Housekeeping:** Mike deletes the 10-24 session scratchpad if he has not
   (`rm -rf /private/tmp/claude-501/-Users-md-homefolder-Desktop-multi-model-mcp/4f51124c-ac8f-415c-a800-6240d8d6e191/scratchpad`
   — `rm -rf` is Denied to Claude here).

Close with `/archive`. Anything that did not pass is a backlog item with the evidence that failed.
