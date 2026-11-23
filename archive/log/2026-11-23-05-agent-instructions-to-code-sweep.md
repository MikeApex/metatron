### 2026-11-23, fifth (where code should replace model judgment — a sweep of every agent instruction file, a Fable review, Mike's rulings, and a build driver held for the data-object project) — no code; **nothing deployed**

**Incoming handoff:** `archive/handoffs/2026-11-23-agent-instructions-to-code-sweep-prompt.md`.
This was strand (c) of "where should code replace model judgment" `[DB-0810-11]`, which had been
left without a home since Mark 2 ended on 11-18.

**Done:**
- Read all 24 `config/agents/*.md` and the three `synthesizer_*.md` modules in full, against the
  dispatch code and the live routing file.
- Findings: `archive/plans/agent_instructions_to_code_sweep_2026-11-23.md`. 25 moves to code
  (bins A–C) and 6 One Home contradictions, in four build clusters, with decisions D1–D9.
- Fable review: `archive/plans/agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md`.
  21 of 25 rows confirmed, 19 misses, four new decisions (D10–D13).
- Mike's rulings are recorded in § 6 of the sweep document.

**Believed true, wrong (caught by the review and checked against the code):**
- **The `read_goals` fix as first written would have deleted goals.** `write_goals` and
  `update_goal` read the raw file and write it back (`tools/goals.py:63`, `:162`, `:312`). The
  fix is to remove the grant from Work & Vocation and Finance; `tools/goals.py` stays as it is.
- **"Scheduled-turn events are about a third of the noise" was wrong.** Of ~170, ~130 are
  `ROUTING_MISS`, which the move keeps. The veto removes ~7% of the stream.
- **Wiring quick mode would have switched off the medication check.** Physical Health runs quick
  on 58 of 64 recorded calls, and quick mode skips the scan that holds the check.
- The sweep ran at **medium** effort (Mike). The document header's "high" is wrong.

**Rulings (Mike):**
- D1–D9 as recommended, with the review's amendments.
- `[DB-0810-11]` closed into the sweep document. `temperature` got its own inbox line.
- The rebuild notebook is to be retired.
- The "config files are the product" principle is to be amended in all three copies.
- Medication check (Mike's own wording): "clean while working as quickly as possible". It moves
  into code, runs in every mode and after the specialist returns; quick mode is wired only after
  it.
- D10: lift A4 for the C3 fixtures.
- D11: "medication taken today" is a default data object, being built in another chat.
- D12: estimate task lengths and update the estimates on evidence; ask only for an unknown task.
- D13: no forced Diarist until capture fidelity reports.

**Rejected:**
- A Red round per stage. Mike asked for two: one before any code, one after all of it.
- Deleting the quick-mode sections. They are kept, to be wired once the medication check is in
  code.

**Next:**
- `archive/handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md` (Opus 5.5, high).
  One driver chat runs Stages 0–5 up to commit and push; Mike approves two Red rounds and then
  deploys.
- **Held until the data-object project finishes.** The prompt's first step checks that the object
  is live.
- The review's 19 misses are not ruled and are not built.

**Also found:** `CLAUDE.md` trap 6 says only two agents are on the cached path. Eight
specialists have been on it since 08-28. The driver's Stage 0 corrects it.

